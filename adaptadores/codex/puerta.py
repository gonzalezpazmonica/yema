"""Traduce PreToolUse de Codex 0.163 a la puerta de Yema, sin cambiar el núcleo.

Solo se aceptan formatos documentados. Un parche toca un único fichero; borrar,
mover y las herramientas sin traducción se rechazan. JSON por stdin, rc 2 deniega.
"""
import json
import shlex
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
CUPULAS = {"vault_read", "vault_search", "vault_domes", "vault_health", "vault_rag_status",
           "vault_write", "vault_rag_sync", "vault_index"}


class Rechazo(ValueError):
    pass


def parche(orden):
    """Devuelve (herramienta, ruta) para un Add/Update de un solo fichero."""
    if not isinstance(orden, str) or "\x00" in orden:
        raise Rechazo("parche ilegible")
    lineas = orden.splitlines()
    if len(lineas) < 4 or lineas[0] != "*** Begin Patch" or lineas[-1] != "*** End Patch":
        raise Rechazo("se exige un parche completo")
    for prefijo, herramienta in (("*** Add File: ", "Write"), ("*** Update File: ", "Edit")):
        if lineas[1].startswith(prefijo):
            ruta = lineas[1][len(prefijo):]
            break
    else:
        raise Rechazo("solo Add File y Update File; borrar y mover no están soportados")
    if not ruta or ruta != ruta.strip():
        raise Rechazo("ruta de parche vacía o ambigua")
    for linea in lineas[2:-1]:
        if herramienta == "Write" and linea.startswith("+"):
            continue
        if herramienta == "Edit" and (linea.startswith(("+", "-", " ", "@@")) or linea == "*** End of File"):
            continue
        raise Rechazo("parche no soportado: un solo fichero, sin borrar ni mover")
    return herramienta, ruta


def traducir(ev):
    if not isinstance(ev, dict) or ev.get("hook_event_name") != "PreToolUse":
        raise Rechazo("se exige un evento PreToolUse por stdin")
    nombre, entrada, cwd = ev.get("tool_name"), ev.get("tool_input"), ev.get("cwd")
    if not isinstance(nombre, str) or not isinstance(entrada, dict):
        raise Rechazo("tool_name y tool_input no válidos")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        raise Rechazo("falta cwd absoluto")
    entrada = dict(entrada)
    if nombre == "Bash":
        if not isinstance(entrada.get("command"), str) or not entrada["command"].strip():
            raise Rechazo("falta command")
        # Los hooks actuales normalizan exec_command como Bash. Si incluyen un
        # workdir, hay que juzgar esa carpeta y no el cwd de la sesión.
        trabajo = entrada.get("workdir", entrada.get("cwd"))
        if "workdir" in entrada and "cwd" in entrada and entrada["workdir"] != entrada["cwd"]:
            raise Rechazo("directorios de herramienta contradictorios")
        if trabajo is not None:
            if not isinstance(trabajo, str) or not Path(trabajo).is_absolute():
                raise Rechazo("directorio de herramienta no absoluto")
            cwd = trabajo
        if entrada.get("tty") or entrada.get("sandbox_permissions", "use_default") != "use_default":
            raise Rechazo("no se admiten TTY ni escaladas de sandbox")
        if entrada.get("additional_permissions"):
            raise Rechazo("no se admiten permisos adicionales")
        if entrada.get("shell") is not None:
            raise Rechazo("no se admiten intérpretes alternativos")
    elif nombre == "apply_patch":
        nombre, ruta = parche(entrada.get("command"))
        entrada = {"file_path": ruta}
        destino = Path(os.path.realpath(Path(cwd) / ruta))
        # El adaptador también es gobierno, aunque el núcleo no conozca Codex.
        for protegida in (RAIZ / ".codex", RAIZ / "adaptadores/codex", RAIZ / "bin/yema-sesion-codex"):
            if destino == protegida or protegida in destino.parents:
                raise Rechazo("configuración del adaptador protegida")
    elif nombre.startswith(("mcp__savia-vaults__", "mcp__savia_vaults__")):
        prefijo = "mcp__savia-vaults__" if nombre.startswith("mcp__savia-vaults__") else "mcp__savia_vaults__"
        operacion = nombre[len(prefijo):]
        if operacion not in CUPULAS:
            raise Rechazo("herramienta de cúpulas sin clasificación conocida")
        # 0.163 normaliza el guion del servidor al entregar el evento real.
        # Solo este alias exacto: el núcleo conserva cúpula, nivel y efecto.
        nombre = "mcp__savia-vaults__" + operacion
    elif nombre == "update_plan":
        nombre = "TodoWrite"
    else:
        raise Rechazo("herramienta Codex sin traducción: " + nombre)
    # No crear tickets consumibles por la CLI sin presencia humana. La solicitud
    # fuera de banda se registra por separado, sin llamar al evaluador con ask.
    return {"tool_name": nombre, "tool_input": entrada, "cwd": cwd, "permission_mode": "dontAsk"}


