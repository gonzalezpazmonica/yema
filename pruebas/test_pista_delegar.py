"""Si delegar no está concedido, el rechazo dice que lo haga ella misma (tarea E: Yema citó sin abrir las fuentes)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, aprobado  # noqa: E402


class TestPistaDelegar(Entorno):
    def test_rechazo_de_delegar_dice_hazlo_tu(self):
        self.activar(aprobado(self.trabajo))
        ok, motivo, efecto = self.decide("Agent", {"prompt": "lee estas páginas", "subagent_type": "general-purpose"})
        self.assertFalse(ok)
        self.assertEqual(efecto, "delegar")
        self.assertIn("WebFetch", motivo)
        self.assertIn("tú misma", motivo)


if __name__ == "__main__":
    unittest.main()
