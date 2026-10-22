"""Un borrador se encuentra por el id que lleva dentro, no por el nombre del fichero (nota de Yema, C-0001-space)."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, base  # noqa: E402
from nucleo import contrato, puerta, yema  # noqa: E402


class TestBorradorPorId(Entorno):
    def setUp(self):
        super().setUp()
        self.c = base(self.trabajo)
        self.c["estado"] = "borrador"
        (self.yema / "contratos/borradores/C-0001-space.json").write_text(json.dumps(self.c))

    def cli(self, *args, tty=False):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = yema.main(list(args), raiz=self.yema, tty=tty)
        return rc, out.getvalue() + err.getvalue()

    def test_resumen_por_id(self):
        rc, out = self.cli("resumen", "C-0001")
        self.assertEqual(rc, 0, out)
        self.assertIn("C-0001", out)

    def test_estado_muestra_el_id(self):
        visible, detalle = yema.situacion(self.yema)
        self.assertIn("C-0001", detalle)
        self.assertNotIn("C-0001-space", detalle)

    def test_aprobar_por_id_y_retira_el_borrador(self):
        rc, out = self.cli("aprobar", "C-0001", contrato.huella(self.c)[:8], tty=True)
        self.assertEqual(rc, 0, out)
        self.assertFalse((self.yema / "contratos/borradores/C-0001-space.json").exists())
        self.assertTrue((self.yema / "contratos/C-0001.json").exists())

    def test_la_puerta_lo_encuentra_por_id(self):
        self.assertIsNotNone(puerta._contrato_de_gobierno(self.yema, "C-0001"))

    def test_id_con_barra_sigue_rechazado(self):
        self.assertIsNone(puerta._contrato_de_gobierno(self.yema, "../C-0001"))


if __name__ == "__main__":
    unittest.main()
