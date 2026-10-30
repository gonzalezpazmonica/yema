"""Aislar una orden concedida: el kernel acota lo que lee y escribe al ámbito del contrato.

La puerta juzga la orden, no lo que hace por dentro: `python3 lee.py` podría abrir cualquier
fichero del disco. Por eso la puerta no lanza la orden tal cual, sino a través de este ejecutor,
que aplica Landlock (Linux ≥ 5.13, sin privilegios, sin bwrap ni espacios de nombres) y después
la ejecuta. Dentro solo se lee el ámbito, sus carpetas de lectura y lo del sistema que hace falta
para arrancar (/usr, /etc, /proc…), y solo se escribe en el ámbito y en un /tmp propio que se
borra al terminar. Fallo cerrado: si el kernel no admite Landlock, la orden no corre, salvo que
el contrato aprobado diga `ambito.aislamiento: "si_hay"`.

Uso (lo compone la puerta): aislar.py --raiz R [--lee P]... [--sin-kernel-ejecuta] -- orden args
"""
import ctypes
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SYS_CREATE, SYS_ADD_RULE, SYS_RESTRICT = 444, 445, 446  # iguales en x86_64 y aarch64
VERSION = 1  # LANDLOCK_CREATE_RULESET_VERSION
REGLA_RUTA = 1  # LANDLOCK_RULE_PATH_BENEATH
PR_SET_NO_NEW_PRIVS = 38

EJECUTAR, ESCRIBIR_F, LEER_F, LEER_D = 1, 2, 4, 8
QUITAR_D, QUITAR_F, HACER_CHR, HACER_D, HACER_REG, HACER_SOCK, HACER_FIFO, HACER_BLK, HACER_SYM = (
    16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
REFER, TRUNCAR, IOCTL_DEV = 8192, 16384, 32768  # ABI 2, 3 y 5
AMBITO_SOCKET, AMBITO_SENAL = 1, 2  # ABI 6

LECTURA = EJECUTAR | LEER_F | LEER_D
DE_FICHERO = EJECUTAR | ESCRIBIR_F | LEER_F | TRUNCAR | IOCTL_DEV
SISTEMA = ("/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/etc", "/proc", "/sys/devices/system/cpu")
DISPOSITIVOS = ("/dev/null", "/dev/zero", "/dev/full", "/dev/random", "/dev/urandom", "/dev/tty", "/dev/pts",
                "/dev/shm")
ASIGNACION = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")


class Rechazo(Exception):
    pass


class _Ruleset(ctypes.Structure):
    _fields_ = [("fs", ctypes.c_uint64), ("net", ctypes.c_uint64), ("scoped", ctypes.c_uint64)]


class _Beneath(ctypes.Structure):
    # En el kernel va empaquetada (12 bytes): el relleno de ctypes queda al final y no se lee.
    _fields_ = [("acceso", ctypes.c_uint64), ("fd", ctypes.c_int32)]


_libc = ctypes.CDLL(None, use_errno=True)
_libc.syscall.restype = ctypes.c_long


def _sys(n, *args):
    r = _libc.syscall(ctypes.c_long(n), *args)
    if r < 0:
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e))
    return r


def abi():
    """Versión de Landlock que ofrece el kernel; 0 si no hay (kernel viejo, desactivado o sin la llamada)."""
    try:
        return int(_sys(SYS_CREATE, None, ctypes.c_size_t(0), ctypes.c_uint32(VERSION)))
    except (OSError, AttributeError):
        return 0


def derechos(version):
    """Todos los derechos de ficheros que entiende esa versión: los que se controlan."""
    d = LECTURA | ESCRIBIR_F | QUITAR_D | QUITAR_F | HACER_CHR | HACER_D | HACER_REG | HACER_SOCK | HACER_FIFO \
        | HACER_BLK | HACER_SYM
    if version >= 2:
        d |= REFER
    if version >= 3:
        d |= TRUNCAR
    if version >= 5:
        d |= IOCTL_DEV
    return d


def reglas(raiz, lectura=(), tmp=None, orden=None):
    """(lee, escribe): rutas reales que existen. Las relativas de `lectura` cuelgan de la raíz."""
    raiz = Path(os.path.realpath(raiz))
    lee = [Path(p) for p in SISTEMA]
    for p in lectura:
        p = Path(os.path.expanduser(str(p)))
        lee.append(p if p.is_absolute() else raiz / p)
    if orden:
        prog = shutil.which(orden[0])
        if prog:
            lee.append(Path(prog))  # el ejecutable, aunque viva fuera del sistema (solo ese fichero)
    escribe = [raiz] + [Path(p) for p in DISPOSITIVOS] + ([Path(tmp)] if tmp else [])
    real = lambda xs: list(dict.fromkeys(Path(os.path.realpath(x)) for x in xs if os.path.exists(x)))  # noqa: E731
    return real(lee), real(escribe)


