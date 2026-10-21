"""Puerta de efectos: decide si una herramienta puede actuar bajo el contrato activo.

Hook PreToolUse (formato Claude Code): JSON por stdin; exit 0 permite,
exit 2 bloquea con el motivo en stderr. Cualquier error bloquea.
Sin contrato vigente solo se permiten los efectos de `efectos_sin_contrato`.
"""
import fnmatch
import json
import os
import shlex
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nucleo import contrato, evidencia  # noqa: E402

INTERNAS = {"TodoWrite", "AskUserQuestion", "ToolSearch", "EnterPlanMode", "ExitPlanMode", "ListAgents", "Skill"}
LECTURA = {"Read", "Glob", "Grep", "LS", "NotebookRead"}
ESCRITURA = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
RED = {"WebFetch", "WebSearch"}
DELEGACION = {"Agent", "Task", "SendMessage"}
CUPULA_ESCRITURA = {"vault_write", "vault_rag_sync", "vault_index"}
METACARACTERES = set(";|&`$<>()\n\\")
PROTEGIDAS = ("nucleo", "gobierno", "contratos", "evidencia", ".claude")
IDENTIDAD = ("AGENTS.md", "CLAUDE.md", "ALMA.md")
GOBIERNO_LIBRE = {"estado", "validar", "resumen", "evidencia", "admitir", "suspender", "revocar", "cuidado", "copia",
                  "checkpoint"}
TRANSICIONES_LIBRES = {"borrador", "cuestionado", "candidato", "en_revision", "rechazado", "validando"}
MODOS_SIN_PREGUNTA = {"bypassPermissions", "dontAsk", "auto"}
# Lectores inertes: leen o listan, no escriben ni ejecutan otros programas. Sin ellos no hay E0 útil.
LECTORES = {"ls", "find", "cat", "head", "tail", "wc", "grep", "tree", "pwd", "stat", "file", "du", "realpath"}
FIND_PELIGROSO = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
GREP_RECURSIVO = ("-r", "-R", "--recursive", "--dereference-recursive", "-d", "--directories")


class _Preguntar:
    """Decisión «pregunta a la persona». Es falsa: quien no la entienda, deniega."""

    def __bool__(self):
        return False

    def __repr__(self):
        return "PREGUNTAR"


PREGUNTAR = _Preguntar()
EJECUTABLES_ESTADO = ("casa/*",)
PUSH_PELIGROSO = ("-f", "--force", "--force-with-lease", "--mirror", "--all", "--delete", "-d", "--prune")


def _politica(raiz):
    return json.loads((raiz / "gobierno/politica.json").read_text(encoding="utf-8"))


def estado_de(raiz, pol):
    """Estado privado (contratos reales, evidencia, memoria, buzón), fuera del repo.

    YEMA_ESTADO o `estado` en la política; sin ninguno, el propio repo (modo pruebas)."""
    e = os.environ.get("YEMA_ESTADO") or pol.get("estado")
    return Path(os.path.realpath(os.path.expanduser(e))) if e else Path(os.path.realpath(raiz))


def activo(raiz, pol, ahora):
    """(contrato vigente o None, motivo si hay uno declarado pero no vale)."""
    raiz = estado_de(raiz, pol)
    puntero = raiz / "contratos/ACTIVO"
    if not puntero.exists():
        return None, "sin contrato activo"
    cid = puntero.read_text(encoding="utf-8").strip()
    ruta = raiz / "contratos" / f"{cid}.json"
    if not cid or "/" in cid or not ruta.exists():
        return None, "contrato no vigente: ACTIVO apunta a un contrato inexistente"
    c = contrato.cargar(ruta)
    ok, motivo = contrato.vigente(c, pol, ahora)
    return (c, "") if ok else (None, motivo)


def _real(ruta, cwd):
    p = Path(os.path.expanduser(str(ruta)))
    return Path(os.path.realpath(p if p.is_absolute() else Path(cwd) / p))


def _dentro(p, base):
    return p == base or base in p.parents


