"""Supervisor serial; la configuración de autoridad solo llega por argv humano."""
import argparse
import json
from pathlib import Path
import sys

from .motor import Configuracion, Incierto, LIMITE, Rechazo, ejecutar, reconciliar
from .productor import proponer


def bucle(cfg, salida, prompt, lecturas, auth, turnos=1):
    if type(turnos) is not int or not 1 <= turnos <= 6:
        raise Rechazo('entre uno y seis turnos')
    resultados = []
    for turno in range(turnos):
        cfg.vinculo()
        contexto = (prompt + '\nPropón UNA creación en JSON; no uses herramientas para aplicarla. '
                    'Cada id debe ser nuevo. Las rutas son relativas al workspace real. '
                    f'Turno: {turno + 1}. Resultados previos: ' + json.dumps(resultados))
        datos = proponer(cfg, salida, contexto, lecturas, auth)
        resultado = ejecutar(datos, cfg)
        resultados.append({'turno': turno + 1, 'resultado': resultado})
    return resultados


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for nombre in ('yema', 'estado', 'trabajo'):
        p.add_argument('--' + nombre, required=True, type=Path)
    sub = p.add_subparsers(dest='modo', required=True)
    sub.add_parser('aplicar', help='una propuesta por stdin, para un supervisor confiable')
    sub.add_parser('reconciliar', help='observar pendientes sin repetir efectos')
    sesion = sub.add_parser('sesion', help='Codex aislado → JSON → puerta → aplicación')
    sesion.add_argument('--salida', required=True, type=Path)
    sesion.add_argument('--auth', type=Path, default=Path.home() / '.codex/auth.json')
    sesion.add_argument('--leer', action='append', default=[])
    sesion.add_argument('--turnos', type=int, default=1)
    sesion.add_argument('prompt')
    args = p.parse_args()
    try:
        cfg = Configuracion(args.yema, args.estado, args.trabajo)
        if args.modo == 'aplicar':
            resultado = ejecutar(sys.stdin.buffer.read(LIMITE + 1), cfg)
        elif args.modo == 'reconciliar':
            resultado = reconciliar(cfg)
        else:
            if not args.salida.is_dir() or cfg.trabajo == args.salida or cfg.trabajo in args.salida.resolve().parents:
                raise Rechazo('la salida privada debe existir fuera del workspace')
            resultado = bucle(cfg, args.salida, args.prompt, args.leer, args.auth, args.turnos)
        print(json.dumps({'resultado': resultado}, ensure_ascii=False))
        rechazado = resultado == 'rechazada' or (isinstance(resultado, list) and any(
            isinstance(r, dict) and r.get('resultado') == 'rechazada' for r in resultado))
        return 2 if rechazado else 0
    except Rechazo:
        print('{"resultado":"rechazada"}')
        return 2
    except Exception:
        print('{"resultado":"detenida","accion":"inspeccionar y reconciliar"}')
        return 3


if __name__ == '__main__':
    sys.exit(main())
