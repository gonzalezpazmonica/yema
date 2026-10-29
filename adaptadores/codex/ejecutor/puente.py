"""Hijo confiable de la supervisora: stdin cerrado, puerta real y recibo durable."""
import argparse
import sys

from nucleo import evidencia, puerta
from .motor import (Configuracion, LIMITE, Rechazo, canon, cargar, estado_nativo,
                    huella, propuesta, sincronizar, verificar)


def evaluar(peticion, cfg):
    if (not isinstance(peticion, dict) or set(peticion) != {
            'version', 'nonce', 'propuesta', 'efecto_sha256', 'vinculo'}
            or type(peticion['version']) is not int or peticion['version'] != 1
            or not isinstance(peticion['nonce'], str) or len(peticion['nonce']) != 32):
        raise Rechazo('petición inválida')
    p = propuesta(canon(peticion['propuesta']))
    if huella(canon(p)) != peticion['efecto_sha256'] or cfg.vinculo() != peticion['vinculo']:
        raise Rechazo('vínculo inválido')
    evento = {'tool_name': 'Write', 'tool_input': {
        'file_path': str(cfg.trabajo / p['ruta']), 'content': p['contenido']},
        'cwd': str(cfg.trabajo), 'permission_mode': 'dontAsk'}
    registro = cfg.estado / 'evidencia' / (peticion['vinculo']['contrato'] + '.jsonl')
    anteriores = verificar(registro.read_bytes())
    with estado_nativo(cfg.estado):
        ok, _, efecto = puerta.evaluar_y_registrar(evento, cfg.yema)
    sincronizar(registro)
    recibos = verificar(registro.read_bytes())
    if (ok is not True or efecto != 'escribir' or len(recibos) != len(anteriores) + 1
            or recibos[-1].get('permitido') is not True):
        raise Rechazo('puerta sin permiso')
    if cfg.vinculo() != peticion['vinculo']:
        raise Rechazo('gobierno cambiado durante evaluación')
    return {'version': 1, 'nonce': peticion['nonce'], 'efecto_sha256': peticion['efecto_sha256'],
            'decision': 'allow', 'vinculo': peticion['vinculo'], 'reserva': recibos[-1]['hash']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for nombre in ('yema', 'estado', 'trabajo'):
        p.add_argument('--' + nombre, required=True)
    args = p.parse_args()
    try:
        cfg = Configuracion(args.yema, args.estado, args.trabajo)
        datos = sys.stdin.buffer.read(LIMITE + 8193)
        if len(datos) > LIMITE + 8192:
            raise Rechazo('petición excesiva')
        respuesta = evaluar(cargar(datos), cfg)
        sys.stdout.buffer.write(canon(respuesta) + b'\n')
        return 0
    except Exception:
        # Ni entradas ni motivos potencialmente privados se devuelven al modelo.
        return 2


if __name__ == '__main__':
    sys.exit(main())
