"""Aprendizajes de los repos de la cuenta: borrar es un efecto aparte, la aprobación fija la política,
y la puerta no repite secretos en sus motivos ni en la evidencia."""
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, Entorno, base, politica  # noqa: E402
from nucleo import contrato, firma, puerta  # noqa: E402

import unittest  # noqa: E402


class TestBorrar(Entorno):
    def activo_con(self, efectos, ordenes):
        c = base(self.trabajo)
        c["autoridad"]["efectos"] = efectos
        c["autoridad"]["ordenes"] = ordenes
        for e in ("aprobado", "aprovisionado", "activo"):
            c, err = contrato.transicion(c, e, "operadora", "x", politica(), AHORA)
            self.assertIsNone(err)
        self.activar(c)

    def test_borrar_es_efecto_valido(self):
        self.assertIn("borrar", contrato.EFECTOS)

    def test_rm_exige_borrar_aunque_se_pueda_escribir(self):
        self.activo_con(["leer", "escribir", "ejecutar"], ["rm", "python3"])
        ok, motivo, efecto = self.decide("Bash", {"command": "rm src/a.py"})
        self.assertFalse(ok)
        self.assertEqual(efecto, "borrar")

    def test_rm_con_borrar_concedido(self):
        self.activo_con(["leer", "escribir", "borrar"], ["rm"])
        self.assertTrue(self.decide("Bash", {"command": "rm src/a.py"})[0])

    def test_git_rm_y_clean_son_borrar(self):
        for cmd in ("git rm src/a.py", "git clean -fd", "git branch -D x"):
            self.assertEqual(puerta.clasificar_orden(cmd)[0], "borrar", cmd)
        self.assertEqual(puerta.clasificar_orden("git branch")[0], "git-local")


class TestPoliticaFijada(Entorno):
    def setUp(self):
        super().setUp()
        self.pol = {**politica(), "firma_aprobacion": True}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(self.pol))

    def aprobar_firmado(self):
        c = base(self.trabajo)
        c, _ = contrato.transicion(c, "aprobado", "operadora", "ok", self.pol, AHORA)
        c["autoridad"]["aprobacion"]["politica"] = puerta.huella_politica(self.pol)
        c["autoridad"]["aprobacion"]["firma"] = firma.firmar(c, firma.clave(self.yema, crear=True))
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "ok", self.pol, AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "ok", self.pol, AHORA)
        self.activar(c)
        return c

    def editar(self):
        return self.decide("Edit", {"file_path": str(self.trabajo / "src/a.py")})

    def test_misma_politica_vale(self):
        self.aprobar_firmado()
        self.assertTrue(self.editar()[0])

    def test_politica_cambiada_no_vale(self):
        self.aprobar_firmado()
        nueva = {**self.pol, "cupulas_lectura": self.pol["cupulas_lectura"] + ["Otra"]}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(nueva))
        ok, motivo, _ = self.editar()
        self.assertFalse(ok)
        self.assertIn("política", motivo)

    def test_la_huella_de_politica_entra_en_la_firma(self):
        c = self.aprobar_firmado()
        c["autoridad"]["aprobacion"]["politica"] = "0" * 64
        self.assertFalse(firma.verificar(c, firma.clave(self.yema)))


class TestRedaccion(Entorno):
    def test_motivo_no_repite_un_token(self):
        token = "ghp_" + "a1B2" * 9
        ok, motivo, _ = self.decide("Bash", {"command": f"curl -H 'Authorization: token {token}' http://x"})
        self.assertFalse(ok)
        self.assertNotIn(token, motivo)

    def test_redactar(self):
        for secreto in ("ghp_" + "x" * 36, "github_pat_" + "y" * 40, "sk-" + "z" * 40,
                        "AKIA" + "Q" * 16, "password=hunter22secret", "--token " + "w" * 32):
            r = puerta.redactar(f"orden con {secreto} dentro")
            self.assertNotIn(secreto, r, secreto)
            self.assertIn("orden con", r)

    def test_evidencia_no_guarda_el_token(self):
        token = "ghp_" + "c3D4" * 9
        ev = {"tool_name": "Bash", "tool_input": {"command": f"git push https://{token}@github.com/x/y"},
              "cwd": str(self.trabajo)}
        puerta.evaluar_y_registrar(ev, self.yema, AHORA)
        texto = "".join(p.read_text() for p in (self.yema / "evidencia").glob("*.jsonl"))
        self.assertNotIn(token, texto)


if __name__ == "__main__":
    unittest.main()
