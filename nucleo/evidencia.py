"""Registro de evidencia: JSONL encadenado por hash (solo añadir)."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def _hash(prev, cuerpo):
    canon = json.dumps(cuerpo, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256((prev + canon).encode()).hexdigest()


def leer(ruta):
    ruta = Path(ruta)
    if not ruta.exists():
        return []
    return [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]


def anotar(ruta, datos):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    previas = leer(ruta)
    prev = previas[-1]["hash"] if previas else GENESIS
    cuerpo = {"ts": datetime.now(timezone.utc).isoformat(), **datos, "prev": prev}
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**cuerpo, "hash": _hash(prev, cuerpo)}, ensure_ascii=False) + "\n")


def verificar(ruta):
    """(True, n) si la cadena está íntegra; (False, índice del primer fallo)."""
    prev = GENESIS
    lineas = leer(ruta)
    for i, l in enumerate(lineas):
        cuerpo = {k: v for k, v in l.items() if k != "hash"}
        if l.get("prev") != prev or _hash(prev, cuerpo) != l.get("hash"):
            return False, i
        prev = l["hash"]
    return True, len(lineas)
