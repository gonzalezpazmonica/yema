"""Lecturas filtradas, caja externa efectiva y ciclo de credenciales temporales."""
import json
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apoyo_test import Entorno, aprobado, sellar
from nucleo import evidencia, puerta
from adaptadores.codex.ejecutor import motor as e, productor as p, puente
from adaptadores.codex.ejecutor.__main__ import bucle


class TestProductor(Entorno):
    def setUp(self):
        super().setUp()
        c = aprobado(self.trabajo)
        c['autoridad']['caduca'] = '2999-01-01T00:00:00+00:00'
        self.activar(sellar(c))
        self.cfg = e.Configuracion(self.yema, self.yema, self.trabajo)
        self.contexto = self.trabajo / 'src/contexto.txt'
        self.contexto.write_text('contexto público\n')
        self.salida = Path(self.tmp.name) / 'campana'
        self.salida.mkdir()
        self.auth = self.yema / 'auth-fixture.json'
        self.auth.write_text('{"fixture":true}')

    def test_vista_solo_lecturas_permitidas_y_version_fijada(self):
        vista = self.salida / 'vista'
        manifiesto = p.vista(self.cfg, vista, ['src/contexto.txt'])
        self.assertEqual((vista / 'src/contexto.txt').read_bytes(), self.contexto.read_bytes())
        self.assertEqual(manifiesto, [{'ruta': 'src/contexto.txt', 'sha256': e.huella(self.contexto.read_bytes())}])
        self.contexto.write_text('cambio posterior')
        self.assertEqual((vista / 'src/contexto.txt').read_text(), 'contexto público\n')
        registro = self.yema / 'evidencia/C-0001.jsonl'
        self.assertEqual(puerta.efectos_usados(registro), 0)
        self.assertTrue(evidencia.verificar(registro)[0])

    def test_vista_denegada_y_enlaces_no_entran(self):
        (self.trabajo / 'src/privado.env').write_text('no copiar')
        (self.trabajo / 'src/enlace').symlink_to(self.contexto)
        for i, ruta in enumerate(['src/privado.env', 'src/enlace', '../estado/auth-fixture.json', '.git/config']):
            with self.subTest(ruta=ruta), self.assertRaises((e.Rechazo, OSError)):
                p.vista(self.cfg, self.salida / f'vista-{i}', [ruta])
            self.assertFalse((self.salida / f'vista-{i}' / ruta).is_file())

    def test_hogar_auth_se_borra_incluso_ante_excepcion(self):
        with self.assertRaisesRegex(RuntimeError, 'ensayo'):
            with p.hogar(self.salida, self.auth) as h:
                self.assertEqual((h / 'auth.json').read_bytes(), self.auth.read_bytes())
                self.assertEqual((h / 'auth.json').stat().st_mode & 0o777, 0o600)
                raise RuntimeError('ensayo')
        self.assertFalse(h.exists())
        self.assertEqual(self.auth.read_text(), '{"fixture":true}')

    def test_contador_seis_y_datos_inesperados_cierran(self):
        self.assertEqual([p.reservar(self.salida) for _ in range(6)], list(range(1, 7)))
        with self.assertRaises(e.Rechazo):
            p.reservar(self.salida)
        for valor in ('true', '-1', '"0"', '{}'):
            (self.salida / 'invocaciones.json').write_text(valor)
            with self.subTest(valor=valor), self.assertRaises(e.Rechazo):
                p.reservar(self.salida)

    def test_perfil_productor_no_depende_de_hooks_ni_pide_escritura(self):
        import tomllib
        orden = p.orden_codex()
        cfg = tomllib.loads('\n'.join(orden[i + 1] for i, x in enumerate(orden) if x == '-c'))
        self.assertEqual(cfg['model'], 'gpt-6.1-terra')
        self.assertEqual(cfg['model_reasoning_effort'], 'medium')
        self.assertEqual(cfg['sandbox_mode'], 'read-only')
        self.assertEqual(cfg['approval_policy'], 'never')
        self.assertEqual(cfg['mcp_servers'], {})
        self.assertEqual(cfg['hooks'], {})
        self.assertIs(cfg['features']['hooks'], False)
        self.assertIs(cfg['features']['shell_tool'], False)

    def test_fallo_productor_no_llega_al_aplicador(self):
        with patch('adaptadores.codex.ejecutor.__main__.proponer', side_effect=e.Rechazo('timeout')), \
             patch('adaptadores.codex.ejecutor.__main__.ejecutar') as aplicar:
            with self.assertRaises(e.Rechazo):
                bucle(self.cfg, self.salida, 'encargo', [], self.auth)
            aplicar.assert_not_called()
        self.assertFalse((self.trabajo / 'src/nueva.txt').exists())

    def test_puente_no_convierte_preguntar_ni_uno_en_permiso(self):
        propuesta = {'version': 1, 'id': 'p-1', 'tipo': 'crear', 'ruta': 'src/nueva.txt', 'contenido': 'x'}
        peticion = {'version': 1, 'nonce': 'n' * 32, 'propuesta': propuesta,
                    'efecto_sha256': e.huella(e.canon(propuesta)), 'vinculo': self.cfg.vinculo()}
        with e.Diario(self.cfg) as diario:
            for ok in (puerta.PREGUNTAR, 1):
                def simular(*_):
                    evidencia.anotar(diario.ruta, {'permitido': True})
                    return ok, '', 'escribir'
                with self.subTest(ok=ok), patch.object(puerta, 'evaluar_y_registrar', simular), self.assertRaises(e.Rechazo):
                    puente.evaluar(peticion, self.cfg)
        self.assertFalse((self.trabajo / 'src/nueva.txt').exists())

    def test_transporte_mata_descendientes_al_agotar_plazo(self):
        marca = self.salida / 'NO-DEBE-EXISTIR'
        nieto = f'import time; from pathlib import Path; time.sleep(0.4); Path({str(marca)!r}).touch()'
        hijo = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{nieto!r}]); time.sleep(10)'
        with self.assertRaises(e.Rechazo):
            e.proceso_acotado([sys.executable, '-c', hijo], b'', 0.1, 1024)
        time.sleep(0.5)
        self.assertFalse(marca.exists())

    def test_salida_privada_fuera_del_workspace(self):
        self.assertEqual(p.validar_salida(self.cfg, self.salida), self.salida)
        for salida in (self.trabajo, self.trabajo / 'src', self.salida / 'ausente'):
            with self.subTest(salida=salida), self.assertRaises(e.Rechazo):
                p.validar_salida(self.cfg, salida)

    def test_propuesta_fichero_regular_acotado_sin_enlaces(self):
        propuesta = self.salida / 'propuesta.json'
        propuesta.write_bytes(b'{}')
        self.assertEqual(p.leer_propuesta(self.salida), b'{}')
        propuesta.write_bytes(b' ' * (e.LIMITE + 1))
        with self.assertRaises(e.Rechazo):
            p.leer_propuesta(self.salida)
        propuesta.unlink()
        propuesta.symlink_to(self.auth)
        with self.assertRaises((OSError, e.Rechazo)):
            p.leer_propuesta(self.salida)

    def test_cli_no_anuncia_exito_si_un_turno_fue_rechazado(self):
        from adaptadores.codex.ejecutor.__main__ import main
        argv = ['ejecutor', '--yema', str(self.yema), '--estado', str(self.yema),
                '--trabajo', str(self.trabajo), 'sesion', '--salida', str(self.salida), 'encargo']
        for resultado, esperado in [('aplicada', 0), ('rechazada', 2)]:
            with self.subTest(resultado=resultado), patch.object(sys, 'argv', argv), \
                 patch('adaptadores.codex.ejecutor.__main__.bucle', return_value=[{'resultado': resultado}]), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), esperado)

    def test_bucle_informa_resultado_y_reevalua_cada_efecto(self):
        propuesta = {'version': 1, 'tipo': 'crear', 'id': 'turno-1', 'ruta': 'src/nueva.txt', 'contenido': 'exacto'}
        segunda = {**propuesta, 'id': 'turno-2', 'ruta': 'fuera.txt'}
        with patch('adaptadores.codex.ejecutor.__main__.proponer',
                   side_effect=[e.canon(propuesta), e.canon(segunda)]) as proponer:
            resultado = bucle(self.cfg, self.salida, 'encargo', [], self.auth, turnos=2)
            self.assertIn('aplicada', proponer.call_args_list[1].args[2])
        self.assertEqual([r['resultado'] for r in resultado], ['aplicada', 'rechazada'])
        self.assertTrue((self.trabajo / 'src/nueva.txt').is_file())
        self.assertEqual((self.trabajo / 'src/nueva.txt').read_bytes(), b'exacto')
        self.assertFalse((self.trabajo / 'fuera.txt').exists())
        self.assertTrue(evidencia.verificar(self.yema / 'evidencia/C-0001.jsonl')[0])


