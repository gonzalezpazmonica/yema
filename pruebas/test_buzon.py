"""Ideas de harness2: entregable comprobado y lecciones con evidencia en el buzón."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, base, politica  # noqa: E402
from nucleo import buzon, contrato, puerta, yema  # noqa: E402


class TestEntregableComprobado(Entorno):
    def test_post_con_orden_vale(self):
        self.assertEqual(contrato.errores(base(self.trabajo)), [])

    def test_post_solo_descriptiva_no_vale(self):
        c = base(self.trabajo)
        c["condiciones"]["post"].append({"id": "informe", "descripcion": "un informe en memoria"})
        self.assertTrue(any("informe" in e and "comprob" in e for e in contrato.errores(c)))

    def test_post_descriptiva_con_comprobacion_vale(self):
        c = base(self.trabajo)
        c["condiciones"]["post"].append({"id": "informe", "descripcion": "un informe en memoria",
                                         "comprobar": "reabrirlo y ver que tiene fuentes numeradas"})
        self.assertEqual(contrato.errores(c), [])

    def test_ejemplos_publicos_validos(self):
        raiz = Path(__file__).resolve().parent.parent / "ejemplos"
        for f in raiz.glob("*.json"):
            c = json.loads(f.read_text())
            c["ambito"]["raiz"] = str(self.trabajo)
            self.assertFalse([e for e in contrato.errores(c) if "comprob" in e], f.name)


class TestLeccion(unittest.TestCase):
    def leccion(self, **kw):
        cuerpo = {"cuando": "una tarea de cúpula en headless", "leccion": "nombrar la cúpula",
                  "evidencia": "E8: 3/3 leídas con cúpula nombrada", "confianza": "media"}
        cuerpo.update(kw)
        return {"de": "yema", "para": "savia", "tipo": "aprendizaje",
                "ts": "2026-10-21T21:00:00+02:00", "cuerpo": cuerpo}

    def test_leccion_completa(self):
        self.assertEqual(buzon.errores(self.leccion()), [])

    def test_sin_evidencia_se_rechaza(self):
        self.assertTrue(any("evidencia" in e for e in buzon.errores(self.leccion(evidencia=" "))))

    def test_sin_cuando_se_rechaza(self):
        self.assertTrue(any("cuando" in e for e in buzon.errores(self.leccion(cuando=""))))

    def test_confianza_acotada(self):
        self.assertTrue(buzon.errores(self.leccion(confianza="total")))

    def test_otros_tipos_cuerpo_libre(self):
        m = {"de": "yema", "para": "savia", "tipo": "aviso", "ts": "x", "cuerpo": "texto"}
        self.assertEqual(buzon.errores(m), [])

    def test_tipo_desconocido(self):
        m = {"de": "yema", "para": "savia", "tipo": "orden", "ts": "x", "cuerpo": "haz esto"}
        self.assertTrue(buzon.errores(m))


class TestAprende(Entorno):
    def setUp(self):
        super().setUp()
        self.estado = self.yema  # sin «estado» en la política, el estado vive junto al código

    def cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = yema.main(list(args), raiz=self.yema, tty=False)
        return rc, out.getvalue()

    def test_aprende_escribe_en_salida(self):
        rc, out = self.cli("aprende", "--cuando", "c", "--leccion", "l", "--evidencia", "e", "--confianza", "alta")
        self.assertEqual(rc, 0, out)
        ficheros = list((self.estado / "buzon/salida").glob("*.json"))
        self.assertEqual(len(ficheros), 1)
        m = json.loads(ficheros[0].read_text())
        self.assertEqual(m["tipo"], "aprendizaje")
        self.assertEqual(m["cuerpo"]["evidencia"], "e")

    def test_aprende_sin_evidencia_falla(self):
        rc, _ = self.cli("aprende", "--cuando", "c", "--leccion", "l", "--evidencia", "", "--confianza", "alta")
        self.assertNotEqual(rc, 0)
        self.assertFalse(list((self.estado / "buzon/salida").glob("*.json")))

    def test_aprende_es_gobierno_libre(self):
        self.assertIn("aprende", puerta.GOBIERNO_LIBRE)

if __name__ == "__main__":
    unittest.main()
