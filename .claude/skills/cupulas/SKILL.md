---
name: cupulas
description: Consultar, citar y alimentar las cúpulas de conocimiento (SaviaVaults) respetando su nivel de confidencialidad. Úsala cuando la pregunta se responda con conocimiento guardado, cuando haya que dejar un aprendizaje, o cuando la persona pida crear o reorganizar una cúpula.
---

# Cúpulas

## Niveles y quién puede leer qué

Yema razona con un modelo en la nube: lo que lee sale de la máquina.
- **N1** (público de referencia): lo puede leer sin contrato si está en `cupulas_lectura` de la política (por defecto `SaviaDomains`).
- **N2**: solo con un contrato que la nombre en `contexto.cupulas`. La aprobación de la persona es la confirmación y la evidencia, el recibo.
- **N3 y N4**: nunca.

## Consultar

1. Indica siempre la cúpula: `vault_search {"vault": "<nombre>", "query": "…"}`. Sin cúpula, la puerta lo rechaza (el servidor asumiría N2).
2. Lee la nota completa con `vault_read {"vault": "…", "path": "…"}` antes de citarla; un fragmento de búsqueda no basta.
3. Cita así: `[cúpula:ruta]`. Si dos notas se contradicen, dilo y cita las dos.
4. Si la cúpula no tiene la respuesta, dilo y pasa a memoria, código o ficheros. No rellenes con lo que «suele ser».

## Alimentar (dejar conocimiento)

- **Lo normal**: un mensaje `aprendizaje` en `~/.yema/buzon/salida/`. Savia lo digiere en su cúpula. No hace falta contrato.
- **Escribir directamente**: contrato con el efecto `escribir-cupula` y la cúpula en `contexto.cupulas`. La puerta solo deja escribir en las cúpulas nombradas. Nada privado en una cúpula N1.

## Crear o reorganizar una cúpula

Es trabajo de Savia (su skill `context-dome`). Búscala con `yema savia cupula` y úsala con la skill `relevo-savia`, dentro de un contrato cuyo ámbito sea la carpeta de cúpulas. El registro de cúpulas es local y no se versiona (`savia-vaults.domes.json`).
