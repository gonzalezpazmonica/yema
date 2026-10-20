"""Evidencia: cadena por hash."""
import os
import subprocess
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, RAIZ, Entorno, aprobado, base, politica  # noqa: E402,F401
from nucleo import evidencia  # noqa: E402


class TestEvidencia(Entorno):
    def test_cadena_integra(self):
        f = self.yema / "evidencia/C-1.jsonl"
        for i in range(3):
            evidencia.anotar(f, {"n": i})
        self.assertEqual(evidencia.verificar(f), (True, 3))

    def test_cadena_manipulada(self):
        f = self.yema / "evidencia/C-1.jsonl"
        for i in range(3):
            evidencia.anotar(f, {"n": i})
        lineas = f.read_text().splitlines()
        lineas[1] = lineas[1].replace('"n": 1', '"n": 9')
        f.write_text("\n".join(lineas) + "\n")
        self.assertFalse(evidencia.verificar(f)[0])

    def test_linea_borrada(self):
        f = self.yema / "evidencia/C-1.jsonl"
        for i in range(3):
            evidencia.anotar(f, {"n": i})
        lineas = f.read_text().splitlines()
        f.write_text("\n".join([lineas[0], lineas[2]]) + "\n")
        self.assertFalse(evidencia.verificar(f)[0])


if __name__ == "__main__":
    unittest.main()
