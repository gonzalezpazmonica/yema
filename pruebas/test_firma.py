"""F4: aprobación firmada con una clave que la agente no puede leer, y comodines en lecturas vetadas."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, Entorno, base, politica  # noqa: E402
from nucleo import contrato, firma, puerta, yema  # noqa: E402


class TestFirma(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.estado = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clave_se_crea_privada_y_estable(self):
        k1 = firma.clave(self.estado, crear=True)
        k2 = firma.clave(self.estado)
        self.assertEqual(k1, k2)
        ruta = firma.ruta_clave(self.estado)
        self.assertEqual(ruta.stat().st_mode & 0o777, 0o600)

    def test_sin_clave_y_sin_crear(self):
        self.assertIsNone(firma.clave(self.estado))

    def test_firma_verifica_y_detecta_cambios(self):
        k = firma.clave(self.estado, crear=True)
        c = base(self.estado)
        c, _ = contrato.transicion(c, "aprobado", "operadora", "ok", politica(), AHORA)
        c["autoridad"]["aprobacion"]["firma"] = firma.firmar(c, k)
        self.assertTrue(firma.verificar(c, k))
        c["autoridad"]["aprobacion"]["por"] = "otra"
        self.assertFalse(firma.verificar(c, k))

    def test_firma_falsa(self):
        k = firma.clave(self.estado, crear=True)
        c = base(self.estado)
        c, _ = contrato.transicion(c, "aprobado", "operadora", "ok", politica(), AHORA)
        c["autoridad"]["aprobacion"]["firma"] = "0" * 64
        self.assertFalse(firma.verificar(c, k))


class TestPuertaConFirma(Entorno):
    def setUp(self):
        super().setUp()
        self.pol = {**politica(), "firma_aprobacion": True}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(self.pol))

    def activo_firmado(self, firmar=True):
        c = base(self.trabajo)
        c, _ = contrato.transicion(c, "aprobado", "operadora", "ok", self.pol, AHORA)
        if firmar:
            c["autoridad"]["aprobacion"]["politica"] = puerta.huella_politica(self.pol)  # como «yema aprobar»
            c["autoridad"]["aprobacion"]["firma"] = firma.firmar(c, firma.clave(self.yema, crear=True))
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "ok", self.pol, AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "ok", self.pol, AHORA)
        self.activar(c)

    def editar(self):
        return self.decide("Edit", {"file_path": str(self.trabajo / "src/a.py")})

    def test_firmado_vale(self):
        self.activo_firmado()
        self.assertTrue(self.editar()[0])

    def test_sin_firma_no_vale(self):
        firma.clave(self.yema, crear=True)
        self.activo_firmado(firmar=False)
        ok, motivo, _ = self.editar()
        self.assertFalse(ok)
        self.assertIn("firma", motivo)

    def test_sin_clave_no_vale(self):
        self.activo_firmado(firmar=False)
        ok, motivo, _ = self.editar()
        self.assertFalse(ok)
        self.assertIn("firma", motivo)

    def test_la_clave_no_se_lee(self):
        firma.clave(self.yema, crear=True)
        ruta = firma.ruta_clave(self.yema)
        self.assertFalse(self.decide("Read", {"file_path": str(ruta)})[0])
        self.assertFalse(self.decide("Bash", {"command": f"cat {ruta}"})[0])
        self.assertFalse(self.decide("Bash", {"command": f"cat {ruta.parent}/*"})[0])

    def test_grep_sobre_la_carpeta_de_estado_no_lee_la_clave(self):
        firma.clave(self.yema, crear=True)
        ok, motivo, _ = self.decide("Grep", {"pattern": ".", "path": str(self.yema)})
        self.assertFalse(ok)
        self.assertIn("vetada", motivo)

    def test_grep_en_el_proyecto_sigue_permitido(self):
        self.assertTrue(self.decide("Grep", {"pattern": "x", "path": str(self.trabajo)})[0])

    def test_la_clave_no_se_escribe(self):
        ruta = firma.ruta_clave(self.yema)
        self.assertFalse(self.decide("Write", {"file_path": str(ruta), "content": "x"})[0])


class TestComodinesEnVetadas(Entorno):
    def test_comodin_que_abre_una_vetada(self):
        secreta = Path(self.tmp.name) / "casa/.ssh"
        secreta.mkdir(parents=True)
        (secreta / "id_ed25519").write_text("clave")
        pol = {**politica(), "lectura_vetada": [str(secreta) + "/*"]}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))
        casa = Path(self.tmp.name) / "casa"
        self.assertFalse(self.decide("Bash", {"command": f"cat {casa}/.s*/id_*"})[0])
        self.assertFalse(self.decide("Bash", {"command": f"head {casa}/.ss?/id_ed25519"})[0])

    def test_grep_que_abarca_una_vetada(self):
        secreta = Path(self.tmp.name) / "casa/.ssh"
        secreta.mkdir(parents=True)
        pol = {**politica(), "lectura_vetada": [str(secreta) + "/*"]}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))
        self.assertFalse(self.decide("Grep", {"pattern": "BEGIN", "path": str(Path(self.tmp.name) / "casa")})[0])

    def test_comodin_inocente_sigue_permitido(self):
        (self.trabajo / "src/a.py").write_text("x")
        self.assertTrue(self.decide("Bash", {"command": f"cat {self.trabajo}/src/*.py"})[0])


class TestAprobarFirma(Entorno):
    def test_aprobar_por_terminal_firma(self):
        pol = {**politica(), "firma_aprobacion": True}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))
        (self.yema / "contratos/borradores").mkdir(parents=True, exist_ok=True)
        c = base(self.trabajo)
        c["estado"] = "borrador"
        (self.yema / "contratos/borradores/C-0001.json").write_text(json.dumps(c))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = yema.main(["aprobar", "C-0001", contrato.huella(c)[:8]], raiz=self.yema, tty=True)
        self.assertEqual(rc, 0, err.getvalue())
        guardado = contrato.cargar(self.yema / "contratos/C-0001.json")
        self.assertTrue(firma.verificar(guardado, firma.clave(self.yema)))
        self.assertTrue(self.decide("Edit", {"file_path": str(self.trabajo / "src/a.py")})[0])


if __name__ == "__main__":
    unittest.main()
