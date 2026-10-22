"""F4: aprobación firmada con HMAC. Ver docs/seguridad.md, sección «Aprobación firmada»."""
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

CARPETA = "llaves"
NOMBRE = "aprobacion.yema-llave"


def ruta_clave(estado):
    return Path(estado) / CARPETA / NOMBRE


def clave(estado, crear=False):
    ruta = ruta_clave(estado)
    if ruta.exists():
        return bytes.fromhex(ruta.read_text(encoding="utf-8").strip())
    if not crear:
        return None
    ruta.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(ruta.parent, 0o700)
    k = secrets.token_bytes(32)
    fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(k.hex() + "\n")
    return k


def _mensaje(c):
    ap = c.get("autoridad", {}).get("aprobacion", {})
    datos = {"id": c.get("id"), "version": c.get("version"), "huella": ap.get("huella"),
             "por": ap.get("por"), "fecha": ap.get("fecha"), "politica": ap.get("politica")}
    return json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def firmar(c, k):
    return hmac.new(k, _mensaje(c), hashlib.sha256).hexdigest()


def verificar(c, k):
    f = c.get("autoridad", {}).get("aprobacion", {}).get("firma")
    if not k or not isinstance(f, str):
        return False
    return hmac.compare_digest(f, firmar(c, k))
