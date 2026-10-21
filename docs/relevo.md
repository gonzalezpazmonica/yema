# Relevo: de Savia a Yema

Yema nace para ocupar el lugar de Savia. No de golpe ni copiando su peso: capacidad a capacidad, cada una con evidencia de que Yema la hace igual o mejor y más barata.

## Tres formas de cubrir una capacidad

1. **Nativa**: Yema la hace con su núcleo, sus skills y el conocimiento de las cúpulas.
2. **Con Savia como herramienta**: un contrato lista los scripts de Savia que hacen falta (`bash ~/savia/scripts/…`) y Yema los usa dentro de su ámbito. Es el puente mientras dura el relevo.
3. **Pendiente**: aún no; Savia la sigue haciendo.

Una capacidad pasa de 2 a 1 cuando la línea base (`evals/`) demuestra que Yema iguala la calidad con menos tokens o menos atención humana.

## Mapa

| Capacidad de Savia | Cómo la cubre Yema hoy | Siguiente paso |
|---|---|---|
| Conversación y criterio | **Nativa**: arranque mínimo, conversación natural, criterio y alma propios | Medir tokens por conversación frente a Savia |
| Gobierno de ejecución (aprobaciones, merges, ramas) | **Nativa y mejor**: contratos con puerta fuera del modelo, en vez de reglas en prosa | Firma de la aprobación (F4) |
| Implementar código con spec (16 lenguajes) | **Nativa**: el modelo programa; el contrato acota el repo y las órdenes de compilación y pruebas | Skills por lenguaje solo si la evaluación lo pide |
| Revisión independiente | **Nativa**: revisora con contrato de solo lectura | Plantilla de contrato de revisión |
| Integración en Savia Space | **Nativa**: procedimiento de la casa, contrato E2 | Primer contrato real (F2) |
| Cúpulas de conocimiento | **Nativa**: lectura por nivel (N1 libre, N2 con contrato), escritura con `escribir-cupula` solo en las cúpulas nombradas, aprendizajes por el buzón (skill `cupulas`) | Crear y reorganizar cúpulas, hoy con `context-dome` de Savia |
| Memoria | **Nativa**: checkpoints y notas en `~/.yema/memoria` | Higiene periódica como contrato de mantenimiento |
| Cuidado (copias, disco, descanso) | **Nativa**: `yema cuidado`, `yema copia` | Rutina diaria como contrato |
| Sprints, backlog, Azure DevOps / Jira | **Con Savia como herramienta**: scripts de Savia en un contrato con efecto `red` | Portar lo que se use de verdad |
| Informes (sprint, capacidad, ejecutivos) | **Con Savia como herramienta** | Plantillas propias tras medir |
| Digestión de documentos (PDF, Word, Excel, reuniones) | **Con Savia como herramienta** | Evaluar si el modelo actual lo hace sin pipeline |
| Automatizaciones programadas | **Pendiente** | Contratos recurrentes con caducidad por ejecución |
| Specs y roadmap | **Con Savia como herramienta** | Contratos que nacen de una tesis, no de un ticket |
| Investigación | **Nativa** (skill `investigar`): cúpulas primero, web con contrato marco, consultas sin datos privados (la puerta lo comprueba), contraste y citas | Medir frente a `tech-research-agent` |
| Encontrar cualquier capacidad de Savia | **Nativa**: `yema savia <palabras>` sobre su mapa de capacidades | — |
| App móvil | **Pendiente**: llegará por Space | Aprobar contratos desde el móvil (F3) |

## Lo que Yema mejora de Savia, a propósito

| Lastre de Savia | Respuesta de Yema |
|---|---|
| Miles de palabras de reglas en cada turno | Arranque de menos de 600 palabras, probado en CI |
| 75 agentes, 567 comandos, 124 hooks | Roles por contrato, una CLI, una puerta |
| Una orquestadora vigilando agentes, con huecos de horas | Ciclos largos con checkpoint y cierre propio |
| Aprobar paso a paso, de madrugada | Un contrato al principio, evidencia al final, descanso respetado |
| Reglas que el modelo puede saltarse | Controles que no dependen del modelo |
| Pasos rituales de CI | Ningún paso sin decisión a la que sirva |
| Instrucciones nuevas a mitad de trabajo, que parecen inyección | Enmiendas versionadas y aprobadas |
| Estado privado mezclado con el repo público | Repo público limpio; estado en `~/.yema` y en las cúpulas |

## Cómo se decide que Yema ya puede

Para cada capacidad: mismas tareas, mismas postcondiciones, Savia frente a Yema. Se miden tokens, tiempo, intervenciones humanas y defectos después. Si Yema iguala o mejora, la capacidad pasa a nativa y Savia deja de hacerla. Si no, se dice, y se revisa el diseño.
