# Adaptador Codex 0.163

**Experimental: no hay equivalencia operativa E2 con Claude Code.**
La campaña G11–G14 conserva 11/15 coincidencias funcionales en sondas y deja
G12–G15 abiertas. En seis invocaciones reales, la puerta concedió la escritura
permitida y bloqueó dos destinos fuera de alcance, pero el editor no consiguió
escribir. Un error o timeout del hook exterior permite continuar al editor.
[Matriz](../../docs/codex-garantias.md) · [Ensayo](../../docs/codex-ensayo.md).

## Uso restringido

Requiere Python 3.11+ y **Codex CLI 0.163.0**, autenticado por la persona.
No instala paquetes ni escribe configuración en `~/.codex`.

```sh
bin/yema-sesion-codex 'Resume el contexto de arranque'
bin/yema-sesion-codex --json < encargo.txt
```

El lanzador fija `gpt-6.1-terra`, esfuerzo `medium`, aprobación `never` y
sandbox `read-only`. Retira shell, servidores MCP, web, apps, plugins,
navegador, imágenes e instalación de dependencias. El perfil pierde ejecución,
lectura mediante shell y acceso a cúpulas; no sirve para desarrollo E2.
La retirada total del catálogo nativo aún no está certificada.

`--experimental-workspace-write` se conserva como argumento reconocido para
dar un error claro, pero devuelve 2 **antes de iniciar Codex**. No habilita
escritura ni siquiera con un contrato E2 firmado. La autorización del contrato
no resuelve el fallo abierto del hook exterior.

Codex necesita estado de ejecución escribible bajo `CODEX_HOME`, incluso con
`--ephemeral`. La persona debe proporcionar un hogar apropiado al lanzador;
este no copia auth automáticamente. El ensayo usa un hogar temporal privado,
copia solo auth y configuración mínima y lo borra al salir, también ante error.

## Aprobación humana fuera de banda

El traductor reconoce una solicitud `Bash` con `yema aprobar <id> <huella8>`.
Comprueba el contrato, devuelve deny con `ticket Codex codex-<huella completa>`
y encadena una solicitud con huella de contrato y política. Ese recibo es
inerte: **no** crea el token de diálogo que la CLI podría consumir sin terminal.

La persona revisa `bin/yema resumen <id>` y ejecuta en su terminal:

```sh
bin/yema aprobar <id> <huella8>
```

La CLI existente comprueba de nuevo la huella, firma según la política y encadena
la activación. El efecto posterior se reevalúa normalmente. No se modifica la
puerta ni se confía en una variable que afirme que hubo aprobación humana.
El flujo completo se prueba con terminal simulada; la sonda real solo solicita,
sin aprobar. Como el perfil actual retira Bash, la solicitud automática del
modelo solo se ejercita en la fixture de ensayo; la aprobación de producción
se inicia por la persona fuera de la sesión.

## Fronteras y traducción

`config.toml` se carga por invocación. El lanzador ignora ajustes personales,
fija `project_root_markers=[]`, rechaza otras capas de configuración/hooks del
proyecto y hooks del hogar activo, y comprueba la versión. Usa
`--dangerously-bypass-hook-trust` solo para sus hooks auditados; no concede
contratos ni desactiva sandbox. No usa `--ignore-rules`.

`SessionStart` reutiliza `nucleo/arranque.py`. `PreToolUse` con matcher `*`
llama a `vigilante.py`, que entrega el JSON intacto por stdin al traductor.
El vigilante exige veredicto explícito `allow` y rc=0. Devuelve 2 ante salida
inválida, error, ausencia o timeout del evaluador; al agotar 10 s mata su grupo
de procesos, antes de los 30 s del arnés. **No protege su propia muerte ni el
timeout exterior de Codex.** Read-only reduce efectos sin demostrar G12/G13.

| Entrada Codex por stdin | Entrada del núcleo |
|---|---|
| `Bash`, `command` | Misma orden; respeta `workdir`/`cwd` si llegan; solicitud de aprobación tratada fuera de banda |
| `apply_patch`, `command` | Add/Update de un único fichero → Write/Edit con ruta |
| MCP de `savia-vaults` o alias `savia_vaults` conocido | Nombre canónico y argumentos originales; traducción conservada, servidor retirado del perfil |
| `update_plan` | `TodoWrite` |
| Otra herramienta o formato | Deny, rc=2 |

Se mantiene `permission_mode=dontAsk` al **evaluar y registrar**. La consulta
sin registro para preparar una solicitud no produce permisos ni tokens.
El traductor exige evento `PreToolUse`, cwd absoluto y objeto de entrada.
Rechaza TTY, intérpretes alternativos, escaladas, permisos adicionales, parches
de varios ficheros, borrado y movimiento. Protege además el adaptador y `.codex`.

## Verificación

```sh
python3 -m unittest discover -s pruebas -p 'test_codex*.py' -v
python3 -m unittest discover -s pruebas -v
```

56/56 pruebas del adaptador; 314 pasan de 326 generales, con 12 omitidas por
confianza de bwrap preexistente. Los 19 tests nuevos detectan mutaciones.
`pruebas/ensayo_codex_garantias.py` cuenta hasta seis invocaciones, incluso
fallos, en copias con contratos y claves sintéticos. Solo ese ensayo contiene
sondas de workspace-write. La campaña autorizada ya está agotada: no iniciar
otra cambiando su directorio. Un rc=0 sin escritura, eventos y recibos no es PASS.

Riesgos y decisiones abiertas: catálogo efectivo sin inspección autoritativa,
colaboración nativa y funciones genéricas aún sin retirada certificada, fallos
del hook exterior, escritura E2 fallida y transporte MCP de producción pendiente.
No habilitar E2 hasta disponer de una frontera que controle cada efecto incluso
si el hook falla.
