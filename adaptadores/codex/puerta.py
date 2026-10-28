"""Traduce PreToolUse de Codex 0.163 a la puerta de Yema, sin cambiar el núcleo.

Solo se aceptan formatos documentados. Un parche toca un único fichero; borrar,
mover y las herramientas sin traducción se rechazan. JSON por stdin, rc 2 deniega.
"""
import json
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
    # Codex no implementa permissionDecision=ask en PreToolUse. Nunca producir
    # tickets de aprobación para una petición que no puede llegar a la persona.
    return {"tool_name": nombre, "tool_input": entrada, "cwd": cwd, "permission_mode": "dontAsk"}


def ejecutar(ev, raiz=None, ahora=None):
    from nucleo import puerta
    normal = traducir(ev)
    return puerta.evaluar_y_registrar(normal, raiz or RAIZ, ahora)


def main():
    try:
        raiz = Path(os.environ.get("YEMA_RAIZ") or RAIZ)
        ok, motivo, _ = ejecutar(json.load(sys.stdin), raiz)
        if not ok:
            raise Rechazo(motivo)
    except Exception as exc:
        # No volcar entradas ni excepciones con contenido privado al modelo.
        from nucleo.puerta import redactar
        print("YEMA Codex: bloqueo: " + redactar(str(exc)), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
