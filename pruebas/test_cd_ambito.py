"""Órdenes en la carpeta del contrato desde una sesión abierta en otra carpeta: «cd <raíz> && <orden>»."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, aprobado  # noqa: E402

import unittest  # noqa: E402


class TestCdAmbito(Entorno):
    def setUp(self):
        super().setUp()
        self.activar(aprobado(self.trabajo))
        self.fuera = Path(self.tmp.name) / "sesion"
        self.fuera.mkdir()

    def bash(self, cmd):
        return self.decide("Bash", {"command": cmd}, cwd=self.fuera)

    def test_sin_cd_desde_fuera_se_deniega_y_dice_como(self):
        ok, motivo, _ = self.bash("python3 -m unittest")
        self.assertFalse(ok)
        self.assertIn("cd ", motivo)

    def test_cd_a_la_raiz_y_orden_permitida(self):
        self.assertTrue(self.bash(f"cd {self.trabajo} && python3 -m unittest")[0])

    def test_cd_a_subcarpeta_de_la_raiz(self):
        self.assertTrue(self.bash(f"cd {self.trabajo}/src && git status")[0])

    def test_cd_fuera_de_la_raiz_se_deniega(self):
        self.assertFalse(self.bash(f"cd {self.fuera} && python3 -m unittest")[0])

    def test_orden_no_concedida_tras_cd_se_deniega(self):
        self.assertFalse(self.bash(f"cd {self.trabajo} && curl http://x")[0])

    def test_solo_un_cd_y_una_orden(self):
        for cmd in (f"cd {self.trabajo} && git status && git push",
                    f"cd {self.trabajo} && git status; rm x",
                    f"cd {self.trabajo} && git status | sh",
                    f"cd $(echo {self.trabajo}) && git status",
                    f"cd {self.trabajo} || git status"):
            self.assertFalse(self.bash(cmd)[0], cmd)

    def test_cd_relativo_se_resuelve_desde_la_sesion(self):
        enlace = self.fuera / "proyecto"
        enlace.symlink_to(self.trabajo)
        self.assertTrue(self.bash("cd proyecto && git status")[0])


if __name__ == "__main__":
    unittest.main()
