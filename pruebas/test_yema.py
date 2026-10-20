"""CLI humana: validar, transicionar, activar y verificar evidencia."""
import io
import json
from contextlib import redirect_stderr, redirect_stdout
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import RAIZ, Entorno, base  # noqa: E402
from nucleo import yema  # noqa: E402


class TestCli(Entorno):
    def cli(self, *args, tty=True):
        """Con tty=True llama en proceso (como una persona en su terminal);
        con tty=False lanza un proceso sin terminal, como haría un agente."""
        if not tty:
            env = {**os.environ, "YEMA_RAIZ": str(self.yema)}
            return subprocess.run([sys.executable, str(RAIZ / "nucleo/yema.py"), *args],
                                  capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = yema.main(list(args), raiz=self.yema, tty=True)
        return subprocess.CompletedProcess(args, rc, out.getvalue(), err.getvalue())

    def borrador(self):
        c = base(self.trabajo)
        c["estado"] = "candidato"
        c["autoridad"]["caduca"] = "2999-01-01T00:00:00+00:00"
        ruta = self.yema / "contratos/borradores/C-0001.json"
        ruta.write_text(json.dumps(c))
        return ruta

    def test_validar(self):
        r = self.cli("validar", str(self.borrador()))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_ciclo_completo(self):
        self.assertEqual(self.cli("admitir", str(self.borrador())).returncode, 0)
        for estado in ("en_revision", "aprobado", "aprovisionado"):
            r = self.cli("transicion", "C-0001", estado, "--por", "operadora", "--motivo", "ok")
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.cli("activar", "C-0001", "--por", "operadora").returncode, 0)
        r = self.cli("estado")
        self.assertIn("C-0001", r.stdout)
        self.assertIn("vigente", r.stdout)

    def test_aprobar_exige_terminal_humana(self):
        self.cli("admitir", str(self.borrador()))
        self.cli("transicion", "C-0001", "en_revision", "--por", "operadora", "--motivo", "ok")
        r = self.cli("transicion", "C-0001", "aprobado", "--por", "operadora", "--motivo", "ok", tty=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("terminal", r.stderr)

    def test_autoaprobacion_rechazada(self):
        self.cli("admitir", str(self.borrador()))
        self.cli("transicion", "C-0001", "en_revision", "--por", "operadora", "--motivo", "ok")
        r = self.cli("transicion", "C-0001", "aprobado", "--por", "yema", "--motivo", "yo")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