def preparar(lee, escribe, version):
    """Ruleset de Landlock con esas reglas: devuelve su descriptor (aún sin aplicar)."""
    if version < 1:
        raise Rechazo("el kernel no admite Landlock")
    todo = derechos(version)
    attr = _Ruleset(fs=todo, net=0, scoped=(AMBITO_SOCKET | AMBITO_SENAL) if version >= 6 else 0)
    tam = 24 if version >= 6 else 16 if version >= 4 else 8
    fd = _sys(SYS_CREATE, ctypes.byref(attr), ctypes.c_size_t(tam), ctypes.c_uint32(0))
    for rutas, acceso in ((lee, LECTURA), (escribe, todo)):
        for r in rutas:
            permitido = acceso & todo if r.is_dir() else acceso & todo & DE_FICHERO
            pfd = os.open(r, os.O_PATH | os.O_CLOEXEC)
            try:
                _sys(SYS_ADD_RULE, ctypes.c_int(fd), ctypes.c_int(REGLA_RUTA),
                     ctypes.byref(_Beneath(acceso=permitido, fd=pfd)), ctypes.c_uint32(0))
            finally:
                os.close(pfd)
    return fd


def aplicar(fd):
    """Encierra al proceso actual (y a todo lo que lance) en el ruleset. No tiene vuelta atrás."""
    if _libc.prctl(PR_SET_NO_NEW_PRIVS, ctypes.c_ulong(1), ctypes.c_ulong(0), ctypes.c_ulong(0), ctypes.c_ulong(0)):
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e))
    _sys(SYS_RESTRICT, ctypes.c_int(fd), ctypes.c_uint32(0))


def ejecutar(orden, raiz, lectura=(), sin_kernel_ejecuta=False, version=None):
    """rc de la orden corrida bajo Landlock. Lanza Rechazo si no puede aislarla y no está permitido correr sin."""
    if not orden:
        raise Rechazo("falta la orden")
    if not Path(raiz).is_dir():
        raise Rechazo(f"la raíz del contrato no es una carpeta: {raiz}")
    env = dict(os.environ)
    while orden and ASIGNACION.fullmatch(orden[0]):
        k, v = orden[0].split("=", 1)
        env[k], orden = v, orden[1:]
    version = abi() if version is None else version
    if version < 1:
        if not sin_kernel_ejecuta:
            raise Rechazo("el kernel no admite Landlock: la orden no corre sin aislar "
                          "(el contrato puede declararlo con ambito.aislamiento «si_hay»)")
        print("YEMA aislar: el kernel no admite Landlock; el contrato permite correr SIN aislar", file=sys.stderr)
        return subprocess.call(orden, env=env)
    tmp = tempfile.mkdtemp(prefix="yema-aislar-")
    try:
        env.update(TMPDIR=tmp, TMP=tmp, TEMP=tmp)
        lee, escribe = reglas(raiz, lectura, tmp, orden)
        fd = preparar(lee, escribe, version)
        try:
            return subprocess.call(orden, env=env, preexec_fn=lambda: aplicar(fd))
        except subprocess.SubprocessError as e:
            raise Rechazo(f"no pude aplicar Landlock: {e}") from e
        finally:
            os.close(fd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def prefijo(raiz_yema, c):
    """Lo que la puerta antepone a una orden concedida para que corra aislada con el ámbito de `c`."""
    amb = c["ambito"]
    args = [sys.executable, str(Path(raiz_yema) / "nucleo/aislar.py"), "--raiz", str(amb["raiz"])]
    for p in amb.get("lectura", []):
        args += ["--lee", str(p)]
    if amb.get("aislamiento") == "si_hay":
        args.append("--sin-kernel-ejecuta")
    return " ".join(shlex.quote(a) for a in args) + " -- "


def main(argv=None, version=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        print("YEMA aislar: uso: aislar.py --raiz R [--lee P]... [--sin-kernel-ejecuta] -- orden", file=sys.stderr)
        return 2
    corte = argv.index("--")
    opciones, orden = argv[:corte], argv[corte + 1:]
    raiz, lectura, sin_kernel = None, [], False
    i = 0
    while i < len(opciones):
        o = opciones[i]
        if o in ("--raiz", "--lee") and i + 1 < len(opciones):
            if o == "--raiz":
                raiz = opciones[i + 1]
            else:
                lectura.append(opciones[i + 1])
            i += 2
        elif o == "--sin-kernel-ejecuta":
            sin_kernel, i = True, i + 1
        else:
            print(f"YEMA aislar: opción desconocida {o}", file=sys.stderr)
            return 2
    if not raiz:
        print("YEMA aislar: falta --raiz", file=sys.stderr)
        return 2
    try:
        return ejecutar(orden, raiz, lectura, sin_kernel, version)
    except FileNotFoundError as e:
        print(f"YEMA aislar: no encuentro la orden: {e.filename}", file=sys.stderr)
        return 127
    except (Rechazo, OSError) as e:
        print(f"YEMA aislar: {e}", file=sys.stderr)
        return 126


if __name__ == "__main__":
    sys.exit(main())
