"""Juicio ciego: copia las respuestas de cada sistema con letras al azar y guarda el mapa aparte.

Uso: python3 -m evals.ciego <runs> <ciego> <mapa.json> --tarea D
<runs>/<sistema>/<n>.md  →  <ciego>/<tarea>-<letra>-<n>.md
La jueza solo ve <ciego>; el mapa no se le enseña hasta tener el veredicto.
"""
import argparse
import json
import random
import re
from pathlib import Path

LETRAS = "XYZW"


def anonimizar(runs, ciego, mapa_ruta, tarea, semilla=None):
    runs, ciego, mapa_ruta = Path(runs), Path(ciego), Path(mapa_ruta)
    sistemas = sorted(p.name for p in runs.iterdir() if p.is_dir())
    letras = list(LETRAS[:len(sistemas)])
    random.Random(semilla).shuffle(letras)
    mapa = dict(zip(sistemas, letras))
    nombres = re.compile(r"\b(" + "|".join(re.escape(s) for s in sistemas) + r")\b", re.I)
    ciego.mkdir(parents=True, exist_ok=True)
    for sis, letra in mapa.items():
        for f in sorted((runs / sis).glob("*.md")):
            texto = nombres.sub("[sistema]", f.read_text(encoding="utf-8"))
            (ciego / f"{tarea}-{letra}-{f.stem}.md").write_text(texto, encoding="utf-8")
    previo = json.loads(mapa_ruta.read_text()) if mapa_ruta.exists() else {}
    previo[tarea] = mapa
    mapa_ruta.write_text(json.dumps(previo, ensure_ascii=False) + "\n", encoding="utf-8")
    return mapa


def main(argv=None):
    p = argparse.ArgumentParser(prog="ciego")
    p.add_argument("runs"), p.add_argument("ciego"), p.add_argument("mapa")
    p.add_argument("--tarea", required=True)
    p.add_argument("--semilla", type=int)
    a = p.parse_args(argv)
    anonimizar(a.runs, a.ciego, a.mapa, a.tarea, a.semilla)
    print(f"anonimizado en {a.ciego}; el mapa queda en {a.mapa}, no se lo enseñes a la jueza")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
