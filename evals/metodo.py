"""Huellas de método de una evaluación: qué se prerregistró, sobre qué corpus, con qué política y qué código.

Un resultado sin estas huellas no se puede reproducir ni comparar. Las limitaciones son obligatorias:
un resultado que no dice qué no demuestra, se lee como si demostrara más.

Uso: python3 -m evals.metodo --criterios c.md --corpus dir --politica p.json --implementacion dir \
       --limitacion UNA_REPETICION [--limitacion ...] --salida metodo.json
"""
import argparse
import hashlib
import json
from pathlib import Path


def _fichero(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def _carpeta(ruta):
    """Huella de los nombres relativos y del contenido de cada fichero, en orden estable."""
    raiz, h = Path(ruta), hashlib.sha256()
    for f in sorted(p for p in raiz.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(str(f.relative_to(raiz)).encode() + b"\0" + _fichero(f).encode() + b"\n")
    return h.hexdigest()


def _huella(ruta):
    return _carpeta(ruta) if Path(ruta).is_dir() else _fichero(ruta)


def huellas(criterios, corpus, politica, implementacion, limitaciones):
    if not limitaciones:
        raise ValueError("declara al menos una limitación: qué no demuestra este resultado")
    return {"prerregistro": _huella(criterios), "corpus": _huella(corpus), "politica": _huella(politica),
            "implementacion": _huella(implementacion), "limitaciones": list(limitaciones)}


def diferencias(guardado, actual):
    return [k for k in ("prerregistro", "corpus", "politica", "implementacion") if guardado.get(k) != actual.get(k)]


def main(argv=None):
    p = argparse.ArgumentParser(prog="metodo")
    for k in ("criterios", "corpus", "politica", "implementacion", "salida"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--limitacion", action="append", default=[])
    a = p.parse_args(argv)
    r = huellas(a.criterios, a.corpus, a.politica, a.implementacion, a.limitacion)
    Path(a.salida).write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"huellas en {a.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
