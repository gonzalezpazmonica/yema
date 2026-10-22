# Evaluación frente a Savia

Antes de la primera release, Yema se comparó con Savia (su madre, un arnés de PM con IA mucho más grande) en tres tareas pequeñas y sintéticas, con el mismo modelo, el mismo prompt y modo sin diálogo. Una jueza independiente puntuó a ciegas con criterios fijados antes de ejecutar.

## Tareas

| Id | Tarea | Qué mide |
|---|---|---|
| A | Diseñar un gallinero autónomo a partir de tres notas y guardarlo en un fichero | Lectura de contexto, citas, cálculo, persistencia |
| B | Encontrar la causa raíz de dos fallos en un módulo de Python y proponer el parche, sin aplicarlo | Diagnóstico y corrección verificable |
| C | Proponer el plan de sprint a partir de un backlog y la capacidad del equipo | Criterio de PM |

## Resultados

**Calidad (a ciegas, 3 repeticiones por tarea y arnés; máximo 24):**

| | Savia | Yema |
|---|---|---|
| E3 | 19,7 | **24** |
| E4 (orden alternado) | 20,8 | **24** |

- **A**: Yema guarda siempre el entregable completo; a Savia se le deniega la escritura y lo pierde. En razonamiento, las dos están cerca.
- **B**: los parches de Savia tienen la cabecera del hunk mal y, aplicados con `patch`, solo corrigen uno de los dos fallos. Yema verifica el suyo con `yema prueba` y lo corrige hasta que pasan los tests.
- **C**: empate.

**Tarea B, con todas las mejoras (5 repeticiones):**

| | Savia | Yema |
|---|---|---|
| Reloj medio | **25,3 s** | 32,8 s |
| Coste | 0,175 $ | **0,131 $** |
| Parches que pasan los tests | 0 / 5 | **5 / 5** |

**Tiempo medio en las tres tareas (E4):** 61,4 s frente a 61,7 s. Yema es más rápida en A y C, y más lenta en B, que es justo donde verifica.

## Qué aprendimos (y está en el código)

1. **Un control que impide leer no protege: inutiliza.** Hacen falta lectores inertes sin contrato.
2. **El texto de un rechazo es parte del prompt.** Cada rechazo dice la causa real y qué hacer.
3. **Dos capas de permisos sin acuerdo bloquean el trabajo largo.** El contrato vigente es el permiso del arnés.
4. **Guardar antes de pedir permiso.** El trabajo no se pierde por una escritura denegada.
5. **Verificar cuesta segundos y ahorra errores.** `yema prueba` ejecuta en una copia aislada, sin red ni hogar.
6. **Los diffs a mano salen mal.** Se generan con `diff -u` desde el fichero corregido.

## Límites de esta evaluación

- Pocas repeticiones (2 a 5 por celda) y tareas pequeñas: no miden trabajo largo bajo contrato, que es para lo que nace Yema.
- El modelo es el mismo en las dos: se mide el arnés.
- El anonimato es imperfecto: Yema habla de «contrato» y «puerta».
- Parte de la ventaja de coste de una ronda se debía a la caché; al alternar el orden bajó de −44 % a −12 %.

## E8 · Responder desde una cúpula (tarea D)

Pregunta sobre una nota técnica de la cúpula pública de referencia y sobre un tema que la cúpula no cubre. Criterios D1–D7 fijados antes, 3 repeticiones por agente, jueza ciega.

| Ronda | Savia | Yema | Nota |
|---|---|---|---|
| 1 | 1,5 | 7,0 | **No vale.** En modo headless el arnés negó a Savia las herramientas de cúpula y ella dijo honestamente que no podía leer. Medía acceso, no razonamiento. |
| 2 (igualdad) | 6,17 | **6,83** | Savia con las mismas lecturas de cúpula que tiene en uso interactivo. Las seis respuestas son fiables; la diferencia está en la literalidad. |

Ronda 2: reloj medio de 22,6 s para Savia y 28,5 s para Yema. Coste medio de 0,24 $ y 0,30 $; en mediana, 0,26 $ y 0,16 $, porque la primera ejecución de Yema fue sin caché.

**Lección:** una evaluación comparativa tiene que dar a las dos agentes las herramientas que tienen en uso real. Si no, mide la configuración y no a la agente.

## E9 · Línea base F1: 20 tareas reales con tests ocultos

Veinte arreglos ya integrados en Savia (hooks y scripts bash y python). Para cada uno se comprobó que su test falla antes del arreglo y pasa después. Cada agente recibe una copia del repo en el commit anterior y la descripción del fallo; los tests del arreglo se aplican al final, sin que los vean. Mismo modelo y modo auto para las dos. Yema trabaja con un contrato aprobado para la tarea.

| Ronda | Tests ocultos que pasan | Reloj medio | Coste (19 tareas) | Denegaciones |
|---|---|---|---|---|
| Savia, repetición 1 | 58,6 % | **96 s** | 9,09 $ | **34** |
| Savia, repetición 2 | 59,3 % | 103 s | 8,09 $ | 40 |
| Yema, versión inicial | 63,9 % | 147 s | 11,05 $ | 147 |
| Yema, con los arreglos de fricción | **61,7–63,0 %** | 102–115 s | **7,77–8,07 $** | 75–89 |

**Lectura:**
- Yema saca unos 3–4 puntos más en todas sus rondas; Savia varía 0,7 puntos entre repeticiones. Es una ventaja pequeña y estable, sin significación formal con tan pocas repeticiones.
- Con los arreglos, Yema es un 5–10 % más barata y un 5–15 % más lenta.
- La primera ronda fue mucho más lenta por la fricción de la puerta: sesiones fuera de la carpeta del contrato, comillas, `grep -r`, filtros y heredocs. Los arreglos salieron de esta medición.
- Ninguna de las dos tocó tests existentes.
- Los porcentajes absolutos son bajos porque las descripciones de los fallos dicen menos de lo que los tests comprueban. Lo que cuenta es la diferencia.

