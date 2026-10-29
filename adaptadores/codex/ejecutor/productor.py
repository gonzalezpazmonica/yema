"""Codex produce JSON dentro de bwrap; el workspace y el estado no se montan.

No se depende de PreToolUse. La caja conserva red para el proveedor: no certifica
G12 ni un proxy de destino único. Binarios y ancestros son fuentes confiables de
la operadora; la caja debe probarse antes de cada llamada, sin fallback nativo.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import tomllib

from adaptadores.codex.sesion import opciones
from nucleo import puerta
from .motor import (Diario, FUENTES, LIMITE, Rechazo, canon, directorio, estado_nativo,
                    huella, proceso_acotado, ruta_relativa, sincronizar)

ESQUEMA = {'type': 'object', 'additionalProperties': False,
    'required': ['version', 'id', 'tipo', 'ruta', 'contenido'], 'properties': {
        'version': {'type': 'integer', 'enum': [1]}, 'id': {'type': 'string'},
        'tipo': {'type': 'string', 'enum': ['crear']}, 'ruta': {'type': 'string'},
        'contenido': {'type': 'string'}}}


def vista(cfg, destino, rutas):
    """Lista explícita, Read real por fichero, sin enlaces/especiales/secretos."""
    if len(rutas) > 64 or len(set(rutas)) != len(rutas):
        raise Rechazo('manifiesto excesivo o repetido')
    destino = Path(destino)
    destino.mkdir(mode=0o700)
    manifiesto = []
    with Diario(cfg) as diario:
        for ruta in rutas:
            ruta_relativa(ruta)
            if any(p in ('.git', '.codex', '.ssh', '.aws', 'credenciales') for p in Path(ruta).parts):
                raise Rechazo('fuente de configuración o credenciales')
            fd, nombre = directorio(cfg.trabajo, ruta)
            try:
                fichero = os.open(nombre, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                with os.fdopen(fichero, 'rb') as f:
                    st = os.fstat(f.fileno())
                    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > LIMITE:
                        raise Rechazo('lectura no regular, enlazada o excesiva')
                    with estado_nativo(cfg.estado):
                        ok, _, efecto = puerta.evaluar_y_registrar({'tool_name': 'Read',
                            'tool_input': {'file_path': str(cfg.trabajo / ruta)},
                            'cwd': str(cfg.trabajo), 'permission_mode': 'dontAsk'}, cfg.yema)
                    if ok is not True or efecto != 'leer':
                        raise Rechazo('lectura no concedida')
                    datos = f.read(LIMITE + 1)
                    if len(datos) > LIMITE or cfg.vinculo() != diario.vinculo:
                        raise Rechazo('lectura excesiva o gobierno cambiado')
                    # Se fija la versión visible; no se da un enlace al origen.
                    salida = destino / ruta
                    salida.parent.mkdir(parents=True, exist_ok=True)
                    salida.write_bytes(datos)
                    manifiesto.append({'ruta': ruta, 'sha256': huella(datos)})
            finally:
                os.close(fd)
        diario.anotar({'id': os.urandom(16).hex()}, 'vista', evento='codex-vista', manifiesto=manifiesto)
    return manifiesto


@contextmanager
def hogar(destino, auth):
    """La única copia de auth se borra también si falla Codex o su caja."""
    with tempfile.TemporaryDirectory(prefix='codex-home-', dir=destino) as t:
        h = Path(t)
        copia = h / 'auth.json'
        try:
            with copia.open('xb') as out:
                os.chmod(copia, 0o600)
                with Path(auth).open('rb') as entrada:
                    shutil.copyfileobj(entrada, out)
            (h / 'config.toml').write_text('model = "gpt-6.1-terra"\nmodel_reasoning_effort = "medium"\n')
            yield h
        finally:
            copia.unlink(missing_ok=True)


def reservar(salida):
    """Seis llamadas por campaña, contando los fallos antes de invocar Codex."""
    salida = Path(salida)
    with (salida / 'contador.lock').open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        contador = salida / 'invocaciones.json'
        n = json.loads(contador.read_text()) if contador.exists() else 0
        if type(n) is not int or not 0 <= n < 6:
            raise Rechazo('contador inválido o seis invocaciones agotadas')
        temporal = salida / 'contador.tmp'
        temporal.write_text(json.dumps(n + 1) + '\n')
        sincronizar(temporal)
        os.replace(temporal, contador)
        sincronizar(contador)
        return n + 1


def herramientas(codex=None, bwrap=None):
    codex = Path(codex or shutil.which('codex') or '/ausente/codex').resolve(strict=True)
    bwrap = Path(bwrap or '/usr/bin/bwrap').resolve(strict=True)
    paquete = codex.parent.parent
    if not os.access(codex, os.X_OK) or not os.access(bwrap, os.X_OK):
        raise Rechazo('faltan ejecutables de aislamiento o Codex')
    # Distribución standalone de 0.163; no ejecutar lanzadores de shell/npm.
    if not (paquete / 'codex-resources/bwrap').is_file() or codex.name != 'codex':
        raise Rechazo('se requiere distribución standalone auditada de Codex')
    return codex, bwrap, paquete


def caja(snapshot, h, esquema, *, codex=None, bwrap=None):
    codex, bwrap, paquete = herramientas(codex, bwrap)
    orden = [str(bwrap), '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
        '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
        '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
        '--ro-bind', str(paquete), '/opt/codex', '--ro-bind', str(snapshot), '/w',
        '--bind', str(h), '/h', '--ro-bind', str(esquema), '/esquema.json',
        '--unshare-all', '--share-net', '--die-with-parent', '--new-session',
        '--clearenv', '--setenv', 'PATH', '/opt/codex/bin:/usr/bin:/bin',
        '--setenv', 'HOME', '/h', '--setenv', 'CODEX_HOME', '/h',
        '--setenv', 'LANG', 'C.UTF-8', '--chdir', '/w']
    for ruta in ('/etc/resolv.conf', '/etc/hosts', '/etc/nsswitch.conf', '/etc/ssl/certs'):
        if Path(ruta).exists():
            orden += ['--ro-bind', ruta, ruta]
    for nombre in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
                   'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy'):
        if nombre in os.environ:
            orden += ['--setenv', nombre, os.environ[nombre]]
    certificado = os.environ.get('SSL_CERT_FILE') or os.environ.get('REQUESTS_CA_BUNDLE')
    if certificado:
        orden += ['--ro-bind', certificado, '/ca.crt', '--setenv', 'SSL_CERT_FILE', '/ca.crt']
    return orden


def comprobar_caja(orden, ocultas=()):
    """Prueba efectiva con el mismo montaje, antes de enviar contexto al modelo."""
    programa = '''import os,pathlib
assert pathlib.Path('/w').is_dir()
for p in __import__('json').loads(__import__('sys').argv[1]):
    assert not pathlib.Path(p).exists(), 'ruta de autoridad visible'
try:
    pathlib.Path('/w/NO-ESCRIBIR').write_text('fallo')
except OSError:
    pass
else:
    raise AssertionError('snapshot escribible')
assert os.readlink('/proc/self/root') == '/'
print('aislada')
'''
    rc, salida = proceso_acotado(orden + ['--', '/usr/bin/python3', '-I', '-c', programa,
                                json.dumps([str(p) for p in ocultas])], b'', 5, 1024)
    if rc != 0 or salida != b'aislada\n':
        raise Rechazo('no se pudo verificar la caja externa')


def orden_codex():
    cfg = tomllib.loads((FUENTES / 'adaptadores/codex/config.toml').read_text())
    # No existe un hook confiable dentro del productor. El supervisor decide fuera.
    cfg['features']['hooks'] = False
    cfg['hooks'] = {}
    return ['/opt/codex/bin/codex', '--no-daemon', '--strict-config', 'exec',
            '--ignore-user-config', '--ephemeral', '--skip-git-repo-check', '--json',
            '--output-schema', '/esquema.json', '--output-last-message', '/h/propuesta.json',
            '-C', '/w', *opciones(cfg), '--', '-']


def validar_salida(cfg, salida):
    salida = Path(salida)
    if not salida.is_dir() or salida.resolve() == cfg.trabajo or cfg.trabajo in salida.resolve().parents:
        raise Rechazo('la salida privada debe existir fuera del workspace')
    return salida


def leer_propuesta(h):
    fd = os.open(h / 'propuesta.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise Rechazo('propuesta no regular')
        datos = f.read(LIMITE + 1)
    if len(datos) > LIMITE:
        raise Rechazo('propuesta de Codex excesiva')
    return datos


def proponer(cfg, salida, prompt, lecturas, auth, *, timeout=180):
    """Una llamada, sin acceso al workspace; retorno todavía no autorizado."""
    salida = validar_salida(cfg, salida)
    with tempfile.TemporaryDirectory(prefix='productor-', dir=salida) as t:
        temporal = Path(t)
        snapshot = temporal / 'vista'
        manifiesto = vista(cfg, snapshot, lecturas)
        esquema = temporal / 'esquema.json'
        esquema.write_bytes(canon(ESQUEMA))
        with hogar(temporal, auth) as h:
            orden = caja(snapshot, h, esquema)
            comprobar_caja(orden, (cfg.trabajo, cfg.estado, cfg.yema, Path(auth).parent))
            rc, version = proceso_acotado(orden + ['--', '/opt/codex/bin/codex', '--version'], b'', 5, 1024)
            if rc != 0 or version.strip() != b'codex-cli 0.163.0':
                raise Rechazo('se requiere Codex CLI 0.163.0')
            n = reservar(salida)
            rc, eventos = proceso_acotado(orden + ['--', *orden_codex()], prompt.encode(), timeout, 2_000_000)
            # Logs privados de campaña, sin copiar auth ni configuración personal.
            (salida / f'codex-{n}.jsonl').write_bytes(eventos)
            resumen = {'invocacion': n, 'rc': rc, 'aislamiento': True, 'manifiesto': manifiesto,
                       'version_cli': version.strip().decode(), 'modelo_solicitado': 'gpt-6.1-terra',
                       'esfuerzo': 'medium', 'hooks_productor': False,
                       'fuentes_sha256': {f.name: huella(f.read_bytes())
                           for f in Path(__file__).parent.glob('*.py')}}
            (salida / f'codex-{n}-resumen.json').write_bytes(canon(resumen) + b'\n')
            if rc != 0:
                raise Rechazo('Codex falló; no se acepta ninguna propuesta')
            return leer_propuesta(h)
