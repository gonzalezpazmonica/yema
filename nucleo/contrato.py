"""Contratos de trabajo: esquema, huella, ciclo de vida y vigencia.

Un contrato no concede autoridad por existir: la recibe de una aprobadora
legítima, queda sellado por su huella y caduca.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

NIVELES = ("E0", "E1", "E2", "E3", "E4")
EFECTOS = {"leer", "escribir", "ejecutar", "red", "git-local", "git-remoto",
           "fusionar", "publicar", "delegar", "escribir-cupula"}
REQUERIDOS = ("id", "version", "estado", "proposito", "responsable", "ejecutora",
              "nivel", "ambito", "autoridad", "recursos", "evidencia")
TRANSICIONES = {
    "borrador": {"cuestionado", "candidato", "rechazado"},
    "cuestionado": {"borrador", "candidato", "rechazado"},
    "candidato": {"en_revision", "borrador", "rechazado"},
    "en_revision": {"aprobado", "borrador", "rechazado"},
    "aprobado": {"aprovisionado", "revocado", "caducado"},
    "aprovisionado": {"activo", "revocado", "caducado"},
    "activo": {"validando", "suspendido", "revocado", "caducado", "fallido"},
    "suspendido": {"activo", "revocado", "caducado"},
    "validando": {"cerrado", "activo", "fallido"},
}
TERMINALES = {"cerrado", "rechazado", "revocado", "caducado", "fallido"}
ESTADOS = set(TRANSICIONES) | TERMINALES


def cargar(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def guardar(ruta, c):
    Path(ruta).write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def huella(c):
    """sha256 del contenido material: excluye estado, aprobación e historial."""
    material = {k: v for k, v in c.items() if k not in ("estado", "historial")}
    material["autoridad"] = {k: v for k, v in c.get("autoridad", {}).items() if k != "aprobacion"}
    canon = json.dumps(material, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def _glob_seguro(g):
    return isinstance(g, str) and g and not g.startswith(("/", "~")) and ".." not in g.split("/")


def errores(c):
    e = [f"falta {k}" for k in REQUERIDOS if k not in c]
    if e:
        return e
    if c["nivel"] not in NIVELES:
        e.append(f"nivel desconocido {c['nivel']}")
    if c["estado"] not in ESTADOS:
        e.append(f"estado desconocido {c['estado']}")
    a, amb = c["autoridad"], c["ambito"]
    efectos, prohibidos = set(a.get("efectos", [])), set(a.get("prohibidos", []))
    for x in (efectos | prohibidos) - EFECTOS:
        e.append(f"efecto desconocido {x}")
    for x in efectos & prohibidos:
        e.append(f"efecto concedido y prohibido a la vez: {x}")
    if not str(amb.get("raiz", "")).startswith("/"):
        e.append("ambito.raiz debe ser absoluta")
    for g in amb.get("escritura", []) + amb.get("vetadas", []):
        if not _glob_seguro(g):
            e.append(f"glob inseguro {g!r}: relativo a la raíz, sin '..'")
    for g in amb.get("pruebas", []) + amb.get("pruebas_editables", []):
        if not _glob_seguro(g):
            e.append(f"glob inseguro {g!r} en pruebas")
    if c["ejecutora"] == c["responsable"]:
        e.append("la ejecutora no puede ser la responsable")
    posts = {p.get("id") for p in c.get("condiciones", {}).get("post", [])}
    for p in c.get("condiciones", {}).get("post", []):
        if not str(p.get("orden", "")).strip() and not str(p.get("comprobar", "")).strip():
            e.append(f"postcondición {p.get('id', '?')} sin comprobación: una orden, o en «comprobar» "
                     "cómo se reabre y verifica el entregable (escribirlo no prueba que sirva)")
    for r in c.get("requisitos", []):
        rid = r.get("id", "?")
        if not str(r.get("cita", "")).strip():
            e.append(f"requisito {rid} sin cita literal de la persona")
        for p in r.get("post", []):
            if p not in posts:
                e.append(f"requisito {rid} apunta a una postcondición inexistente: {p}")
    return e


def _fecha(s):
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def transicion(c, nuevo, quien, motivo, politica, ahora=None):
    """Devuelve (contrato_nuevo, None) o (c, error). No toca el original."""
    ahora = ahora or datetime.now(timezone.utc)
    if nuevo not in TRANSICIONES.get(c.get("estado"), set()):
        return c, f"transición ilegal {c.get('estado')} → {nuevo}"
    if nuevo in ("aprobado", "activo") and errores(c):
        return c, "contrato inválido: " + "; ".join(errores(c))
    n = json.loads(json.dumps(c))
    if nuevo == "aprobado":
        if quien == c["ejecutora"]:
            return c, "la ejecutora no puede aprobar su propio contrato"
        if quien not in politica.get("aprobadoras", []):
            return c, f"{quien} no tiene autoridad para aprobar"
        n["autoridad"]["aprobacion"] = {"por": quien, "fecha": ahora.isoformat(), "huella": huella(c)}
    n["estado"] = nuevo
    n.setdefault("historial", []).append(
        {"de": c["estado"], "a": nuevo, "por": quien, "motivo": motivo, "fecha": ahora.isoformat()})
    return n, None


def vigente(c, politica, ahora=None):
    """(True, '') si el contrato autoriza efectos ahora mismo."""
    ahora = ahora or datetime.now(timezone.utc)
    if errores(c):
        return False, "contrato inválido"
    if c["estado"] != "activo":
        return False, f"contrato no vigente: estado {c['estado']}"
    ap = c["autoridad"].get("aprobacion")
    if not ap:
        return False, "contrato no vigente: sin aprobación"
    if ap["por"] not in politica.get("aprobadoras", []) or ap["por"] == c["ejecutora"]:
        return False, "contrato no vigente: aprobadora sin autoridad"
    if ap["huella"] != huella(c):
        return False, "contrato no vigente: la huella no coincide con lo aprobado"
    cad = c["autoridad"].get("caduca")
    if not cad or _fecha(cad) <= ahora:
        return False, "contrato no vigente: caducado o sin caducidad"
    return True, ""


def resumen(c):
    """El contrato en lenguaje llano, para que una persona sepa qué aprueba."""
    a, amb, r = c.get("autoridad", {}), c.get("ambito", {}), c.get("recursos", {})
    lineas = [
        f"Contrato {c.get('id')} v{c.get('version')} · nivel {c.get('nivel')} · huella {huella(c)[:8]}",
        f"Para qué: {c.get('proposito')}",
        f"Dónde: {amb.get('raiz')}",
        f"Puede: {', '.join(a.get('efectos', [])) or 'nada'}",
        f"Puede escribir en: {', '.join(amb.get('escritura', [])) or 'ningún sitio'}",
        f"Órdenes: {'; '.join(a.get('ordenes', [])) or 'ninguna'}",
        f"No puede: {', '.join(a.get('prohibidos', [])) or '—'}"
        + (f" · nunca en: {', '.join(amb.get('vetadas', []))}" if amb.get("vetadas") else ""),
        f"Presupuesto: {r.get('efectos_max', 0)} efectos · Caduca: {a.get('caduca')}",
    ]
    post = [p.get("id", "") for p in c.get("condiciones", {}).get("post", [])]
    if post:
        lineas.append(f"Al cerrar demostrará: {', '.join(post)}")
    return "\n".join(lineas)


def checkpoint(c):
    """Documento de reanudación con forma fija: Requisitos (citas literales), Tareas, Log.

    Lo estable va arriba (aprovecha la caché del prompt); se edita por partes, nunca se reescribe."""
    a = c.get("autoridad", {})
    lineas = [
        f"# {c.get('id')} · {c.get('proposito')}",
        f"Contrato v{c.get('version')} · huella {huella(c)[:8]} · caduca {a.get('caduca')}",
        "",
        "## Requisitos",
    ]
    reqs = c.get("requisitos", [])
    lineas += [f"- {r['id']} «{r['cita']}» → {', '.join(r.get('post', [])) or 'sin postcondición'}" for r in reqs] or [
        "- (sin requisitos citados: pide a la persona sus palabras exactas)"]
    lineas += ["", "## Tareas", "- [ ] T1 (por definir; cada tarea enlaza un requisito y deja su evidencia)", "", "## Log"]
    if c.get("peticion"):
        lineas.append(f"- Petición original: «{c['peticion']}»")
    lineas.append(f"- Contrato {c.get('id')} v{c.get('version')} en estado {c.get('estado')}")
    return "\n".join(lineas) + "\n"
