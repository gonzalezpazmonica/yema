"""evals/metodo.py: huellas del prerregistro, del corpus, de la política y de la implementación, y límites declarados."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals import metodo  # noqa: E402


class TestMetodo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        (t / "corpus/a").mkdir(parents=True)
        (t / "corpus/a/tarea.json").write_text('{"x": 1}')
        (t / "corpus/b.md").write_text("b")
        (t / "criterios.md").write_text("D1 ...")
        (t / "politica.json").write_text('{"p": 1}')
        (t / "impl").mkdir()
        (t / "impl/puerta.py").write_text("x = 1\n")
        self.t = t

    def tearDown(self):
        self.tmp.cleanup()

    def registro(self, **kw):
        t = self.t
        return metodo.huellas(t / "criterios.md", t / "corpus", t / "politica.json", t / "impl",
                              limitaciones=kw.get("limitaciones", ["UNA_REPETICION"]))

    def test_campos_y_limites(self):
        r = self.registro()
        for k in ("prerregistro", "corpus", "politica", "implementacion"):
            self.assertEqual(len(r[k]), 64, k)
        self.assertEqual(r["limitaciones"], ["UNA_REPETICION"])

    def test_estable(self):
        self.assertEqual(self.registro(), self.registro())

    def test_cambiar_un_byte_del_corpus_cambia_su_huella(self):
        antes = self.registro()
        (self.t / "corpus/a/tarea.json").write_text('{"x": 2}')
        despues = self.registro()
        self.assertNotEqual(antes["corpus"], despues["corpus"])
        self.assertEqual(antes["prerregistro"], despues["prerregistro"])

    def test_renombrar_un_fichero_cambia_la_huella(self):
        antes = self.registro()["corpus"]
        (self.t / "corpus/b.md").rename(self.t / "corpus/c.md")
        self.assertNotEqual(antes, self.registro()["corpus"])

    def test_sin_limitaciones_se_rechaza(self):
        with self.assertRaises(ValueError):
            self.registro(limitaciones=[])

    def test_comprobar_detecta_cambios(self):
        guardado = self.registro()
        self.assertEqual(metodo.diferencias(guardado, self.registro()), [])
        (self.t / "politica.json").write_text('{"p": 2}')
        self.assertEqual(metodo.diferencias(guardado, self.registro()), ["politica"])

    def test_cli_escribe_json(self):
        t = self.t
        salida = t / "metodo.json"
        rc = metodo.main(["--criterios", str(t / "criterios.md"), "--corpus", str(t / "corpus"),
                          "--politica", str(t / "politica.json"), "--implementacion", str(t / "impl"),
                          "--limitacion", "UNA_REPETICION", "--salida", str(salida)])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(salida.read_text())["limitaciones"], ["UNA_REPETICION"])


if __name__ == "__main__":
    unittest.main()
