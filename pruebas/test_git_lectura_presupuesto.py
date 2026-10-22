"""Las consultas git de solo lectura siguen necesitando estar en el contrato, pero no gastan presupuesto
(C-0001: 25 de los 26 primeros efectos eran git log/show/diff del reconocimiento)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, Entorno, aprobado  # noqa: E402
from nucleo import puerta  # noqa: E402


class TestGitLectura(Entorno):
    def setUp(self):
        super().setUp()
        self.activar(aprobado(self.trabajo))  # órdenes: git status, git diff, git add, git commit…

    def ev(self, cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(self.trabajo)}

    def usados(self):
        return puerta.efectos_usados(self.yema / "evidencia/C-0001.jsonl")

    def test_consultas_no_gastan(self):
        for cmd in ("git status", "git diff", "git diff --stat"):
            self.assertTrue(puerta.evaluar_y_registrar(self.ev(cmd), self.yema, AHORA)[0], cmd)
        self.assertEqual(self.usados(), 0)

    def test_cambios_si_gastan(self):
        self.assertTrue(puerta.evaluar_y_registrar(self.ev("git add src/a.py"), self.yema, AHORA)[0])
        self.assertEqual(self.usados(), 1)

    def test_consulta_no_listada_sigue_denegada(self):
        self.assertFalse(puerta.evaluar_y_registrar(self.ev("git log"), self.yema, AHORA)[0])

    def test_es_git_de_lectura(self):
        si = ("git status", "git log --oneline", "git show HEAD", "git diff a b", "git rev-list --count x",
              "git merge-base main x", "git remote -v", "git branch", "git branch -a", "git rev-parse HEAD")
        no = ("git com" + "mit -m x", "git branch nueva", "git branch -D x", "git remote add o u",
              "git merge x", "git cherry-pick a", "git pu" + "sh", "git diff --output=f")
        for c in si:
            self.assertTrue(puerta.es_git_de_lectura(c.split()), c)
        for c in no:
            self.assertFalse(puerta.es_git_de_lectura(c.split()), c)


if __name__ == "__main__":
    unittest.main()
