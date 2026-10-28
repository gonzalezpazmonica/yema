# Codex: inventario y garantías de Yema

Fuente del encargo: «Yema tiene que ejecutar desarrollos con Codex con las mismas
garantías que con Claude Code», pasos 0–2. Inspección: 2026-10-28, base
`3c3a595` de `origin/main`, rama `agent/yema-codex-20261028`.

| Requisito de la persona | Fuente | Entrega / comprobación |
|---|---|---|
| Inventariar hooks, rules, sandbox y MCP de 0.163 | Paso 0 | Inventario de esta página y salidas locales del CLI |
| Comparar las garantías sin suposiciones ocultas | Paso 0 | Matriz G01–G15, separando sondas de sesión real |
| Configuración, README y lanzador; traductor si hay hooks | Paso 1 | `adaptadores/codex/`, `bin/yema-sesion-codex` |
| Mismas sondas Claude/Codex, positivas y negativas | Paso 2 y autorrevisión | `pruebas/test_codex.py`; mutaciones detectadas |
| Ensayo con `gpt-6.1-terra`, medium, máximo cinco | Paso 2 | Cinco intentos, dos sesiones con herramientas y bloqueo real; desarrollo incompleto; [registro](codex-ensayo.md) |
| Conservar el núcleo; no publicar | Alcance específico | Ningún cambio de núcleo, push o PR |

**Resultado: 10/15 garantías compatibles en sondas; equivalencia operativa
pendiente.** Dos sesiones reales demuestran la entrega de hooks, el bloqueo
de una orden prohibida y los recibos íntegros. Git, escritura y lectura MCP
no se completan. La escritura queda desactivada por defecto.

No hubo prerregistro previo: las primeras mediciones ya existían al reanudar.
Los metadatos git siguen montados en solo lectura; los cambios quedan sin commit.

## Fuentes y hechos comprobados

Fuentes locales: `AGENTS.md`, `ALMA.md`, `adaptadores/claude-code/README.md`,
`bin/yema-sesion`, `nucleo/puerta.py`, `.claude/settings.json`, `.mcp.json`,
`gobierno/politica.json`, `ejemplos/contrato-ejemplo.json` y pruebas existentes.
`MAP.md` no está en esta base y figura en `.gitignore`; no se inventó su contenido.

El ejecutable instalado declara **`codex-cli 0.163.0`**; el manifiesto del paquete
confirma versión y plataforma Linux musl. En el paquete standalone inspeccionado
no aparece un manual textual de hooks/configuración: hay binarios y recursos.
Se consultó la documentación oficial mediante el manual descargado con la skill
OpenAI Docs. La ayuda instalada tiene prioridad ante diferencias de versión.

Órdenes de inventario ejecutadas: `codex --help`, `codex exec --help`,
`codex features list`, `codex mcp --help`, `codex sandbox --help`,
`codex execpolicy --help`, `codex execpolicy check --help` y `codex doctor`.
No se actualizaron ni instalaron dependencias.

`~/.codex/config.toml` se leyó sin modificarlo ni copiar credenciales: modelo
personal `gpt-6.1-sol`, esfuerzo `high`, sin sandbox ni aprobación explícitos,
sin perfiles, con estado de confianza de hooks y tres MCP (`savia-vaults`,
`codegraph`, `codebase-memory-mcp`). Esos ajustes no son los del adaptador:
`--ignore-user-config` y opciones explícitas evitan heredarlos. No hay
`~/.codex/hooks.json` ni configuración en la capa `.codex/` de este worktree.
El ensayo reanudado usa `CODEX_HOME` temporal con credencial copiada en privado
y borrada al salir; no escribe en el hogar original. Fijar
`project_root_markers=[]` acota el descubrimiento al directorio lanzado.

### Hooks

