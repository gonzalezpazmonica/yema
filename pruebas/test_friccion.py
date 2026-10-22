"""Fricción medida en la batería F1: lecturas legítimas que la puerta denegaba, sin abrir huecos."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, aprobado, politica  # noqa: E402


class TestComillas(Entorno):
    def leer(self, cmd):
        return self.decide("Bash", {"command": cmd})

    def test_regex_con_barra_y_dolar_entre_comillas_simples(self):
        (self.trabajo / "src/a.py").write_text("x\n")
        self.assertTrue(self.leer("grep -nE '^\\s+(id|gate):$' src/a.py")[0])

    def test_barra_entre_comillas_dobles(self):
        self.assertTrue(self.leer('grep -n "a\\.b" src/a.py')[0])

    def test_dolar_entre_comillas_dobles_sigue_prohibido(self):
        self.assertFalse(self.leer('grep -n "$(rm -f x)" src/a.py')[0])
        self.assertFalse(self.leer('grep -n "`rm x`" src/a.py')[0])

    def test_metacaracteres_fuera_de_comillas_siguen_prohibidos(self):
        for cmd in ("grep x src/a.py; rm y", "grep x src/a.py & rm y", "cat src/a.py > z",
                    "grep '$x' src/a.py; rm y", "grep 'a' src/a.py\nrm y", "grep 'sin cerrar src/a.py"):
            self.assertFalse(self.leer(cmd)[0], cmd)

    def test_tubo_entre_comillas_no_engaña_a_la_cadena(self):
        self.assertFalse(self.leer("grep 'a|rm -f x' src/a.py | sh")[0])


class TestGrepRecursivoEnAmbito(Entorno):
    def setUp(self):
        super().setUp()
        self.activar(aprobado(self.trabajo))
        (self.trabajo / "src/a.py").write_text("x\n")

    def test_grep_recursivo_dentro_del_ambito(self):
        self.assertTrue(self.decide("Bash", {"command": f"grep -rn x {self.trabajo}/src"})[0])
        self.assertTrue(self.decide("Bash", {"command": "grep -rli x ."})[0])

    def test_grep_recursivo_fuera_del_ambito(self):
        self.assertFalse(self.decide("Bash", {"command": f"grep -rn x {self.yema}"})[0])

    def test_grep_recursivo_sin_contrato_sigue_denegado(self):
        (self.yema / "contratos/ACTIVO").unlink()
        self.assertFalse(self.decide("Bash", {"command": "grep -rn x ."})[0])

    def test_grep_recursivo_que_abarca_una_vetada(self):
        secreta = self.trabajo / "src/claves"
        secreta.mkdir()
        pol = {**politica(), "lectura_vetada": [str(secreta) + "/*"]}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))
        self.assertFalse(self.decide("Bash", {"command": f"grep -rn x {self.trabajo}/src"})[0])


if __name__ == "__main__":
    unittest.main()
