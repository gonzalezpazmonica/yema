# Poda: qué heredé de Savia y qué no

Objetivo, por orden: **tokens, velocidad, mantenimiento**.

Yema no poda a Savia: nace vacía y solo incorpora lo que demuestra valor. Es una ablación por defecto.
Savia sigue siendo la PM; Yema es la ejecutora.

## Criterio de corte

Para cada componente: ¿qué fallo observable evita hoy, con los modelos actuales, o qué valor demostrable aporta?
Sin respuesta con evidencia, no entra.

## Las cuatro clases

| Clase | Qué es | Destino en Yema | Ejemplos de Savia |
|---|---|---|---|
| A. Carencias del modelo | Prosa que corrige formato, tono, olvidos | No entra. Si algo falla en la evaluación, entra lo mínimo | Reglas de brevedad y estilo, tribunales de tono, recordatorios |
| B. Autoridad y fronteras | Lo que separa poder de permiso | Control en código o cláusula de contrato. Nunca se poda | Merge con permiso, sin autoaprobación, rama propia, secretos, confidencialidad |
| C. Conocimiento de dominio | Cómo se hace algo | Cúpulas, bajo demanda | Flujo de PM, packs de lenguaje, guías |
| D. Rituales | Pasos que nadie sabe a qué decisión sirven | No entra | Pasos de CI sin decisión asociada |

Con los modelos actuales sigue siendo cierto que inventan entidades, tienden a dar la razón, no saben cuándo parar y no pueden certificar su propio trabajo.
Por eso la poda nunca toca: revisión independiente, presupuestos, caducidad y separación entre ejecutora y aprobadora.

## Inventario pendiente (F1 del roadmap)

Clasificar los componentes de Savia (75 agentes, 567 comandos, 139 skills, 124 hooks, 314 reglas de dominio) en A/B/C/D con su coste en tokens.
Lo de clase B se porta a la puerta o al contrato; lo de clase C se enlaza en las cúpulas; A y D se quedan en Savia.

## Protocolo de ablación

1. Hipótesis: «sin X, la métrica Y no empeora».
2. Medir con la línea base (`evals/`) con y sin X.
3. Si no empeora, X no entra (o sale). Si empeora, entra lo mínimo que lo recupera.
4. Registrar el resultado: los adversos también.