def _coincide(rel, globs):
    return any(fnmatch.fnmatch(rel, g) for g in globs)


def _toca_protegida(p, raiz, estado, pol):
    if _dentro(p, estado):
        rel = str(p.relative_to(estado))
        return not _coincide(rel, list(EJECUTABLES_ESTADO) + pol.get("zonas_libres", []))
    return any(_dentro(p, raiz / d) for d in PROTEGIDAS) or p in [raiz / f for f in IDENTIDAD]


def _orden_casa(norm, patron):
    """Prefijo por tokens; cada token del patrón admite comodines (fnmatch)."""
    return len(norm) >= len(patron) and all(fnmatch.fnmatchcase(t, p) for t, p in zip(norm, patron))


def _vetada(real, pol):
    for g in pol.get("lectura_vetada", []):
        g = os.path.expanduser(g)
        if fnmatch.fnmatch(str(real), g) or ("/" not in g and fnmatch.fnmatch(real.name, g)):
            return True
    return False


def clasificar_orden(cmd):
    """(efecto, tokens normalizados, rutas -C) o (None, motivo, [])."""
    if any(ch in METACARACTERES for ch in cmd):
        return None, "orden compuesta, con redirección o sustitución: pártela en órdenes simples", []
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return None, "orden ilegible", []
    if not toks:
        return None, "orden vacía", []
    prog, rutas, norm = os.path.basename(toks[0]), [], [os.path.basename(toks[0])]
    if prog == "git":
        i = 1
        while i < len(toks) and toks[i].startswith("-"):
            if toks[i] in ("-C", "-c") and i + 1 < len(toks):
                if toks[i] == "-C":
                    rutas.append(toks[i + 1])
                else:
                    return None, "git -c cambia la configuración: no permitido", []
                i += 2
            else:
                i += 1
        resto = toks[i:]
        norm += resto
        sub = resto[0] if resto else ""
        if sub == "push":
            if any(t.startswith(PUSH_PELIGROSO) or t.startswith("+") or t.startswith(":") for t in resto[1:]):
                return None, "push forzado, borrado o masivo: nunca", []
            return "git-remoto", norm, rutas
        if sub in ("fetch", "pull", "clone", "ls-remote"):
            return "red", norm, rutas
        if sub == "merge":
            return "fusionar", norm, rutas
        return "git-local", norm, rutas
    norm += toks[1:]
    if prog == "gh":
        if "merge" in toks:
            return "fusionar", norm, rutas
        if toks[1:3] in (["pr", "create"], ["repo", "create"]) or "release" in toks[1:2]:
            return "publicar", norm, rutas
        return "red", norm, rutas
    if prog in ("curl", "wget", "ssh", "scp", "rsync", "nc", "npm", "pip", "pip3", "cargo"):
        return "red", norm, rutas
    return "ejecutar", norm, rutas


def orden_de_gobierno(cmd, raiz, cwd):
    """Argumentos de la CLI de Yema si `cmd` la invoca de verdad; si no, None."""
    if any(ch in METACARACTERES for ch in cmd):
        return None
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return None
    cli, envoltorio = raiz / "nucleo/yema.py", raiz / "bin/yema"
    if len(toks) > 1 and os.path.basename(toks[0]) in ("python3", "python") and _real(toks[1], cwd) == cli:
        return toks[2:]
    if toks and "/" in toks[0] and _real(toks[0], cwd) == envoltorio:
        return toks[1:]
    if toks and toks[0] == "yema":
        en_path = shutil.which("yema")
        if en_path and Path(os.path.realpath(en_path)) == envoltorio:
            return toks[1:]
    return None


def lector_inerte(cmd, cwd, pol):
    """True si la orden solo lee o lista y no toca nada vetado por la política."""
    if any(ch in METACARACTERES for ch in cmd):
        return False
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return False
    if not toks or "/" in toks[0] or toks[0] not in LECTORES:
        return False
    args = toks[1:]
    if toks[0] == "find" and any(a in FIND_PELIGROSO for a in args):
        return False
    if toks[0] == "grep" and any(a in GREP_RECURSIVO or (a.startswith("-") and not a.startswith("--") and "r" in a.lower())
                                 for a in args):
        return False
    return not any(_vetada(_real(a, cwd), pol) for a in args if not a.startswith("-"))


