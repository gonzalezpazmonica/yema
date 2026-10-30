"""Compensaciones G11–G14; los contratos y las aprobadoras son fixtures."""
import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apoyo_test import AHORA, RAIZ, Entorno, base, politica
from test_codex import codex, modulo, sesion
from nucleo import contrato, evidencia, firma, puerta, yema


class TestAprobacionCodex(Entorno):
    def setUp(self):
        super().setUp()
        self.env = patch.dict(os.environ, {"YEMA_ESTADO": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.pol = {**politica(), "firma_aprobacion": True}
        (self.yema / "gobierno/politica.json").write_text(json.dumps(self.pol))
        (self.yema / "nucleo/yema.py").touch()
        self.c = base(self.trabajo)
        self.c["autoridad"]["caduca"] = "2999-01-01T00:00:00+00:00"
        self.borrador = self.yema / "contratos/borradores/C-0001.json"
        self.borrador.write_text(json.dumps(self.c))
        self.h8 = contrato.huella(self.c)[:8]
        self.registro = self.yema / "evidencia/C-0001.jsonl"

    def evento(self, huella=None):
        return {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(self.trabajo),
                "tool_input": {"command": f"python3 {self.yema}/nucleo/yema.py aprobar C-0001 {huella or self.h8}"}}

    def cli(self, tty=False):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return yema.main(["aprobar", "C-0001", self.h8], raiz=self.yema, tty=tty)

    def test_ticket_inerte_y_terminal_firma_antes_de_reintentar(self):
        ok, motivo, efecto = codex.ejecutar(self.evento(), self.yema, AHORA)
        self.assertIs(ok, False)
        self.assertEqual(efecto, "gobierno")
        self.assertIn("ticket Codex", motivo)
        self.assertIn(f"aprobar C-0001 {self.h8}", motivo)
        self.assertIn(self.c["proposito"], motivo)
        recibo = evidencia.leer(self.registro)[-1]
        self.assertEqual(recibo["evento"], "solicitud-aprobacion-codex")
        self.assertEqual(recibo["huella"], contrato.huella(self.c))
        self.assertEqual(recibo["politica"], puerta.huella_politica(self.pol))
        self.assertIs(recibo["permitido"], False)
        self.assertFalse((self.yema / "aprobaciones").exists())
        self.assertEqual(self.cli(tty=False), 3)
        self.assertFalse((self.yema / "contratos/ACTIVO").exists())
        escribir = {"hook_event_name": "PreToolUse", "tool_name": "apply_patch", "cwd": str(self.trabajo),
                    "tool_input": {"command": "*** Begin Patch\n*** Add File: src/a.py\n+x\n*** End Patch"}}
        self.assertIs(codex.ejecutar(escribir, self.yema, AHORA)[0], False)
        self.assertEqual(self.cli(tty=True), 0)
        c = contrato.cargar(self.yema / "contratos/C-0001.json")
        self.assertTrue(firma.verificar(c, firma.clave(self.yema)))
        self.assertIs(codex.ejecutar(escribir, self.yema)[0], True)
        self.assertTrue(evidencia.verificar(self.registro)[0])
        self.assertTrue(any(r.get("via") == "terminal" for r in evidencia.leer(self.registro)))

    def test_huella_incorrecta_no_emite_ticket(self):
        ok, motivo, _ = codex.ejecutar(self.evento("deadbeef"), self.yema, AHORA)
        self.assertIs(ok, False)
        self.assertIn("huella", motivo)
        self.assertFalse(any(r.get("evento") == "solicitud-aprobacion-codex" for r in evidencia.leer(self.registro)))
        self.assertEqual(self.cli(), 3)

    def test_id_del_contenido_no_puede_elegir_destino_del_recibo(self):
        self.c["id"] = "../recibo-ajeno"
        self.borrador.write_text(json.dumps(self.c))
        with self.assertRaisesRegex(codex.Rechazo, "id"):
            codex.ejecutar(self.evento(contrato.huella(self.c)[:8]), self.yema, AHORA)
        self.assertFalse((self.yema / "recibo-ajeno.jsonl").exists())

    def test_ticket_no_autoriza_contrato_modificado(self):
        _, motivo, _ = codex.ejecutar(self.evento(), self.yema, AHORA)
        self.assertIn("ticket Codex", motivo)
        self.c["ambito"]["escritura"].append("*")
        self.borrador.write_text(json.dumps(self.c))
        self.assertEqual(self.cli(tty=True), 1)
        self.assertFalse((self.yema / "contratos/ACTIVO").exists())

    def test_ticket_no_es_permiso_ni_se_genera_para_id_inexistente(self):
        self.borrador.unlink()
        ok, motivo, _ = codex.ejecutar(self.evento(), self.yema, AHORA)
        self.assertIs(ok, False)
        self.assertIn("no encuentro", motivo)
        self.assertFalse((self.yema / "aprobaciones").exists())
        self.assertFalse(any(r.get("evento") == "solicitud-aprobacion-codex" for r in evidencia.leer(self.registro)))


class TestVigilanteCodex(unittest.TestCase):
    def setUp(self):
        self.v = modulo("vigilante_codex", RAIZ / "adaptadores/codex/vigilante.py")

    def ejecutar(self, programa, timeout=1):
        return self.v.evaluar('{"fixture":true}', orden=[sys.executable, "-c", programa], timeout=timeout)

    def test_veredicto_explicito_y_stdin(self):
        programa = ('import sys,json; assert json.load(sys.stdin)=={"fixture":True}; '
                    'print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse",'
                    '"permissionDecision":"allow"}}))')
        rc, salida, _ = self.ejecutar(programa)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(salida)["hookSpecificOutput"]["permissionDecision"], "allow")

    def test_salida_cero_sin_veredicto_es_bloqueo(self):
        for programa in ('pass', 'print("{}")', 'print("no json")',
                         'print(\'{"hookSpecificOutput":null}\')',
                         'print(\'{"hookSpecificOutput":{"permissionDecision":"allow"}}\')'):
            with self.subTest(programa=programa):
                self.assertEqual(self.ejecutar(programa)[0], 2)

    def test_muerte_y_error_del_evaluador_se_bloquean(self):
        for programa in ('raise SystemExit(1)', 'import os,signal; os.kill(os.getpid(),signal.SIGKILL)',
                         'import sys; print("secreto-fixture",file=sys.stderr); raise SystemExit(1)'):
            with self.subTest(programa=programa):
                rc, _, error = self.ejecutar(programa)
                self.assertEqual(rc, 2)
                self.assertIn("bloqueo", error)
                self.assertNotIn("secreto-fixture", error)
        rc, _, _ = self.v.evaluar('{}', orden=['/no/existe/evaluador'], timeout=1)
        self.assertEqual(rc, 2)

    def test_timeout_se_bloquea(self):
        rc, _, error = self.ejecutar('import time; time.sleep(10)', timeout=0.05)
        self.assertEqual(rc, 2)
        self.assertIn("timeout", error)

    def test_timeout_termina_tambien_descendientes(self):
        with tempfile.TemporaryDirectory() as t:
            marca = Path(t) / "NO-DEBE-EXISTIR"
            nieto = f"import time; from pathlib import Path; time.sleep(0.4); Path({str(marca)!r}).touch()"
            hijo = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{nieto!r}]); time.sleep(10)"
            self.assertEqual(self.ejecutar(hijo, timeout=0.1)[0], 2)
            time.sleep(0.5)
            self.assertFalse(marca.exists())

    def test_rc_dos_con_allow_no_es_permiso(self):
        programa = ('import json; print(json.dumps({"hookSpecificOutput": '
                    '{"hookEventName":"PreToolUse","permissionDecision":"allow"}})); raise SystemExit(2)')
        self.assertEqual(self.ejecutar(programa)[0], 2)

    def test_deny_y_ask_no_se_convierten_en_allow(self):
        for decision in ('deny', 'ask'):
            programa = 'print(' + repr(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": decision,
                "permissionDecisionReason": "ticket de prueba"}})) + ')'
            rc, _, _ = self.ejecutar(programa)
            self.assertEqual(rc, 2)


