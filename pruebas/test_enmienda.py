"""Enmienda: una versión nueva del contrato activo se aprueba por su huella y sustituye a la anterior."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, aprobado, base  # noqa: E402
from nucleo import contrato, puerta, yema  # noqa: E402


class TestEnmienda(Entorno):
    def setUp(self):
        super().setUp()
        self.v1 = aprobado(self.trabajo)
        self.activar(self.v1)
        v2 = base(self.trabajo)
        v2["version"] = 2
        v2["estado"] = "borrador"
        v2["autoridad"]["ordenes"] = v2["autoridad"]["ordenes"] + ["git merge-base"]
        self.v2 = v2
        (self.yema / "contratos/borradores/C-0001.json").write_text(json.dumps(v2))

    def cli(self, *args, tty=True):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = yema.main(list(args), raiz=self.yema, tty=tty)
        return rc, out.getvalue() + err.getvalue()

    def test_la_puerta_encuentra_la_version_por_huella(self):
        h2 = contrato.huella(self.v2)[:8]
        self.assertEqual(puerta._contrato_de_gobierno(self.yema, "C-0001", h2)["version"], 2)
        h1 = contrato.huella(self.v1)[:8]
        self.assertEqual(puerta._contrato_de_gobierno(self.yema, "C-0001", h1)["version"], 1)

    def test_aprobar_la_enmienda(self):
        rc, out = self.cli("aprobar", "C-0001", contrato.huella(self.v2)[:8])
        self.assertEqual(rc, 0, out)
        activo = contrato.cargar(self.yema / "contratos/C-0001.json")
        self.assertEqual(activo["version"], 2)
        self.assertEqual(activo["estado"], "activo")
        self.assertIn("git merge-base", activo["autoridad"]["ordenes"])
        self.assertFalse((self.yema / "contratos/borradores/C-0001.json").exists())

    def test_la_puerta_pregunta_por_la_enmienda(self):
        (self.yema / "nucleo/yema.py").write_text("")
        ev = {"tool_name": "Bash", "tool_input": {"command": f"python3 {self.yema}/nucleo/yema.py aprobar C-0001 "
                                                              f"{contrato.huella(self.v2)[:8]}"},
              "cwd": str(self.trabajo), "permission_mode": "default"}
        ok, motivo, _ = puerta.decidir(ev, self.yema)
        self.assertIs(ok, puerta.PREGUNTAR, motivo)
        self.assertIn("v2", motivo)

    def test_huella_que_no_es_de_ninguna_version(self):
        rc, out = self.cli("aprobar", "C-0001", "deadbeef")
        self.assertNotEqual(rc, 0)
        self.assertEqual(contrato.cargar(self.yema / "contratos/C-0001.json")["version"], 1)


if __name__ == "__main__":
    unittest.main()
