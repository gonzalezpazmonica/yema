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
Opcionales: `contexto` (cúpulas permitidas, fuentes), `spec`, `condiciones` (`pre`, `invariantes`, `post`).

- `ambito.raiz`: directorio absoluto donde se trabaja. `ambito.escritura` / `ambito.vetadas`: globs relativos.
- `autoridad.efectos` / `autoridad.prohibidos`: de `leer, escribir, ejecutar, red, git-local, git-remoto, fusionar, publicar, delegar, escribir-cupula`.
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
- Aprobar y activar exige terminal interactiva (`nucleo/yema.py`). Es una barrera débil; la v1 la sustituye por firma (ver ROADMAP).

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
- La terminal interactiva no prueba que sea una persona. La firma llega en la v1.
- El presupuesto cuenta efectos, no tokens: el arnés no expone el consumo al hook.
