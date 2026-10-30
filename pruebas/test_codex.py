"""Mismas sondas para Claude y Codex; la traducción no concede autoridad."""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apoyo_test import AHORA, RAIZ, Entorno, aprobado, base, politica, sellar
from nucleo import contrato, evidencia, firma, puerta


def modulo(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


codex = modulo("puerta_codex", RAIZ / "adaptadores/codex/puerta.py")
sesion = modulo("sesion_codex", RAIZ / "adaptadores/codex/sesion.py")
ensayo = modulo("ensayo_codex", RAIZ / "pruebas/ensayo_codex.py")


class TestCompatibilidadCodex(Entorno):
    def setUp(self):
        super().setUp()
        self.env = patch.dict(os.environ, {"YEMA_ESTADO": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def evento(self, nombre, entrada, cwd=None):
        return {"hook_event_name": "PreToolUse", "tool_name": nombre,
                "tool_input": entrada, "cwd": str(cwd or self.trabajo), "permission_mode": "default"}

    def igual(self, nombre_claude, entrada_claude, nombre_codex=None, entrada_codex=None, esperado=True):
        ev = self.evento(nombre_codex or nombre_claude, entrada_codex if entrada_codex is not None else entrada_claude)
        normal = codex.traducir(ev)
        claude = {"tool_name": nombre_claude, "tool_input": entrada_claude, "cwd": str(self.trabajo),
                  "permission_mode": "dontAsk"}
        a = puerta.decidir(claude, self.yema, AHORA)
        b = puerta.decidir(normal, self.yema, AHORA)
        self.assertEqual(a, b)
        self.assertIs(b[0], esperado, b[1])

    def test_lectura_y_escritura_sin_contrato(self):
        self.igual("Bash", {"command": f"cat {self.yema}/memoria/nota"})
        self.igual("Bash", {"command": "git status"}, esperado=False)
        self.igual("Write", {"file_path": "src/a.py"}, "apply_patch",
                   {"command": "*** Begin Patch\n*** Add File: src/a.py\n+x\n*** End Patch"}, False)

    def test_contrato_escritura_y_ruta_vetada(self):
        self.activar(aprobado(self.trabajo))
        for ruta, permitido in (("src/a.py", True), ("README.md", False), ("src/secreto.py", False),
                                ("../fuera.py", False)):
            with self.subTest(ruta=ruta):
                self.igual("Edit", {"file_path": ruta}, "apply_patch",
                           {"command": f"*** Begin Patch\n*** Update File: {ruta}\n@@\n-a\n+b\n*** End Patch"}, permitido)

    def test_enlace_que_sale(self):
        self.activar(aprobado(self.trabajo))
        (self.trabajo / "src/fuera").symlink_to(self.yema, target_is_directory=True)
        self.igual("Write", {"file_path": "src/fuera/a.py"}, "apply_patch",
                   {"command": "*** Begin Patch\n*** Add File: src/fuera/a.py\n+x\n*** End Patch"}, False)

    def test_ordenes_permitidas_y_compuestas(self):
        self.activar(aprobado(self.trabajo))
        for cmd, permitido in (("git status", True), ("python3 -m unittest -q", True),
                               ("git status; touch fuera", False), ("git status > fuera", False),
                               ("git push --force origin main", False), ("rm src/a.py", False)):
            with self.subTest(cmd=cmd):
                self.igual("Bash", {"command": cmd}, esperado=permitido)

    def test_contrato_caducado_o_huella_alterada(self):
        c = aprobado(self.trabajo)
        c["autoridad"]["caduca"] = (AHORA - timedelta(seconds=1)).isoformat()
        self.activar(c)
        self.igual("Bash", {"command": "git status"}, esperado=False)
        c = aprobado(self.trabajo)
        c["ambito"]["escritura"].append("*")
        self.activar(c)
        self.igual("Bash", {"command": "git status"}, esperado=False)

    def test_firma_de_aprobacion(self):
        pol = {**politica(), "firma_aprobacion": True}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))
        c = aprobado(self.trabajo)
        c["autoridad"]["aprobacion"]["politica"] = puerta.huella_politica(pol)
        c["autoridad"]["aprobacion"]["firma"] = firma.firmar(c, firma.clave(self.yema, crear=True))
        self.activar(c)
        self.igual("Bash", {"command": "git status"})
        c["autoridad"]["aprobacion"]["firma"] = "0" * 64
        self.activar(c)
        self.igual("Bash", {"command": "git status"}, esperado=False)

    def test_tiempo_de_contrato_en_el_limite(self):
        c = aprobado(self.trabajo)
        c["recursos"]["minutos_max"] = 1
        self.activar(sellar(c))
        ev = self.evento("Bash", {"command": "git add src/a.py"})
        self.assertIs(codex.ejecutar(ev, self.yema, AHORA + timedelta(minutes=1))[0], True)
        self.assertIs(codex.ejecutar(ev, self.yema, AHORA + timedelta(minutes=1, seconds=1))[0], False)

    def test_nucleo_gobierno_identidad_y_evidencia_protegidos(self):
        c = aprobado(self.yema)
        c["ambito"]["escritura"] = ["*"]
        self.activar(sellar(c))
        for ruta in ("nucleo/puerta.py", "gobierno/politica.json", "ALMA.md", "contratos/ACTIVO", "evidencia/recibo"):
            ev = self.evento("apply_patch", {"command": f"*** Begin Patch\n*** Add File: {ruta}\n+x\n*** End Patch"}, self.yema)
            self.assertIs(codex.ejecutar(ev, self.yema, AHORA)[0], False)

    def test_lectura_vetada(self):
        self.igual("Bash", {"command": f"cat {self.yema}/memoria/nota"})
        self.igual("Bash", {"command": f"cat {self.yema}/memoria/prod.env"}, esperado=False)

    def test_cupula_permitida_sin_indicar_y_ajena(self):
        for entrada, permitido in (({"vault": "savia-docs", "query": "guía"}, True),
                                   ({"query": "guía"}, False), ({"vault": "ajena"}, False)):
            for prefijo in ("mcp__savia-vaults__", "mcp__savia_vaults__"):
                self.igual("mcp__savia-vaults__vault_search", entrada,
                           prefijo + "vault_search", esperado=permitido)

    def test_mcp_normalizado_observado_y_operacion_desconocida(self):
        self.igual("mcp__savia-vaults__vault_read", {"vault": "savia-docs", "path": "nota.md"},
                   "mcp__savia_vaults__vault_read")
        for nombre in ("mcp__savia_vaults__vault_nueva", "mcp__savia_vaults_otro__vault_read"):
            with self.subTest(nombre=nombre), self.assertRaises(codex.Rechazo):
                codex.traducir(self.evento(nombre, {"vault": "savia-docs"}))

    def test_cupula_n3_y_escritura_no_concedida(self):
        registro = self.yema / "domes.json"
        registro.write_text(json.dumps({"domes": {"savia-docs": {"confidentiality": "N3"}}}))
        pol = {**politica(), "registro_cupulas": str(registro)}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(pol))
        self.igual("mcp__savia-vaults__vault_read", {"vault": "savia-docs", "path": "nota.md"}, esperado=False)
        self.activar(aprobado(self.trabajo))
        self.igual("mcp__savia-vaults__vault_write", {"vault": "savia-docs", "path": "nota.md"}, esperado=False)

    def test_tests_preexistentes_protegidos(self):
        c = aprobado(self.trabajo)
        c["ambito"]["pruebas"] = ["pruebas/*"]
        self.activar(sellar(c))
        (self.trabajo / "pruebas").mkdir()
        (self.trabajo / "pruebas/test.py").write_text("assert False")
        self.igual("Edit", {"file_path": "pruebas/test.py"}, "apply_patch",
                   {"command": "*** Begin Patch\n*** Update File: pruebas/test.py\n@@\n-assert False\n+pass\n*** End Patch"}, False)

    def test_presupuesto_limite_y_git_lectura_gratis(self):
        c = aprobado(self.trabajo)
        c["recursos"]["efectos_max"] = 1
        self.activar(sellar(c))
        ev = self.evento("Bash", {"command": "git add src/a.py"})
        self.assertIs(codex.ejecutar(ev, self.yema, AHORA)[0], True)
        self.assertIs(codex.ejecutar(ev, self.yema, AHORA)[0], False)
        self.assertIs(codex.ejecutar(self.evento("Bash", {"command": "git status"}), self.yema, AHORA)[0], True)
        self.assertEqual(puerta.efectos_usados(self.yema / "evidencia/C-0001.jsonl"), 1)
        self.assertIs(codex.ejecutar(self.evento("Bash", {"command": "git log"}), self.yema, AHORA)[0], False)
        self.assertTrue(evidencia.verificar(self.yema / "evidencia/C-0001.jsonl")[0])

    def test_workdir_real_de_la_herramienta(self):
        self.activar(aprobado(self.trabajo))
        ev = self.evento("Bash", {"command": "git status", "workdir": str(self.yema)})
        self.assertIs(codex.ejecutar(ev, self.yema, AHORA)[0], False)
        ev["tool_input"]["workdir"] = str(self.trabajo)
        self.assertIs(codex.ejecutar(ev, self.yema, AHORA)[0], True)

    def test_aprobar_nunca_genera_ticket(self):
        c = base(self.trabajo)
        (self.yema / "contratos/borradores/C-0001.json").write_text(json.dumps(c))
        (self.yema / "nucleo/yema.py").write_text("")
        cmd = f"python3 {self.yema}/nucleo/yema.py aprobar C-0001 {contrato.huella(c)[:8]}"
        ev = self.evento("Bash", {"command": cmd})
        self.assertIs(codex.ejecutar(ev, self.yema, AHORA)[0], False)
        self.assertFalse((self.yema / "aprobaciones").exists())

    def test_stdin_no_variables_de_entorno_y_error_cerrado(self):
        env = {**os.environ, "YEMA_RAIZ": str(self.yema), "YEMA_ESTADO": "",
               "TOOL_NAME": "Bash", "TOOL_INPUT": '{"command":"cat memoria/nota"}'}
        for entrada in ("{", "null", "[]", "{}"):
            r = subprocess.run([sys.executable, str(RAIZ / "adaptadores/codex/puerta.py")], input=entrada,
                               text=True, capture_output=True, env=env)
            self.assertEqual(r.returncode, 2)
        ev = self.evento("Bash", {"command": f"cat {self.yema}/memoria/nota"})
        r = subprocess.run([sys.executable, str(RAIZ / "adaptadores/codex/puerta.py")], input=json.dumps(ev),
                           text=True, capture_output=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        (self.yema / "gobierno/politica.json").write_text("{")
        r = subprocess.run([sys.executable, str(RAIZ / "adaptadores/codex/puerta.py")], input=json.dumps(ev),
                           text=True, capture_output=True, env=env)
        self.assertEqual(r.returncode, 2)


class TestFormatoCodex(unittest.TestCase):
    def evento(self, nombre="Bash", entrada=None):
        return {"hook_event_name": "PreToolUse", "cwd": str(RAIZ), "tool_name": nombre,
                "tool_input": entrada if entrada is not None else {"command": "pwd"}}

    def test_formatos_invalidos_no_se_permiten(self):
        bueno = self.evento()
        self.assertEqual(codex.traducir(bueno)["tool_name"], "Bash")
        for ev in (None, [], {}, {**bueno, "cwd": "relativa"}, {**bueno, "tool_input": "pwd"},
                   {**bueno, "hook_event_name": "PostToolUse"}, self.evento("exec_command"),
                   self.evento(entrada={}), self.evento(entrada={"command": []})):
            with self.subTest(evento=ev), self.assertRaises(codex.Rechazo):
                codex.traducir(ev)

    def test_solo_parches_de_un_fichero_sin_borrar(self):
        add = "*** Begin Patch\n*** Add File: src/a.py\n+hola\n*** End Patch"
        self.assertEqual(codex.parche(add), ("Write", "src/a.py"))
        for orden in (None, "", add + "\nextra", add.replace("+hola", "hola"),
                      add.replace("+hola", "+hola\n*** Add File: src/b.py\n+otra"),
                      "*** Begin Patch\n*** Delete File: a\n*** End Patch",
                      add.replace("*** Add File: src/a.py", "*** Update File: src/a.py\n*** Move to: fuera")):
            with self.subTest(orden=orden), self.assertRaises(codex.Rechazo):
                codex.parche(orden)

    def test_adaptador_protegido(self):
        for ruta in (".codex/config.toml", "adaptadores/codex/puerta.py", "bin/yema-sesion-codex"):
            with self.subTest(ruta=ruta), self.assertRaises(codex.Rechazo):
                codex.traducir(self.evento("apply_patch", {"command": f"*** Begin Patch\n*** Add File: {ruta}\n+x\n*** End Patch"}))

    def test_tty_escalada_y_workdir_ambiguo_se_rechazan(self):
        self.assertEqual(codex.traducir(self.evento())["tool_input"]["command"], "pwd")
        for extra in ({"tty": True}, {"sandbox_permissions": "require_escalated"},
                      {"additional_permissions": {"network": True}}, {"workdir": ".."}, {"shell": "/tmp/otra-shell"},
                      {"cwd": "/otra", "workdir": str(RAIZ)}):
            with self.subTest(extra=extra), self.assertRaises(codex.Rechazo):
                codex.traducir(self.evento(entrada={"command": "pwd", **extra}))

    def test_herramienta_nueva_y_otro_mcp_no_se_disfrazan(self):
        self.assertEqual(codex.traducir(self.evento("update_plan", {"plan": []}))["tool_name"], "TodoWrite")
        for nombre in ("desconocida", "spawn_agent", "write_stdin", "mcp__otro__vault_read", "WebSearch",
                       "mcp__savia-vaults__vault_nueva_operacion", "mcp__savia-vaults__otra__vault_read"):
            with self.subTest(nombre=nombre), self.assertRaises(codex.Rechazo):
                codex.traducir(self.evento(nombre))


class TestSesionCodex(unittest.TestCase):
    def args(self, **kw):
        return argparse.Namespace(experimental_workspace_write=False, json=False,
                                  output_last_message=None, prompt="hola", **kw)

    def configuracion(self, orden):
        texto = "\n".join(orden[i + 1] for i, x in enumerate(orden) if x == "-c")
        return tomllib.loads(texto)

    def test_configuracion_aislada_y_solo_lectura(self):
        orden = sesion.construir(self.args())
        cfg = self.configuracion(orden)
        self.assertEqual(cfg["sandbox_mode"], "read-only")
        self.assertEqual(cfg["approval_policy"], "never")
        self.assertEqual(cfg["model"], "gpt-6.1-terra")
        self.assertEqual(cfg["model_reasoning_effort"], "medium")
        self.assertEqual(cfg["web_search"], "disabled")
        self.assertEqual(cfg["project_root_markers"], [])
        self.assertEqual(cfg["mcp_servers"], {})
        for opcion in ("--no-daemon", "--strict-config", "--ignore-user-config", "--ephemeral"):
            self.assertIn(opcion, orden)
        for feature in ("apps", "plugins", "multi_agent"):
            self.assertFalse(cfg["features"][feature])
        self.assertFalse(cfg["sandbox_workspace_write"]["network_access"])
        self.assertTrue(cfg["sandbox_workspace_write"]["exclude_slash_tmp"])

    def test_hooks_en_todas_y_fallo_del_ejecutor_devuelve_2(self):
        cfg = self.configuracion(sesion.construir(self.args()))
        pre = cfg["hooks"]["PreToolUse"][0]
        self.assertEqual(pre["matcher"], "*")
        comando = pre["hooks"][0]["command"]
        self.assertIn("adaptadores/codex/vigilante.py", comando)
        self.assertIn("SessionStart", cfg["hooks"])
        r = subprocess.run(["sh", "-c", comando.replace(sys.executable, "/no/existe/python", 1)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_escritura_retirada_y_prompt_literal(self):
        args = self.args()
        args.experimental_workspace_write = True
        with self.assertRaisesRegex(ValueError, "G13.*G14"):
            sesion.construir(args)
        args.experimental_workspace_write = False
        args.json = True
        args.prompt = "--config sandbox_mode=danger-full-access"
        orden = sesion.construir(args)
        self.assertEqual(self.configuracion(orden)["sandbox_mode"], "read-only")
        self.assertEqual(orden[-2:], ["--", args.prompt])
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", orden)
        self.assertIn("--json", orden)

    def test_fuentes_no_auditadas_se_rechazan(self):
        with tempfile.TemporaryDirectory() as t:
            raiz, usuario = Path(t) / "repo", Path(t) / "usuario"
            raiz.mkdir()
            usuario.mkdir()
            sesion.comprobar_fuentes(raiz, usuario)
            for fichero in (usuario / "hooks.json", raiz / ".codex/config.toml", raiz / ".codex/hooks.json"):
                fichero.parent.mkdir(exist_ok=True)
                fichero.write_text("{}")
                with self.subTest(fichero=fichero), self.assertRaises(ValueError):
                    sesion.comprobar_fuentes(raiz, usuario)
                fichero.unlink()

    def test_fuentes_acotadas_al_proyecto_con_hogar_temporal(self):
        with tempfile.TemporaryDirectory() as t:
            padre = Path(t)
            raiz, hogar = padre / "repo", padre / "temporal"
            raiz.mkdir()
            hogar.mkdir()
            (padre / ".codex").mkdir()
            (padre / ".codex/config.toml").write_text('model = "ajeno"')
            (padre / ".codex/hooks.json").write_text('{}')
            # project_root_markers=[] limita el descubrimiento a la raíz lanzada.
            sesion.comprobar_fuentes(raiz, hogar)
            (hogar / "hooks.json").write_text('{}')
            with self.assertRaises(ValueError):
                sesion.comprobar_fuentes(raiz, hogar)

    def test_lanzador_version_y_argumentos_restringidos(self):
        with tempfile.TemporaryDirectory() as t:
            falso = Path(t) / "codex"
            falso.write_text('#!/bin/sh\nif [ "$1" = --version ]; then echo codex-cli 0.163.0; else printf "%s\\n" "$@"; fi\n')
            falso.chmod(0o755)
            env = {**os.environ, "PATH": t + os.pathsep + os.environ["PATH"]}
            r = subprocess.run([str(RAIZ / "bin/yema-sesion-codex"), "hola"], env=env, text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("--ignore-user-config", r.stdout)
            r = subprocess.run([str(RAIZ / "bin/yema-sesion-codex"), "--config", "x=1"], env=env, text=True, capture_output=True)
            self.assertEqual(r.returncode, 2)
            falso.write_text('#!/bin/sh\necho codex-cli 0.164.0\n')
            r = subprocess.run([str(RAIZ / "bin/yema-sesion-codex"), "hola"], env=env, text=True, capture_output=True)
            self.assertEqual(r.returncode, 2)


class TestEnsayoCodex(unittest.TestCase):
    def test_hogar_temporal_copia_auth_y_se_borra_tambien_con_error(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            origen, destino = raiz / "original", raiz / "ensayo"
            origen.mkdir()
            destino.mkdir()
            credencial = '{"fixture": "secreto sintetico"}'
            (origen / "auth.json").write_text(credencial)
            (origen / "config.toml").write_text('model = "no-heredar"')
            for fallo in (False, True):
                with self.subTest(fallo=fallo):
                    try:
                        with ensayo.hogar_codex(destino, origen) as hogar:
                            self.assertEqual(hogar.parent, destino)
                            self.assertEqual(hogar.stat().st_mode & 0o777, 0o700)
                            self.assertEqual((hogar / "auth.json").stat().st_mode & 0o777, 0o600)
                            self.assertEqual((hogar / "auth.json").read_text(), credencial)
                            cfg = tomllib.loads((hogar / "config.toml").read_text())
                            self.assertEqual(cfg["model"], "gpt-6.1-terra")
                            self.assertEqual(cfg["model_reasoning_effort"], "medium")
                            if fallo:
                                raise RuntimeError("fallo sintetico del ensayo")
                    except RuntimeError:
                        if not fallo:
                            raise
                    self.assertFalse(hogar.exists())
            self.assertEqual((origen / "auth.json").read_text(), credencial)
            self.assertEqual((origen / "config.toml").read_text(), 'model = "no-heredar"')

    def test_hogar_sin_auth_no_invoca_y_no_deja_ficheros(self):
        with tempfile.TemporaryDirectory() as t:
            origen, destino = Path(t) / "original", Path(t) / "ensayo"
            origen.mkdir()
            destino.mkdir()
            with self.assertRaises(FileNotFoundError):
                with ensayo.hogar_codex(destino, origen):
                    self.fail("sin auth no se puede iniciar el ensayo")
            self.assertEqual(list(destino.iterdir()), [])

    def test_ensayo_transmite_hogar_temporal_y_lo_limpia(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            (raiz / ".codex").mkdir()
            (raiz / ".codex/auth.json").write_text('{"fixture": true}')
            hogares = []

            def invocar(cmd, env, cwd, out, err):
                hogar = Path(env["CODEX_HOME"])
                hogares.append(hogar)
                self.assertEqual(hogar.parent, raiz / "log/intento-1")
                self.assertTrue((hogar / "auth.json").exists())
                raise RuntimeError("fallo sintetico al iniciar")

            with patch.object(ensayo.Path, "home", return_value=raiz), \
                    patch.dict(os.environ, {"CODEX_HOME": str(raiz / "no-heredar")}), \
                    patch.object(sys, "argv", ["ensayo", "--salida", str(raiz / "log")]), \
                    patch.object(ensayo, "invocar", side_effect=invocar), \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                ensayo.main()
            self.assertEqual(len(hogares), 1)
            self.assertFalse(hogares[0].exists())
            self.assertEqual(json.loads((raiz / "log/invocaciones.json").read_text()), 1)

    def test_invocar_rc_y_timeout_mata_el_grupo(self):
        with patch.object(ensayo.subprocess, "Popen") as popen, patch.object(ensayo.os, "killpg") as killpg:
            proceso = popen.return_value.__enter__.return_value
            proceso.pid = 12345
            proceso.wait.return_value = 0
            self.assertEqual(ensayo.invocar(["codex"], {}, RAIZ, None, None), 0)
            killpg.assert_not_called()
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            proceso.wait.side_effect = [subprocess.TimeoutExpired(["codex"], 1), 0]
            self.assertEqual(ensayo.invocar(["codex"], {}, RAIZ, None, None, timeout=1), 124)
            killpg.assert_called_once_with(12345, ensayo.signal.SIGKILL)

    def test_log_dentro_del_repo_se_rechaza(self):
        import contextlib
        import io
        with patch.object(sys, "argv", ["ensayo", "--salida", str(RAIZ / "log-ensayo")]), patch.object(ensayo, "preparar") as preparar:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
                ensayo.main()
            self.assertEqual(cm.exception.code, 2)
            preparar.assert_not_called()

    def test_fixture_valida_firmada_y_sin_estado_real(self):
        with tempfile.TemporaryDirectory() as t:
            copia, estado = ensayo.preparar(Path(t))
            with patch.dict(os.environ, {"YEMA_ESTADO": str(estado)}):
                c, motivo = puerta.activo(copia, puerta._politica(copia), None)
            self.assertIsNotNone(c, motivo)
            self.assertEqual(c["responsable"], "fixture")
            self.assertEqual(c["ambito"]["escritura"], ["docs/sonda-codex.txt"])
            self.assertNotEqual(copia, RAIZ)
            self.assertIn("cupulas-fixture", (copia / "bin/savia-vaults-mcp").read_text())

    def test_sin_eventos_no_hay_exito_y_caso_positivo(self):
        with tempfile.TemporaryDirectory() as t:
            copia, estado = ensayo.preparar(Path(t))
            registro = estado / "evidencia/C-SONDA-CODEX.jsonl"
            self.assertFalse(all(ensayo.comprobar(copia, registro, [], True).values()))
            (copia / "docs/sonda-codex.txt").write_text("sonda correcta.\n")
            for r in ({"efecto": "escribir", "permitido": True}, {"efecto": "ejecutar", "permitido": False}):
                evidencia.anotar(registro, r)
            eventos = [{"tool_name": "Bash", "tool_input": {"command": "git status --short"}},
                       {"tool_name": "apply_patch"}, {"tool_name": "mcp__savia-vaults__vault_read"}]
            # Un hook observado no prueba que el sandbox o el MCP ejecutaran nada.
            self.assertFalse(all(ensayo.comprobar(copia, registro, eventos, True).values()))
            (copia.parent / "mcp-llamadas.jsonl").write_text(json.dumps({"name": "vault_read",
                "arguments": {"vault": "savia-docs", "path": "sonda.md"}}) + "\n")
            salida_cli = [{"type": "item.completed", "item": {"type": "command_execution",
                "command": "/bin/bash -lc 'git status --short'", "exit_code": 0, "status": "completed"}}]
            self.assertTrue(all(ensayo.comprobar(copia, registro, eventos, True, salida_cli).values()))
            (copia / "docs/NO-DEBE-EXISTIR").touch()
            self.assertFalse(all(ensayo.comprobar(copia, registro, eventos, True, salida_cli).values()))

    def test_mcp_fixture_registra_solo_llamadas_y_responde(self):
        with tempfile.TemporaryDirectory() as t:
            copia, _ = ensayo.preparar(Path(t))
            cmd = [sys.executable, str(copia / "bin/savia-vaults-mcp")]
            req = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
            r = subprocess.run(cmd, input=json.dumps(req) + "\n", text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            registro = copia.parent / "mcp-llamadas.jsonl"
            self.assertFalse(registro.exists())
            req.update(method="tools/call", params={"name": "vault_read",
                "arguments": {"vault": "savia-docs", "path": "sonda.md"}})
            r = subprocess.run(cmd, input=json.dumps(req) + "\n", text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Nota sintética", json.loads(r.stdout)["result"]["content"][0]["text"])
            self.assertEqual(json.loads(registro.read_text()), req["params"])

    def test_cinco_invocaciones_impiden_una_sexta(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as t:
            for contador in ("5", "-1", "true", '"0"'):
                (Path(t) / "invocaciones.json").write_text(contador)
                with patch.object(sys, "argv", ["ensayo", "--salida", t]), patch.object(ensayo, "preparar") as preparar:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
                        ensayo.main()
                    self.assertEqual(cm.exception.code, 2)
                    preparar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
