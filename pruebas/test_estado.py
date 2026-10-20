"""Estado privado fuera del repo: contratos reales, evidencia, memoria y buzón."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, Entorno, aprobado, politica, sellar  # noqa: E402
from nucleo import puerta  # noqa: E402


class TestEstadoExterno(Entorno):
    def setUp(self):
        super().setUp()
        self.tmp2 = tempfile.TemporaryDirectory()
        self.estado = Path(self.tmp2.name) / "estado"
        for d in ("contratos/borradores", "evidencia", "memoria", "casa"):
            (self.estado / d).mkdir(parents=True)
        (self.yema / "gobierno/politica.json").write_text(json.dumps({**politica(), "estado": str(self.estado)}))

    def tearDown(self):
        self.tmp2.cleanup()
        super().tearDown()

    def activar(self, c):
        (self.estado / "contratos" / f"{c['id']}.json").write_text(json.dumps(c))
        (self.estado / "contratos/ACTIVO").write_text(c["id"])

    def test_zonas_libres_en_el_estado(self):
        for rel in ("memoria/C-0001.md", "contratos/borradores/C-2.json"):
            self.assertTrue(self.decide("Write", {"file_path": str(self.estado / rel)})[0], rel)

    def test_estado_protegido(self):
        for rel in ("contratos/C-0001.json", "contratos/ACTIVO", "evidencia/C-0001.jsonl", "casa/x.sh"):
            self.assertFalse(self.decide("Write", {"file_path": str(self.estado / rel)})[0], rel)

    def test_identidad_y_nucleo_del_repo_protegidos(self):
        c = aprobado(self.trabajo)
        c["ambito"]["raiz"] = str(self.yema)
        c["ambito"]["escritura"] = ["*"]
        self.activar(sellar(c))
        self.assertTrue(self.decide("Write", {"file_path": str(self.yema / "docs/nota.md")})[0])
        for rel in ("nucleo/puerta.py", "gobierno/politica.json", ".claude/settings.json", "ALMA.md", "AGENTS.md"):
            self.assertFalse(self.decide("Write", {"file_path": str(self.yema / rel)})[0], rel)

    def test_contrato_activo_se_lee_del_estado(self):
        self.activar(aprobado(self.trabajo))
        self.assertTrue(self.decide("Edit", {"file_path": str(self.trabajo / "src/a.py")})[0])

    def test_evidencia_en_el_estado(self):
        self.activar(aprobado(self.trabajo))
        ev = {"tool_name": "Edit", "tool_input": {"file_path": str(self.trabajo / "src/a.py")}, "cwd": str(self.trabajo)}
        puerta.evaluar_y_registrar(ev, self.yema, AHORA)
        self.assertTrue((self.estado / "evidencia/C-0001.jsonl").exists())
        self.assertFalse((self.yema / "evidencia/C-0001.jsonl").exists())

    def test_scripts_de_casa_del_estado(self):
        c = aprobado(self.trabajo)
        script = self.estado / "casa/verificar.sh"
        script.write_text("true")
        c["autoridad"]["ordenes"].append(f"bash {script}")
        c["estado"] = "en_revision"
        from nucleo import contrato
        c, _ = contrato.transicion(c, "aprobado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "x", politica(), AHORA)
        self.activar(c)
        self.assertTrue(self.decide("Bash", {"command": f"bash {script}"})[0])
        self.assertFalse(self.decide("Bash", {"command": f"cat {self.estado}/contratos/C-0001.json"})[0])


if __name__ == "__main__":
    unittest.main()
