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
- **Gobierno por conversación**: `yema aprobar` pide la decisión al diálogo nativo del arnés (que el modelo no puede pulsar), con ticket de un solo uso; se deniega solo en `bypassPermissions` y `dontAsk`.
- **Aprobación firmada (F4)**: la aprobación se firma con HMAC y un secreto local que la agente no puede leer ni escribir; la puerta solo da por vigente un contrato con firma válida.
- **Presupuesto de tiempo**: `recursos.minutos_max`; pasado ese tiempo, se deniegan los efectos materiales.
- **La aprobación fija la política**: si `politica.json` cambia después de aprobar, el contrato deja de valer hasta volver a aprobarlo.
- **Borrar es un efecto aparte**: `rm`, `git rm`, `git clean` y similares exigen `borrar`; conceder escribir ya no basta.
- **Órdenes desde otra carpeta**: `cd <raíz del contrato> && <orden>` funciona desde una sesión abierta en el repo de Yema; el arranque lo indica.
- **Menos fricción sin abrir huecos**:
  - lecturas con comillas;
  - `grep -r` dentro del ámbito;
  - orden concedida con filtros de lectura (`| head`, `| grep`…);
  - heredoc citado para un intérprete concedido.
- **Estado visible coherente con la puerta**: nunca dice «Trabajando» con un contrato que la puerta rechaza.
- **`bin/yema-sesion`**: abre Claude Code solo con los MCP de Yema y con las herramientas bajo demanda (−17 % de tokens al arrancar).
- **El contrato es el permiso**: lo concedido no se vuelve a preguntar paso a paso; las lecturas validadas en carpetas conocidas tampoco.
- **Ejecución aislada** (`yema prueba`): copia desechable en un sandbox bwrap de root, sin red ni hogar, con tiempo y tamaño limitados y parche opcional.
- **Cuidado**: `yema cuidado` (permisos, copias, disco, descanso) y `yema copia`.
- **Arranque**: contexto de sesión con estado, rutas y herramientas disponibles; `AGENTS.md` de menos de 600 palabras, comprobado en CI.
- **Instalación**: `yema instalar` (estado privado, ajustes locales, CLI en el PATH).

### Conocimiento e investigación
- **Cúpulas por nivel**: sin contrato solo se leen las cúpulas públicas de la política; las N2, con un contrato que las nombre; escribir, solo en las cúpulas nombradas.
- **Alarma de nivel**: una cúpula N3/N4, o una nota que declare N3 o más, no se lee aunque la cúpula esté permitida.
- **Investigación** (skill `investigar`): primero cúpulas y ficheros; la web, con un contrato marco. La puerta rechaza consultas con correos, IP o términos de la lista privada.
- **Relevo de Savia**: `yema savia <palabras>` encuentra cualquier capacidad de Savia en su mapa, para usarla como herramienta dentro de un contrato.

### Seguridad
- Los motivos de la puerta y la evidencia sustituyen los secretos por `***`.
- Un heredoc con la marca de cierre escondida en el cuerpo se rechaza.
- Un comodín en un lector (`cat ~/.s*/id_*`) se juzga por lo que abriría, y Grep no puede abarcar una carpeta con algo vetado.

### Ideas adoptadas de ODD (Gentleman Programming), con control en código
Prueba de reanudación, cuatro estados visibles, checkpoint con forma fija, tests preexistentes intocables, rechazos que dicen qué hacer y garantías probadas a través del hook real.

### Calidad
222 pruebas, incluidas garantías negativas, mutaciones comprobadas y aislamiento real en CI. Evaluación a ciegas frente a Savia en `docs/evaluacion.md`, incluida una ronda que no valió (E8) y la línea base sobre 20 tareas reales (E9). `evals/` incluye el juicio ciego y las huellas de método.
