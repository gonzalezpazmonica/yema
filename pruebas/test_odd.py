"""Ideas adoptadas de ODD (Organic Driven Development), con control en código:
estados visibles, checkpoint con forma fija, tests preexistentes intocables,
rechazos que dicen qué hacer y garantías probadas a través del hook real."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, RAIZ, Entorno, base, politica, sellar  # noqa: E402
from nucleo import contrato, puerta, yema  # noqa: E402


class ConEstado(Entorno):
    def setUp(self):
        super().setUp()
        self.tmp2 = tempfile.TemporaryDirectory()
        self.estado = Path(self.tmp2.name) / "estado"
        for d in ("contratos/borradores", "evidencia", "memoria", "aprobaciones"):
            (self.estado / d).mkdir(parents=True)
        (self.yema / "gobierno/politica.json").write_text(json.dumps({**politica(), "estado": str(self.estado)}))

    def tearDown(self):
        self.tmp2.cleanup()
        super().tearDown()

    def activar(self, c):
        (self.estado / "contratos" / f"{c['id']}.json").write_text(json.dumps(c))
        (self.estado / "contratos/ACTIVO").write_text(c["id"])

    def vigente(self, **cambios):
        c = base(self.trabajo)
        c["autoridad"]["caduca"] = "2999-01-01T00:00:00+00:00"
        for k, v in cambios.items():
            c[k] = v
        return sellar(c)

    def cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = yema.main(list(args), raiz=self.yema, tty=False)
        return rc, out.getvalue()


class TestCuatroEstados(ConEstado):
    def test_sin_nada_lista(self):
        self.assertEqual(yema.situacion(self.yema)[0], "Lista")

    def test_borrador_pendiente_necesita_decision(self):
        (self.estado / "contratos/borradores/C-0002.json").write_text(json.dumps(base(self.trabajo)))
        estado, detalle = yema.situacion(self.yema)
        self.assertEqual(estado, "Necesita tu decisión")
        self.assertIn("C-0002", detalle)

    def test_activo_trabajando(self):
        self.activar(self.vigente())
        self.assertEqual(yema.situacion(self.yema)[0], "Trabajando")

    def test_validando_comprobando(self):
        c, _ = contrato.transicion(self.vigente(), "validando", "yema", "fin", politica())
        self.activar(c)
        self.assertEqual(yema.situacion(self.yema)[0], "Comprobando")

    def test_suspendido_o_caducado_necesita_decision(self):
        c, _ = contrato.transicion(self.vigente(), "suspendido", "yema", "pausa", politica())
        self.activar(c)
        self.assertEqual(yema.situacion(self.yema)[0], "Necesita tu decisión")

    def test_presupuesto_agotado_necesita_decision(self):
        c = base(self.trabajo)
        c["autoridad"]["caduca"] = "2999-01-01T00:00:00+00:00"
        c["recursos"]["efectos_max"] = 0
        self.activar(sellar(c))
        self.assertEqual(yema.situacion(self.yema)[0], "Necesita tu decisión")

    def test_cli_estado_muestra_el_estado_visible(self):
        self.activar(self.vigente())
        rc, out = self.cli("estado")
        self.assertIn("Trabajando", out)


class TestCheckpoint(ConEstado):
    def contrato_con_requisitos(self):
        c = base(self.trabajo)
        c["peticion"] = "Arregla los tests rotos sin tocar la API"
        c["requisitos"] = [{"id": "S1", "cita": "sin tocar la API", "post": ["pruebas"]}]
        return c

    def test_requisito_que_apunta_a_post_inexistente(self):
        c = self.contrato_con_requisitos()
        c["requisitos"][0]["post"] = ["no-existe"]
        self.assertTrue(any("S1" in e for e in contrato.errores(c)))

    def test_requisito_sin_cita_literal(self):
        c = self.contrato_con_requisitos()
        c["requisitos"][0]["cita"] = ""
        self.assertTrue(contrato.errores(c))

    def test_forma_fija(self):
        texto = contrato.checkpoint(self.contrato_con_requisitos())
        secciones = [l for l in texto.splitlines() if l.startswith("## ")]
        self.assertEqual(secciones, ["## Requisitos", "## Tareas", "## Log"])
        self.assertIn("«sin tocar la API»", texto)
        self.assertIn("Arregla los tests rotos sin tocar la API", texto.split("## Log")[1])
        self.assertIn(contrato.huella(self.contrato_con_requisitos())[:8], texto)

    def test_cli_crea_y_no_pisa(self):
        c = self.contrato_con_requisitos()
        c["autoridad"]["caduca"] = "2999-01-01T00:00:00+00:00"
        self.activar(sellar(c))
        self.assertEqual(self.cli("checkpoint", "C-0001")[0], 0)
        f = self.estado / "memoria/C-0001.md"
        f.write_text(f.read_text() + "- avance\n")
        self.assertEqual(self.cli("checkpoint", "C-0001")[0], 0)
        self.assertIn("- avance", f.read_text())


class TestPruebasPreexistentes(ConEstado):
    def setUp(self):
        super().setUp()
        (self.trabajo / "src/test_viejo.py").write_text("assert True")
        amb = {"raiz": str(self.trabajo), "escritura": ["src/*"], "pruebas": ["src/test_*"]}
        self.activar(self.vigente(ambito=amb))

    def escribe(self, rel):
        return self.decide("Edit", {"file_path": str(self.trabajo / rel)})

    def test_test_existente_no_se_toca(self):
        ok, motivo, _ = self.escribe("src/test_viejo.py")
        self.assertFalse(ok)
        self.assertIn("enmienda", motivo)

    def test_test_nuevo_si(self):
        self.assertTrue(self.escribe("src/test_nuevo.py")[0])

    def test_codigo_normal_si(self):
        self.assertTrue(self.escribe("src/app.py")[0])

    def test_editable_por_enmienda(self):
        amb = {"raiz": str(self.trabajo), "escritura": ["src/*"], "pruebas": ["src/test_*"],
               "pruebas_editables": ["src/test_viejo.py"]}
        self.activar(self.vigente(ambito=amb))
        self.assertTrue(self.escribe("src/test_viejo.py")[0])


class TestRechazosUtiles(ConEstado):
    def test_cada_rechazo_dice_que_hacer(self):
        casos = [("Write", {"file_path": str(self.trabajo / "src/a.py")})]  # sin contrato
        self.activar(self.vigente())
        casos += [
            ("Write", {"file_path": str(self.trabajo / "README.md")}),      # fuera de escritura
            ("Bash", {"command": "make all"}),                              # orden no listada
            ("Bash", {"command": "git push origin main"}),                  # efecto prohibido
            ("Bash", {"command": "git status; ls"}),                        # compuesta
            ("WebFetch", {"url": "https://ejemplo.org"}),                   # efecto no concedido
            ("Write", {"file_path": str(self.yema / "nucleo/x.py")}),       # zona protegida
        ]
        for i, (h, e) in enumerate(casos):
            if i == 0:
                (self.estado / "contratos/ACTIVO").rename(self.estado / "ACTIVO.bak")
            ok, motivo, _ = self.decide(h, e)
            if i == 0:
                (self.estado / "ACTIVO.bak").rename(self.estado / "contratos/ACTIVO")
            self.assertFalse(ok, (h, e))
            self.assertIn("Qué hacer:", motivo, (h, e, motivo))


class TestGarantiasPorElHookReal(unittest.TestCase):
    """Un control que no está cableado no es un control: se prueba por el hook
    tal como lo registra .claude/settings.json, no solo la función."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.estado = Path(self.tmp.name) / "estado"
        (self.estado / "contratos/borradores").mkdir(parents=True)
        self.trabajo = Path(self.tmp.name) / "trabajo"
        (self.trabajo / "src").mkdir(parents=True)
        ajustes = json.loads((RAIZ / ".claude/settings.json").read_text())
        grupos = ajustes["hooks"]["PreToolUse"]
        self.assertTrue(any(g.get("matcher") == "*" for g in grupos), "la puerta debe cubrir todas las herramientas")
        self.orden = [h["command"] for g in grupos for h in g["hooks"] if "puerta.py" in h["command"]][0]

    def tearDown(self):
        self.tmp.cleanup()

    def hook(self, herramienta, entrada):
        ev = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(self.trabajo), "permission_mode": "default"}
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(RAIZ), "YEMA_ESTADO": str(self.estado)}
        return subprocess.run(self.orden, shell=True, input=json.dumps(ev), capture_output=True, text=True, env=env)

    def test_garantias(self):
        casos = [
            ("leer sin contrato", "Read", {"file_path": str(self.trabajo / "src/a.py")}, 0),
            ("escribir sin contrato", "Write", {"file_path": str(self.trabajo / "src/a.py")}, 2),
            ("borrador libre", "Write", {"file_path": str(self.estado / "contratos/borradores/C-1.json")}, 0),
            ("núcleo protegido", "Edit", {"file_path": str(RAIZ / "nucleo/puerta.py")}, 2),
            ("gobierno protegido", "Write", {"file_path": str(RAIZ / "gobierno/politica.json")}, 2),
            ("lectura vetada", "Read", {"file_path": os.path.expanduser("~/.ssh/id_ed25519")}, 2),
            ("orden compuesta", "Bash", {"command": "ls; id"}, 2),
            ("herramienta desconocida", "Teletransporte", {}, 2),
            ("cúpula sin nombre", "mcp__savia-vaults__vault_search", {"query": "x"}, 2),
        ]
        for nombre, h, e, esperado in casos:
            r = self.hook(h, e)
            self.assertEqual(r.returncode, esperado, f"{nombre}: {r.stderr}")


if __name__ == "__main__":
    unittest.main()
