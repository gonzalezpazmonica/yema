"""yema — herramienta humana de gobierno de contratos.

    yema validar <ruta.json>
    yema admitir <borrador.json>          copia un borrador a contratos/ como candidato
    yema transicion <id> <estado> --por <quien> --motivo <texto>
    yema activar <id> --por <quien>       activo + puntero ACTIVO
    yema suspender | revocar <id> --por <quien> --motivo <texto>
    yema estado                           contrato activo y vigencia
    yema evidencia <id>                   verifica la cadena de evidencia

Aprobar, activar o reanudar exige una terminal interactiva: lo hace una persona.
(Es una barrera débil; la autenticidad fuerte llega con la firma de la v1.)
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nucleo import contrato, evidencia, puerta  # noqa: E402

HUMANAS = {"aprobado", "activo"}


def _raiz(raiz):
    return Path(raiz or os.environ.get("YEMA_RAIZ") or Path(__file__).resolve().parent.parent)


def _ruta(raiz, cid):
    if "/" in cid or not cid:
        raise SystemExit("identificador inválido")
    return raiz / "contratos" / f"{cid}.json"


def main(argv=None, raiz=None, tty=None):
    raiz = _raiz(raiz)
    tty = sys.stdin.isatty() if tty is None else tty
    p = argparse.ArgumentParser(prog="yema")
    s = p.add_subparsers(dest="orden", required=True)
    s.add_parser("validar").add_argument("ruta")
    s.add_parser("admitir").add_argument("ruta")
    t = s.add_parser("transicion")
    t.add_argument("id"), t.add_argument("estado")
    for nombre in ("activar", "suspender", "revocar"):
        x = s.add_parser(nombre)
        x.add_argument("id")
    for x in (t, s.choices["activar"], s.choices["suspender"], s.choices["revocar"]):
        x.add_argument("--por", required=True)
        x.add_argument("--motivo", default="")
    s.add_parser("estado")
    s.add_parser("evidencia").add_argument("id")
    a = p.parse_args(argv)
    pol = json.loads((raiz / "gobierno/politica.json").read_text(encoding="utf-8"))
    codigo, raiz = raiz, puerta.estado_de(raiz, pol)

    if a.orden == "validar":
        e = contrato.errores(contrato.cargar(a.ruta))
        print("\n".join(e) or "válido")
        return 1 if e else 0
    if a.orden == "admitir":
        c = contrato.cargar(a.ruta)
        if contrato.errores(c) or c.get("estado") not in ("borrador", "candidato"):
            print("borrador inválido o en estado no admisible", file=sys.stderr)
            return 1
        destino = _ruta(raiz, c["id"])
        if destino.exists():
            print(f"ya existe {c['id']}: nueva versión con otro id o versión", file=sys.stderr)
            return 1
        c["estado"] = "candidato"
        contrato.guardar(destino, c)
        print(f"admitido {c['id']} como candidato")
        return 0
    if a.orden == "estado":
        punt = raiz / "contratos/ACTIVO"
        if not punt.exists():
            print("sin contrato activo (E0: solo lectura)")
            return 0
        c, motivo = puerta.activo(codigo, pol, None)
        cid = punt.read_text().strip()
        print(f"{cid}: {'vigente' if c else motivo}")
        return 0
    if a.orden == "evidencia":
        ok, n = evidencia.verificar(raiz / "evidencia" / f"{a.id}.jsonl")
        print(f"cadena íntegra, {n} recibos" if ok else f"cadena ROTA en el recibo {n}")
        return 0 if ok else 1

    nuevo = {"activar": "activo", "suspender": "suspendido", "revocar": "revocado"}.get(a.orden, getattr(a, "estado", None))
    if nuevo in HUMANAS and not tty:
        print("aprobar o activar exige una terminal interactiva (una persona)", file=sys.stderr)
        return 3
    ruta = _ruta(raiz, a.id)
    c, err = contrato.transicion(contrato.cargar(ruta), nuevo, a.por, a.motivo, pol)
    if err:
        print(err, file=sys.stderr)
        return 1
    contrato.guardar(ruta, c)
    punt = raiz / "contratos/ACTIVO"
    if nuevo == "activo":
        punt.write_text(a.id)
    elif nuevo in contrato.TERMINALES | {"suspendido"} and punt.exists() and punt.read_text().strip() == a.id:
        punt.unlink()
    evidencia.anotar(raiz / "evidencia" / f"{a.id}.jsonl",
                     {"contrato": a.id, "transicion": nuevo, "por": a.por, "motivo": a.motivo})
    print(f"{a.id}: {nuevo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