def _contrato_de_gobierno(estado, cid):
    if not cid or "/" in cid:
        return None
    for ruta in (estado / "contratos" / f"{cid}.json", estado / "contratos/borradores" / f"{cid}.json"):
        if ruta.exists():
            return contrato.cargar(ruta)
    return None


def decidir_gobierno(args, ev, estado):
    sub = args[0] if args else ""
    if sub in GOBIERNO_LIBRE:
        return True, "", "gobierno"
    if sub == "transicion" and len(args) > 2 and args[2] in TRANSICIONES_LIBRES:
        return True, "", "gobierno"
    if sub == "aprobar" and len(args) >= 3:
        if ev.get("permission_mode") in MODOS_SIN_PREGUNTA:
            return False, (f"aprobar exige que la persona conteste un diálogo; el modo "
                           f"{ev.get('permission_mode')} no pregunta. Cambia a modo normal."), "gobierno"
        c = _contrato_de_gobierno(estado, args[1])
        if c is None:
            return False, f"no encuentro el contrato {args[1]}", "gobierno"
        if contrato.huella(c)[:8] != args[2]:
            return False, "la huella no casa con el contrato: alguien lo cambió después de enseñártelo", "gobierno"
        return PREGUNTAR, "Yema pide aprobar y activar este contrato:\n" + contrato.resumen(c), "gobierno"
    return False, "esa orden de gobierno es de la persona (aprobar con diálogo o en su terminal)", "gobierno"


def efecto_de(herramienta, entrada):
    if herramienta in INTERNAS:
        return "interno"
    if herramienta in LECTURA:
        return "leer"
    if herramienta in ESCRITURA:
        return "escribir"
    if herramienta in RED:
        return "red"
    if herramienta in DELEGACION:
        return "delegar"
    if herramienta == "Bash":
        return "bash"
    if herramienta.startswith("mcp__savia-vaults__"):
        return "escribir-cupula" if herramienta.split("__")[-1] in CUPULA_ESCRITURA else "leer"
    return None


def _ruta_de(entrada):
    return entrada.get("file_path") or entrada.get("notebook_path") or entrada.get("path")


QUE_HACER = (
    ("contrato no vigente", "propón un contrato (skill contrato) o pide a la persona que reanude el que hay."),
    ("sin contrato", "si ya tienes el contenido, guárdalo en tu memoria (~/.yema/memoria/, zona libre) para no perderlo; después propón un contrato (skill contrato) y pide su aprobación."),
    ("zona protegida", "eso solo lo cambia una persona; si hace falta, díselo con el porqué."),
    ("lectura vetada", "no lo leas; si de verdad lo necesitas, pide a la persona solo el dato."),
    ("orden compuesta", "pártela en órdenes simples, una por llamada."),
    ("push forzado", "no se hace nunca; si el remoto está mal, cuéntaselo a la persona."),
    ("git -c", "no se hace nunca; usa la configuración que ya tiene el repo."),
    ("orden ilegible", "revisa las comillas y vuelve a escribirla."),
    ("orden no listada", "usa una orden listada en el contrato o propón una enmienda que la añada."),
    ("efecto prohibido", "no se hace en este contrato; si es imprescindible, plantéalo a la persona como decisión aparte."),
    ("efecto no concedido", "propón una enmienda que conceda ese efecto, explicando por qué hace falta."),
    ("test preexistente", "si el código está mal, arregla el código; si el test está mal, propón una enmienda que lo liste en ambito.pruebas_editables."),
    ("fuera del ámbito", "trabaja dentro del ámbito o propón una enmienda que lo amplíe."),
    ("ruta no concedida", "trabaja en las rutas concedidas o propón una enmienda que añada esa."),
    ("cúpula", "indica una cúpula permitida en «dome» o pide que el contrato la nombre."),
    ("herramienta desconocida", "usa otra herramienta: esta no está clasificada en la puerta."),
    ("presupuesto", "cierra lo que tengas, deja checkpoint y propón una enmienda con más presupuesto."),
    ("orden de gobierno", "enseña el resumen del contrato a la persona y lanza «yema aprobar <id> <huella>»."),
    ("huella", "vuelve a enseñar el contrato (yema resumen) y pide la aprobación con la huella nueva."),
    ("modo", "pide a la persona que cambie a modo normal o que apruebe en su terminal."),
    ("Yema no ejecuta", "eso es de la persona; si hace falta, díselo."),
)


