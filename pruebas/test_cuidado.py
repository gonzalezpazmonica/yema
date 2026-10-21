"""Cuidado: chequeos de salud y copias del estado privado."""
import json
import os
import sys
import tarfile
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import politica  # noqa: E402
from nucleo import cuidado  # noqa: E402


class TestCuidado(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.estado, self.copias = t / "estado", t / "copias"
        (self.estado / "memoria").mkdir(parents=True)
        (self.estado / "memoria/nota.md").write_text("hola")
        os.chmod(self.estado, 0o700)
        self.pol = {**politica(), "copias": str(self.copias), "descanso": {"desde": 23, "hasta": 8}}

    def tearDown(self):
        self.tmp.cleanup()

    def niveles(self, ahora):
        return {k: n for n, k, _ in cuidado.chequeos(self.estado, self.pol, ahora)}

    def test_sin_copia_es_aviso(self):
        self.assertEqual(self.niveles(datetime(2026, 10, 21, 12))["copia"], "aviso")

    def test_copia_reciente_ok_y_restaurable(self):
        ruta = cuidado.copia(self.estado, self.pol)
        self.assertTrue(ruta.exists())
        self.assertEqual(oct(ruta.stat().st_mode & 0o777), "0o600")
        with tarfile.open(ruta) as tar:
            self.assertIn("estado/memoria/nota.md", tar.getnames())
        self.assertEqual(self.niveles(datetime.now())["copia"], "ok")

    def test_copia_vieja_es_aviso(self):
        ruta = cuidado.copia(self.estado, self.pol)
        viejo = time.time() - 3 * 86400
        os.utime(ruta, (viejo, viejo))
        self.assertEqual(self.niveles(datetime.now())["copia"], "aviso")

    def test_copias_rotan(self):
        for i in range(cuidado.COPIAS_A_GUARDAR + 3):
            r = cuidado.copia(self.estado, self.pol, sufijo=str(i))
            os.utime(r, (time.time() - 1000 + i, time.time() - 1000 + i))
        cuidado.rotar(self.pol)
        self.assertEqual(len(list(self.copias.glob("*.tar.gz"))), cuidado.COPIAS_A_GUARDAR)

    def test_permisos_abiertos_es_alerta(self):
        os.chmod(self.estado, 0o755)
        self.assertEqual(self.niveles(datetime(2026, 10, 21, 12))["permisos"], "alerta")

    def test_descanso(self):
        self.assertEqual(self.niveles(datetime(2026, 10, 21, 2))["descanso"], "aviso")
        self.assertEqual(self.niveles(datetime(2026, 10, 21, 12))["descanso"], "ok")

    def test_disco(self):
        self.assertIn(self.niveles(datetime(2026, 10, 21, 12))["disco"], ("ok", "aviso", "alerta"))

    def test_cli_cuidado_y_copia(self):
        import io
        import json as _json
        from contextlib import redirect_stdout
        from nucleo import yema
        raiz = Path(self.tmp.name) / "codigo"
        (raiz / "gobierno").mkdir(parents=True)
        (raiz / "gobierno/politica.json").write_text(_json.dumps({**self.pol, "estado": str(self.estado)}))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(yema.main(["copia"], raiz=raiz, tty=False), 0)
            yema.main(["cuidado"], raiz=raiz, tty=False)
        self.assertIn("copia", out.getvalue())
        self.assertEqual(len(list(self.copias.glob("*.tar.gz"))), 1)

    def test_es_hora_de_descanso(self):
        self.assertTrue(cuidado.es_descanso(self.pol, datetime(2026, 10, 21, 23, 30)))
        self.assertTrue(cuidado.es_descanso(self.pol, datetime(2026, 10, 21, 7, 59)))
        self.assertFalse(cuidado.es_descanso(self.pol, datetime(2026, 10, 21, 8, 0)))


if __name__ == "__main__":
    unittest.main()
