"""Entorno común de las pruebas del núcleo (no es un módulo de pruebas)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from nucleo import contrato, puerta  # noqa: E402

AHORA = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)


def politica():
    return {
        "aprobadoras": ["operadora"],
        "efectos_sin_contrato": ["leer"],
        "zonas_libres": ["contratos/borradores/*", "buzon/salida/*", "memoria/*"],
        "cupulas_lectura": ["savia-docs", "SaviaLearning"],
        "lectura_vetada": ["~/.ssh/*", "~/.savia/confidentiality-key", "*.env"],
    }


def base(trabajo):
    return {
        "id": "C-0001",
        "version": 1,
        "estado": "en_revision",
        "proposito": "Prueba",
        "responsable": "operadora",
        "ejecutora": "yema",
        "nivel": "E2",
        "ambito": {"raiz": str(trabajo), "escritura": ["src/*", "pruebas/*"], "vetadas": ["src/secreto*"]},
        "autoridad": {
            "efectos": ["leer", "escribir", "ejecutar", "git-local"],
            "prohibidos": ["fusionar", "publicar", "git-remoto"],
            "ordenes": ["python3 -m unittest", "git status", "git diff", "git add", "git commit"],
            "caduca": (AHORA + timedelta(hours=8)).isoformat(),
        },
        "recursos": {"efectos_max": 50},
        "condiciones": {"post": [{"id": "pruebas", "orden": "python3 -m unittest"}]},
        "evidencia": {"requerida": ["recibo-decision", "postcondiciones"]},
    }


def aprobado(trabajo, por="operadora"):
    c = base(trabajo)
    c, err = contrato.transicion(c, "aprobado", por, "ok", politica(), AHORA)
    assert err is None, err
    c, _ = contrato.transicion(c, "aprovisionado", "operadora", "ok", politica(), AHORA)
    c, _ = contrato.transicion(c, "activo", "operadora", "ok", politica(), AHORA)
    return c


def sellar(c):
    """Aprueba y activa un contrato ya modificado (nueva huella)."""
    c = {**c, "estado": "en_revision"}
    for e in ("aprobado", "aprovisionado", "activo"):
        c, err = contrato.transicion(c, e, "operadora", "ok", politica(), AHORA)
        assert err is None, err
    return c


class Entorno(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.yema = t / "yema"
        self.trabajo = t / "trabajo"
        for d in ("gobierno", "contratos/borradores", "evidencia", "nucleo", "memoria"):
            (self.yema / d).mkdir(parents=True)
        (self.trabajo / "src").mkdir(parents=True)
        (self.yema / "gobierno/politica.json").write_text(json.dumps(politica()))

    def tearDown(self):
        self.tmp.cleanup()

    def activar(self, c):
        (self.yema / "contratos" / f"{c['id']}.json").write_text(json.dumps(c))
        (self.yema / "contratos/ACTIVO").write_text(c["id"])

    def decide(self, herramienta, entrada, cwd=None):
        ev = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(cwd or self.trabajo)}
        return puerta.decidir(ev, self.yema, AHORA)
