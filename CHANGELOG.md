# Cambios

## 0.1.0 · 2026-10-21 · Primera release pública

Yema nace: una compañera de trabajo con IA que hace trabajo largo dentro de contratos que aprueba una persona, con una puerta fuera del modelo que hace cumplir sus límites.

### Núcleo
- **Aprobar desde el harness también en modo auto**: los diálogos que fuerza la puerta aparecen en el modo de serie de Claude Code; solo `bypassPermissions` y `dontAsk` deniegan.
- **Entregable comprobado**: cada postcondición lleva una orden o un `comprobar`.
- **Lecciones con evidencia**: `yema aprende` y el validador del buzón rechazan un aprendizaje sin cuándo, lección, evidencia y confianza.
- **Juicio ciego reutilizable**: `evals/ciego.py`.
- **Contratos**: esquema, huella sellada al aprobar, ciclo de vida (borrador → … → cerrado; suspendido, revocado, caducado), vigencia, requisitos con citas literales y petición original.
- **Puerta** (hook `PreToolUse`): sin contrato, solo lectura y zonas libres; con contrato, ámbito, efectos, órdenes exactas, presupuesto y caducidad. Falla cerrado. Cada rechazo dice qué hacer.
- **Evidencia** encadenada por hash.
- **Gobierno por conversación**: `yema aprobar` pide la decisión al diálogo nativo del arnés (que el modelo no puede pulsar), con ticket de un solo uso; se deniega en modos sin preguntas.
- **El contrato es el permiso**: lo concedido no se vuelve a preguntar paso a paso; las lecturas validadas en carpetas conocidas tampoco.
- **Ejecución aislada** (`yema prueba`): copia desechable en un sandbox bwrap de root, sin red ni hogar, con tiempo y tamaño limitados y parche opcional.
- **Cuidado**: `yema cuidado` (permisos, copias, disco, descanso) y `yema copia`.
- **Arranque**: contexto de sesión con estado, rutas y herramientas disponibles; `AGENTS.md` de menos de 600 palabras, comprobado en CI.
- **Instalación**: `yema instalar` (estado privado, ajustes locales, CLI en el PATH).

### Ideas adoptadas de ODD (Gentleman Programming), con control en código
Prueba de reanudación, cuatro estados visibles, checkpoint con forma fija, tests preexistentes intocables, rechazos que dicen qué hacer y garantías probadas a través del hook real.

### Calidad
123 pruebas, incluidas garantías negativas, mutaciones comprobadas y aislamiento real en CI. Evaluación frente a Savia en `docs/evaluacion.md`.