class TestContencionCodex(unittest.TestCase):
    def args(self, escritura=False):
        return argparse.Namespace(experimental_workspace_write=escritura, json=False,
                                  output_last_message=None, prompt="hola")

    def cfg(self):
        import tomllib
        orden = sesion.construir(self.args())
        return tomllib.loads('\n'.join(orden[i+1] for i,x in enumerate(orden) if x == '-c'))

    def test_shell_stdin_alojadas_y_conectores_retirados(self):
        cfg = self.cfg()
        for feature in ('shell_tool', 'apps', 'plugins', 'multi_agent', 'browser_use',
                        'computer_use', 'image_generation', 'view_image', 'remote_plugin', 'multi_agent_v2', 'goals',
                        'skill_mcp_dependency_install', 'workspace_dependencies'):
            with self.subTest(feature=feature):
                self.assertIs(cfg['features'][feature], False)
        self.assertEqual(cfg['web_search'], 'disabled')
        self.assertEqual(cfg['mcp_servers'], {})
        self.assertEqual(cfg['sandbox_mode'], 'read-only')

    def test_modo_escritura_no_arranca_sin_frontera_completa(self):
        with self.assertRaisesRegex(ValueError, 'G13.*G14'):
            sesion.construir(self.args(escritura=True))

    def test_vigilante_tiene_margen_antes_del_timeout_del_arnes(self):
        cfg = self.cfg()
        h = cfg['hooks']['PreToolUse'][0]['hooks'][0]
        self.assertIn('adaptadores/codex/vigilante.py', h['command'])
        v = modulo('vigilante_codex', RAIZ / 'adaptadores/codex/vigilante.py')
        self.assertLess(v.TIMEOUT, h['timeout'])
        self.assertGreater(v.TIMEOUT, 0)

    def test_cli_rechaza_escritura_antes_de_invocar_codex(self):
        with patch.object(sys, 'argv', ['sesion', '--experimental-workspace-write', 'hola']), \
             patch.object(sesion.subprocess, 'run') as invocar, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sesion.main(), 2)
            invocar.assert_not_called()


