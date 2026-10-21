"""Índice perezoso de capacidades de Savia: encontrarlas sin buscar a ciegas."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, politica  # noqa: E402
from nucleo import yema  # noqa: E402

INDICE = """# Savia Capability Map — INDEX
> hash: x | resources: 4
[research] tech-research-agent — investigar,fuentes,tecnologia — skill:.claude/skills/tech-research-agent/SKILL.md
[knowledge] context-dome — cupula,contexto,crear — skill:.claude/skills/context-dome/SKILL.md
[pm] sprint-status — sprint,estado,velocity — script:scripts/sprint-status.sh
[digest] pdf-digest — pdf,documento,digestion — cmd:.claude/commands/pdf-digest.md
"""


class TestSavia(Entorno):
    def setUp(self):
        super().setUp()
        self.savia = Path(self.tmp.name) / "savia"
        (self.savia / ".scm").mkdir(parents=True)
        (self.savia / ".scm/INDEX.scm").write_text(INDICE)
        (self.yema / "gobierno/politica.json").write_text(json.dumps({**politica(), "savia": str(self.savia)}))

    def cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = yema.main(list(args), raiz=self.yema, tty=False)
        return rc, out.getvalue()

    def test_busca_por_tema(self):
        rc, out = self.cli("savia", "cupula")
        self.assertEqual(rc, 0)
        self.assertIn("context-dome", out)
        self.assertIn(str(self.savia / ".claude/skills/context-dome/SKILL.md"), out)
        self.assertNotIn("sprint-status", out)

    def test_varias_palabras_ordena_por_coincidencias(self):
        rc, out = self.cli("savia", "investigar", "fuentes")
        self.assertTrue(out.strip().splitlines()[0].count("tech-research-agent"))

    def test_sin_resultados(self):
        rc, out = self.cli("savia", "zzzz")
        self.assertEqual(rc, 1)

    def test_es_libre_para_yema(self):
        from nucleo import puerta
        (self.yema / "nucleo/yema.py").write_text("")
        ok, motivo, _ = self.decide("Bash", {"command": f"python3 {self.yema}/nucleo/yema.py savia cupula"})
        self.assertIs(ok, True, motivo)


if __name__ == "__main__":
    unittest.main()
