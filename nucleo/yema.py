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
    yema prueba <carpeta> [--parche f.diff] -- <orden>
                                          ejecuta en una copia aislada (sin red, sin hogar)
    yema savia <palabras…>                busca en el mapa de capacidades de Savia (.scm/INDEX.scm)
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
from nucleo import aislado, buzon, contrato, cuidado, evidencia, firma, puerta  # noqa: E402

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
    sv = s.add_parser("savia")
    sv.add_argument("palabras", nargs="+")
    sv.add_argument("--max", type=int, default=12)
    s.add_parser("checkpoint").add_argument("id")
    pr = s.add_parser("prueba")
    pr.add_argument("carpeta")
    pr.add_argument("--parche")
    pr.add_argument("--tiempo", type=int, default=120)
    pr.add_argument("orden_prueba", nargs="*")
    ins = s.add_parser("instalar")
    ins.add_argument("--bin", default=os.path.expanduser("~/.local/bin"))
    s.add_parser("copia")
    apr = s.add_parser("aprende")
    for k in ("--cuando", "--leccion", "--evidencia", "--confianza"):
        apr.add_argument(k, required=True)
    apr.add_argument("--para", default="savia")
    ap = s.add_parser("aprobar")
    ap.add_argument("id"), ap.add_argument("huella")
    ap.add_argument("--por", default=None)
    ap.add_argument("--motivo", default="aprobado por la persona")
    argv = list(sys.argv[1:] if argv is None else argv)
    resto = []
    if argv[:1] == ["prueba"] and "--" in argv:
        corte = argv.index("--")
        argv, resto = argv[:corte], argv[corte + 1:]
    a = p.parse_args(argv)
    if a.orden == "prueba":
        a.orden_prueba = list(a.orden_prueba) + resto
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
    if a.orden == "prueba":
        return _prueba(a, raiz, codigo, pol)
    if a.orden == "aprende":
        m = buzon.leccion("yema", a.para, a.cuando, a.leccion, a.evidencia, a.confianza)
        ruta, e = buzon.dejar(m, raiz / "buzon/salida")
        if e:
            print("\n".join(e), file=sys.stderr)
            return 1
        print(f"aprendizaje en {ruta}")
        return 0
    if a.orden == "instalar":
        return _instalar(codigo, raiz, Path(a.bin))
    if a.orden == "savia":
        return _savia(a, pol)
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
        visible, detalle = situacion(codigo)
        print(f"{visible}: {detalle}")
        print(f"estado privado: {raiz}")
        return 0
    if a.orden == "checkpoint":
        c = puerta._contrato_de_gobierno(raiz, a.id)
        if c is None:
            print(f"no encuentro {a.id}", file=sys.stderr)
            return 1
        f = raiz / "memoria" / f"{a.id}.md"
        if not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(contrato.checkpoint(c), encoding="utf-8")
        print(f)
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
    if nuevo == "aprobado" and pol.get("firma_aprobacion"):
        c["autoridad"]["aprobacion"]["politica"] = puerta.huella_politica(pol)
        c["autoridad"]["aprobacion"]["firma"] = firma.firmar(c, firma.clave(raiz, crear=True))
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


def _prueba(a, raiz, codigo, pol):
    orden = list(a.orden_prueba)
    if orden[:1] == ["--"]:
        orden = orden[1:]
    vetado = lambda p: puerta._vetada(Path(os.path.realpath(p)), pol)  # noqa: E731
    try:
        r = aislado.ejecutar(a.carpeta, orden, base=raiz / "aislado", parche=a.parche, timeout=a.tiempo,
                             vetado=vetado)
    except aislado.Rechazo as e:
        print(f"no ejecuto: {e}", file=sys.stderr)
        return 3
    print(r["salida"])
    print(f"rc={r['rc']} en {r['segundos']} s · copia aislada sin red ni hogar; el original no ha cambiado")
    return r["rc"]


