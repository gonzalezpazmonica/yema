"""Lanzador headless, sin modificar la configuración personal de Codex.

El propio CLI necesita estado escribible bajo CODEX_HOME (por defecto ~/.codex).
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def toml_valor(valor):
    if isinstance(valor, dict):
        return "{" + ", ".join(json.dumps(k) + " = " + toml_valor(v) for k, v in valor.items()) + "}"
    if isinstance(valor, list):
        return "[" + ", ".join(toml_valor(v) for v in valor) + "]"
    return json.dumps(valor, ensure_ascii=False)


def opciones(ajustes, prefijo=""):
    resultado = []
    for clave, valor in ajustes.items():
        nombre = prefijo + clave
        if isinstance(valor, dict) and valor:
            resultado += opciones(valor, nombre + ".")
        else:
            resultado += ["-c", nombre + "=" + toml_valor(valor)]
    return resultado


def comprobar_fuentes(raiz, codex_home):
    # --ignore-user-config no promete ignorar hooks.json ni las capas de proyecto.
    # No ejecutar hooks ajenos usando el bypass de confianza de nuestra automatización.
    # project_root_markers=[] fija la raíz de descubrimiento en el cwd lanzado.
    # Un CODEX_HOME temporal no convierte ~/.codex en una capa del proyecto.
    fuentes = [codex_home / "hooks.json", raiz / ".codex/hooks.json"]
    config = raiz / ".codex/config.toml"
    if config != codex_home / "config.toml":
        fuentes.append(config)
    if any(f.exists() for f in fuentes):
        raise ValueError("hay otra capa .codex con hooks o configuración; revisarla antes de usar este lanzador")


def construir(args, raiz=RAIZ):
    ajustes = tomllib.loads((raiz / "adaptadores/codex/config.toml").read_text())
    if args.experimental_workspace_write:
        raise ValueError("G13 y G14 sin equivalente: workspace-write no se inicia sin una frontera externa por efecto")
    # Un objeto vacío necesita override explícito; opciones() no lo recorría.
    traductor = shlex.join([sys.executable, str(raiz / "adaptadores/codex/vigilante.py")])
    # Si Python no existe o el proceso muere, la shell también debe devolver 2.
    manejador = {"type": "command", "command": traductor + " || exit 2", "timeout": 30}
    ajustes["hooks"] = {"PreToolUse": [{"matcher": "*", "hooks": [manejador]}]}
    inicio = shlex.join([sys.executable, str(raiz / "nucleo/arranque.py")])
    ajustes["hooks"]["SessionStart"] = [{"hooks": [{"type": "command", "command": inicio, "timeout": 5}]}]
    orden = ["codex", "--no-daemon", "--strict-config", "exec", "--ignore-user-config", "--ephemeral",
             "--dangerously-bypass-hook-trust", "-C", str(raiz)]
    orden += opciones(ajustes)
    if args.json:
        orden.append("--json")
    if args.output_last_message:
        orden += ["--output-last-message", args.output_last_message]
    orden += ["--", args.prompt if args.prompt is not None else "-"]
    return orden


def main():
    p = argparse.ArgumentParser(description="Yema con Codex 0.163: conversación restringida, sin escritura.")
    p.add_argument("--experimental-workspace-write", action="store_true",
                   help="opción retirada: se rechaza hasta verificar G13 y G14")
    p.add_argument("--json", action="store_true")
    p.add_argument("--output-last-message")
    p.add_argument("prompt", nargs="?", help="encargo; sin argumento se lee de stdin")
    args = p.parse_args()
    try:
        orden = construir(args)
        comprobar_fuentes(RAIZ, Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))
        version = subprocess.run(["codex", "--version"], capture_output=True, text=True, check=True)
        if version.stdout.strip() != "codex-cli 0.163.0":
            raise ValueError("se requiere Codex CLI 0.163.0; volver a validar el adaptador para otra versión")
        os.chdir(RAIZ)
        os.execvp(orden[0], orden)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("YEMA Codex: no se inicia: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
