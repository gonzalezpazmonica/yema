"""Hook SessionStart: Yema empieza sabiendo su estado, sin gastar turnos en averiguarlo.

Nunca rompe la sesión: ante cualquier error, no dice nada.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    try:
        sys.stdin.read()
        from nucleo import puerta, yema
        codigo = Path(os.environ.get("YEMA_RAIZ") or Path(__file__).resolve().parent.parent)
        pol = json.loads((codigo / "gobierno/politica.json").read_text(encoding="utf-8"))
        estado = puerta.estado_de(codigo, pol)
        if not estado.is_dir():
            return 0
        visible, detalle = yema.situacion(codigo)
        import shutil
        import subprocess
        hay = [h for h in ("python3", "cargo", "node", "npm", "go") if shutil.which(h)]
        if "python3" in hay:
            pt = subprocess.run(["python3", "-c", "import pytest"], capture_output=True).returncode == 0
            hay.append("pytest" if pt else "sin pytest (usa python3 -m unittest)")
        ctx = (f"Yema · {visible}: {detalle}. Estado privado: {estado} (borradores en {estado}/contratos/borradores, "
               f"memoria en {estado}/memoria). CLI: yema. Herramientas: {', '.join(hay) or 'ninguna'}.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}},
                         ensure_ascii=False))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
