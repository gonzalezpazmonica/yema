# Gobernanza

## Principio

La especificación describe qué se espera. El contrato dice qué está autorizado a ocurrir, por quién, con qué límites y hasta cuándo.
Yema distingue **autonomía cognitiva** (explorar, comparar, proponer: amplia) de **autonomía ejecutiva** (producir efectos: delegada, acotada y revocable).

## Niveles de efecto

| Nivel | Qué cubre | Exigencia | Revisión humana |
|---|---|---|---|
| E0 | Exploración sin efectos | Ninguna: es el modo sin contrato | — |
| E1 | Propuestas internas reversibles (borradores, buzón, memoria) | Zonas libres de la política | Cuando se lean |
| E2 | Cambios acotados y reversibles (código en rama propia, pruebas) | Contrato aprobado, ámbito, órdenes, presupuesto, postcondiciones | Evidencia al cierre + muestreo de diffs |
| E3 | Efectos sobre terceros, remoto o producción (push, PR, merge) | Autoridad explícita por efecto y revisión independiente | Por efecto |
| E4 | Seguridad, derechos, dinero, irreversibles | Fuera del alcance de Yema en v0 | Siempre, y fuera de Yema |

La persona aprueba **contratos antes** de ejecutar y revisa **evidencia después**. En E2 no lee cada diff: muestrea.
En E3 cada efecto lo decide ella (merge, publicación).

## Contrato (v0, JSON)

Campos obligatorios: `id`, `version`, `estado`, `proposito`, `responsable`, `ejecutora`, `nivel`, `ambito`, `autoridad`, `recursos`, `evidencia`.
Opcionales: `contexto` (cúpulas permitidas, fuentes), `spec`, `condiciones` (`pre`, `invariantes`, `post`), `peticion` (las palabras exactas de la persona) y `requisitos` (`[{id: "S1", cita: "frase literal", post: ["id de postcondición"]}]`: cada requisito cita a la persona y apunta a cómo se demostrará; el validador rechaza citas vacías y postcondiciones inexistentes).
- `ambito.pruebas` / `ambito.pruebas_editables`: los tests que ya existían y casan con `pruebas` no se pueden modificar salvo que estén en `pruebas_editables`. Los tests nuevos, sí.

- `ambito.raiz`: directorio absoluto donde se trabaja. `ambito.escritura` / `ambito.vetadas`: globs relativos.
- `autoridad.efectos` / `autoridad.prohibidos`: de `leer, escribir, borrar, ejecutar, red, git-local, git-remoto, fusionar, publicar, delegar, escribir-cupula`.
- `autoridad.ordenes`: prefijos de orden permitidos (`python3 -m unittest`, `cargo test`…). Las órdenes compuestas se rechazan siempre.
- `autoridad.caduca`: obligatoria. Sin caducidad no hay contrato.
- `recursos.efectos_max`: presupuesto de efectos materiales.

Ejemplo: `ejemplos/contrato-ejemplo.json`. Los contratos reales viven en el estado privado `~/.yema/contratos/`, fuera del repo.

## Ciclo de vida

```
borrador → cuestionado → candidato → en_revision → aprobado → aprovisionado → activo → validando → cerrado
                                            ↘ rechazado         activo ⇄ suspendido;  → revocado | caducado | fallido
```

- Aprobar exige una aprobadora de `gobierno/politica.json` distinta de la ejecutora.
- La aprobación sella la **huella** del contenido. Cualquier cambio material posterior invalida el contrato: hace falta versión nueva y aprobación nueva.
- Aprobar y activar (`yema aprobar <id> <huella>`) lo hace una persona: o en su terminal, o contestando el diálogo de permisos del arnés cuando Yema lo pide en la conversación. La puerta responde «preguntar» (nunca «permitir») a esa orden, deja un ticket de un solo uso que caduca en 5 minutos y deniega en los modos que no preguntan. La v1 añadirá firma (ver ROADMAP).

## Garantías y dónde se cumplen

