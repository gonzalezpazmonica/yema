"""El trailer «Co-Authored-By: Nombre <correo>» de un `git commit` pasa la puerta; cualquier otro «<» o «>»
sigue rechazado como orden compuesta o con redirección."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, Entorno, aprobado  # noqa: E402
from nucleo import puerta  # noqa: E402

TRAILER = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"


class TestCoautor(Entorno):
    def setUp(self):
        super().setUp()
        self.activar(aprobado(self.trabajo))  # órdenes: git add, git commit…

    def ok(self, cmd, cwd=None):
        return self.decide("Bash", {"command": cmd}, cwd)[0]

    def test_trailer_en_comillas_dobles_y_simples(self):
        self.assertTrue(self.ok(f'git commit -m "feat: x" -m "{TRAILER}"'))
        self.assertTrue(self.ok(f"git commit -m 'feat: x' -m '{TRAILER}'"))

    def test_varios_trailers(self):
        self.assertTrue(self.ok(f'git commit -m x -m "{TRAILER}" -m "Co-Authored-By: Otra <otra.p+x@ej.org>"'))

    def test_con_cd_y_commit(self):
        self.assertTrue(self.ok(f'cd {self.trabajo} && git commit -m x -m "{TRAILER}"', cwd=self.yema))

    def test_sin_el_arreglo_el_correo_era_redireccion(self):
        self.assertEqual(puerta.sin_coautor(f'git commit -m "{TRAILER}"'),
                         'git commit -m "Co-Authored-By: Claude Sonnet 5.5 "')
        self.assertEqual(puerta.sin_coautor(f'git add "{TRAILER}"'), f'git add "{TRAILER}"')

    def test_otros_menor_y_mayor_siguen_rechazados(self):
        for cmd in (
            'git commit -m "a <b>"',
            'git commit -m "x" > fuera.txt',
            f'git commit -m "{TRAILER}" > fuera.txt',
            f'git commit -m "{TRAILER}" < entrada.txt',
            f'git commit -m "{TRAILER}"; rm x',
            f'git commit -m "{TRAILER} $(id)"',
            f'git commit -m "{TRAILER} <otro@ej.org>"',
            f"git commit -m x {TRAILER}",
            f'git commit -m "x"{TRAILER}""',
            'git commit -m "Co-Authored-By: $(id) <a@b.co>"',
            'git commit -m "Co-Authored-By: N <a@b>"',
            'git commit -m "Co-Authored-By: N <a b@c.co>"',
            'git commit -m "Co-Authored-By: N <a@b.co>" -m "<x>"',
            'git commit -m "Co-Authored-By: `id` <a@b.co>"',
            f'git add "{TRAILER}"',
        ):
            ok, motivo, _ = self.decide("Bash", {"command": cmd})
            self.assertFalse(ok, cmd)

    def test_solo_commit(self):
        self.assertEqual(puerta.sin_coautor(f'git log --format="{TRAILER}"'), f'git log --format="{TRAILER}"')
        self.assertEqual(puerta.sin_coautor(f'echo "{TRAILER}"'), f'echo "{TRAILER}"')

    def test_sigue_contando_como_efecto(self):
        puerta.evaluar_y_registrar({"tool_name": "Bash", "cwd": str(self.trabajo),
                                    "tool_input": {"command": f'git commit -m x -m "{TRAILER}"'}}, self.yema, AHORA)
        self.assertEqual(puerta.efectos_usados(self.yema / "evidencia/C-0001.jsonl"), 1)


if __name__ == "__main__":
    unittest.main()
