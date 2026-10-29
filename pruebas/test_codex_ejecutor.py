"""Ejecutor con puerta real; autoridad y ficheros siempre sintéticos."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apoyo_test import Entorno, aprobado, sellar
from nucleo import contrato, evidencia, puerta
from adaptadores.codex.ejecutor import motor as e


class TestEjecutor(Entorno):
    def setUp(self):
        super().setUp()
        self.c = aprobado(self.trabajo)
        self.c['autoridad']['caduca'] = '2999-01-01T00:00:00+00:00'
        self.c = sellar(self.c)
        self.activar(self.c)
        self.cfg = e.Configuracion(self.yema, self.yema, self.trabajo)
        self.registro = self.yema / 'evidencia/C-0001.jsonl'
        self.salida = self.trabajo / 'src/nueva.txt'

    def datos(self, **cambios):
        return e.canon({
            'version': 1, 'id': 'p-1', 'tipo': 'crear', 'ruta': 'src/nueva.txt',
            'contenido': 'hola ñ\n', **cambios})

    def ejecutar(self, **opciones):
        return e.ejecutar(opciones.pop('datos', self.datos()), self.cfg, **opciones)

    def sin_efectos(self):
        self.assertEqual(list((self.trabajo / 'src').iterdir()), [])

    def test_permitido_se_aplica_y_reserva_una_vez(self):
        self.assertEqual(self.ejecutar(), 'aplicada')
        self.assertTrue(self.salida.is_file())
        self.assertEqual(self.salida.read_bytes(), 'hola ñ\n'.encode())
        self.assertEqual(puerta.efectos_usados(self.registro), 1)
        registros = evidencia.leer(self.registro)
        fases = [r['fase'] for r in registros if r.get('evento') == e.EVENTO]
        self.assertEqual(fases, ['propuesta', 'autorizada', 'intencion', 'aplicada'])
        reserva = next(r for r in registros if r.get('herramienta') == 'Write')
        autorizada = next(r for r in registros if r.get('fase') == 'autorizada')
        self.assertEqual(autorizada['reserva'], reserva['hash'])
        self.assertTrue(evidencia.verificar(self.registro)[0])

    def test_fuera_de_ambito_pasa_por_puerta_real_y_no_aplica(self):
        self.assertEqual(self.ejecutar(datos=self.datos(ruta='fuera.txt')), 'rechazada')
        self.assertFalse((self.trabajo / 'fuera.txt').exists())
        denegado = next(r for r in evidencia.leer(self.registro) if r.get('herramienta') == 'Write')
        self.assertIs(denegado['permitido'], False)
        self.assertEqual(puerta.efectos_usados(self.registro), 0)
        self.assertTrue(evidencia.verificar(self.registro)[0])

    def test_presupuesto_real_agotado(self):
        self.c['recursos']['efectos_max'] = 1
        self.activar(sellar(self.c))
        self.assertEqual(self.ejecutar(), 'aplicada')
        self.assertEqual(self.ejecutar(datos=self.datos(id='p-2', ruta='src/otra.txt')), 'rechazada')
        self.assertFalse((self.trabajo / 'src/otra.txt').exists())
        self.assertEqual(puerta.efectos_usados(self.registro), 1)

    def test_puerta_muere_excepcion_ausente_y_timeout_no_aplican(self):
        programas = ['import os,signal; os.kill(os.getpid(),signal.SIGKILL)',
                     'raise RuntimeError("fallo")', 'import time; time.sleep(10)']
        for i, programa in enumerate(programas):
            with self.subTest(programa=programa):
                self.assertEqual(self.ejecutar(datos=self.datos(id=f'fallo-{i}'),
                    orden=[sys.executable, '-c', programa], timeout=0.15), 'rechazada')
                self.sin_efectos()
        self.assertEqual(self.ejecutar(datos=self.datos(id='ausente'),
            orden=[str(self.yema / 'ausente')]), 'rechazada')
        self.sin_efectos()

    def test_respuesta_invalida_nunca_es_permiso(self):
        for i, salida in enumerate(['', '{}', '[]', 'no JSON', '{"decision":"allow"}']):
            with self.subTest(salida=salida):
                self.assertEqual(self.ejecutar(datos=self.datos(id=f'invalida-{i}'),
                    orden=[sys.executable, '-c', f'print({salida!r})']), 'rechazada')
                self.sin_efectos()

    def test_respuesta_ligada_y_rc_cero_no_bastan_sin_reserva(self):
        programa = ('import json,sys; p=json.load(sys.stdin); '
                    'print(json.dumps({"version":1,"nonce":p["nonce"],'
                    '"efecto_sha256":p["efecto_sha256"],"decision":"allow",'
                    '"vinculo":p["vinculo"],"reserva":"' + '0' * 64 + '"}))')
        self.assertEqual(self.ejecutar(orden=[sys.executable, '-c', programa]), 'rechazada')
        self.sin_efectos()

    def test_esquema_cerrado_escapes_y_limite(self):
        for i, cambios in enumerate(({'ruta': '../fuera'}, {'ruta': '/tmp/fuera'}, {'ruta': 'src//a'},
                        {'ruta': 'src/./a'}, {'ruta': 'src/a\\b'}, {'version': True},
                        {'tipo': 'orden'}, {'aprobado': True}, {'contenido': 7})):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.ejecutar(datos=self.datos(id=f'validacion-{i}', **cambios)), 'rechazada')
                self.sin_efectos()
        for datos in (b'{"id":"a","id":"b"}', b'x' * (e.LIMITE + 1), b'NaN'):
            self.assertEqual(self.ejecutar(datos=datos), 'rechazada')
        p = json.loads(self.datos())
        p['contenido'] += 'x' * (e.LIMITE - len(e.canon(p)))
        self.assertEqual(len(e.canon(p)), e.LIMITE)
        self.assertEqual(self.ejecutar(datos=e.canon({**p, 'contenido': p['contenido'] + 'x'})), 'rechazada')
        self.assertEqual(self.ejecutar(datos=e.canon(p)), 'aplicada')

    def test_enlaces_y_destino_existente_no_sobrescribe(self):
        self.salida.symlink_to(self.yema / 'memoria/ajeno')
        self.assertEqual(self.ejecutar(), 'rechazada')
        self.assertFalse((self.yema / 'memoria/ajeno').exists())
        self.salida.unlink()
        self.salida.write_text('anterior')
        self.assertEqual(self.ejecutar(datos=self.datos(id='existente')), 'rechazada')
        self.assertEqual(self.salida.read_text(), 'anterior')
        (self.trabajo / 'enlace').symlink_to(self.trabajo / 'src', target_is_directory=True)
        self.assertEqual(self.ejecutar(datos=self.datos(id='padre', ruta='enlace/otro')), 'rechazada')
        self.assertFalse((self.trabajo / 'src/otro').exists())

    def test_repeticion_no_reaplica(self):
        self.assertEqual(self.ejecutar(), 'aplicada')
        self.salida.unlink()
        with self.assertRaises(e.Rechazo):
            self.ejecutar()
        self.sin_efectos()

    def test_cadena_alterada_y_truncado_impiden_aplicar(self):
        evidencia.anotar(self.registro, {'fixture': True})
        original = self.registro.read_bytes()
        for datos in (original.replace(b'true', b'false'), original[:-1]):
            self.registro.write_bytes(datos)
            with self.subTest(datos=datos), self.assertRaises(e.Incierto):
                self.ejecutar()
            self.sin_efectos()

    def test_excepcion_antes_de_publicar_no_aplica_y_reserva_se_conserva(self):
        with patch.object(e, 'crear', side_effect=OSError('disco')):
            with self.assertRaises(e.Incierto):
                self.ejecutar()
        self.sin_efectos()
        self.assertEqual(puerta.efectos_usados(self.registro), 1)
        with self.assertRaises(e.Incierto):
            self.ejecutar(datos=self.datos(id='nuevo'))

    def test_evidencia_previa_durable_antes_de_escritura(self):
        original = e.Diario.anotar
        def fallo(diario, p, fase, **datos):
            if fase == 'intencion':
                raise OSError('fsync')
            return original(diario, p, fase, **datos)
        with patch.object(e.Diario, 'anotar', fallo), self.assertRaises(e.Incierto):
            self.ejecutar()
        self.sin_efectos()
        self.assertEqual(puerta.efectos_usados(self.registro), 1)

    def test_reconciliar_caida_tras_publicacion_y_conflicto(self):
        original = e.Diario.anotar
        def fallo(diario, p, fase, **datos):
            if fase == 'aplicada':
                raise OSError('caida')
            return original(diario, p, fase, **datos)
        with patch.object(e.Diario, 'anotar', fallo), self.assertRaises(e.Incierto):
            self.ejecutar()
        self.assertEqual(self.salida.read_text(), 'hola ñ\n')
        with self.assertRaises(e.Incierto):
            self.ejecutar(datos=self.datos(id='p-2'))
        self.salida.write_text('conflicto')
        with self.assertRaises(e.Incierto):
            e.reconciliar(self.cfg)
        self.salida.write_text('hola ñ\n')
        self.assertEqual(e.reconciliar(self.cfg), ['aplicada'])
        self.assertTrue(evidencia.verificar(self.registro)[0])
        self.assertEqual(puerta.efectos_usados(self.registro), 1)

    def test_reconciliar_ausente_no_reintenta(self):
        with patch.object(e, 'crear', side_effect=OSError('disco')), self.assertRaises(e.Incierto):
            self.ejecutar()
        self.assertEqual(e.reconciliar(self.cfg), ['no_aplicada'])
        self.sin_efectos()
        self.assertEqual(puerta.efectos_usados(self.registro), 1)

    def test_cambio_gobierno_entre_permiso_y_publicacion_bloquea(self):
        original = e.consultar
        def revocar(*args, **kwargs):
            r = original(*args, **kwargs)
            c = contrato.cargar(self.yema / 'contratos/C-0001.json')
            c['estado'] = 'revocado'
            contrato.guardar(self.yema / 'contratos/C-0001.json', c)
            return r
        with patch.object(e, 'consultar', revocar):
            self.assertEqual(self.ejecutar(), 'rechazada')
        self.sin_efectos()

    def test_bloqueo_exclusivo_del_estado(self):
        with e.Diario(self.cfg) as diario:
            with self.assertRaises(e.Incierto):
                self.ejecutar()
            self.assertEqual(diario.registros, [])
        self.sin_efectos()

    def test_deadline_invalido_y_agotado(self):
        for plazo in (True, 0, -1, float('nan'), float('inf')):
            with self.subTest(plazo=plazo), self.assertRaises(e.Rechazo):
                self.ejecutar(timeout=plazo)
        original = e.consultar
        def lenta(*args, **kwargs):
            r = original(*args, **kwargs)
            time.sleep(0.2)
            return r
        with patch.object(e, 'consultar', lenta):
            self.assertEqual(self.ejecutar(timeout=0.15), 'rechazada')
        self.sin_efectos()

    def test_respuesta_debe_casar_nonce_huella_vinculo_y_retorno(self):
        peticion = {'nonce': 'n' * 32, 'efecto_sha256': 'a' * 64, 'vinculo': self.cfg.vinculo()}
        respuesta = {'version': 1, **peticion, 'decision': 'allow', 'reserva': 'b' * 64}
        self.assertEqual(e.consultar([sys.executable, '-c', f'print({json.dumps(respuesta)!r})'], peticion, 1), respuesta)
        for campo, malo in [('nonce', 'otro'), ('efecto_sha256', '0' * 64), ('vinculo', {}),
                            ('decision', 'ask'), ('version', True), ('reserva', None)]:
            programa = f'print({json.dumps({**respuesta, campo: malo})!r})'
            with self.subTest(campo=campo), self.assertRaises(e.Rechazo):
                e.consultar([sys.executable, '-c', programa], peticion, 1)
        with self.assertRaises(e.Rechazo):
            e.consultar([sys.executable, '-c', f'print({json.dumps(respuesta)!r}); raise SystemExit(2)'], peticion, 1)

    def test_carrera_destino_no_sobrescribe(self):
        original = e.crear
        def carrera(*args):
            self.salida.write_text('otra escritora')
            return original(*args)
        with patch.object(e, 'crear', carrera), self.assertRaises(e.Incierto):
            self.ejecutar()
        self.assertEqual(self.salida.read_text(), 'otra escritora')
        with self.assertRaises(e.Incierto):
            e.reconciliar(self.cfg)

    def test_carrera_directorio_no_publica_en_el_directorio_desplazado(self):
        original = e.consultar
        def carrera(*args, **kwargs):
            r = original(*args, **kwargs)
            (self.trabajo / 'src').rename(self.trabajo / 'desplazada')
            (self.trabajo / 'src').mkdir()
            return r
        with patch.object(e, 'consultar', carrera):
            self.assertEqual(self.ejecutar(), 'rechazada')
        self.assertFalse((self.trabajo / 'desplazada/nueva.txt').exists())
        self.sin_efectos()

    def test_muerte_supervisora_antes_de_publicar_impide_continuidad(self):
        marca = self.yema / 'lista'
        programa = ("from adaptadores.codex.ejecutor import motor as e; from pathlib import Path; import time; "
                    f"cfg=e.Configuracion(Path({str(self.yema)!r}),Path({str(self.yema)!r}),Path({str(self.trabajo)!r})); "
                    f"e.crear=lambda *a: (Path({str(marca)!r}).touch(),time.sleep(10)); "
                    f"e.ejecutar({self.datos()!r},cfg)")
        proceso = subprocess.Popen([sys.executable, '-B', '-c', programa], cwd=e.FUENTES,
                                   start_new_session=True, stderr=subprocess.DEVNULL)
        try:
            fin = time.monotonic() + 3
            while not marca.exists() and proceso.poll() is None and time.monotonic() < fin:
                time.sleep(0.01)
            self.assertTrue(marca.exists(), 'no se llegó a la intención durable')
        finally:
            e.matar(proceso)
        self.sin_efectos()
        self.assertEqual(puerta.efectos_usados(self.registro), 1)
        with self.assertRaises(e.Incierto):
            self.ejecutar(datos=self.datos(id='tras-caida'))
        self.assertEqual(e.reconciliar(self.cfg), ['no_aplicada'])

    def test_pendiente_bloquea_tambien_un_nuevo_contrato(self):
        with patch.object(e, 'crear', side_effect=OSError('disco')), self.assertRaises(e.Incierto):
            self.ejecutar()
        c2 = {**self.c, 'id': 'C-0002'}
        self.activar(sellar(c2))
        with self.assertRaises(e.Incierto):
            self.ejecutar(datos=self.datos(id='contrato-nuevo'))
        self.sin_efectos()
        self.assertEqual(e.reconciliar(self.cfg), ['no_aplicada'])
        self.assertEqual(puerta.efectos_usados(self.registro), 1)

    def test_cadena_historica_corrupta_bloquea_nuevos_efectos(self):
        (self.yema / 'evidencia/C-ANTERIOR.jsonl').write_text('{"corrupto":true}\n')
        with self.assertRaises(e.Incierto):
            self.ejecutar()
        self.sin_efectos()

    def test_reconciliar_revocado_solo_observa_sin_nuevo_permiso(self):
        original = e.Diario.anotar
        def fallo(diario, p, fase, **datos):
            if fase == 'aplicada':
                raise OSError('caida')
            return original(diario, p, fase, **datos)
        with patch.object(e.Diario, 'anotar', fallo), self.assertRaises(e.Incierto):
            self.ejecutar()
        c = contrato.cargar(self.yema / 'contratos/C-0001.json')
        c['estado'] = 'revocado'
        contrato.guardar(self.yema / 'contratos/C-0001.json', c)
        self.assertEqual(e.reconciliar(self.cfg), ['aplicada'])
        self.assertEqual(self.salida.read_bytes(), 'hola ñ\n'.encode())
        self.assertEqual(puerta.efectos_usados(self.registro), 1)
        with self.assertRaises(e.Rechazo):
            self.ejecutar(datos=self.datos(id='tras-revocacion'))


if __name__ == '__main__':
    unittest.main()
