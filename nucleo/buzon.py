"""Buzón entre Yema y Savia: mensajes con forma fija; un aprendizaje sin evidencia no se guarda."""
import json
from datetime import datetime, timezone
from pathlib import Path

TIPOS = {"consulta", "respuesta", "traspaso", "aprendizaje", "aviso", "propuesta"}
REQUERIDOS = ("de", "para", "tipo", "ts", "cuerpo")
LECCION = ("cuando", "leccion", "evidencia")
CONFIANZA = {"alta", "media", "baja"}


def errores(m):
    e = [f"falta {k}" for k in REQUERIDOS if k not in m]
    if e:
        return e
    if m["tipo"] not in TIPOS:
        return [f"tipo desconocido {m['tipo']}: un mensaje informa, no ordena"]
    if m["tipo"] == "aprendizaje":
        c = m["cuerpo"] if isinstance(m["cuerpo"], dict) else {}
        for k in LECCION:
            if not str(c.get(k, "")).strip():
                e.append(f"aprendizaje sin {k}: sin {k} no se guarda")
        if c.get("confianza") not in CONFIANZA:
            e.append("confianza debe ser alta, media o baja")
    return e


def leccion(de, para, cuando, texto, evidencia, confianza, ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    return {"de": de, "para": para, "tipo": "aprendizaje", "ts": ahora.isoformat(),
            "cuerpo": {"cuando": cuando, "leccion": texto, "evidencia": evidencia, "confianza": confianza}}


def dejar(m, carpeta):
    """Valida y escribe en la carpeta de salida; devuelve (ruta, errores)."""
    e = errores(m)
    if e:
        return None, e
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    sello = datetime.fromisoformat(m["ts"]).strftime("%Y%m%dT%H%M%S%f")
    ruta = carpeta / f"{sello}-{m['tipo']}.json"
    ruta.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return ruta, []