class TestCajaExterna(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        for carpeta in ('vista', 'hogar', 'paquete/bin', 'paquete/codex-resources'):
            (self.base / carpeta).mkdir(parents=True)
        self.codex = self.base / 'paquete/bin/codex'
        self.codex.write_text('#!/bin/sh\nexit 0\n')
        self.codex.chmod(0o755)
        (self.base / 'paquete/codex-resources/bwrap').touch()
        self.esquema = self.base / 'esquema.json'
        self.esquema.write_text('{}')
        self.secreto = self.base / 'autoridad'
        self.secreto.write_text('invisible')
        if not Path('/usr/bin/bwrap').exists():
            self.skipTest('sin bwrap instalado: la sesión de producción también se deniega')
        self.orden = p.caja(self.base / 'vista', self.base / 'hogar', self.esquema,
                             codex=self.codex, bwrap='/usr/bin/bwrap')
        rc = subprocess.run(['/usr/bin/bwrap', '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
            '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64', '--unshare-all', '--',
            '/usr/bin/true'], capture_output=True).returncode
        if rc != 0:
            self.skipTest('sin bwrap operativo: la sesión de producción también se deniega')

    def test_caja_oculta_autoridad_y_monta_vista_solo_lectura(self):
        aislada = True
        try:
            p.comprobar_caja(self.orden, [self.secreto])
        except e.Rechazo:
            aislada = False
        self.assertTrue(aislada)
        self.assertFalse((self.base / 'vista/NO-ESCRIBIR').exists())
        self.assertEqual(self.secreto.read_text(), 'invisible')

    def test_preflight_detecta_vista_escribible(self):
        orden = self.orden[:]
        i = orden.index(str(self.base / 'vista'))
        orden[i - 1] = '--bind'
        with self.assertRaises(e.Rechazo):
            p.comprobar_caja(orden, [self.secreto])
        self.assertTrue((self.base / 'vista/NO-ESCRIBIR').is_file())


if __name__ == '__main__':
    unittest.main()
