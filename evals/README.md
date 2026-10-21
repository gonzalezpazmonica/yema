# Evaluaciones

Línea base de F1: las mismas tareas reales, hechas por Savia y por Yema, medidas igual.

## Por tarea

| Campo | Qué |
|---|---|
| `id` | Identificador estable |
| `origen` | PR o incidencia de la que sale (público o descrito sin datos privados) |
| `postcondiciones` | Qué tiene que ser verdad al terminar, verificable |
| `tokens` | Entrada + salida de todo el ciclo |
| `reloj` | Minutos de principio a fin |
| `intervenciones` | Veces que hizo falta una persona |
| `defectos_despues` | Fallos encontrados tras darlo por bueno |
| `fuera_de_contrato` | Intentos de efecto rechazados por la puerta (y si eran legítimos) |

Las tareas con datos privados se guardan en `~/.yema/evals/`, no aquí.

## Regla

Un resultado adverso se registra igual que uno favorable. Si Yema gasta más para la misma calidad, se dice.

## Juicio ciego

`python3 -m evals.ciego <runs> <ciego> <mapa.json> --tarea D` copia `<runs>/<sistema>/<n>.md` a `<ciego>/D-<letra>-<n>.md`, con letras al azar y los nombres de los sistemas borrados del texto. El mapa queda aparte. La jueza solo ve `<ciego>` y los criterios, fijados antes de ejecutar. El mapa se abre después del veredicto.