| Garantía | Mecanismo en v0 | Prueba |
|---|---|---|
| Identidad | `responsable`, `ejecutora`, `aprobacion.por` | `test_contrato` |
| Legitimidad | Aprobadoras de la política; nunca la ejecutora | `test_autoaprobacion_rechazada` |
| Alcance | Puerta: efectos, globs, órdenes, cwd, `git -C` | `test_puerta` |
| Suficiencia | Esquema válido para aprobar y activar | `test_esquema_valido` |
| Separación | La ejecutora no aprueba ni toca su núcleo | `test_nucleo_y_contratos_protegidos_aun_con_contrato` |
| Evidencia | Recibo encadenado por hash de cada efecto material y cada rechazo | `test_evidencia` |
| Revocabilidad | Suspender/revocar quita el puntero y la puerta vuelve a E0 | `test_contrato_revocado_vuelve_a_e0` |
| Evolución controlada | Huella sellada al aprobar | `test_cambio_tras_aprobar_invalida` |

## Límites conocidos de la v0 (honestidad)

- Una orden permitida puede hacer más de lo que su nombre sugiere (`python3 -m unittest` ejecuta código del repo). La frontera fuerte es el sistema operativo: en Space, el sandbox del modo mediado.
- La puerta solo ve lo que el arnés le enseña. Si el arnés no pasa una herramienta por el hook, no la controla.
- El diálogo y la terminal prueban que alguien con acceso a la sesión contestó, no quién. La firma llega en la v1.
- El presupuesto cuenta efectos, no tokens: el arnés no expone el consumo al hook.

## Aprobación firmada (F4)

Con `firma_aprobacion: true` en la política, aprobar no basta con cambiar el estado del contrato:
- `yema aprobar`, tras el diálogo o en la terminal de la persona, firma con HMAC-SHA256 el identificador, la versión, la huella, quién aprobó y cuándo.
- La firma usa un secreto local en `<estado>/llaves/` (permisos 0600) que solo crea y usa la CLI.
- La puerta solo da por vigente un contrato cuya firma verifica.

La agente no puede leer el secreto: la puerta veta cualquier ruta bajo `llaves/`, también con comodines y con Grep sobre una carpeta que la contenga. Tampoco puede escribirlo, porque está fuera de las zonas libres. Así que no puede fabricar un contrato «aprobado» editando el JSON aunque encontrara la manera.

Sigue sin cubrir lo que pase fuera de la puerta, como un proceso con acceso al disco. La firma con la clave de la persona o de Space queda para la mudanza (F3).

Al activar la firma, los contratos aprobados antes dejan de valer y hay que volver a aprobarlos.

## Comodines y búsquedas en lecturas vetadas

Un comodín (`cat ~/.s*/id_*`) se juzga por lo que abriría al ejecutarse, no por su texto. Una búsqueda con Grep no puede abarcar una carpeta que contenga algo vetado, porque leería su contenido sin nombrarlo.

## Borrar es un efecto aparte

`rm`, `rmdir`, `unlink`, `shred`, `git rm`, `git clean` y `git branch -d/-D` exigen el efecto `borrar`. Conceder `escribir` ya no permite borrar.

## La aprobación fija la política

Con la firma activada, la aprobación guarda la huella de `gobierno/politica.json`. Si la política cambia después (otra cúpula legible, otra zona libre), el contrato deja de ser vigente hasta que la persona lo vuelva a aprobar: nadie trabaja con reglas que no vio al decir «sí».

## Secretos fuera de los motivos y de la evidencia

Los rechazos de la puerta citan la orden. Antes de mostrarlos o guardarlos, se sustituye por `***` todo lo que parezca un secreto: tokens de GitHub, OpenAI o AWS, credenciales en una URL y valores de `password=`, `token=`, `--token` y similares.

## Buscar dentro de las carpetas es leer

`grep -r` es una lectura. Sin contrato se permite en las carpetas conocidas (el repo de Yema, su estado, las declaradas en la configuración local o en `YEMA_CARPETAS`), y con contrato dentro de su ámbito. En los dos casos, solo si lo que recorre no abarca el estado privado ni nada vetado. Una búsqueda en una carpeta desconocida sigue denegada.

## Aprobar con `!` no vale

Lanzar `yema aprobar` con `!` desde Claude Code no tiene terminal ni pasa por el diálogo, así que la puerta no puede distinguir a una persona de la agente. Se aprueba en el diálogo («aprueba C-0002») o en una terminal propia.

