# Adaptador Codex 0.163

Adaptar Yema a Codex sin cambiar `nucleo/puerta.py`: traducir herramientas,
mantener el contrato y sus recibos, y comprobar los límites del arnés.
Fuente del alcance: encargo «adaptador Codex», pasos 0–2.

**Estado: experimental, equivalencia operativa pendiente.** Las sondas verifican
10 de 15 garantías de la [matriz](../../docs/codex-garantias.md), sobre eventos
documentados. En el [ensayo real](../../docs/codex-ensayo.md), dos sesiones
recibieron cuatro hooks y bloquearon la orden prohibida. Se agotaron los cinco
intentos: git y escritura fallan en este entorno, y el MCP sigue requiriendo una
aprobación que el modo headless no puede pedir. No se completó un desarrollo.

## Uso

Requiere Python 3.11+ y **Codex CLI 0.163.0**, autenticado por la persona. No
instala paquetes ni modifica `~/.codex/config.toml`. El propio CLI necesita
estado de ejecución escribible bajo `CODEX_HOME` (por defecto `~/.codex`),
incluso con `--ephemeral`. El ensayo prepara un hogar temporal privado,
copia allí la autenticación y la borra al terminar, también ante un error.

```sh
bin/yema-sesion-codex 'Lee AGENTS.md y resume el estado del proyecto'
bin/yema-sesion-codex --json < encargo.txt
```

Es un lanzador de `codex exec`, para sesiones sin preguntas. Se fija
`gpt-6.1-terra`, esfuerzo `medium`, sandbox `read-only`, aprobación `never`.
No hay modo interactivo ni reanudación en esta versión del adaptador.
Para actuar sobre un contrato hay que tenerlo aprobado previamente por la
persona en su terminal. Una petición de aprobación desde el modelo se deniega:
Codex no admite la decisión `ask` del hook que usa Claude Code.

La escritura requiere una opción explícita:

```sh
bin/yema-sesion-codex --experimental-workspace-write 'Encargo ya contratado'
```

Esta opción permite escribir en el worktree; **no establece equivalencia con
Claude Code**. El sandbox no conoce globs, presupuesto ni contratos, los hooks
no cubren toda la ejecución y sus fallos pueden dejar continuar la herramienta.
Para desarrollo con esas garantías hace falta una frontera externa que haga
cumplir cada efecto. No usar el modo experimental sobre el núcleo de Yema.

## Configuración y traducción

- `config.toml` es la base declarativa, cargada por `sesion.py` como opciones
  `-c`; no se instala una capa `.codex/` en el proyecto ni en el hogar.
- `bin/yema-sesion-codex` inicia desde la raíz de Yema. Solo admite prompt,
  `--json`, `--output-last-message` y la opción experimental de escritura.
- Se ignora la configuración personal, se desactivan apps, plugins, subagentes
  y búsqueda web. Solo se declara `savia-vaults`, mediante el mismo
  `bin/savia-vaults-mcp` que Claude. Si no inicializa, la sesión debe fallar
  (`required = true`). Las variables `SAVIA_VAULTS_*` se transmiten al servidor.
- Se fija `project_root_markers=[]` para descubrir solo la raíz lanzada. Se
  rechazan `.codex/config.toml` y `.codex/hooks.json` de esa raíz y `hooks.json`
  del hogar activo. La configuración original de usuario no se confunde con
  un ancestro del proyecto al usar un hogar temporal. Los requisitos
  administrados del sistema siguen siendo de Codex.
- Los hooks auditados se construyen en cada invocación. Se utiliza
  `--dangerously-bypass-hook-trust` exclusivamente para esos hooks, después de
  comprobar sus fuentes; **no** desactiva el sandbox ni aprueba contratos.
  No se usan `--ignore-rules` ni el bypass de aprobaciones y sandbox.
- `SessionStart` reutiliza `nucleo/arranque.py`. `PreToolUse` llama al traductor
  con `matcher = "*"`. La shell convierte también un fallo del intérprete en
  exit 2. Un timeout impuesto por Codex sigue fuera de esa compensación.

| Entrada Codex por stdin | Entrada del núcleo |
|---|---|
| `Bash`, `tool_input.command` | `Bash`, misma orden; respeta `workdir`/`cwd` de herramienta si se incluyen |
| `apply_patch`, `tool_input.command` | `Write` para Add File, `Edit` para Update File, con `file_path` |
| `mcp__savia-vaults__…` o alias real `mcp__savia_vaults__…` conocido | nombre `mcp__savia-vaults__…` y mismos argumentos; solo ese servidor |
| `update_plan` | `TodoWrite` |
| cualquier otra herramienta/formato | exit 2 |

El traductor exige `hook_event_name = "PreToolUse"`, `cwd` absoluto y
`tool_input` objeto. No lee la petición de variables de entorno. Fuerza
`permission_mode = "dontAsk"` hacia el núcleo para impedir tickets de
aprobación sin diálogo. Llama a `evaluar_y_registrar`, incluido el cómputo
gratuito de consultas git; no duplica la lógica del contrato.

La salida 0 del hook no bastó para conceder la lectura MCP en Codex: con
`approval_policy=never`, el arnés la rechazó después de superar el traductor.
Queda pendiente resolver ese permiso sin conceder efectos ajenos al contrato;
no se presenta la inicialización del servidor como una lectura ejecutada.

Solo se aceptan parches Add/Update **de un fichero**. Borrar, mover y parches de
varios ficheros se bloquean; así no se conceden borrados como simples escrituras
ni se cargan parcialmente varios efectos. Cada fichero requiere una llamada.
Se protegen además `.codex/`, `adaptadores/codex/` y el lanzador frente a parches.
Se deniegan TTY, escaladas, permisos adicionales e intérpretes alternativos cuando
aparecen en la entrada. Esto no demuestra que el arnés entregue esos campos.
Las operaciones MCP admitidas son las documentadas por Yema: `vault_read`,
`vault_search`, `vault_domes`, `vault_health`, `vault_rag_status`, `vault_write`,
`vault_rag_sync` y `vault_index`. Una operación nueva requiere revisar la traducción.

## Verificación

```sh
python3 -m unittest discover -s pruebas -p test_codex.py -v
python3 -m unittest discover -s pruebas -v
# Optativo, consume una invocación del modelo y necesita un directorio de log:
python3 pruebas/ensayo_codex.py --salida "$LOG/ensayo"
python3 pruebas/ensayo_codex.py --salida "$LOG/ensayo" --escritura-experimental
```

El ensayo copia el código, deriva un contrato sintético del ejemplo, usa una
clave desechable y sustituye el servidor MCP por una fixture. No aprueba ni
modifica contratos reales. Cuenta también los intentos fallidos, hasta cinco
por directorio de log. Un rc=0 sin herramientas, recibos y artefactos esperados
no se considera éxito; también se exige git ejecutado y llamada recibida por
la fixture MCP. Esta campaña ya agotó sus cinco intentos: no reiniciar su
contador ni cambiar el directorio para ampliarlo. El ensayo con MCP real de
producción queda pendiente.

Riesgos y decisiones abiertas: cobertura incompleta de hooks, timeout del arnés,
`write_stdin` sin nueva evaluación, protección externa de secretos y gobierno,
y validación del modelo y del transporte MCP real. Detalle y compensaciones en
la matriz; no habilitar escritura general hasta resolverlos.
