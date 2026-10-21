"""El arranque es el primer objetivo de la poda: AGENTS.md ≤ 600 palabras."""
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LIMITE = 600


class TestArranque(unittest.TestCase):
    def test_agents_cabe_en_el_presupuesto(self):
        palabras = len((RAIZ / "AGENTS.md").read_text(encoding="utf-8").split())
        self.assertLessEqual(palabras, LIMITE, f"AGENTS.md tiene {palabras} palabras")

    def test_instalar_prepara_estado_ajustes_locales_y_cli(self):
        import io
        import json
        import os
        import shutil
        import tempfile
        from contextlib import redirect_stdout
        import sys
        sys.path.insert(0, str(RAIZ))
        from nucleo import yema
        with tempfile.TemporaryDirectory() as t:
            codigo = Path(t) / "yema"
            shutil.copytree(RAIZ, codigo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            casa = Path(t) / "casa"
            estado = casa / ".yema"
            pol = json.loads((codigo / "gobierno/politica.json").read_text())
            pol["estado"] = str(estado)
            (codigo / "gobierno/politica.json").write_text(json.dumps(pol))
            with redirect_stdout(io.StringIO()):
                rc = yema.main(["instalar", "--bin", str(casa / "bin")], raiz=codigo, tty=True)
            self.assertEqual(rc, 0)
            self.assertEqual(oct(estado.stat().st_mode & 0o777), "0o700")
            for d in ("contratos/borradores", "evidencia", "memoria", "buzon/salida", "aprobaciones"):
                self.assertTrue((estado / d).is_dir(), d)
            local = json.loads((codigo / ".claude/settings.local.json").read_text())
            self.assertIn(str(estado), local["permissions"]["additionalDirectories"])
            self.assertEqual(os.path.realpath(casa / "bin/yema"), str(codigo / "bin/yema"))

    def test_ordenes_libres_permitidas_y_aprobar_no(self):
        import json
        permitidas = json.loads((RAIZ / ".claude/settings.json").read_text())["permissions"]["allow"]
        for sub in ("estado", "resumen", "validar", "evidencia", "checkpoint", "cuidado", "copia", "admitir",
                    "suspender", "revocar"):
            self.assertIn(f"Bash(yema {sub}:*)", permitidas)
        self.assertFalse(any("aprobar" in p or "instalar" in p or "transicion" in p for p in permitidas))

    def test_settings_local_no_se_versiona(self):
        self.assertIn(".claude/settings.local.json", (RAIZ / ".gitignore").read_text())

    def test_claude_md_solo_importa_agents(self):
        self.assertEqual((RAIZ / "CLAUDE.md").read_text().strip(), "@AGENTS.md")

    def test_ejemplos_de_contrato_validos(self):
        import sys
        sys.path.insert(0, str(RAIZ))
        from nucleo import contrato
        for f in (RAIZ / "ejemplos").glob("*.json"):
            self.assertEqual(contrato.errores(contrato.cargar(f)), [], f.name)


if __name__ == "__main__":
    unittest.main()