def con_que_hacer(motivo):
    if "Qué hacer:" in motivo:
        return motivo
    for clave, consejo in QUE_HACER:
        if clave in motivo:
            return f"{motivo}. Qué hacer: {consejo}"
    return f"{motivo}. Qué hacer: detente y cuéntaselo a la persona."


def decidir(ev, raiz, ahora=None):
    """(permitido, motivo, efecto); cada rechazo dice qué hacer."""
    ok, motivo, efecto = _decidir(ev, raiz, ahora)
    if ok is False:
        motivo = con_que_hacer(motivo)
    return ok, motivo, efecto


def _decidir(ev, raiz, ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    raiz = Path(os.path.realpath(raiz))
    pol = _politica(raiz)
    estado = estado_de(raiz, pol)
    herr, entrada = ev.get("tool_name", ""), ev.get("tool_input") or {}
    cwd = ev.get("cwd") or os.getcwd()
    efecto = efecto_de(herr, entrada)
    if efecto is None:
        return False, f"herramienta desconocida: {herr}", None
    if efecto == "interno":
        return True, "", efecto
    if efecto == "bash":
        args = orden_de_gobierno(entrada.get("command", ""), raiz, cwd)
        if args is not None:
            return decidir_gobierno(args, ev, estado)
        if lector_inerte(entrada.get("command", ""), cwd, pol):
            return True, "", "leer"
        if any(ch in METACARACTERES for ch in entrada.get("command", "")):
            return False, "orden compuesta, con redirección o sustitución: pártela en órdenes simples", "bash"
    c, motivo_c = activo(raiz, pol, ahora)
    ruta = _ruta_de(entrada)
    real = _real(ruta, cwd) if ruta else None

    if efecto == "leer" and herr.startswith("mcp__"):
        # Sin cúpula explícita el servidor asume N2: Yema razona en la nube y no la lee.
        permitidas = set(pol.get("cupulas_lectura", [])) | set((c or {}).get("contexto", {}).get("cupulas", []))
        if entrada.get("dome") not in permitidas:
            return False, f"cúpula no permitida o sin indicar: {entrada.get('dome')!r}", efecto
        return True, "", efecto
    if efecto == "leer":
        if real and _vetada(real, pol):
            return False, f"lectura vetada por la política: {real}", efecto
        return True, "", efecto

    if efecto == "escribir":
        if real is None:
            return False, "escritura sin ruta", efecto
        if _dentro(real, estado):
            rel = str(real.relative_to(estado))
            if _coincide(rel, pol.get("zonas_libres", [])):
                return True, "", efecto
            return False, f"zona protegida de Yema: {rel} (solo la cambia una persona)", efecto
        if _toca_protegida(real, raiz, estado, pol):
            return False, f"zona protegida de Yema: {real.relative_to(raiz)} (solo la cambia una persona)", efecto

    if c is None:
        if efecto in pol.get("efectos_sin_contrato", []) and efecto != "bash":
            return True, "", efecto
        return False, f"{motivo_c}; sin contrato solo: {pol.get('efectos_sin_contrato', [])}", efecto

    a, amb = c["autoridad"], c["ambito"]
    base = Path(os.path.realpath(amb["raiz"]))
    if efecto == "bash":
        efecto, norm, rutas = clasificar_orden(entrada.get("command", ""))
        if efecto is None:
            return False, norm, "bash"
        if any(_toca_protegida(_real(t, cwd), raiz, estado, pol) for t in norm[1:] if "/" in t or t.endswith(".py")):
            return False, "Yema no ejecuta su propio núcleo ni toca su gobierno desde una orden", efecto
        for r in rutas + [cwd]:
            if not _dentro(_real(r, cwd), base):
                return False, f"orden fuera del ámbito del contrato: {r}", efecto
        if not any(_orden_casa(norm, o.split()) for o in a.get("ordenes", [])):
            return False, f"orden no listada en el contrato: {' '.join(norm[:3])}", efecto
    if efecto in a.get("prohibidos", []):
        return False, f"efecto prohibido por el contrato: {efecto}", efecto
    if efecto not in a.get("efectos", []):
        return False, f"efecto no concedido por el contrato: {efecto}", efecto
    if efecto == "escribir":
        if not _dentro(real, base):
            return False, f"escritura fuera del ámbito: {real}", efecto
        rel = str(real.relative_to(base))
        if _coincide(rel, amb.get("vetadas", [])) or not _coincide(rel, amb.get("escritura", [])):
            return False, f"ruta no concedida por el contrato: {rel}", efecto
        if real.exists() and _coincide(rel, amb.get("pruebas", [])) and not _coincide(rel, amb.get("pruebas_editables", [])):
            return False, f"test preexistente: {rel} no se cambia para que algo pase", efecto
    return True, "", efecto


def efectos_usados(registro):
    return sum(1 for x in evidencia.leer(registro)
               if x.get("permitido") is True and x.get("efecto") not in ("leer", "interno", "gobierno"))


def evaluar_y_registrar(ev, raiz, ahora=None):
    """decidir + presupuesto de efectos + recibo en el registro de evidencia."""
    ahora = ahora or datetime.now(timezone.utc)
    raiz = Path(os.path.realpath(raiz))
    ok, motivo, efecto = decidir(ev, raiz, ahora)
    c, _ = activo(raiz, _politica(raiz), ahora)
    cid = c["id"] if c else "sin-contrato"
    registro = estado_de(raiz, _politica(raiz)) / "evidencia" / f"{cid}.jsonl"
    material = efecto not in ("leer", "interno")
    if ok is PREGUNTAR:
        args = orden_de_gobierno(ev.get("tool_input", {}).get("command", ""), raiz, ev.get("cwd") or os.getcwd())
        tickets = estado_de(raiz, _politica(raiz)) / "aprobaciones"
        tickets.mkdir(parents=True, exist_ok=True)
        (tickets / f"{args[1]}-{args[2]}.json").write_text(json.dumps({"ts": time.time()}))
    elif ok and material and c and efecto != "gobierno":
        usados = efectos_usados(registro)
        if usados >= c["recursos"].get("efectos_max", 0):
            ok, motivo = False, con_que_hacer(f"presupuesto de efectos agotado ({usados})")
    if material or not ok:
        evidencia.anotar(registro, {"contrato": cid, "version": c["version"] if c else None,
                                    "herramienta": ev.get("tool_name"), "efecto": efecto,
                                    "permitido": "preguntado" if ok is PREGUNTAR else ok,
                                    "motivo": motivo.splitlines()[0] if motivo else ""})
    return ok, motivo, efecto


def main():
    raiz = Path(os.environ.get("YEMA_RAIZ") or Path(__file__).resolve().parent.parent)
    try:
        ev = json.loads(sys.stdin.read())
        ok, motivo, efecto = evaluar_y_registrar(ev, raiz)
    except Exception as e:  # falla cerrado
        print(f"YEMA: puerta en error, bloqueo: {e}", file=sys.stderr)
        return 2
    if ok is PREGUNTAR:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": motivo}}, ensure_ascii=False))
        return 0
    if ok and efecto not in ("leer", "interno"):
        # El contrato es el permiso: lo concedido no se vuelve a preguntar paso a paso.
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                                 "permissionDecisionReason": f"Yema: {efecto} concedido"}},
                         ensure_ascii=False))
        return 0
    if not ok:
        print(f"YEMA: {motivo}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
