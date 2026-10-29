"""Propuesta inerte → reserva real → intención durable → creación exclusiva.

Linux/POSIX, biblioteca estándar. Configuración del supervisor, nunca del modelo.
Un estado dedicado y un escritor: CLI/Claude no deben usarlo simultáneamente.
No hay atomicidad entre publicar un fichero y persistir el recibo posterior.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from nucleo import contrato, evidencia, puerta

LIMITE = 16384
RESPUESTA_MAX = 8192
EVENTO = 'codex-ejecutor'
TERMINALES = {'aplicada', 'rechazada', 'reconciliada'}
FUENTES = Path(__file__).resolve().parents[3]


class Rechazo(ValueError):
    """No hay permiso para aplicar."""


class Incierto(RuntimeError):
    """Detener y reconciliar; nunca reintentar automáticamente."""


def canon(objeto):
    return json.dumps(objeto, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def huella(datos):
    return hashlib.sha256(datos).hexdigest()


def _pares(pares):
    objeto = {}
    for k, v in pares:
        if k in objeto:
            raise Rechazo('clave JSON repetida')
        objeto[k] = v
    return objeto


def cargar(datos):
    try:
        return json.loads(datos, object_pairs_hook=_pares,
                          parse_constant=lambda _: (_ for _ in ()).throw(Rechazo('constante JSON')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Rechazo('JSON inválido') from exc


def ruta_relativa(ruta):
    if (not isinstance(ruta, str) or not ruta or len(ruta) > 240
            or any(c in ruta for c in '\\\x00\n\r')
            or any(p in ('', '.', '..') for p in ruta.split('/'))):
        raise Rechazo('ruta no relativa canónica')
    return ruta


def propuesta(datos):
    if not isinstance(datos, bytes) or len(datos) > LIMITE:
        raise Rechazo('propuesta excesiva o no binaria')
    p = cargar(datos)
    if not isinstance(p, dict) or set(p) != {'version', 'id', 'tipo', 'ruta', 'contenido'}:
        raise Rechazo('esquema desconocido')
    if type(p['version']) is not int or p['version'] != 1 or p['tipo'] != 'crear':
        raise Rechazo('operación no implementada')
    if not isinstance(p['id'], str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', p['id']):
        raise Rechazo('identificador inválido')
    ruta_relativa(p['ruta'])
    if not isinstance(p['contenido'], str):
        raise Rechazo('contenido no textual')
    try:
        canon(p)
    except UnicodeError as exc:
        raise Rechazo('Unicode inválido') from exc
    return p


@contextmanager
def estado_nativo(estado):
    """API nativa basada en entorno; uso serial, se restaura incluso ante fallo."""
    previo = os.environ.get('YEMA_ESTADO')
    os.environ['YEMA_ESTADO'] = str(estado)
    try:
        yield
    finally:
        if previo is None:
            os.environ.pop('YEMA_ESTADO', None)
        else:
            os.environ['YEMA_ESTADO'] = previo


@dataclass(frozen=True)
class Configuracion:
    yema: Path
    estado: Path
    trabajo: Path

    def __post_init__(self):
        for nombre in ('yema', 'estado', 'trabajo'):
            p = Path(getattr(self, nombre))
            if not p.is_absolute() or p != p.resolve(strict=True) or not p.is_dir():
                raise Rechazo('se exige configuración absoluta, existente y sin enlaces')
            object.__setattr__(self, nombre, p)
        if (self.estado == self.trabajo or self.trabajo in self.estado.parents
                or self.estado in self.trabajo.parents):
            raise Rechazo('el estado debe estar separado del workspace')

    def vinculo(self, *, cid=None, vigente=True):
        pol = puerta._politica(self.yema)
        if vigente:
            with estado_nativo(self.estado):
                c, _ = puerta.activo(self.yema, pol, datetime.now(timezone.utc))
        else:
            if not isinstance(cid, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', cid):
                raise Rechazo('identificador de observación inválido')
            c = contrato.cargar(self.estado / 'contratos' / (cid + '.json'))
            if c.get('id') != cid:
                raise Incierto('contrato histórico incoherente')
        if not c or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', c['id']):
            raise Rechazo('se exige un contrato activo válido')
        if Path(c['ambito']['raiz']).resolve() != self.trabajo:
            raise Rechazo('el workspace no coincide con el contrato')
        return {'contrato': c['id'], 'version': c['version'], 'huella': contrato.huella(c),
                'contrato_sha256': huella(canon(c)), 'politica': puerta.huella_politica(pol)}

    def orden(self):
        return [sys.executable, '-B', '-m', 'adaptadores.codex.ejecutor.puente',
                '--yema', str(self.yema), '--estado', str(self.estado), '--trabajo', str(self.trabajo)]


def verificar(datos):
    if datos and not datos.endswith(b'\n'):
        raise Incierto('evidencia incompleta')
    prev, registros = evidencia.GENESIS, []
    try:
        for linea in datos.splitlines():
            r = cargar(linea)
            cuerpo = {k: v for k, v in r.items() if k != 'hash'}
            if r['prev'] != prev or r['hash'] != evidencia._hash(prev, cuerpo):
                raise Incierto('evidencia alterada')
            prev = r['hash']
            registros.append(r)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise Incierto('evidencia inválida') from exc
    return registros


def sincronizar(ruta):
    fd = os.open(ruta, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    fd = os.open(Path(ruta).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def historias(cfg):
    """El bloqueo de pendientes y la integridad abarcan todos los contratos."""
    registros = []
    for ruta in sorted((cfg.estado / 'evidencia').glob('*.jsonl')):
        fd = os.open(ruta, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as f:
            st = os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                raise Incierto('diario histórico no regular o enlazado')
            registros.extend(verificar(f.read()))
    return registros


class Diario:
    """Cadena común, append durable y bloqueo exclusivo del estado dedicado."""
    def __init__(self, cfg, pendientes=False, cid=None):
        self.cfg, self.pendientes, self.cid = cfg, pendientes, cid
        self.cerrojo = self.fd = None

    def __enter__(self):
        try:
            self.cerrojo = os.open(self.cfg.estado / '.codex-ejecutor.lock',
                                   os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            fcntl.flock(self.cerrojo, fcntl.LOCK_EX | fcntl.LOCK_NB)
            todas = historias(self.cfg)
            ultimas = {(r['contrato'], r['id']): r for r in todas if r.get('evento') == EVENTO}
            if not self.pendientes and any(r['fase'] not in TERMINALES for r in ultimas.values()):
                raise Incierto('propuesta pendiente en el estado; reconciliar')
            self.vinculo = self.cfg.vinculo(cid=self.cid, vigente=not self.pendientes)
            self.ruta = self.cfg.estado / 'evidencia' / (self.vinculo['contrato'] + '.jsonl')
            self.fd = os.open(self.ruta, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            st = os.fstat(self.fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                raise Incierto('diario no regular o enlazado')
            self.recargar()
            self.ultimas = {r['id']: r for r in self.registros if r.get('evento') == EVENTO}
            if self.pendientes and any(r.get('huella') != self.vinculo['huella'] for r in self.ultimas.values()):
                raise Incierto('material del contrato histórico cambiado; inspección humana')
            return self
        except BaseException as exc:
            self.__exit__()
            if isinstance(exc, OSError):
                raise Incierto('estado ocupado o evidencia no disponible') from exc
            raise

    def __exit__(self, *_):
        for nombre in ('fd', 'cerrojo'):
            fd = getattr(self, nombre)
            if fd is not None:
                os.close(fd)
                setattr(self, nombre, None)

    def recargar(self):
        with os.fdopen(os.dup(self.fd), 'rb') as f:
            f.seek(0)
            self.registros = verificar(f.read())
        if os.stat(self.ruta, follow_symlinks=False).st_ino != os.fstat(self.fd).st_ino:
            raise Incierto('diario reemplazado')

    def anotar(self, p, fase, **datos):
        self.recargar()
        evidencia.anotar(self.ruta, {'evento': EVENTO, 'id': p['id'], 'fase': fase,
            'efecto_sha256': huella(canon(p)), **self.vinculo, **datos})
        sincronizar(self.ruta)
        self.recargar()


def matar(proceso):
    try:
        os.killpg(proceso.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proceso.wait()


def proceso_acotado(orden, entrada, timeout, limite, *, env=None, cwd=None):
    """Canal stdin/stdout acotado; mata descendientes también al recibir EOF."""
    fin, proceso = time.monotonic() + timeout, None
    try:
        with tempfile.TemporaryFile() as f:
            f.write(entrada)
            f.seek(0)
            proceso = subprocess.Popen(orden, stdin=f, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True, env=env, cwd=cwd)
            salida = bytearray()
            with selectors.DefaultSelector() as selector:
                selector.register(proceso.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    restante = fin - time.monotonic()
                    if restante <= 0 or not selector.select(restante):
                        raise Rechazo('timeout del proceso')
                    bloque = os.read(proceso.stdout.fileno(), min(limite + 1, 65536))
                    if not bloque:
                        selector.unregister(proceso.stdout)
                    salida.extend(bloque)
                    if len(salida) > limite:
                        raise Rechazo('salida excesiva')
            rc = proceso.wait(timeout=max(0, fin - time.monotonic()))
            return rc, bytes(salida)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Rechazo('proceso ausente, fallido o agotado') from exc
    finally:
        if proceso is not None:
            matar(proceso)
            proceso.stdout.close()


def consultar(orden, peticion, timeout):
    env = {**os.environ, 'PYTHONPATH': str(FUENTES), 'PYTHONDONTWRITEBYTECODE': '1'}
    rc, salida = proceso_acotado(orden, canon(peticion), timeout, RESPUESTA_MAX, env=env, cwd=FUENTES)
    r = cargar(salida)
    if (rc != 0 or not isinstance(r, dict) or set(r) != {
            'version', 'nonce', 'efecto_sha256', 'decision', 'vinculo', 'reserva'}
            or type(r['version']) is not int or r['version'] != 1
            or r['nonce'] != peticion['nonce'] or r['efecto_sha256'] != peticion['efecto_sha256']
            or r['vinculo'] != peticion['vinculo'] or r['decision'] != 'allow'
            or not isinstance(r['reserva'], str) or not re.fullmatch('[0-9a-f]{64}', r['reserva'])):
        raise Rechazo('sin permiso explícito ligado a la propuesta')
    return r


def directorio(raiz, ruta):
    """Abre cada componente, incluidos ancestros absolutos, sin seguir enlaces."""
    ruta_relativa(ruta)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for parte in [*Path(raiz).parts[1:], *ruta.split('/')[:-1]]:
            hijo = os.open(parte, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = hijo
        return fd, ruta.split('/')[-1]
    except OSError as exc:
        os.close(fd)
        raise Rechazo('directorio no disponible o enlazado') from exc
    except BaseException:
        os.close(fd)
        raise


def destino(raiz, ruta):
    fd, nombre = directorio(raiz, ruta)
    try:
        try:
            os.stat(nombre, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return fd, nombre
        raise Rechazo('crear exige destino ausente')
    except BaseException:
        os.close(fd)
        raise


def crear(fd, nombre, contenido, fin, revalidar):
    temporal = '.yema-' + uuid.uuid4().hex
    tmp = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        with os.fdopen(tmp, 'wb') as f:
            f.write(contenido)
            f.flush()
            os.fsync(f.fileno())
        revalidar()
        if time.monotonic() >= fin:
            raise Rechazo('plazo agotado antes de publicar')
        os.link(temporal, nombre, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        os.fsync(fd)
    finally:
        os.unlink(temporal, dir_fd=fd)
        os.fsync(fd)


def ejecutar(datos, cfg, *, orden=None, timeout=2.0):
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise Rechazo('plazo inválido')
    fin = time.monotonic() + timeout
    with Diario(cfg) as diario:
        try:
            p = propuesta(datos)
        except Rechazo:
            diario.anotar({'id': uuid.uuid4().hex}, 'rechazada', entrada_sha256=huella(datos))
            return 'rechazada'
        if p['id'] in diario.ultimas:
            raise Rechazo('identificador ya consumido')
        diario.anotar(p, 'propuesta')
        fd = None
        try:
            fd, nombre = destino(cfg.trabajo, p['ruta'])
            # El adaptador y sus fuentes también son gobierno, fuera del núcleo.
            real = cfg.trabajo / p['ruta']
            for protegida in (FUENTES / 'adaptadores/codex', FUENTES / '.codex', FUENTES / 'bin/yema-sesion-codex'):
                if real == protegida or protegida in real.parents:
                    raise Rechazo('adaptador protegido')
            peticion = {'version': 1, 'nonce': uuid.uuid4().hex, 'propuesta': p,
                        'efecto_sha256': huella(canon(p)), 'vinculo': diario.vinculo}
            permiso = consultar(cfg.orden() if orden is None else orden, peticion, max(0, fin - time.monotonic()))
            diario.recargar()
            reserva = diario.registros[-1]
            if (reserva.get('hash') != permiso['reserva'] or reserva.get('permitido') is not True
                    or reserva.get('herramienta') != 'Write' or reserva.get('efecto') != 'escribir'
                    or reserva.get('contrato') != diario.vinculo['contrato']):
                raise Rechazo('reserva real ausente')

            def revalidar():
                if cfg.vinculo() != diario.vinculo:
                    raise Rechazo('contrato o política cambiados')
                actual, _ = directorio(cfg.trabajo, p['ruta'])
                try:
                    a, b = os.fstat(actual), os.fstat(fd)
                    if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
                        raise Rechazo('directorio reemplazado')
                finally:
                    os.close(actual)
                if time.monotonic() >= fin:
                    raise Rechazo('plazo del ejecutor agotado')

            revalidar()
            diario.anotar(p, 'autorizada', reserva=reserva['hash'])
            diario.anotar(p, 'intencion', ruta=p['ruta'], contenido_sha256=huella(p['contenido'].encode()))
            crear(fd, nombre, p['contenido'].encode(), fin, revalidar)
            diario.anotar(p, 'aplicada', contenido_sha256=huella(p['contenido'].encode()))
            return 'aplicada'
        except Rechazo:
            diario.anotar(p, 'rechazada')
            return 'rechazada'
        except Exception as exc:
            # También cubre un fallo posterior a link: no afirmar que no escribió.
            raise Incierto('operación sin resultado durable; reconciliar') from exc
        finally:
            if fd is not None:
                os.close(fd)


def reconciliar(cfg):
    """Observa pendientes sin repetir ni reembolsar efectos; conflicto detiene."""
    resultados = []
    todas = historias(cfg)
    ultimas = {(r['contrato'], r['id']): r for r in todas if r.get('evento') == EVENTO}
    contratos = sorted({cid for (cid, _), r in ultimas.items() if r['fase'] not in TERMINALES})
    for cid in contratos:
        resultados.extend(_reconciliar_contrato(cfg, cid))
    return resultados


def _reconciliar_contrato(cfg, cid):
    resultados = []
    with Diario(cfg, pendientes=True, cid=cid) as diario:
        for pid, ultima in diario.ultimas.items():
            if ultima['fase'] in TERMINALES:
                continue
            fases = [r for r in diario.registros if r.get('evento') == EVENTO and r['id'] == pid]
            intenciones = [r for r in fases if r['fase'] == 'intencion']
            resultado = 'no_aplicada'
            if intenciones:
                intencion = intenciones[-1]
                fd, nombre = directorio(cfg.trabajo, intencion['ruta'])
                try:
                    try:
                        fichero = os.open(nombre, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    except FileNotFoundError:
                        fichero = None
                    if fichero is not None:
                        with os.fdopen(fichero, 'rb') as f:
                            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode) or huella(f.read(LIMITE + 1)) != intencion['contenido_sha256']:
                                raise Incierto('conflicto al reconciliar')
                        resultado = 'aplicada'
                finally:
                    os.close(fd)
            # Se conserva la huella original, sin reconstruir contenido del modelo.
            diario.anotar({'id': pid}, 'reconciliada', resultado=resultado,
                          efecto_sha256=ultima['efecto_sha256'])
            resultados.append(resultado)
    return resultados
