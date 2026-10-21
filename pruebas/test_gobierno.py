"""Gobierno por conversación: Yema redacta y propone; la persona aprueba en el diálogo
de permisos nativo del arnés, que el modelo no puede pulsar."""
import io
import json
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, RAIZ, Entorno, base, politica, sellar  # noqa: E402
from nucleo import contrato, puerta, yema  # noqa: E402


class TestGobierno(Entorno):
    def setUp(self):
        super().setUp()
        self.tmp2 = tempfile.TemporaryDirectory()
        self.estado = Path(self.tmp2.name) / "estado"
        for d in ("contratos/borradores", "evidencia", "memoria", "aprobaciones"):
            (self.estado / d).mkdir(parents=True)
        (self.yema / "gobierno/politica.json").write_text(json.dumps({**politica(), "estado": str(self.estado)}))
        (self.yema / "nucleo").mkdir(exist_ok=True)
        (self.yema / "nucleo/yema.py").write_text("")
        c = base(self.trabajo)
        c["estado"] = "candidato"
        c["autoridad"]["caduca"] = "2999-01-01T00:00:00+00:00"
        self.c = c
        (self.estado / "contratos/borradores/C-0001.json").write_text(json.dumps(c))
        self.h8 = contrato.huella(c)[:8]
        self.cli_yema = f"python3 {self.yema}/nucleo/yema.py"

    def tearDown(self):
        self.tmp2.cleanup()
        super().tearDown()

    def decide(self, cmd, modo="default"):
        ev = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(self.trabajo), "permission_mode": modo}
        return puerta.decidir(ev, self.yema, AHORA)

    def cli(self, *args, tty=False):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = yema.main(list(args), raiz=self.yema, tty=tty)
        return rc, out.getvalue(), err.getvalue()

    def test_consultas_libres_sin_contrato(self):
        for sub in ("estado", "resumen C-0001", "evidencia C-0001", "validar " + str(self.estado / "contratos/borradores/C-0001.json")):
            ok, motivo, efecto = self.decide(f"{self.cli_yema} {sub}")
            self.assertIs(ok, True, f"{sub}: {motivo}")
            self.assertEqual(efecto, "gobierno")

    def test_aprobar_pide_a_la_persona(self):
        ok, motivo, _ = self.decide(f"{self.cli_yema} aprobar C-0001 {self.h8}")
        self.assertIs(ok, puerta.PREGUNTAR)
        self.assertFalse(ok)  # falsy: cualquier código que no lo entienda, deniega
        self.assertIn(self.c["proposito"], motivo)
        self.assertIn(self.h8, motivo)

    def test_aprobar_huella_que_no_casa(self):
        ok, motivo, _ = self.decide(f"{self.cli_yema} aprobar C-0001 deadbeef")
        self.assertIs(ok, False)
        self.assertIn("huella", motivo)

    def test_aprobar_en_modo_sin_preguntas_se_deniega(self):
        for modo in ("bypassPermissions", "dontAsk"):
            ok, motivo, _ = self.decide(f"{self.cli_yema} aprobar C-0001 {self.h8}", modo)
            self.assertIs(ok, False, modo)
            self.assertIn("modo", motivo)

    def test_aprobar_en_modo_auto_pregunta(self):
        # El modo auto de Claude Code sigue mostrando los diálogos que fuerza un hook:
        # la persona aprueba desde el harness, sin consola.
        ok, motivo, _ = self.decide(f"{self.cli_yema} aprobar C-0001 {self.h8}", "auto")
        self.assertIs(ok, puerta.PREGUNTAR)
        self.assertIn(self.h8, motivo)

    def test_transicion_humana_directa_denegada(self):
        for cmd in (f"{self.cli_yema} transicion C-0001 aprobado --por operadora",
                    f"{self.cli_yema} activar C-0001 --por operadora"):
            self.assertIs(self.decide(cmd)[0], False, cmd)

    def test_instalar_es_de_la_persona(self):
        self.assertIs(self.decide(f"{self.cli_yema} instalar")[0], False)

    def test_suspender_y_revocar_libres(self):
        for sub in ("suspender C-0001 --por yema --motivo x", "revocar C-0001 --por yema --motivo x"):
            self.assertIs(self.decide(f"{self.cli_yema} {sub}")[0], True, sub)

    def test_impostor_llamado_yema(self):
        falso = self.estado / "memoria/yema.py"
        falso.write_text("")
        self.assertIs(self.decide(f"python3 {falso} estado")[0], False)

    def test_ticket_y_aprobacion_por_dialogo(self):
        ev = {"tool_name": "Bash", "tool_input": {"command": f"{self.cli_yema} aprobar C-0001 {self.h8}"},
              "cwd": str(self.trabajo), "permission_mode": "default"}
        ok, _, _ = puerta.evaluar_y_registrar(ev, self.yema, AHORA)
        self.assertIs(ok, puerta.PREGUNTAR)
        rc, out, err = self.cli("aprobar", "C-0001", self.h8)
        self.assertEqual(rc, 0, err)
        c = contrato.cargar(self.estado / "contratos/C-0001.json")
        self.assertEqual(c["estado"], "activo")
        self.assertEqual((self.estado / "contratos/ACTIVO").read_text().strip(), "C-0001")
        self.assertEqual(list((self.estado / "aprobaciones").iterdir()), [])  # ticket consumido

    def test_sin_ticket_ni_terminal_no_aprueba(self):
        rc, _, err = self.cli("aprobar", "C-0001", self.h8)
        self.assertNotEqual(rc, 0)
        self.assertIn("persona", err)

    def test_ticket_caducado(self):
        t = self.estado / "aprobaciones" / f"C-0001-{self.h8}.json"
        t.write_text(json.dumps({"ts": time.time() - 3600}))
        rc, _, _ = self.cli("aprobar", "C-0001", self.h8)
        self.assertNotEqual(rc, 0)

    def test_terminal_humana_aprueba_sin_ticket(self):
        rc, _, err = self.cli("aprobar", "C-0001", self.h8, tty=True)
        self.assertEqual(rc, 0, err)

    def test_no_sustituye_un_contrato_vigente(self):
        otro = base(self.trabajo)
        otro["id"] = "C-0009"
        otro["autoridad"]["caduca"] = "2999-01-01T00:00:00+00:00"
        otro = sellar(otro)
        (self.estado / "contratos/C-0009.json").write_text(json.dumps(otro))
        (self.estado / "contratos/ACTIVO").write_text("C-0009")
        rc, _, err = self.cli("aprobar", "C-0001", self.h8, tty=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("C-0009", err)

    def test_resumen_en_lenguaje_llano(self):
        texto = contrato.resumen(self.c)
        for trozo in (self.c["proposito"], "Puede", "No puede", "Caduca", self.h8):
            self.assertIn(trozo, texto)

    def test_hook_devuelve_ask_en_json(self):
        import os
        import subprocess
        ev = {"tool_name": "Bash", "tool_input": {"command": f"{self.cli_yema} aprobar C-0001 {self.h8}"},
              "cwd": str(self.trabajo), "permission_mode": "default"}
        r = subprocess.run([sys.executable, str(RAIZ / "nucleo/puerta.py")], input=json.dumps(ev),
                           capture_output=True, text=True, env={**os.environ, "YEMA_RAIZ": str(self.yema)})
        self.assertEqual(r.returncode, 0, r.stderr)
        salida = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(salida["permissionDecision"], "ask")
        self.assertIn(self.h8, salida["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