def ejecutar(ev, raiz=None, ahora=None):
    from nucleo import puerta
    normal = traducir(ev)
    raiz = Path(raiz or RAIZ)
    if normal["tool_name"] == "Bash":
        args = puerta.orden_de_gobierno(normal["tool_input"]["command"], raiz, normal["cwd"])
        if args and args[0] == "aprobar":
            return solicitar_aprobacion(normal, raiz, ahora)
    return puerta.evaluar_y_registrar(normal, raiz, ahora)


def solicitar_aprobacion(normal, raiz, ahora=None):
    """Deny con solicitud encadenada; jamás crea el token de diálogo del núcleo.

    La persona usa la CLI existente desde su terminal. La CLI vuelve a comprobar
    la huella, firma la aprobación y encadena la activación. El siguiente efecto
    vuelve a pasar por evaluar_y_registrar; este ticket no concede autoridad.
    """
    from nucleo import contrato, evidencia, puerta
    consulta = {**normal, "permission_mode": "default"}
    ok, motivo, efecto = puerta.decidir(consulta, raiz, ahora)
    # Registrar también el rechazo real en modo dontAsk, sin producir PREGUNTAR.
    puerta.evaluar_y_registrar(normal, raiz, ahora)
    if ok is not puerta.PREGUNTAR:
        return False, motivo, efecto
    args = puerta.orden_de_gobierno(normal["tool_input"]["command"], raiz, normal["cwd"])
    pol = puerta._politica(raiz)
    estado = puerta.estado_de(raiz, pol)
    c = puerta._contrato_de_gobierno(estado, args[1], args[2])
    if not c or c.get("id") != args[1]:
        raise Rechazo("el id del contrato no casa con la solicitud")
    huella = contrato.huella(c)
    ticket = "codex-" + huella
    evidencia.anotar(estado / "evidencia" / f"{c['id']}.jsonl", {
        "contrato": c["id"], "version": c["version"], "herramienta": "Bash", "efecto": "gobierno",
        "permitido": False, "evento": "solicitud-aprobacion-codex", "ticket": ticket,
        "huella": huella, "politica": puerta.huella_politica(pol), "via": "codex-fuera-de-banda"})
    orden = shlex.join([str(raiz / "bin/yema"), "aprobar", c["id"], huella[:8]])
    return False, (f"ticket Codex {ticket}: pendiente de la persona.\n{motivo}\n"
                   f"La persona debe ejecutar en su terminal: {orden}\n"
                   "Después puede reintentar el efecto contratado; el ticket no es un permiso."), "gobierno"


def veredicto(permitido, motivo=""):
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
        "permissionDecision": "allow" if permitido else "deny", "permissionDecisionReason": motivo}},
        ensure_ascii=False)


def main():
    try:
        raiz = Path(os.environ.get("YEMA_RAIZ") or RAIZ)
        ok, motivo, _ = ejecutar(json.load(sys.stdin), raiz)
        if not ok:
            raise Rechazo(motivo)
    except Exception as exc:
        # No volcar entradas ni excepciones con contenido privado al modelo.
        from nucleo.puerta import redactar
        motivo = "YEMA Codex: bloqueo: " + redactar(str(exc))
        print(veredicto(False, motivo))
        print(motivo, file=sys.stderr)
        return 2
    print(veredicto(True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