def _savia(a, pol):
    """Busca capacidades de Savia en su índice perezoso y devuelve rutas absolutas para usarlas con el relevo."""
    savia = Path(os.path.expanduser(pol.get("savia", "~/savia")))
    indice = savia / ".scm/INDEX.scm"
    if not indice.exists():
        print(f"no encuentro el índice de Savia en {indice} (define «savia» en la política)", file=sys.stderr)
        return 2
    palabras = [p.lower() for p in a.palabras]
    resultados = []
    for linea in indice.read_text(encoding="utf-8").splitlines():
        if not linea.startswith("["):
            continue
        puntos = sum(linea.lower().count(p) for p in palabras)
        if puntos:
            resultados.append((puntos, linea))
    if not resultados:
        print("sin resultados")
        return 1
    for _, linea in sorted(resultados, key=lambda x: -x[0])[:a.max]:
        tipo, _, ruta = linea.rpartition(" — ")[2].partition(":")
        print(f"{linea.split(' — ')[0]} · {tipo}: {savia / ruta}")
    return 0


def _instalar(codigo, estado, bindir):
    """Prepara el estado privado, los ajustes locales del arnés y la CLI en el PATH."""
    for d in ("contratos/borradores", "evidencia", "memoria", "buzon/entrada", "buzon/salida", "casa", "aprobaciones"):
        (estado / d).mkdir(parents=True, exist_ok=True)
    os.chmod(estado, 0o700)
    privados = estado / "terminos-privados.txt"
    if not privados.exists():
        privados.write_text("# Un término por línea: nombres de proyectos, clientes o personas que nunca deben salir en una búsqueda web.\n")
        os.chmod(privados, 0o600)
    local = codigo / ".claude/settings.local.json"
    ajustes = json.loads(local.read_text()) if local.exists() else {}
    dirs = ajustes.setdefault("permissions", {}).setdefault("additionalDirectories", [])
    if str(estado) not in dirs:
        dirs.append(str(estado))
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps(ajustes, ensure_ascii=False, indent=2) + "\n")
    bindir.mkdir(parents=True, exist_ok=True)
    enlace = bindir / "yema"
    if not enlace.exists() and not enlace.is_symlink():
        enlace.symlink_to(codigo / "bin/yema")
    print(f"estado privado: {estado}\najustes locales: {local}\nCLI: {enlace}")
    if str(bindir) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"aviso: {bindir} no está en tu PATH")
    return 0


def situacion(codigo, ahora=None):
    """Estado visible para la persona: Trabajando, Comprobando, Lista o Necesita tu decisión."""
    codigo = Path(codigo)
    pol = json.loads((codigo / "gobierno/politica.json").read_text(encoding="utf-8"))
    raiz = puerta.estado_de(codigo, pol)
    punt = raiz / "contratos/ACTIVO"
    if punt.exists():
        cid = punt.read_text().strip()
        ruta = raiz / "contratos" / f"{cid}.json"
        if not ruta.exists():
            return "Necesita tu decisión", f"ACTIVO apunta a {cid}, que no existe"
        c = contrato.cargar(ruta)
        if c["estado"] == "validando":
            return "Comprobando", f"{cid}: ejecutando las postcondiciones"
        vigente, motivo = puerta.activo(codigo, pol, ahora)  # lo mismo que aplica la puerta: firma, política…
        if vigente is None:
            return "Necesita tu decisión", f"{cid}: {motivo}"
        usados = puerta.efectos_usados(raiz / "evidencia" / f"{cid}.jsonl")
        if usados >= c["recursos"].get("efectos_max", 0):
            return "Necesita tu decisión", f"{cid}: presupuesto agotado ({usados} efectos); hace falta una enmienda"
        return "Trabajando", f"{cid}: {c['proposito']} ({usados}/{c['recursos'].get('efectos_max', 0)} efectos)"
    borradores = sorted(p.stem for p in (raiz / "contratos/borradores").glob("*.json"))
    if borradores:
        return "Necesita tu decisión", f"borradores pendientes de aprobar: {', '.join(borradores)}"
    return "Lista", "sin encargo en curso"


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
    if pol.get("firma_aprobacion"):
        c["autoridad"]["aprobacion"]["politica"] = puerta.huella_politica(pol)
        c["autoridad"]["aprobacion"]["firma"] = firma.firmar(c, firma.clave(raiz, crear=True))
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