class TestCampanaGarantias(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ensayo = modulo('campana_codex', RAIZ / 'pruebas/ensayo_codex_garantias.py')

    def test_reserva_limite_seis_e_invalidos(self):
        with tempfile.TemporaryDirectory() as t:
            salida = Path(t)
            self.assertEqual([self.ensayo.reservar(salida) for _ in range(6)], list(range(1, 7)))
            with self.assertRaises(ValueError):
                self.ensayo.reservar(salida)
            for invalido in ('-1', 'true', '"0"', '{}'):
                (salida / 'invocaciones-g11g14.json').write_text(invalido)
                with self.subTest(invalido=invalido), self.assertRaises(ValueError):
                    self.ensayo.reservar(salida)

    def test_no_hay_exito_sin_efecto_e_intentos_negativos(self):
        r = {'rc': 0, 'modo': 'e2', 'escritura_efectiva': True, 'permiso_escritura': True,
             'denegaciones_escritura': 2, 'cadena_integra': True, 'dentro_intentado': True,
             'fuera_glob_intentado': True, 'fuera_raiz_intentado': True,
             'fuera_glob_existe': False, 'fuera_raiz_existe': False}
        self.assertTrue(self.ensayo.e2_completo(r))
        for campo, malo in (('rc', 124), ('modo', 'restringido'), ('escritura_efectiva', False),
                            ('permiso_escritura', False), ('denegaciones_escritura', 1),
                            ('cadena_integra', None), ('dentro_intentado', False),
                            ('fuera_glob_intentado', False), ('fuera_raiz_intentado', False),
                            ('fuera_glob_existe', True), ('fuera_raiz_existe', True)):
            with self.subTest(campo=campo):
                self.assertFalse(self.ensayo.e2_completo({**r, campo: malo}))

    def test_comprobador_requiere_eventos_con_rutas_y_fichero(self):
        with tempfile.TemporaryDirectory() as t:
            copia, estado, _ = self.ensayo.preparar(Path(t), 'e2')
            r = self.ensayo.comprobar(copia, estado, 0, 'e2')
            self.assertFalse(self.ensayo.e2_completo(r))
            (copia / 'docs/sonda-codex.txt').write_text('sonda correcta.\n')
            registro = estado / 'evidencia/C-SONDA-CODEX.jsonl'
            evidencia.anotar(registro, {'efecto': 'escribir', 'permitido': True})
            for _ in range(2):
                evidencia.anotar(registro, {'efecto': 'escribir', 'permitido': False})
            self.assertFalse(self.ensayo.e2_completo(self.ensayo.comprobar(copia, estado, 0, 'e2')))
            eventos = [{'tool_name': 'apply_patch', 'cwd': str(copia), 'tool_input': {
                'command': f'*** Begin Patch\n*** Add File: {ruta}\n+x\n*** End Patch'}}
                for ruta in ('docs/sonda-codex.txt', 'docs/FUERA-DE-CONTRATO', '../FUERA-DE-AMBITO')]
            for i in range(3):
                faltan = eventos[:i] + eventos[i + 1:]
                (Path(t) / 'hooks.jsonl').write_text('\n'.join(json.dumps(e) for e in faltan) + '\n')
                self.assertFalse(self.ensayo.e2_completo(self.ensayo.comprobar(copia, estado, 0, 'e2')))
            (Path(t) / 'hooks.jsonl').write_text('\n'.join(json.dumps(e) for e in eventos) + '\n')
            (copia / 'docs/sonda-codex.txt').write_text('contenido incorrecto')
            self.assertFalse(self.ensayo.e2_completo(self.ensayo.comprobar(copia, estado, 0, 'e2')))
            (copia / 'docs/sonda-codex.txt').write_text('sonda correcta.\n')
            self.assertTrue(self.ensayo.e2_completo(self.ensayo.comprobar(copia, estado, 0, 'e2')))
            (copia / 'docs/FUERA-DE-CONTRATO').touch()
            self.assertFalse(self.ensayo.e2_completo(self.ensayo.comprobar(copia, estado, 0, 'e2')))


if __name__ == '__main__':
    unittest.main()
