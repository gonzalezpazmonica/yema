"""Juicio ciego reutilizable: anonimizar respuestas y guardar el mapa aparte."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals import ciego  # noqa: E402


class TestCiego(unittest.TestCase):
    def test_anonimiza_y_guarda_mapa_aparte(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            for sis in ("savia", "yema"):
                (t / "runs" / sis).mkdir(parents=True)
                for i in (1, 2):
                    (t / "runs" / sis / f"{i}.md").write_text(f"respuesta de {sis} {i}")
            mapa = ciego.anonimizar(t / "runs", t / "ciego", t / "mapa-secreto.json", tarea="D", semilla=7)
            self.assertEqual(sorted(mapa), ["savia", "yema"])
            self.assertEqual(sorted(mapa.values()), ["X", "Y"])
            nombres = sorted(p.name for p in (t / "ciego").iterdir())
            self.assertEqual(nombres, ["D-X-1.md", "D-X-2.md", "D-Y-1.md", "D-Y-2.md"])
            self.assertEqual(json.loads((t / "mapa-secreto.json").read_text()), {"D": mapa})
            for p in (t / "ciego").iterdir():
                self.assertNotIn(p.read_text().split()[2], ("savia", "yema"))

    def test_borra_nombres_de_sistema_en_el_texto(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            for sis in ("savia", "yema"):
                (t / "runs" / sis).mkdir(parents=True)
                (t / "runs" / sis / "1.md").write_text(f"Soy {sis.capitalize()} y usé SaviaDomains")
            ciego.anonimizar(t / "runs", t / "ciego", t / "mapa.json", tarea="D")
            for p in (t / "ciego").iterdir():
                texto = p.read_text()
                self.assertNotIn("Yema", texto)
                self.assertNotRegex(texto, r"\bSavia\b")


if __name__ == "__main__":
    unittest.main()
