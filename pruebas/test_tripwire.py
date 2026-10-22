"""Alarma de nivel en lecturas de cúpula y presupuesto de tiempo del contrato."""
import json
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, Entorno, base, politica  # noqa: E402
from nucleo import contrato, puerta  # noqa: E402

NOTA = "---\ntitle: {t}\nconfidentiality: {n}\n---\n\ncuerpo\n"


class TestTripwireCupula(Entorno):
    def setUp(self):
        super().setUp()
        t = Path(self.tmp.name)
        self.domains = t / "domes/SaviaDomains"
        (self.domains / "tec").mkdir(parents=True)
        (self.domains / "tec/publica.md").write_text(NOTA.format(t="pública", n="N1"))
        (self.domains / "tec/colada.md").write_text(NOTA.format(t="colada", n="N3"))
        (self.domains / "tec/sin-nivel.md").write_text("# sin frontmatter\n")
        (t / "domes/Privada").mkdir(parents=True)
        registro = {"domes": {
            "SaviaDomains": {"path": str(self.domains), "confidentiality": "N1"},
            "Privada": {"path": str(t / "domes/Privada"), "confidentiality": "N4"},
        }}
        (t / "domes.json").write_text(json.dumps(registro))
        pol = {**politica(), "cupulas_lectura": ["SaviaDomains", "Privada"], "registro_cupulas": str(t / "domes.json")}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))

    def leer(self, cupula, ruta):
        return self.decide("mcp__savia-vaults__vault_read", {"vault": cupula, "path": ruta})

    def test_nota_publica_pasa(self):
        self.assertTrue(self.leer("SaviaDomains", "tec/publica.md")[0])

    def test_nota_n3_en_cupula_n1_se_para(self):
        ok, motivo, _ = self.leer("SaviaDomains", "tec/colada.md")
        self.assertFalse(ok)
        self.assertIn("N3", motivo)

    def test_cupula_de_nivel_alto_se_para_aunque_este_permitida(self):
        ok, motivo, _ = self.leer("Privada", "x.md")
        self.assertFalse(ok)
        self.assertIn("N4", motivo)

    def test_busqueda_en_cupula_alta_se_para(self):
        ok, _, _ = self.decide("mcp__savia-vaults__vault_search", {"vault": "Privada", "query": "x"})
        self.assertFalse(ok)

    def test_nota_sin_nivel_hereda_el_de_la_cupula(self):
        self.assertTrue(self.leer("SaviaDomains", "tec/sin-nivel.md")[0])

    def test_ruta_que_escapa_no_se_evalua_como_segura(self):
        ok, motivo, _ = self.leer("SaviaDomains", "../Privada/x.md")
        self.assertFalse(ok)

    def test_sin_registro_no_cambia_nada(self):
        pol = {**politica(), "cupulas_lectura": ["SaviaDomains"]}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))
        self.assertTrue(self.leer("SaviaDomains", "tec/colada.md")[0])


class TestPresupuestoDeTiempo(Entorno):
    def preparar(self, minutos):
        c = base(self.trabajo)
        c["recursos"]["minutos_max"] = minutos
        for estado in ("aprobado", "aprovisionado", "activo"):
            c, err = contrato.transicion(c, estado, "operadora", "x", politica(), AHORA)
            self.assertIsNone(err)
        self.activar(c)
        return {"tool_name": "Edit", "tool_input": {"file_path": str(self.trabajo / "src/a.py")},
                "cwd": str(self.trabajo)}

    def test_dentro_del_tiempo(self):
        ev = self.preparar(60)
        self.assertTrue(puerta.evaluar_y_registrar(ev, self.yema, AHORA + timedelta(minutes=30))[0])

    def test_tiempo_agotado(self):
        ev = self.preparar(60)
        ok, motivo, _ = puerta.evaluar_y_registrar(ev, self.yema, AHORA + timedelta(minutes=61))
        self.assertFalse(ok)
        self.assertIn("tiempo", motivo)

    def test_lecturas_siguen_tras_agotar_el_tiempo(self):
        self.preparar(1)
        ev = {"tool_name": "Read", "tool_input": {"file_path": str(self.trabajo / "src/a.py")}, "cwd": str(self.trabajo)}
        self.assertTrue(puerta.evaluar_y_registrar(ev, self.yema, AHORA + timedelta(minutes=5))[0])


if __name__ == "__main__":
    unittest.main()
