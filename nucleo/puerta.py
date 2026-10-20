"""Puerta de efectos: decide si una herramienta puede actuar bajo el contrato activo.

Hook PreToolUse (formato Claude Code): JSON por stdin; exit 0 permite,
exit 2 bloquea con el motivo en stderr. Cualquier error bloquea.
Sin contrato vigente solo se permiten los efectos de `efectos_sin_contrato`.
"""
import fnmatch
import json
import os
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nucleo import contrato, evidencia  # noqa: E402

INTERNAS = {"TodoWrite", "AskUserQuestion", "ToolSearch", "EnterPlanMode", "ExitPlanMode", "ListAgents"}
LECTURA = {"Read", "Glob", "Grep", "LS", "NotebookRead"}
ESCRITURA = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
RED = {"WebFetch", "WebSearch"}
DELEGACION = {"Agent", "Task", "SendMessage"}
CUPULA_ESCRITURA = {"vault_write", "vault_rag_sync", "vault_index"}
METACARACTERES = set(";|&`$<>()\n\\")
PROTEGIDAS = ("nucleo", "gobierno", "contratos", "evidencia", ".claude")
IDENTIDAD = ("AGENTS.md", "CLAUDE.md", "ALMA.md")
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


def decidir(ev, raiz, ahora=None):
    """(permitido, motivo, efecto). Pura salvo lecturas de disco."""
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
    return True, "", efecto


def evaluar_y_registrar(ev, raiz, ahora=None):
    """decidir + presupuesto de efectos + recibo en el registro de evidencia."""
    ahora = ahora or datetime.now(timezone.utc)
    raiz = Path(os.path.realpath(raiz))
    ok, motivo, efecto = decidir(ev, raiz, ahora)
    c, _ = activo(raiz, _politica(raiz), ahora)
    cid = c["id"] if c else "sin-contrato"
    registro = estado_de(raiz, _politica(raiz)) / "evidencia" / f"{cid}.jsonl"
    material = efecto not in ("leer", "interno")
    if ok and material and c:
        usados = sum(1 for x in evidencia.leer(registro) if x.get("permitido") and x.get("efecto") not in ("leer", "interno"))
        if usados >= c["recursos"].get("efectos_max", 0):
            ok, motivo = False, f"presupuesto de efectos agotado ({usados})"
    if material or not ok:
        evidencia.anotar(registro, {"contrato": cid, "version": c["version"] if c else None,
                                    "herramienta": ev.get("tool_name"), "efecto": efecto,
                                    "permitido": ok, "motivo": motivo})
    return ok, motivo, efecto


def main():
    raiz = Path(os.environ.get("YEMA_RAIZ") or Path(__file__).resolve().parent.parent)
    try:
        ev = json.loads(sys.stdin.read())
        ok, motivo, _ = evaluar_y_registrar(ev, raiz)
    except Exception as e:  # falla cerrado
        print(f"YEMA: puerta en error, bloqueo: {e}", file=sys.stderr)
        return 2
    if not ok:
        print(f"YEMA: {motivo}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