La ayuda incluye `--dangerously-bypass-hook-trust` y la feature `hooks` aparece
estable y activa. La documentación oficial describe hooks en `hooks.json` o
TOML, confianza por huella y un objeto JSON por stdin. `PreToolUse` entrega
`tool_name`, `tool_input`, `cwd`, `hook_event_name` y metadatos. Normaliza shell
y unified exec como `Bash`; `apply_patch` entrega el parche en `command`.
Para MCP usa nombres `mcp__servidor__herramienta`. En la sesión real se recibió
`mcp__savia_vaults__vault_read`: se traduce ese alias exacto al nombre del núcleo.
Se observaron `Bash` con `command` y `apply_patch` con el parche en `command`.
Exit 2 denegó la orden prohibida en ambas sesiones reales. Véase
[Hooks: formatos y cobertura](https://learn.chatgpt.com/docs/hooks).

Límites de documentación **no ejercitados en este ensayo**:
las herramientas alojadas quedan fuera del hook, `write_stdin` no repite
`PreToolUse`, y errores/timeouts pueden dejar continuar una llamada. Codex no
implementa `permissionDecision = "ask"` de PreToolUse. El adaptador nunca lo
emite ni genera el ticket de aprobación correspondiente.

### Rules y execpolicy

El comando `execpolicy` existe aunque no aparezca en la lista principal de ayuda.
Se ejecutó `codex execpolicy check` con una regla sintética que prohíbe el prefijo
`git push`: devuelve `decision: forbidden` para `git push origin main`; para
`git status` no hay regla coincidente **ni decisión de permiso**.

Las reglas usan prefijos estáticos y resuelven coincidencias con la decisión más
restrictiva. No cargan contratos, caducidad ni contadores. Se describen como
control de órdenes fuera del sandbox: no sustituyen una puerta por herramienta.
Un prefijo `git push` tampoco demuestra bloquear todas las variantes con opciones
globales de git. No se ha instalado una regla incompleta como frontera de seguridad.
Fuente: [Rules](https://learn.chatgpt.com/docs/agent-configuration/rules).

### Sandbox y perfiles

La ayuda de `exec` enumera `read-only`, `workspace-write` y `danger-full-access`.
`--ask-for-approval` ofrece `on-request` y `never`. `sandbox --help` anuncia
perfiles de permisos nombrados con `-P` y perfiles de configuración con `-p`;
estos últimos son ficheros `$CODEX_HOME/<nombre>.config.toml` en esta versión.
No se han probado perfiles nombrados propios.

El adaptador fija `read-only`; la opción experimental cambia a `workspace-write`,
con red de shell desactivada y sin añadir `/tmp` ni `TMPDIR` como raíces de
escritura. El worktree continúa siendo una concesión más amplia que los globs
de un contrato. No se concede `danger-full-access`, escalada ni directorios
adicionales. Los requisitos del sistema pueden restringir la configuración.

**No comprobado:** aislamiento efectivo de procesos en una sesión. Git falló
al construir bubblewrap porque el directorio de socket compartido tiene modo
`000`, frente al `0700` requerido; el parche no pudo escribir. Tampoco un
diagnóstico con temporales privados resolvió ese error. No se alteró el sandbox.
Una ejecución fallida no demuestra el aislamiento de una ejecución exitosa.
Referencia: [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

### MCP

La ayuda incluye gestión de servidores (`list`, `get`, `add`, `remove`, login y
logout). La referencia documenta servidores stdio con `command`, `args`, `cwd`,
`env_vars` y `required`. El adaptador reutiliza el envoltorio existente de Yema,
exige inicialización y no añade conectores de cuenta. La comprobación de cúpula
y nivel sigue en el núcleo. El sandbox de shell no contiene un servidor MCP
ejecutado por el arnés; cada servidor necesita sus propios permisos mínimos.
No se ha conectado a cúpulas reales durante este encargo. La fixture inicializó
y anunció `vault_read`, pero el último intento acabó en `MCP tool call requires
approval, but approval policy is never`, después de superar el traductor.
Queda pendiente resolver ese permiso del arnés y comprobar el transporte completo;
la salida 0 del hook no bastó para aprobar la llamada MCP.

## Matriz de compatibilidad

«Compatible en sondas» significa mismo veredicto de la puerta a partir de eventos
sintéticos con formato documentado; no implica que Codex entregue todos los
eventos ni que haga cumplir la decisión. La última columna distingue lo probado
en sesión real de lo pendiente. Claude se describe según la configuración y
pruebas del repo; no se repitió un ensayo de Claude en este encargo.

| ID / garantía | Claude Code / núcleo actual | Codex / adaptador | Evidencia y límite |
|---|---|---|---|
| G01 Puerta por llamada reconocida | PreToolUse `*`, JSON stdin; desconocidas denegadas | Compatible en sondas para Bash, Add/Update de un fichero, MCP y plan | Entrega real de Bash, Add y MCP; orden prohibida bloqueada en ambas sesiones; Update/plan solo en sondas |
| G02 Sin contrato, lectura y zonas libres | Decide con política vigente | Compatible en sondas, mismo evaluador | Lectura permitida, git y escritura externa denegados |
| G03 Ámbito, vetadas, enlaces y zonas protegidas | Rutas reales y globs; núcleo/identidad/evidencia protegidos | Compatible en sondas; se protege además el adaptador para parches | Casos de escape, enlace y rutas vetadas; la shell conserva límites del núcleo |
| G04 Lecturas vetadas | Política y carpetas conocidas | Compatible en sondas para lectores Bash admitidos | Nota permitida y `.env` denegado; herramientas de lectura desconocidas se bloquean |
| G05 Contrato vigente y aprobación íntegra | Estado activo, huella, firma y política | Compatible en sondas | Casos válidos, caducidad, huella cambiada y firma falsa; contrato sintético firmado aceptado en sesión |
| G06 Presupuesto de efectos y tiempo | Evalúa y registra antes de ejecutar | Compatible en sondas | Máximo un efecto y siguiente denegado; límite temporal en sondas; la sesión cuenta el parche aunque falla después |
| G07 Git de lectura gratis, aún contratado | Consultas listadas no gastan; no listadas denegadas | Compatible en sondas | Consulta tras agotar presupuesto, git add consume; en sesión git pasa la puerta sin gasto, pero falla su ejecución |
| G08 Cúpulas nombradas y confidencialidad | MCP con cúpula explícita, control de N3+ y escritura | Compatible en sondas; sin lectura MCP operativa en el ensayo | Cúpula permitida/ajena/omitida, N3 y escritura no concedida; alias real corregido; Codex exige aprobación con política never |
| G09 Tests preexistentes protegidos | Requiere enmienda con pruebas_editables | Compatible en sondas mediante Edit traducido | Editar un test existente se deniega |
| G10 Evidencia encadenada | Recibos y cadena por hash | Compatible en sondas, mismo registrador | Cadena y contador verificados también en ambas sesiones; no prueba atomicidad ante concurrencia |
| G11 Aprobación humana desde el diálogo | El núcleo devuelve ask y genera ticket | Sin equivalente implementado: Codex no admite ese ask | Se fuerza dontAsk y no se genera ticket; aprobación por la persona en terminal |
| G12 Cobertura de todas las vías de acción | La puerta depende de lo que entrega el arnés | Sin equivalente completo: alojadas, vías especiales y write_stdin | Desactivar web/apps/plugins/subagentes reduce superficie; faltan requisitos externos para stdin |
| G13 Fallar cerrado también si falla el arnés | Núcleo en error devuelve 2 | Sin equivalente completo ante fallo/timeout del hook en Codex | Shell devuelve 2 si falla Python; el timeout del arnés puede escapar a esa compensación |
| G14 Desarrollo E2 con escritura efectiva acotada | Write/Edit y órdenes según contrato | Sin equivalente operativo demostrado | Solo lectura por defecto; workspace-write experimental no entiende los globs ni el presupuesto |
| G15 Arranque y exclusividad MCP efectivos | SessionStart y strict-mcp-config en el lanzador | Arranque real con fixture; exclusividad completa no demostrada | Se ignoran ajustes personales, se fija raíz de descubrimiento y se rechazan capas locales; inicialización MCP observada, pero herramientas aún requieren aprobación |

## Supuestos y compensaciones propuestas

**Supuesto de diseño:** quien inicia el lanzador ha revisado el código del
adaptador; por eso se confía en sus hooks por invocación. No se afirma que sea
una frontera frente a una persona que cambie el lanzador o frente a políticas
administradas que agreguen herramientas.

Para alcanzar equivalencia de desarrollo: ejecutar en una copia de proyecto con
gobierno, evidencia, credenciales y núcleo fuera de las raíces escribibles;
controlar la red y los servidores MCP fuera del arnés; y comprobar cada efecto
en una frontera externa que cierre también ante fallo del hook. Los requisitos
administrados de Codex pueden desactivar procesos reanudables y `write_stdin`;
un ajuste de usuario `features.unified_exec=false` se documenta como ignorado.
No se ha instalado esa política administrada ni se ha probado tal despliegue.
Execpolicy puede añadir prohibiciones estáticas, pero no resolver G05–G07.

Riesgos: la documentación actual difiere de 0.163 en algunos campos, el sandbox
no limita MCP, la lectura MCP sigue denegada por el arnés, y una orden permitida
puede tener más efectos internos (límite ya declarado por Yema). Decisiones
abiertas: resolver el permiso MCP, desplegar la frontera externa y validar
G11–G15 antes de habilitar E2. Se agotó el máximo de cinco intentos; otra campaña
necesita autorización y presupuesto nuevos.
