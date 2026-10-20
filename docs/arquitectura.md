# Arquitectura

## Idea central

Savia gobierna con instrucciones en prosa para el modelo. Yema gobierna con **controles fuera del modelo** y deja al modelo pensar.
Cada regla de Savia que Yema necesite acaba en uno de cuatro sitios: un control del núcleo, una cláusula de contrato, conocimiento en una cúpula, o la papelera.

## Código y estado

El repo es público y solo lleva código, documentos y ejemplos. El estado es privado y local: `~/.yema/` (`contratos/`, `evidencia/`, `memoria/`, `buzon/`, `casa/`), configurable con `estado` en `gobierno/politica.json` o `YEMA_ESTADO`. Lo privado que deba compartirse va a las cúpulas.

## Piezas

```
             persona ── aprueba contratos (yema.py) ── revisa evidencia
                │
   ┌────────────▼─────────────┐
   │ ~/.yema/contratos (registro)│ JSON versionado, huella sellada, ciclo de vida
   ├───────────────────────────┤
   │ nucleo/contrato.py        │  validador + máquina de estados + vigencia
   │ nucleo/puerta.py          │  efecto ← herramienta; decide; presupuesto; recibo
   │ nucleo/evidencia.py       │  JSONL encadenado por hash
   │ nucleo/yema.py            │  CLI humana
   └────────────┬──────────────┘
                │ hook PreToolUse
   ┌────────────▼──────────────┐      ┌──────────────────────┐
   │ arnés (Claude Code hoy,   │◄────►│ cúpulas (MCP)         │ solo lectura por nombre
   │  Space mediado mañana)    │      └──────────────────────┘
   └────────────┬──────────────┘      ┌──────────────────────┐
                └────────────────────►│ buzón ↔ Savia         │ datos, nunca órdenes
                                      └──────────────────────┘
```

Las cinco responsabilidades de un contrato ejecutable (registro, validador, compilador, adaptador de ejecución, colector de evidencia) están aquí en cuatro ficheros. El «compilador» es la puerta: traduce cláusulas no ambiguas a decisiones. Lo ambiguo no se interpreta: se rechaza.

## Presupuesto de contexto (el primer objetivo de la poda)

| Concepto | Savia hoy | Yema v0 | Límite |
|---|---|---|---|
| Arranque por turno | ~3 200 palabras de reglas + índice de memoria | `AGENTS.md` (~350 palabras) | 600 palabras, comprobado en CI |
| Agentes definidos | 75 | 0 (roles por contrato) | — |
| Comandos | 567 | 1 CLI humana | — |
| Hooks | 124 | 1 puerta | — |

Todo lo demás se lee bajo demanda o vive en las cúpulas.

## Ciclos largos

Un contrato es la unidad de trabajo, no el turno ni la tarea. Durante un ciclo:

1. **Plan** contra las postcondiciones (`condiciones.post`).
2. **Avance** dentro del ámbito; la puerta corta lo que no toca, sin preguntar a nadie.
3. **Checkpoint** en `~/.yema/memoria/<contrato>.md`: hecho, pendiente, siguiente paso, hipótesis abiertas. Así un ciclo interrumpido se reanuda sin la conversación.
4. **Frontera**: presupuesto, 3 fallos seguidos, descubrimiento que exige más autoridad → paro y escribo una propuesta de enmienda en `~/.yema/contratos/borradores/`.
5. **Cierre**: ejecuto las postcondiciones y paso a `validando`. La persona cierra.

Lo que Savia hacía con vigilantes, marcas de fin y despertares lo sustituyen el contrato (qué y hasta dónde), el checkpoint (dónde voy) y la evidencia (qué pasó).

## Roles, no catálogo de agentes

- **Ejecutora**: Yema bajo un contrato.
- **Revisora independiente**: otra instancia con otro contexto (y, si se puede, otro modelo), con contrato de solo lectura. Sus veredictos son evidencia, no autoridad.
- La especialización (Rust, seguridad, UX) viene del contexto que carga el contrato, no de un fichero de agente.

## Arneses

- **Hoy**: Claude Code con `.claude/settings.json` (hook) y `.mcp.json` (cúpulas). Es un adaptador, no el núcleo.
- **Casa**: Savia Space en modo mediado. Space ya tiene sandbox de sistema operativo, deny-list propia, presupuestos de run, recibos JCS firmados, decisiones registradas y aprobación desde el móvil. Yema se apoya en eso en vez de duplicarlo (ver `docs/casa-space.md`).
- El núcleo es Python de biblioteca estándar, sin dependencias ni proveedor: cualquier arnés que entregue un evento `tool_name`/`tool_input`/`cwd` puede usarlo.
