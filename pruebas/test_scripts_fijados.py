"""Un script que el contrato deja ejecutar queda fijado por su huella: si cambia, la puerta lo deniega.
También: resumen enseña todas las versiones de un contrato y «yema --help» es libre (petición de Yema)."""
import hashlib
import io
import json
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, Entorno, base, politica  # noqa: E402
from nucleo import contrato, puerta, yema  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class TestScriptsFijados(Entorno):
    def setUp(self):
        super().setUp()
        self.script = Path(self.tmp.name) / "repetir.sh"
        self.script.write_text("#!/bin/sh\necho hola\n")

    def activo(self, scripts):
        c = base(self.trabajo)
        c["autoridad"]["ordenes"] = c["autoridad"]["ordenes"] + [f"bash {self.script}"]
        c["autoridad"]["scripts"] = scripts
        for e in ("aprobado", "aprovisionado", "activo"):
            c, err = contrato.transicion(c, e, "operadora", "x", politica(), AHORA)
            self.assertIsNone(err)
        self.activar(c)
        return c

    def test_orden_de_script_exige_huella_en_el_contrato(self):
        c = base(self.trabajo)
        c["autoridad"]["ordenes"].append(f"bash {self.script}")
        self.assertTrue(any("huella" in e for e in contrato.errores(c)))
        c["autoridad"]["scripts"] = {str(self.script): sha(self.script)}
        self.assertEqual(contrato.errores(c), [])

    def test_script_intacto_se_ejecuta(self):
        self.activo({str(self.script): sha(self.script)})
        self.assertTrue(self.decide("Bash", {"command": f"bash {self.script} 2 x"})[0])

    def test_script_cambiado_se_deniega(self):
        self.activo({str(self.script): sha(self.script)})
        self.script.write_text("#!/bin/sh\nnpm publish\n")
        ok, motivo, _ = self.decide("Bash", {"command": f"bash {self.script} 2 x"})
        self.assertFalse(ok)
        self.assertIn("cambió", motivo)

    def test_la_huella_del_contrato_cubre_los_scripts(self):
        c = base(self.trabajo)
        c["autoridad"]["scripts"] = {str(self.script): "a" * 64}
        h1 = contrato.huella(c)
        c["autoridad"]["scripts"] = {str(self.script): "b" * 64}
        self.assertNotEqual(h1, contrato.huella(c))


class TestVersionesYAyuda(Entorno):
    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = yema.main(list(args), raiz=self.yema, tty=False)
            except SystemExit as e:
                rc = e.code
        return rc, out.getvalue() + err.getvalue()

    def test_resumen_ensena_la_enmienda(self):
        v1 = base(self.trabajo)
        for e in ("aprobado", "aprovisionado", "activo"):
            v1, _ = contrato.transicion(v1, e, "operadora", "x", politica(), AHORA)
        self.activar(v1)
        v2 = base(self.trabajo)
        v2["version"], v2["estado"] = 2, "borrador"
        (self.yema / "contratos/borradores/C-0001.json").write_text(json.dumps(v2))
        rc, out = self.cli("resumen", "C-0001")
        self.assertEqual(rc, 0, out)
        self.assertIn(contrato.huella(v1)[:8], out)
        self.assertIn(contrato.huella(v2)[:8], out)
        self.assertIn("v2", out)

    def test_ayuda_es_libre(self):
        (self.yema / "nucleo/yema.py").write_text("")
        for a in ("--help", "-h", "ayuda"):
            ok, _, _ = self.decide("Bash", {"command": f"python3 {self.yema}/nucleo/yema.py {a}"})
            self.assertTrue(ok, a)


if __name__ == "__main__":
    unittest.main()
