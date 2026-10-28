"""Vigila al evaluador, no al arnés. Un fallo de este vigilante aún puede abrir Codex.

El lanzador conserva read-only y retira ejecutores externos por ese límite.
Entrada JSON por stdin; solo un veredicto explícito allow con rc=0 permite.
"""
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

TIMEOUT = 10  # Menor que los 30 s concedidos por Codex al hook completo.


def evaluar(entrada, orden=None, timeout=TIMEOUT):
    orden = orden if orden is not None else [sys.executable, str(Path(__file__).with_name("puerta.py"))]
    try:
        with subprocess.Popen(orden, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, start_new_session=True) as proceso:
            try:
                salida, _ = proceso.communicate(entrada, timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proceso.pid, signal.SIGKILL)
                proceso.communicate()
                return 2, "", "YEMA Codex: bloqueo: timeout del evaluador"
            if proceso.returncode not in (0, 2):
                raise ValueError("evaluador en error")
            datos = json.loads(salida)
            if not isinstance(datos, dict) or not isinstance(datos.get("hookSpecificOutput"), dict):
                raise ValueError("veredicto no es un objeto")
            veredicto = datos["hookSpecificOutput"]
            if veredicto.get("hookEventName") != "PreToolUse":
                raise ValueError("evento de veredicto incorrecto")
            decision = veredicto.get("permissionDecision")
            if proceso.returncode == 0 and decision == "allow":
                return 0, salida, ""
            if decision == "deny":
                return 2, salida, str(veredicto.get("permissionDecisionReason", "YEMA Codex: bloqueo"))
            raise ValueError("sin veredicto válido")
    except (OSError, ValueError, KeyError, TypeError):
        # No exponer salidas arbitrarias del proceso que falló.
        return 2, "", "YEMA Codex: bloqueo: evaluador ausente, en error o sin veredicto explícito"


def main():
    rc, salida, error = evaluar(sys.stdin.read())
    if salida:
        print(salida.strip())
    if error:
        print(error, file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
