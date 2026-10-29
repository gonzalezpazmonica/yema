"""Mutaciones del adaptador en copias: cada test nuevo debe detectar un defecto.

No cuenta importación, sintaxis, excepción del test ni skip como detección.
No se modifica el núcleo ni se invoca Codex real. Solo biblioteca estándar.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RAIZ = Path(__file__).resolve().parents[1]
MOTOR = 'adaptadores/codex/ejecutor/motor.py'
PUENTE = 'adaptadores/codex/ejecutor/puente.py'
PRODUCTOR = 'adaptadores/codex/ejecutor/productor.py'
BUCLE = 'adaptadores/codex/ejecutor/__main__.py'


def t(nombre):
    return 'test_codex_ejecutor.TestEjecutor.test_' + nombre


def p(nombre):
    return 'test_codex_productor.TestProductor.test_' + nombre


MUTACIONES = [
    ('no_crear', MOTOR,
     '        os.link(temporal, nombre, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)', '        pass',
     [t('permitido_se_aplica_y_reserva_una_vez')]),
    ('abrir_ante_rechazo', MOTOR,
     "        except Rechazo:\n            diario.anotar(p, 'rechazada')",
     "        except Rechazo:\n            (cfg.trabajo / p['ruta']).write_text(p['contenido'])\n            diario.anotar(p, 'rechazada')",
     [t('fuera_de_ambito_pasa_por_puerta_real_y_no_aplica'),
      t('puerta_muere_excepcion_ausente_y_timeout_no_aplican'), t('respuesta_invalida_nunca_es_permiso')]),
    ('anunciar_exito_ante_rechazo', MOTOR,
     "        except Rechazo:\n            diario.anotar(p, 'rechazada')\n            return 'rechazada'",
     "        except Rechazo:\n            diario.anotar(p, 'rechazada')\n            return 'aplicada'",
     [t('presupuesto_real_agotado')]),
    ('omitir_reserva', MOTOR,
     "            if (reserva.get('hash') != permiso['reserva']",
     "            if False and (reserva.get('hash') != permiso['reserva']",
     [t('respuesta_ligada_y_rc_cero_no_bastan_sin_reserva')]),
    ('aceptar_campos_extra', MOTOR,
     "    if not isinstance(p, dict) or set(p) != {'version', 'id', 'tipo', 'ruta', 'contenido'}:",
     "    if not isinstance(p, dict) or not {'version', 'id', 'tipo', 'ruta', 'contenido'}.issubset(p):",
     [t('esquema_cerrado_escapes_y_limite')]),
    ('seguir_enlaces_padres', MOTOR,
     '            hijo = os.open(parte, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)',
     '            hijo = os.open(parte, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)',
     [t('enlaces_y_destino_existente_no_sobrescribe')]),
    ('reutilizar_id', MOTOR, "        if p['id'] in diario.ultimas:",
     "        if False and p['id'] in diario.ultimas:", [t('repeticion_no_reaplica')]),
    ('ignorar_corrupcion', MOTOR,
     "            if r['prev'] != prev or r['hash'] != evidencia._hash(prev, cuerpo):",
     '            if False:', [t('cadena_alterada_y_truncado_impiden_aplicar')]),
    ('ignorar_pendientes', MOTOR,
     "            if not self.pendientes and any(r['fase'] not in TERMINALES for r in ultimas.values()):",
     '            if False:', [t('excepcion_antes_de_publicar_no_aplica_y_reserva_se_conserva'),
                               t('muerte_supervisora_antes_de_publicar_impide_continuidad')]),
    ('omitir_intencion', MOTOR,
     "            diario.anotar(p, 'intencion', ruta=p['ruta'], contenido_sha256=huella(p['contenido'].encode()))",
     '            pass', [t('evidencia_previa_durable_antes_de_escritura')]),
    ('ignorar_conflicto', MOTOR,
     "if not stat.S_ISREG(os.fstat(f.fileno()).st_mode) or huella(f.read(LIMITE + 1)) != intencion['contenido_sha256']:",
     'if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):',
     [t('reconciliar_caida_tras_publicacion_y_conflicto')]),
    ('inventar_aplicacion', MOTOR, "            resultado = 'no_aplicada'", "            resultado = 'aplicada'",
     [t('reconciliar_ausente_no_reintenta')]),
    ('ignorar_revocacion', MOTOR, '                if cfg.vinculo() != diario.vinculo:',
     '                if False and cfg.vinculo() != diario.vinculo:',
     [t('cambio_gobierno_entre_permiso_y_publicacion_bloquea')]),
    ('omitir_bloqueo', MOTOR, '            fcntl.flock(self.cerrojo, fcntl.LOCK_EX | fcntl.LOCK_NB)',
     '            pass', [t('bloqueo_exclusivo_del_estado')]),
    ('ignorar_plazo_comun', MOTOR, '    fin = time.monotonic() + timeout\n',
     '    fin = time.monotonic() + timeout + 1\n', [t('deadline_invalido_y_agotado')]),
    ('aceptar_ask', MOTOR, "r['decision'] != 'allow'", "r['decision'] not in ('allow', 'ask')",
     [t('respuesta_debe_casar_nonce_huella_vinculo_y_retorno')]),
    ('sobrescribir_carrera', MOTOR,
     '        os.link(temporal, nombre, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)',
     '        os.replace(temporal, nombre, src_dir_fd=fd, dst_dir_fd=fd)',
     [t('carrera_destino_no_sobrescribe')]),
    ('ignorar_carrera_directorio', MOTOR,
     '                    if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):',
     '                    if False and (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):',
     [t('carrera_directorio_no_publica_en_el_directorio_desplazado')]),
    ('alterar_snapshot', PRODUCTOR, '                    salida.write_bytes(datos)',
     "                    salida.write_bytes(b'alterado')", [p('vista_solo_lecturas_permitidas_y_version_fijada')]),
    ('omitir_filtro_lectura', PRODUCTOR, "                    if ok is not True or efecto != 'leer':",
     '                    if False:', [p('vista_denegada_y_enlaces_no_entran')]),
    ('conservar_hogar', PRODUCTOR,
     "    with tempfile.TemporaryDirectory(prefix='codex-home-', dir=destino) as t:",
     "    with __import__('contextlib').nullcontext(tempfile.mkdtemp(prefix='codex-home-', dir=destino)) as t:",
     [p('hogar_auth_se_borra_incluso_ante_excepcion')]),
    ('septima_llamada', PRODUCTOR, 'not 0 <= n < 6', 'not 0 <= n < 7',
     [p('contador_seis_y_datos_inesperados_cierran')]),
    ('productor_con_hooks', PRODUCTOR, "    cfg['features']['hooks'] = False", "    cfg['features']['hooks'] = True",
     [p('perfil_productor_no_depende_de_hooks_ni_pide_escritura')]),
    ('continuar_tras_fallo_productor', BUCLE,
     '        datos = proponer(cfg, salida, contexto, lecturas, auth)',
     "        try:\n            datos = proponer(cfg, salida, contexto, lecturas, auth)\n        except Rechazo:\n            datos = b'{}'",
     [p('fallo_productor_no_llega_al_aplicador')]),
    ('aceptar_uno_como_true', PUENTE, "    if (ok is not True or efecto != 'escribir'",
     "    if (not ok or efecto != 'escribir'", [p('puente_no_convierte_preguntar_ni_uno_en_permiso')]),
    ('dejar_descendientes', MOTOR, '        os.killpg(proceso.pid, signal.SIGKILL)',
     '        os.kill(proceso.pid, signal.SIGKILL)', [p('transporte_mata_descendientes_al_agotar_plazo')]),
    ('vista_escribible', PRODUCTOR, "'--ro-bind', str(snapshot), '/w'", "'--bind', str(snapshot), '/w'",
     ['test_codex_productor.TestCajaExterna.test_caja_oculta_autoridad_y_monta_vista_solo_lectura']),
    ('aceptar_preflight_fallido', PRODUCTOR, "    if rc != 0 or salida != b'aislada\\n':", '    if False:',
     ['test_codex_productor.TestCajaExterna.test_preflight_detecta_vista_escribible']),
    ('ignorar_historia', MOTOR, ".glob('*.jsonl')", ".glob('NO-EXISTE')",
     [t('pendiente_bloquea_tambien_un_nuevo_contrato'), t('cadena_historica_corrupta_bloquea_nuevos_efectos')]),
    ('reconciliar_sin_observar', MOTOR, '        resultados.extend(_reconciliar_contrato(cfg, cid))',
     '        pass', [t('reconciliar_revocado_solo_observa_sin_nuevo_permiso')]),
    ('salida_en_workspace', PRODUCTOR,
     '    if not salida.is_dir() or salida.resolve() == cfg.trabajo or cfg.trabajo in salida.resolve().parents:',
     '    if not salida.is_dir():', [p('salida_privada_fuera_del_workspace')]),
    ('propuesta_sigue_enlaces', PRODUCTOR,
     "    fd = os.open(h / 'propuesta.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)",
     "    fd = os.open(h / 'propuesta.json', os.O_RDONLY | os.O_NONBLOCK)",
     [p('propuesta_fichero_regular_acotado_sin_enlaces')]),
    ('cli_oculta_rechazo', BUCLE, '        return 2 if rechazado else 0', '        return 0',
     [p('cli_no_anuncia_exito_si_un_turno_fue_rechazado')]),
    ('omitir_retorno_al_modelo', BUCLE, 'json.dumps(resultados)', 'json.dumps([])',
     [p('bucle_informa_resultado_y_reevalua_cada_efecto')]),
]

ARNES = '''import json,sys,unittest
sys.path.insert(0,'pruebas')
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in sys.argv[1:])
result=unittest.TestResult()
suite.run(result)
print(json.dumps({'tests':result.testsRun,'fallos':[t.id() for t,_ in result.failures],
    'errores':[t.id() for t,_ in result.errors],'omitidos':[t.id() for t,_ in result.skipped]}))
'''


def probar(carpeta, nombres):
    r = subprocess.run([sys.executable, '-B', '-c', ARNES, *nombres], cwd=carpeta,
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError('falló el arnés, no es una detección')
    return json.loads(r.stdout)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--salida', required=True, type=Path)
    args = args.parse_args()
    todos = sorted({test for *_, tests in MUTACIONES for test in tests})
    reales = {f'{f.stem}.{c.name}.{m.name}'
        for f in (RAIZ / 'pruebas').glob('test_codex_*.py')
        if f.stem in ('test_codex_ejecutor', 'test_codex_productor')
        for c in ast.parse(f.read_text()).body if isinstance(c, ast.ClassDef)
        for m in c.body if isinstance(m, ast.FunctionDef) and m.name.startswith('test_')}
    if set(todos) != reales:
        raise RuntimeError('tests nuevos sin mutación: ' + str(sorted(reales - set(todos))))
    baseline = probar(RAIZ, todos)
    if baseline['errores'] or baseline['fallos'] or baseline['omitidos'] or baseline['tests'] != len(todos):
        raise RuntimeError('baseline incompleta o fallida: ' + json.dumps(baseline))
    resultados = []
    for nombre, fichero, original, reemplazo, tests in MUTACIONES:
        texto = (RAIZ / fichero).read_text()
        if texto.count(original) != 1:
            raise RuntimeError('mutación obsoleta o ambigua: ' + nombre)
        with tempfile.TemporaryDirectory(prefix='yema-mutacion-') as tdir:
            copia = Path(tdir) / 'repo'
            shutil.copytree(RAIZ, copia, ignore=shutil.ignore_patterns('.git', '.codex', '.agents', '.aws', '__pycache__'))
            (copia / fichero).write_text(texto.replace(original, reemplazo))
            compile((copia / fichero).read_text(), fichero, 'exec')
            r = probar(copia, tests)
            detectada = (r['tests'] == len(tests) and not r['errores'] and not r['omitidos']
                         and all(any(f == test or f.startswith(test + ' (') for f in r['fallos']) for test in tests))
            resultados.append({'mutacion': nombre, 'detectada': detectada, **r})
    fuentes = {str(p.relative_to(RAIZ)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (RAIZ / 'adaptadores/codex/ejecutor').glob('*.py')}
    resultado = {'ok': all(r['detectada'] for r in resultados), 'baseline': baseline,
                 'tests_cubiertos': len(todos), 'mutaciones': resultados, 'fuentes_sha256': fuentes}
    args.salida.write_text(json.dumps(resultado, indent=2) + '\n')
    print(json.dumps({'ok': resultado['ok'], 'tests': len(todos), 'mutaciones': len(resultados),
                      'no_detectadas': [r['mutacion'] for r in resultados if not r['detectada']]}))
    return 0 if resultado['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
