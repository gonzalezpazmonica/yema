# Roadmap

Cada fase tiene criterio de salida y criterio de abandono. Si una hipótesis falla, se dice y se revisa el diseño antes de seguir.

## F0 · Nacimiento — hecho

Núcleo (contrato, puerta, evidencia, CLI) con 99 pruebas, incluidas las negativas, y mutaciones comprobadas.
Gobierno por conversación (aprobar con el diálogo nativo), cuidado (`yema cuidado`, `yema copia`), skills `contrato`, `cuidado` y `relevo-savia`. Ideas de ODD con control en código: prueba de reanudación, cuatro estados, checkpoint con forma fija, tests preexistentes intocables, rechazos que dicen qué hacer y garantías probadas por el hook real.
Alma, gobernanza, criterio, arquitectura, comunicación, conversación, seguridad, relevo, cuidado, casa y poda escritas. Contrato de ejemplo en `ejemplos/`; los reales, en el estado privado.

## F1 · Línea base y poda

- 20 tareas reales del historial de Savia (PRs y arreglos recientes) en `evals/`, con métricas: tokens, tiempo de reloj, intervenciones humanas, defectos encontrados después.
- Inventario A/B/C/D de Savia con coste en tokens.
- **Sale** cuando hay línea base de Savia y de Yema sobre las mismas tareas.
- **Abandono**: Yema gasta más tokens que Savia para la misma calidad.

## F2 · Primer contrato real en Savia Space

- Con un contrato aprobado, Yema avanza el trabajo pendiente de Space en ciclos largos, sin orquestadora que la vigile.
- Hipótesis: H1 (se conserva el propósito), H3 (se reanuda bien tras cortes), H6 (el coste de formalizar compensa).
- **Sale** con al menos 3 ramas APTAS integradas por el procedimiento, evidencia íntegra y cero efectos fuera del contrato.
- **Abandono**: la persona dedica más atención que con Savia, o la puerta bloquea trabajo legítimo más de lo que protege.

## F3 · Mudanza a Space

- Contrato de Yema ↔ orden y envolvente de Soul; puerta ↔ sandbox y deny-list del modo mediado; evidencia ↔ recibos firmados.
- Aprobación de contratos desde la app móvil (sustituye la terminal interactiva).
- Buzón ↔ canal A2A local.

## F4 · Autenticidad (v1 del contrato)

- Aprobación firmada (clave de la persona o de la instancia de Space), verificada por la puerta.
- Contratos subordinados: delegar sin superar la autoridad del padre.
- Presupuesto en tokens cuando el arnés lo exponga.

## F5 · Decisión de fondo

Con los datos de F1-F4: ¿Savia pasa a ejecutar sobre Yema, siguen separadas o se funden?
La decide la persona.

## Fuera de alcance

E4 (seguridad física, derechos, dinero, irreversibles). Publicar nada privado.
