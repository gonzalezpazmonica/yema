"""Cuidado: la salud de la casa y el descanso de la persona.

Chequeos de solo lectura y copias del estado privado. Nada aquí decide por la
persona: avisa, con el problema, su coste y el arreglo.
"""
import os
import shutil
import tarfile
import time
from datetime import datetime
from pathlib import Path

COPIAS_A_GUARDAR = 14
COPIA_MAX_HORAS = 26
DISCO_AVISO_GB, DISCO_ALERTA_GB = 10, 3


def _copias(pol):
    return Path(os.path.expanduser(pol.get("copias", "~/.yema-copias")))


def es_descanso(pol, ahora=None):
    ahora = ahora or datetime.now()
    d = pol.get("descanso", {"desde": 23, "hasta": 8})
    return ahora.hour >= d["desde"] or ahora.hour < d["hasta"]


def copia(estado, pol, sufijo=""):
    """tar.gz del estado privado en el directorio de copias (0700/0600)."""
    destino = _copias(pol)
    destino.mkdir(parents=True, exist_ok=True)
    os.chmod(destino, 0o700)
    nombre = f"yema-estado-{time.strftime('%Y%m%d-%H%M%S')}{('-' + sufijo) if sufijo else ''}.tar.gz"
    ruta = destino / nombre
    fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f, tarfile.open(fileobj=f, mode="w:gz") as tar:
        tar.add(estado, arcname="estado")
    return ruta


def rotar(pol):
    todas = sorted(_copias(pol).glob("yema-estado-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    for vieja in todas[COPIAS_A_GUARDAR:]:
        vieja.unlink()


def chequeos(estado, pol, ahora=None):
    """[(nivel, clave, mensaje)] con nivel ok | aviso | alerta."""
    ahora = ahora or datetime.now()
    r = []
    modo = estado.stat().st_mode & 0o777 if estado.exists() else None
    if modo is None:
        r.append(("alerta", "permisos", f"no existe el estado privado {estado}"))
    elif modo & 0o077:
        r.append(("alerta", "permisos", f"{estado} es legible por otros ({oct(modo)}). Arreglo: chmod 700 {estado}"))
    else:
        r.append(("ok", "permisos", "estado privado solo para la persona"))

    copias = sorted(_copias(pol).glob("yema-estado-*.tar.gz"), key=lambda p: p.stat().st_mtime)
    if not copias:
        r.append(("aviso", "copia", "no hay copia del estado privado. Arreglo: yema copia"))
    else:
        horas = (time.time() - copias[-1].stat().st_mtime) / 3600
        nivel = "ok" if horas <= COPIA_MAX_HORAS else "aviso"
        r.append((nivel, "copia", f"última copia hace {horas:.0f} h ({len(copias)} guardadas)"))

    libres = []
    for ruta in {str(estado.parent if estado.exists() else Path.home()), "/tmp"}:
        try:
            libres.append((ruta, shutil.disk_usage(ruta).free / 1e9))
        except OSError:
            pass
    peor = min(libres, key=lambda x: x[1]) if libres else None
    if peor is None:
        r.append(("aviso", "disco", "no puedo medir el disco"))
    else:
        nivel = "alerta" if peor[1] < DISCO_ALERTA_GB else "aviso" if peor[1] < DISCO_AVISO_GB else "ok"
        r.append((nivel, "disco", f"{peor[0]}: {peor[1]:.1f} GB libres"))

    if es_descanso(pol, ahora):
        r.append(("aviso", "descanso", "es hora de descanso: solo preguntas urgentes; el resto, en el resumen de la mañana"))
    else:
        r.append(("ok", "descanso", "horario de trabajo"))
    return r
