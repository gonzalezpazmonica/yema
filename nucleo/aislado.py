"""Ejecución aislada: probar sin contrato en una copia desechable.

La copia vive en el estado privado y se borra al terminar. La orden corre en un
sandbox bwrap de confianza (de root, no escribible por otros): sin red, sin el
hogar de la persona, solo /usr, /etc y la copia, con tiempo y tamaño limitados.
El original nunca se toca. Lo vetado por la política no se copia.
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

CANDIDATOS = ("/usr/bin/bwrap", "/usr/local/bin/bwrap")
NO_COPIAR = (".git", "node_modules", "target", "__pycache__", ".venv", "venv")
MAX_SALIDA = 20000


class Rechazo(Exception):
    pass


def es_de_confianza(ruta):
    """De root, sin escritura de grupo u otros, en un directorio de root igual de cerrado."""
    try:
        real = Path(os.path.realpath(ruta))
        st, dst = real.stat(), real.parent.stat()
    except OSError:
        return False
    return (st.st_uid == 0 and not st.st_mode & 0o022 and dst.st_uid == 0 and not dst.st_mode & 0o022
            and os.access(real, os.X_OK))


def bwrap_de_confianza():
    for c in CANDIDATOS:
        if Path(c).exists() and es_de_confianza(c):
            return str(Path(os.path.realpath(c)))
    return None


def _tamano(d):
    total = 0
    for raiz, dirs, ficheros in os.walk(d):
        dirs[:] = [x for x in dirs if x not in NO_COPIAR]
        for f in ficheros:
            try:
                total += os.lstat(os.path.join(raiz, f)).st_size
            except OSError:
                pass
    return total


def _copiar(origen, destino, vetado):
    def ignorar(carpeta, nombres):
        fuera = {n for n in nombres if n in NO_COPIAR}
        if vetado:
            fuera |= {n for n in nombres if vetado(Path(carpeta) / n)}
        return fuera
    shutil.copytree(origen, destino, ignore=ignorar, symlinks=True)


def _caja(bw, copia, extra=()):
    return [bw, "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--ro-bind", "/etc", "/etc", "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/tmp", "--bind", str(copia), "/w", *extra, "--chdir", "/w", "--unshare-all",
            "--die-with-parent", "--new-session", "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
            "--setenv", "HOME", "/w", "--setenv", "LANG", "C.UTF-8"]


def ejecutar(origen, orden, base, parche=None, timeout=120, max_mb=200, vetado=None):
    """{rc, salida, agotado, segundos}. Lanza Rechazo si no se puede aislar."""
    bw = bwrap_de_confianza()
    if not bw:
        raise Rechazo("no hay un bwrap de confianza (de root, en /usr/bin): no ejecuto sin aislamiento")
    origen = Path(origen).resolve()
    if not origen.is_dir():
        raise Rechazo(f"no es una carpeta: {origen}")
    if _tamano(origen) > max_mb * 1_000_000:
        raise Rechazo(f"la carpeta pasa de {max_mb} MB: elige una más pequeña")
    if not orden:
        raise Rechazo("falta la orden")
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    trabajo = Path(tempfile.mkdtemp(prefix="caja-", dir=base))
    copia = trabajo / "w"
    t0 = time.time()
    try:
        _copiar(origen, copia, vetado)
        if parche:
            p = trabajo / "parche.diff"
            shutil.copyfile(parche, p)
            salida = ""
            for nivel in ("-p1", "-p0"):
                r = subprocess.run(_caja(bw, copia, ("--ro-bind", str(p), "/parche.diff"))
                                   + ["patch", nivel, "--forward", "--batch", "-i", "/parche.diff"],
                                   capture_output=True, text=True, timeout=30)
                salida += r.stdout + r.stderr
                if r.returncode == 0:
                    break
            else:
                consejo = ("\nNo escribas los hunks a mano: guarda el fichero corregido en tu memoria y genera el parche "
                           "con «diff -u <original> <corregido>», que siempre sale bien formado.")
                return {"rc": 1, "salida": "el parche no aplica:\n" + salida[-MAX_SALIDA:] + consejo, "agotado": False,
                        "segundos": round(time.time() - t0, 1)}
        try:
            r = subprocess.run(_caja(bw, copia) + list(orden), capture_output=True, text=True, timeout=timeout)
            res = {"rc": r.returncode, "salida": (r.stdout + r.stderr)[-MAX_SALIDA:], "agotado": False}
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or b"") + (e.stderr or b"")
            out = out.decode(errors="replace") if isinstance(out, bytes) else out
            res = {"rc": 124, "salida": out[-MAX_SALIDA:] + f"\n(tiempo agotado: {timeout} s)", "agotado": True}
        res["segundos"] = round(time.time() - t0, 1)
        return res
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)
