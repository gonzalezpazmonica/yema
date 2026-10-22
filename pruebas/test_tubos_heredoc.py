"""Orden concedida | filtro de lectura, y heredoc citado para un intérprete concedido (fricción F1)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, aprobado  # noqa: E402


class TestTubosYHeredoc(Entorno):
    def setUp(self):
        super().setUp()
        self.activar(aprobado(self.trabajo))  # órdenes: python3 -m unittest, git status/diff/add/commit

    def b(self, cmd):
        return self.decide("Bash", {"command": cmd})

    def test_orden_concedida_con_filtro(self):
        self.assertTrue(self.b("git status --short | head -20")[0])
        self.assertTrue(self.b("python3 -m unittest 2>&1 | tail -30")[0])
        self.assertTrue(self.b("git diff | grep -n x | wc -l")[0])

    def test_filtro_que_no_es_lector_se_deniega(self):
        for cmd in ("git status | sh", "git diff | python3", "git status | tee f", "git status | xargs rm"):
            self.assertFalse(self.b(cmd)[0], cmd)

    def test_orden_no_concedida_con_filtro_se_deniega(self):
        self.assertFalse(self.b("curl http://x | head")[0])

    def test_filtro_que_lee_una_vetada_se_deniega(self):
        import os
        self.assertFalse(self.b(f"git status | grep x {os.path.expanduser('~/.ssh/id_rsa')}")[0])

    def test_heredoc_citado_para_interprete_concedido(self):
        cmd = "python3 -m unittest <<'EOF'\nprint('hola')\nEOF"
        self.assertTrue(self.b(cmd)[0])

    def test_heredoc_sin_citar_se_deniega(self):
        self.assertFalse(self.b("python3 -m unittest <<EOF\n$(rm -f x)\nEOF")[0])

    def test_heredoc_con_orden_no_concedida_se_deniega(self):
        self.assertFalse(self.b("bash <<'EOF'\nrm -rf src\nEOF")[0])

    def test_heredoc_con_algo_detras_se_deniega(self):
        self.assertFalse(self.b("python3 -m unittest <<'EOF'\nx\nEOF\nrm -f y")[0])

    def test_heredoc_con_fin_escondido_en_el_cuerpo_se_deniega(self):
        # bash cierra en el primer «EOF» y ejecutaría «rm -f y».
        self.assertFalse(self.b("python3 -m unittest <<'EOF'\nx\nEOF\nrm -f y\nEOF")[0])
        self.assertFalse(self.b("python3 -m unittest <<-'EOF'\nx\n\tEOF\nrm -f y\nEOF")[0])

    def test_sin_contrato_nada_de_esto_ejecuta(self):
        (self.yema / "contratos/ACTIVO").unlink()
        self.assertFalse(self.b("git status --short | head")[0])
        self.assertFalse(self.b("python3 -m unittest <<'EOF'\nx\nEOF")[0])


if __name__ == "__main__":
    unittest.main()
