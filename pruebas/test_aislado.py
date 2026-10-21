"""Ejecución aislada sin contrato: copia desechable, sin red, sin el hogar, con límites."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, politica  # noqa: E402
from nucleo import aislado, puerta, yema  # noqa: E402

HAY_SANDBOX = aislado.bwrap_de_confianza() is not None

CODIGO = "def doble(x):\n    return x * 3\n"
TEST = ("import unittest\nfrom m import doble\n\n\nclass T(unittest.TestCase):\n"
        "    def test_doble(self):\n        self.assertEqual(doble(2), 4)\n")
PARCHE = ("--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,2 @@\n def doble(x):\n-    return x * 3\n+    return x * 2\n")


@unittest.skipUnless(HAY_SANDBOX, "sin bwrap de confianza")
class TestAislado(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.proyecto = t / "proyecto"
        self.proyecto.mkdir()
        (self.proyecto / "m.py").write_text(CODIGO)
        (self.proyecto / "test_m.py").write_text(TEST)
        self.base = t / "aislado"
        self.fuera = t / "secreto.txt"
        self.fuera.write_text("no deberías verme")

    def tearDown(self):
        self.tmp.cleanup()

    def corre(self, orden, **kw):
        return aislado.ejecutar(self.proyecto, orden, base=self.base, **kw)

    def test_ejecuta_y_devuelve_resultado(self):
        r = self.corre(["python3", "-m", "unittest", "-q"])
        self.assertNotEqual(r["rc"], 0)
        self.assertIn("FAILED", r["salida"])

    def test_parche_se_aplica_en_la_copia_y_verifica(self):
        parche = Path(self.tmp.name) / "p.diff"
        parche.write_text(PARCHE)
        r = self.corre(["python3", "-m", "unittest", "-q"], parche=parche)
        self.assertEqual(r["rc"], 0, r["salida"])
        self.assertEqual((self.proyecto / "m.py").read_text(), CODIGO)  # el original no cambia

    def test_parche_que_no_aplica_se_dice(self):
        parche = Path(self.tmp.name) / "p.diff"
        parche.write_text(PARCHE.replace("x * 3", "x * 7"))
        r = self.corre(["python3", "-m", "unittest", "-q"], parche=parche)
        self.assertNotEqual(r["rc"], 0)
        self.assertIn("parche", r["salida"])

    def test_escribir_no_toca_el_original(self):
        r = self.corre(["touch", "nuevo.txt"])
        self.assertEqual(r["rc"], 0, r["salida"])
        self.assertFalse((self.proyecto / "nuevo.txt").exists())

    def test_no_ve_el_hogar_ni_ficheros_de_fuera(self):
        r = self.corre(["cat", str(self.fuera)])
        self.assertNotEqual(r["rc"], 0)
        self.assertNotIn("no deberías verme", r["salida"])
        r = self.corre(["ls", os.path.expanduser("~")])
        self.assertNotEqual(r["rc"], 0)

    def test_sin_red(self):
        r = self.corre(["python3", "-c", "import socket; socket.create_connection(('1.1.1.1', 53), 2)"])
        self.assertNotEqual(r["rc"], 0)

    def test_no_copia_lo_vetado(self):
        (self.proyecto / "prod.env").write_text("CLAVE=no-deberias-verme")
        r = self.corre(["cat", "prod.env"], vetado=lambda p: p.name.endswith(".env"))
        self.assertNotEqual(r["rc"], 0)
        self.assertNotIn("no-deberias-verme", r["salida"])

    def test_limite_de_tiempo(self):
        r = self.corre(["sleep", "5"], timeout=1)
        self.assertTrue(r["agotado"])

    def test_copia_demasiado_grande(self):
        with self.assertRaises(aislado.Rechazo):
            self.corre(["true"], max_mb=0)


class TestBwrapDeConfianza(unittest.TestCase):
    def test_rechaza_uno_de_la_usuaria(self):
        with tempfile.TemporaryDirectory() as t:
            falso = Path(t) / "bwrap"
            falso.write_text("#!/bin/sh\n")
            falso.chmod(0o755)
            self.assertFalse(aislado.es_de_confianza(falso))


class TestGobiernoPrueba(Entorno):
    def test_prueba_es_libre_sin_contrato(self):
        cmd = f"python3 {self.yema}/nucleo/yema.py prueba src -- python3 -m unittest"
        (self.yema / "nucleo").mkdir(exist_ok=True)
        (self.yema / "nucleo/yema.py").write_text("")
        ok, motivo, efecto = self.decide("Bash", {"command": cmd})
        self.assertIs(ok, True, motivo)
        self.assertEqual(efecto, "gobierno")


@unittest.skipUnless(HAY_SANDBOX, "sin bwrap de confianza")
class TestCliPrueba(Entorno):
    def test_cli(self):
        (self.trabajo / "m.py").write_text(CODIGO)
        (self.trabajo / "test_m.py").write_text(TEST)
        estado = Path(self.tmp.name) / "estado"
        (self.yema / "gobierno/politica.json").write_text(json.dumps({**politica(), "estado": str(estado)}))
        out = io.StringIO()
        with redirect_stdout(out):
            rc = yema.main(["prueba", str(self.trabajo), "--", "python3", "-m", "unittest", "-q"], raiz=self.yema, tty=False)
        self.assertNotEqual(rc, 0)
        self.assertIn("FAILED", out.getvalue())


if __name__ == "__main__":
    unittest.main()
