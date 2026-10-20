"""Contratos: esquema, ciclo de vida, aprobación y vigencia."""
import os
import subprocess
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, RAIZ, Entorno, aprobado, base, politica  # noqa: E402,F401
from nucleo import contrato  # noqa: E402


class TestContrato(Entorno):
    def test_esquema_valido(self):
        self.assertEqual(contrato.errores(base(self.trabajo)), [])

    def test_efecto_permitido_y_prohibido_a_la_vez(self):
        c = base(self.trabajo)
        c["autoridad"]["prohibidos"].append("escribir")
        self.assertTrue(any("prohibido" in e for e in contrato.errores(c)))

    def test_globs_que_escapan(self):
        c = base(self.trabajo)
        c["ambito"]["escritura"] = ["../fuera/*"]
        self.assertTrue(contrato.errores(c))
        c["ambito"]["escritura"] = ["/etc/*"]
        self.assertTrue(contrato.errores(c))

    def test_transicion_ilegal(self):
        c = base(self.trabajo)
        _, err = contrato.transicion(c, "activo", "operadora", "x", politica(), AHORA)
        self.assertIsNotNone(err)

    def test_autoaprobacion_rechazada(self):
        c = base(self.trabajo)
        _, err = contrato.transicion(c, "aprobado", "yema", "x", {**politica(), "aprobadoras": ["yema"]}, AHORA)
        self.assertIn("ejecutora", err)

    def test_aprobadora_sin_autoridad(self):
        _, err = contrato.transicion(base(self.trabajo), "aprobado", "alguien", "x", politica(), AHORA)
        self.assertIn("autoridad", err)

    def test_vigente(self):
        ok, motivo = contrato.vigente(aprobado(self.trabajo), politica(), AHORA)
        self.assertTrue(ok, motivo)

    def test_cambio_tras_aprobar_invalida(self):
        c = aprobado(self.trabajo)
        c["autoridad"]["efectos"].append("red")
        ok, motivo = contrato.vigente(c, politica(), AHORA)
        self.assertFalse(ok)
        self.assertIn("huella", motivo)

    def test_caducado(self):
        ok, motivo = contrato.vigente(aprobado(self.trabajo), politica(), AHORA + timedelta(days=1))
        self.assertFalse(ok)
        self.assertIn("caduc", motivo)

    def test_suspendido_no_vigente(self):
        c, _ = contrato.transicion(aprobado(self.trabajo), "suspendido", "operadora", "pausa", politica(), AHORA)
        self.assertFalse(contrato.vigente(c, politica(), AHORA)[0])


if __name__ == "__main__":
    unittest.main()
