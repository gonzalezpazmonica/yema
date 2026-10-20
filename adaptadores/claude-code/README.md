# Adaptador: Claude Code

Claude Code es el arnés provisional de Yema. El núcleo no depende de él.

- `.claude/settings.json`: registra `nucleo/puerta.py` como hook `PreToolUse` para todas las herramientas. Exit 0 permite, exit 2 bloquea con el motivo en stderr.
- `.mcp.json`: cúpulas por `savia-vaults` (variables `SAVIA_VAULTS_NODE`, `SAVIA_VAULTS_DIR`, `SAVIA_VAULTS_DOMES`).
- `CLAUDE.md` solo importa `AGENTS.md`.

Cualquier otro arnés que entregue `{tool_name, tool_input, cwd}` puede usar la misma puerta.
