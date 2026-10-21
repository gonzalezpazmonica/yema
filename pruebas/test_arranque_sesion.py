"""Contexto de arranque: Yema empieza sabiendo su estado, sin gastar turnos en averiguarlo."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class TestArranqueSesion(unittest.TestCase):
    def test_hook_registrado(self):
        ajustes = json.loads((RAIZ / ".claude/settings.json").read_text())
        ordenes = [h["command"] for g in ajustes["hooks"]["SessionStart"] for h in g["hooks"]]
        self.assertTrue(any("arranque.py" in o for o in ordenes))

    def test_inyecta_estado_y_ruta(self):
        with tempfile.TemporaryDirectory() as t:
            estado = Path(t) / "estado"
            (estado / "contratos/borradores").mkdir(parents=True)
            env = {**os.environ, "YEMA_ESTADO": str(estado)}
            r = subprocess.run([sys.executable, str(RAIZ / "nucleo/arranque.py")], input="{}",
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Lista", ctx)
            self.assertIn(str(estado), ctx)
            self.assertLess(len(ctx.split()), 80)  # barato: no es un segundo AGENTS.md

    def test_falla_en_silencio_sin_romper_la_sesion(self):
        env = {**os.environ, "YEMA_ESTADO": "/ruta/que/no/existe"}
        r = subprocess.run([sys.executable, str(RAIZ / "nucleo/arranque.py")], input="{}",
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
