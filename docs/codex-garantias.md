# Codex: inventario y garantías de Yema

Fuente: encargos G11–G14 del 2026-10-28 y ejecutor externo del 2026-10-29,
sobre `origin/main` `99f26cf` (PR #19 y #20 fusionadas). Se conserva la lógica
de `nucleo/puerta.py`. El [ejecutor y su ensayo](codex-ejecutor.md) añaden un
recorrido de creación; el lanzador nativo anterior sigue restringido.

| Requisito de la persona | Fuente | Resultado verificable |
|---|---|---|
| Compensar la aprobación humana sin `ask` | G11 | Deny con ticket inerte y recibo encadenado; la CLI humana existente firma y activa; reintento comprobado en fixture |
| Retirar vías que no pasan por la puerta | G12 | Se retiran shell, web, conectores y otras funciones; persisten vías nativas sin retirada verificada: no equivalente |
| Fallar cerrado ante fallo o timeout del hook | G13 | Ejecutor fuera del arnés: exige reserva real y permiso ligado a la propuesta; muerte, timeout y excepción sin destino; productor sin hooks |
| Escribir efectivamente dentro del ámbito E2 | G14 | Creación externa con bytes exactos; fuera del glob y fuera de raíz sin efecto; no se habilita workspace-write |
| Ensayar con Terra medium, máximo seis invocaciones | Encargo del ejecutor | 6/6 en campaña propia; hogares temporales borrados; [resultados](codex-ejecutor-resultados.json). Campaña anterior: [histórico](codex-ensayo.md) |
| No cambiar núcleo, gobierno, identidad ni metadatos git | Restricción del encargo | Cambios solo en adaptador, pruebas, documentación y changelog; sin commits ni publicación |

**Resultado: 13/15 compatibles en el alcance comprobado (G01–G11 y G13/G14
para creación externa de un fichero nuevo). G12 y G15 siguen abiertas;
no hay equivalencia operativa general con Claude Code.**
Esta cifra cuenta comprobaciones del traductor y del flujo humano, no quince
barreras efectivas en una sesión. G13/G14 del recorrido nativo anterior siguen
sin resolver: el recorrido nuevo evita depender de ese editor y sus hooks.

El lanzador queda en **conversación restringida**: sin shell ni servidores MCP,
con sandbox `read-only`. La opción `--experimental-workspace-write` se
rechaza antes de iniciar Codex. El perfil pierde ejecución, acceso a cúpulas y
escritura nativa. `python3 -m adaptadores.codex.ejecutor` ofrece por separado
propuestas JSON y un aplicador externo de creación, con bwrap comprobado.

## Fuentes y comportamiento comprobado

Versión instalada: `codex-cli 0.163.0`; modelo solicitado `gpt-6.1-terra`,
esfuerzo `medium`, aprobación `never`. No se instalaron dependencias.
La documentación oficial actual puede diferir del CLI instalado; los ensayos
son la evidencia de comportamiento de esta versión.

- [Hooks oficiales](https://learn.chatgpt.com/docs/hooks): formatos por stdin,
  cobertura y límites. Las llamadas de shell llegan como `Bash`; el editor como
  `apply_patch`. `write_stdin` no repite la evaluación previa y hay caminos
  especializados que pueden omitir hooks. Las sondas distinguen un bloqueo
  explícito de la continuación tras un error del hook.
- [Referencia de configuración](https://learn.chatgpt.com/docs/config-file/config-reference):
  `shell_tool=false`, opciones de funciones y sandbox. Se usa configuración
  por invocación, `--strict-config`, `--ignore-user-config`, hogar temporal
  y rechazo de capas locales no auditadas. La retirada de herramientas no se
  deduce únicamente de un TOML aceptado.
- [Rules](https://learn.chatgpt.com/docs/agent-configuration/rules): prefijos de
  órdenes para ejecución fuera del sandbox. Incluso una prohibición general de
  shell no media `apply_patch`, ni comprueba contratos o presupuestos. No se
  instala una regla de prefijos como si fuese una barrera completa.

La campaña anterior de la PR #19 tuvo cinco intentos, 37 tests del adaptador
y 10/15 coincidencias de veredicto. La nueva campaña tiene autorización y
contador propios, sin modificar ni ampliar el contador anterior.

## Matriz verificada

«Compatible en sondas» conserva su sentido limitado: la misma puerta decide
sobre formatos conocidos. El perfil restringido no ofrece todas esas acciones.
Claude se describe por el código y pruebas del repo; no se ha repetido un ensayo
real de Claude en este encargo.

| ID / garantía | Claude Code / núcleo | Codex / estado verificado | Evidencia y límite |
|---|---|---|---|
| G01 Puerta por llamada reconocida | PreToolUse `*`, JSON por stdin | Compatible en sondas | Traducción conservada; desconocidas denegadas; Bash y parches observados en vivo |
| G02 Sin contrato, lectura y zonas libres | Política vigente | Compatible en sondas | Lectura, git y escritura con casos positivos y negativos; shell retirada del perfil actual |
| G03 Ámbito, vetadas, enlaces y zonas protegidas | Rutas reales y globs | Compatible en sondas | Escapes, enlaces, núcleo y adaptador protegidos; dos destinos fuera de alcance denegados en el ensayo E2 |
| G04 Lecturas vetadas | Política y carpetas conocidas | Compatible en sondas | Nota permitida y `.env` denegado; no hay lector shell en el perfil actual |
| G05 Vigencia y aprobación íntegra | Estado, huella, firma y política | Compatible en sondas | Caducidad, huella cambiada y firma falsa; contrato de ensayo firmado con clave desechable |
| G06 Presupuesto de efectos y tiempo | Cuenta antes de ejecutar | Compatible en sondas | Límites positivos/negativos; el intento E2 consume un efecto aunque escribir falle |
| G07 Git de lectura gratis y contratado | Consultas listadas gratuitas | Compatible en sondas | Consulta tras agotar presupuesto y git add material; git retirado del perfil actual |
| G08 Cúpulas y confidencialidad | MCP con cúpula y nivel | Compatible en sondas | Alias y controles conservados; el perfil actual no conecta MCP ni permite acceso a cúpulas |
| G09 Tests preexistentes protegidos | Requiere enmienda | Compatible en sondas | Editar un test existente se deniega |
| G10 Evidencia encadenada | Recibos por hash | Compatible en sondas y creación externa | Reserva del núcleo e intención/resultado en la misma cadena, fsync antes de aplicar, corrupción y pendientes bloquean; no usar el estado simultáneamente con CLI/Claude |
| G11 Aprobación humana | `ask` y token consumible; CLI con firma | Flujo fuera de banda compatible en sondas y solicitud real | Ticket inerte, sin token de diálogo; CLI sin terminal rechazada, terminal simulada firma y activa, siguiente efecto pasa. No hubo humana en el ensayo. Con shell retirada, el lanzador no puede emitir automáticamente la solicitud Bash |
| G12 Todas las vías de acción | Depende de la cobertura del arnés | **Sin equivalente completo** | Shell y stdin retiradas; web/apps/plugins desactivados. El perfil ensayado aún anuncia colaboración y funciones genéricas MCP. Estas últimas se bloquean por hook, no están retiradas. No se invocaron subagentes |
| G13 Fallar cerrado si falla el arnés | Evaluador en error devuelve 2 | **Verificada para creación externa** | Productor en caja sin workspace ni estado, sin hooks; solo permiso explícito + rc=0 + reserva real. Puerta muerta, timeout y excepción sin destino en ensayo; caída de supervisora y pendientes en tests. Una caída tras publicar exige reconciliar, sin reintento |
| G14 Escritura efectiva y acotada E2 | Write/Edit y órdenes contratadas | **Verificada para creación externa** | Codex real propone el fichero permitido y existe con bytes exactos; fuera del glob y fuera de raíz se rechazan. Solo crear, sin reemplazo, padres existentes; edición y órdenes no implementadas |
| G15 Arranque y exclusividad MCP efectivos | SessionStart y strict-mcp-config | **Sin equivalente operativo** | Arranque reutilizado, fuentes locales acotadas y MCP vacío; no hay transporte MCP de producción comprobado ni exclusividad total certificada |

## Compensaciones implementadas

G13/G14, actualización del 2026-10-29: `adaptadores/codex/ejecutor/` mantiene
Codex en una caja bwrap con vista filtrada y montada en solo lectura. La caja
no monta workspace, gobierno, evidencia ni hogar original. El supervisor recibe
JSON cerrado, llama a `evaluar_y_registrar` en un hijo con plazo y valida su
reserva durable. La creación exclusiva se publica después de revalidar contrato,
política, directorio y plazo. Diario común y reconciliador conservan el presupuesto
incluso tras una caída; pendientes y corrupción de contratos anteriores también
impiden continuar. Se requiere estado dedicado sin sesiones CLI/Claude simultáneas.
El [informe](codex-ejecutor.md) delimita aislamiento, red y recuperación.

Las siguientes compensaciones del recorrido anterior se conservan; su campaña
histórica no se presenta como verificación del ejecutor nuevo.

G11: el adaptador consulta `decidir` para comprobar la solicitud, registra el
rechazo real en `dontAsk` y añade un recibo `solicitud-aprobacion-codex` con la
huella completa y la huella de política. **Nunca** evalúa y registra en modo
`ask`, ni crea `aprobaciones/<id>-<huella>.json`: ese fichero permitiría a la CLI
aprobar sin terminal. La persona ejecuta `bin/yema aprobar <id> <huella8>` en su
terminal. El núcleo vuelve a verificar la huella, firma según la política y
encadena la activación. El efecto posterior vuelve a evaluarse normalmente;
el ticket no se convierte en un permiso. Huella incorrecta, id inexistente,
id interno distinto y borrador cambiado tienen pruebas negativas.

G13: `vigilante.py` recibe el JSON por stdin y espera un veredicto explícito del
evaluador, con un máximo de 10 segundos dentro de los 30 del arnés. Ante error,
ausencia, salida vacía/malformada o timeout devuelve 2; mata también los procesos
descendientes al agotar tiempo. Un `allow` acompañado de rc=2 no permite. El
traductor emite `allow`/`deny` explícitos; no se envía `ask` a Codex.
Esto protege al evaluador hijo, **no al propio vigilante ni al arnés**.

G12/G14: `shell_tool=false` retira shell y stdin; se desactivan apps, plugins,
navegador, ordenador, imágenes, instalación de dependencias y otras funciones;
`mcp_servers={}` se pasa explícitamente, incluso siendo un objeto vacío. Se
conservan read-only, red de shell desactivada y exclusión de temporales como
raíces de escritura. La retirada total no está probada. Después de la sonda del
catálogo se añaden también `multi_agent_v2=false` y `goals=false`; las sesiones
5 y 6 aceptan esas opciones, pero no repiten la inspección del catálogo.
No se confunde aceptar configuración con retirar efectivamente una herramienta.

## Supuestos, riesgos y decisiones abiertas

**Supuesto:** la persona que inicia el lanzador controla sus fuentes y el estado
privado. El bypass de confianza de hooks solo se aplica a esas fuentes auditadas;
no aprueba contratos ni desactiva el sandbox. No se afirma resistencia frente a
una persona que cambie el lanzador o a requisitos administrados adicionales.

Riesgos: persisten herramientas nativas sin retirada certificada, el editor puede
continuar tras fallar el hook y el sandbox no contiene por sí solo servidores
MCP. Desactivar capacidades reduce utilidad y no demuestra equivalencia por
inactividad. La solicitud G11 no es un diálogo humano nativo ni una autorización
producida por el modelo.

Decisiones abiertas: extender la frontera externa a edición y recetas de órdenes,
reservas coordinadas con otros adaptadores, ancla externa de la cadena, proxy de
red limitado al proveedor y comprobación autoritativa del catálogo efectivo.
Falta transporte MCP real de producción. Las campañas anterior y del ejecutor
están agotadas por separado; esta entrega no autoriza nuevas llamadas.
