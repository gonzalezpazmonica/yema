"""«Contrato inválido» dice por qué (nota de Yema: apareció sin causa al endurecer la regla de scripts)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, aprobado, politica  # noqa: E402
from nucleo import contrato  # noqa: E402


class TestInvalidoConCausa(Entorno):
    def test_vigente_dice_la_causa(self):
        c = aprobado(self.trabajo)
        c["autoridad"]["ordenes"].append("bash /opt/x.sh")
        ok, motivo = contrato.vigente(c, politica())
        self.assertFalse(ok)
        self.assertIn("contrato inválido", motivo)
        self.assertIn("sin huella", motivo)
        self.assertIn("nueva versión", motivo)


if __name__ == "__main__":
    unittest.main()
