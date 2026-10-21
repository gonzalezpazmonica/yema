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
