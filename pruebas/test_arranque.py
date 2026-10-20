"""El arranque es el primer objetivo de la poda: AGENTS.md ≤ 600 palabras."""
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LIMITE = 600


class TestArranque(unittest.TestCase):
    def test_agents_cabe_en_el_presupuesto(self):
        palabras = len((RAIZ / "AGENTS.md").read_text(encoding="utf-8").split())
        self.assertLessEqual(palabras, LIMITE, f"AGENTS.md tiene {palabras} palabras")

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
