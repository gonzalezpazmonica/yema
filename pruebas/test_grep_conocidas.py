"""grep -r sin contrato en carpetas conocidas: leer es libre, siempre que no abarque nada vetado (nota de Yema, 2026-10-22)."""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, politica  # noqa: E402


class TestGrepConocidas(Entorno):
    def setUp(self):
        super().setUp()
        (self.yema / "nucleo/a.py").write_text("exige una persona\n")
        os.environ["YEMA_CARPETAS"] = str(self.trabajo)

    def tearDown(self):
        os.environ.pop("YEMA_CARPETAS", None)
        super().tearDown()

    def b(self, cmd, cwd=None):
        return self.decide("Bash", {"command": cmd}, cwd=cwd)

    def test_el_caso_de_yema(self):
        self.assertTrue(self.b(f'grep -rn -B3 -A12 "exige una persona" {self.yema}/nucleo --include=*.py')[0])

    def test_carpeta_declarada(self):
        self.assertTrue(self.b(f"grep -rn x {self.trabajo}")[0])

    def test_fuera_de_las_conocidas_se_deniega(self):
        fuera = Path(self.tmp.name) / "otra"
        fuera.mkdir()
        self.assertFalse(self.b(f"grep -rn x {fuera}", cwd=fuera)[0])

    def test_no_abarca_una_vetada(self):
        secreta = self.trabajo / "src/claves"
        secreta.mkdir()
        pol = {**politica(), "lectura_vetada": [str(secreta) + "/*"]}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))
        self.assertFalse(self.b(f"grep -rn x {self.trabajo}")[0])

    def test_sigue_sin_poder_ejecutar_ni_escribir(self):
        self.assertFalse(self.b(f"grep -rn x {self.trabajo} ; touch y")[0])
        self.assertFalse(self.b(f"grep -rn x {self.trabajo} > f")[0])


if __name__ == "__main__":
    unittest.main()
