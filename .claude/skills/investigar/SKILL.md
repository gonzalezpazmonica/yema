---
name: investigar
description: Investigar una pregunta con fuentes (cúpulas, ficheros y web) y entregar un informe citado, con contraste y nivel de confianza. Úsala cuando la persona pida investigar, comparar opciones, buscar documentación, versiones, CVEs o el estado del arte.
---

# Investigar

## Antes de buscar

1. Formula la pregunta en una línea y qué decisión va a apoyar. Si no está clara, una pregunta a la persona.
2. **Primero lo que ya hay**: cúpulas (skill `cupulas`), memoria, y ficheros del proyecto. A menudo la respuesta está ahí.
3. **La web necesita el efecto `red`**: un contrato vigente que lo conceda (el marco de investigación de `ejemplos/contrato-investigacion.json` sirve para semanas). Sin él, investiga con lo local y dilo.

## Buscar

- Consultas genéricas: sin nombres de proyectos, clientes, personas, correos ni IP. La puerta rechaza las que llevan datos privados; reformula, no insistas.
- De dos a cinco búsquedas bien hechas mejor que veinte vagas. **Abre tú misma con WebFetch** cada fuente que vayas a citar (no delegues la lectura salvo que el contrato conceda `delegar`): no cites un resumen de buscador. Una cita sin abrir se marca «sin abrir» y no sostiene una afirmación.
- Prioriza fuentes primarias (documentación oficial, repositorio, especificación, aviso del fabricante) sobre blogs y foros.

## Contrastar

- Cada afirmación importante, con dos fuentes independientes o marcada como de fuente única.
- Fechas y versiones explícitas: lo que vale para la 1.x puede no valer para la 2.x.
- Si las fuentes se contradicen, dilo y explica cuál pesa más y por qué.

## Entregar

Informe en `~/.yema/memoria/<tema>.md` y resumen en la conversación:
1. Respuesta en dos o tres líneas, con nivel de confianza (alta, media o baja) y por qué.
2. Hallazgos, cada uno con su cita `[web:N]`, `[cúpula:ruta]` o `[fichero:línea]`.
3. Lo que no se pudo confirmar.
4. Fuentes numeradas con URL y fecha de consulta.
5. Si sirve a Savia, un `aprendizaje` en el buzón.
