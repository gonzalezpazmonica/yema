"""yema — herramienta humana de gobierno de contratos.

    yema validar <ruta.json>
    yema admitir <borrador.json>          copia un borrador a contratos/ como candidato
    yema transicion <id> <estado> --por <quien> --motivo <texto>
    yema activar <id> --por <quien>       activo + puntero ACTIVO
    yema suspender | revocar <id> --por <quien> --motivo <texto>
    yema estado                           contrato activo y vigencia
    yema evidencia <id>                   verifica la cadena de evidencia
    yema resumen <id>                     el contrato en lenguaje llano
    yema aprobar <id> <huella8>           aprueba y activa (solo una persona)
    yema cuidado                          salud: permisos, copias, disco, descanso
    yema copia                            copia del estado privado (rota las viejas)

Aprobar lo hace una persona: o en su terminal, o contestando «sí» al diálogo de
permisos del arnés cuando Yema lo pide en la conversación (la puerta deja un
ticket de un solo uso que caduca en 5 minutos). El modelo no puede pulsar ese diálogo.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nucleo import contrato, cuidado, evidencia, puerta  # noqa: E402

HUMANAS = {"aprobado", "activo"}
VENTANA_TICKET_S = 300


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
    s.add_parser("resumen").add_argument("id")
    s.add_parser("cuidado")
    s.add_parser("copia")
    ap = s.add_parser("aprobar")
    ap.add_argument("id"), ap.add_argument("huella")
    ap.add_argument("--por", default=None)
    ap.add_argument("--motivo", default="aprobado por la persona")
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
    if a.orden == "resumen":
        c = puerta._contrato_de_gobierno(raiz, a.id)
        if c is None:
            print(f"no encuentro {a.id}", file=sys.stderr)
            return 1
        print(contrato.resumen(c))
        return 0
    if a.orden == "cuidado":
        res = cuidado.chequeos(raiz, pol)
        for nivel, clave, msg in res:
            print(f"{nivel:6} {clave:9} {msg}")
        return 1 if any(n == "alerta" for n, _, _ in res) else 0
    if a.orden == "copia":
        ruta = cuidado.copia(raiz, pol)
        cuidado.rotar(pol)
        print(f"copia: {ruta}")
        return 0
    if a.orden == "aprobar":
        return _aprobar(a, raiz, codigo, pol, tty)
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


def _persona_presente(raiz, cid, h8, tty):
    """Terminal interactiva, o ticket fresco que dejó la puerta al preguntar (se consume)."""
    if tty:
        return True
    t = raiz / "aprobaciones" / f"{cid}-{h8}.json"
    if not t.exists():
        return False
    try:
        fresco = time.time() - json.loads(t.read_text())["ts"] <= VENTANA_TICKET_S
    except (ValueError, KeyError):
        fresco = False
    t.unlink()
    return fresco


def _aprobar(a, raiz, codigo, pol, tty):
    c = puerta._contrato_de_gobierno(raiz, a.id)
    if c is None:
        print(f"no encuentro {a.id}", file=sys.stderr)
        return 1
    if contrato.huella(c)[:8] != a.huella:
        print("la huella no casa: el contrato cambió después de enseñarlo", file=sys.stderr)
        return 1
    if not _persona_presente(raiz, a.id, a.huella, tty):
        print("aprobar exige una persona: el diálogo de permisos o su terminal", file=sys.stderr)
        return 3
    vigente, _ = puerta.activo(codigo, pol, None)
    if vigente and vigente["id"] != a.id:
        print(f"ya hay un contrato vigente ({vigente['id']}): suspéndelo o revócalo antes", file=sys.stderr)
        return 1
    por = a.por or pol.get("aprobadoras", ["?"])[0]
    pasos = {"borrador": ["candidato", "en_revision"], "cuestionado": ["candidato", "en_revision"],
             "candidato": ["en_revision"], "en_revision": []}.get(c["estado"])
    if pasos is None:
        print(f"no se puede aprobar desde el estado {c['estado']}", file=sys.stderr)
        return 1
    for nuevo in pasos + ["aprobado", "aprovisionado", "activo"]:
        c, err = contrato.transicion(c, nuevo, por if nuevo == "aprobado" else "yema" if nuevo in pasos else por,
                                     a.motivo, pol)
        if err:
            print(err, file=sys.stderr)
            return 1
    contrato.guardar(_ruta(raiz, a.id), c)
    borrador = raiz / "contratos/borradores" / f"{a.id}.json"
    if borrador.exists():
        borrador.unlink()
    (raiz / "contratos/ACTIVO").write_text(a.id)
    evidencia.anotar(raiz / "evidencia" / f"{a.id}.jsonl",
                     {"contrato": a.id, "transicion": "activo", "por": por, "huella": a.huella,
                      "via": "terminal" if tty else "dialogo"})
    print(contrato.resumen(c))
    print(f"{a.id}: aprobado y activo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
