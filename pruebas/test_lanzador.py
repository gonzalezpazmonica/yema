"""bin/yema-sesion: abre Claude Code en Yema solo con sus servidores MCP (sin conectores de la cuenta)."""
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LANZADOR = RAIZ / "bin/yema-sesion"


class TestLanzador(unittest.TestCase):
    def ejecutar(self, *args):
        with tempfile.TemporaryDirectory() as t:
            falso = Path(t) / "claude"
            falso.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "ts=$ENABLE_TOOL_SEARCH" "$@"\n')
            falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
            env = {**os.environ, "PATH": f"{t}:{os.environ['PATH']}"}
            r = subprocess.run([str(LANZADOR), *args], capture_output=True, text=True, env=env, cwd=t)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.splitlines()

    def test_existe_y_es_ejecutable(self):
        self.assertTrue(os.access(LANZADOR, os.X_OK))

    def test_solo_los_servidores_de_yema(self):
        salida = self.ejecutar()
        self.assertIn("--strict-mcp-config", salida)
        i = salida.index("--mcp-config")
        self.assertEqual(Path(salida[i + 1]).resolve(), (RAIZ / ".mcp.json").resolve())

    def test_arranca_en_el_repo_de_yema(self):
        self.assertEqual(Path(self.ejecutar()[0]).resolve(), RAIZ.resolve())

    def test_herramientas_bajo_demanda(self):
        # Medido: sin esto, con pocas herramientas MCP se cargan todos los esquemas (42k frente a 22k tokens).
        self.assertIn("ts=true", self.ejecutar())

    def test_pasa_los_argumentos(self):
        salida = self.ejecutar("-p", "hola")
        self.assertEqual(salida[-2:], ["-p", "hola"])


if __name__ == "__main__":
    unittest.main()
