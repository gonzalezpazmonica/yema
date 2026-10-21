# Yema

**Yema es una compañera de trabajo con IA que hace trabajo largo y real —código, integraciones, informes, mantenimiento— dentro de contratos que aprueba una persona.**
Hablas con ella con naturalidad. Ella entiende qué quieres, te propone un contrato en lenguaje llano, lo apruebas con un «sí» y trabaja horas sin que tengas que vigilarla, con límites que no dependen de su buena voluntad.

Es hija de [Savia](https://github.com/gonzalezpazmonica/savia), la PM con IA, y nace para tomar su relevo: hacer lo mismo con menos tokens, menos ruido y más autonomía, sin perder nunca de vista quién decide.

> Una especificación dice qué se espera. Un contrato dice qué está autorizado a ocurrir, por quién, con qué límites y hasta cuándo.

---

## Por qué Yema

Los arneses de agentes crecen añadiendo reglas en prosa: «no hagas esto», «recuerda aquello», «pregunta antes de…». Funciona un tiempo y después pesa: miles de palabras en cada turno, cientos de comandos que nadie recuerda, una orquestadora que vigila agentes paso a paso, y una persona que aprueba diffs de madrugada.

Yema cambia cinco cosas:

| Donde el arnés clásico… | Yema… |
|---|---|
| Gobierna con instrucciones al modelo | Gobierna con una **puerta fuera del modelo** que decide cada efecto según el contrato |
| Pide permiso paso a paso | Pide **un contrato** al principio y trabaja horas dentro de él |
| Te hace revisar cada diff | Te trae **evidencia** al final y te deja muestrear |
| Carga todo su reglamento en cada turno | Arranca con **menos de 600 palabras** y lee el resto bajo demanda |
| Confía en que el agente pare | **Caduca**, tiene **presupuesto** y se puede **revocar** en cualquier momento |

El modelo puede pensar con toda libertad. Lo que no puede es actuar fuera de lo que una persona ha concedido.

---

## Cómo se habla con Yema

No hace falta aprender comandos. Se le habla como a una colega.

**Pedir trabajo**

> **Tú:** Yema, quiero que integres las ramas revisadas de Space y que mires por qué falla el test del enlace N2.
>
> **Yema:** Para eso necesito un contrato: escribir en el repo de Space, compilar y probar, y fusionar ramas `agent/*` en la principal local. Sin publicar ni tocar el remoto. Te lo dejo así:
>
> ```
> Contrato C-0002 v1 · nivel E2 · huella 3fa9c210
> Para qué: integrar ramas APTAS y buscar la causa raíz del flake N2
> Dónde: ~/savia-space
> Puede: leer, escribir, ejecutar, git-local, fusionar
> Órdenes: cargo test; cargo clippy; git merge --no-ff agent/*; …
> No puede: git-remoto, publicar
> Presupuesto: 300 efectos · Caduca: viernes 23:59
> Al cerrar demostrará: verificado, evidencia, informe
> ```
>
> ¿Lo apruebo?
>
> **Tú:** Sí.
>
> *(Aparece el diálogo de permisos del arnés con ese mismo resumen. Pulsas «Permitir».)*
>
> **Yema:** C-0002 activo. Empiezo. Te dejo los avances en la memoria y te aviso al cerrar.

**Preguntar cómo va**: «¿cómo vas?», «¿qué te falta?», «enséñame la evidencia».
**Cambiar el encargo**: «añade también el broker». Yema prepara una **enmienda** (versión nueva) y te la enseña; no amplía nada por su cuenta.
**Parar**: «para», «suspende», «revoca C-0002». Parar siempre está permitido y es inmediato.
**Cuidar**: «¿cómo está la casa?» → chequeo de permisos, copias, disco y descanso.

### Por qué el «sí» es seguro

Aprobar un contrato es la única puerta a la autonomía, así que no puede depender de lo que el modelo escriba. Cuando dices «sí», Yema lanza `yema aprobar C-0002 3fa9c210`. La puerta reconoce esa orden y, en lugar de dejarla pasar, **pide la decisión al arnés**, que te muestra su propio diálogo de permisos con el resumen del contrato. Ese diálogo lo contestas tú; el modelo no puede pulsarlo.

- La **huella** (`3fa9c210`) ata lo que ves a lo que se aprueba: si alguien cambia una coma del contrato, la huella deja de casar y la aprobación se rechaza.
- La puerta deja un **ticket de un solo uso** que caduca en 5 minutos; sin él, la CLI no aprueba nada fuera de una terminal humana.
- En modos sin preguntas (`bypassPermissions`, `dontAsk`, `auto`) la aprobación se **deniega**: no hay diálogo que contestar.

---

## Empezar

Requisitos: Python 3.10+ (sin dependencias), un arnés que ejecute hooks `PreToolUse` (hoy, Claude Code) y, para `yema prueba`, bubblewrap instalado por el sistema (`/usr/bin/bwrap`, de root).

```bash
git clone https://github.com/gonzalezpazmonica/yema.git && cd yema
bin/yema instalar                              # estado privado en ~/.yema, ajustes locales y CLI en ~/.local/bin
python3 -m unittest discover -s pruebas        # el núcleo se prueba a sí mismo
yema cuidado                                   # salud de la casa
claude                                         # y a hablar con ella
```

Al abrir el arnés en esta carpeta se cargan `AGENTS.md` (su arranque), la puerta (`.claude/settings.json`), sus skills (`.claude/skills/`) y las cúpulas de conocimiento (`.mcp.json`). Sin contrato activo, Yema lee, investiga, conversa y propone; no cambia nada.

---

## El contrato, para personas

Un contrato responde a seis preguntas:

1. **Para qué**: el propósito, en una frase que entienda cualquiera.
2. **Dónde**: el directorio en el que trabaja y qué rutas puede escribir.
3. **Qué puede hacer**: efectos (`leer`, `escribir`, `ejecutar`, `git-local`, `fusionar`, `red`, `git-remoto`, `publicar`, `delegar`…) y las órdenes exactas permitidas.
4. **Qué nunca**: efectos prohibidos y rutas vetadas.
5. **Hasta cuándo y cuánto**: caducidad obligatoria y presupuesto de efectos.
6. **Cómo sabremos que salió bien**: postcondiciones verificables y la evidencia que se entrega.

Niveles de riesgo:

| Nivel | Qué cubre | Quién decide |
|---|---|---|
| E0 | Pensar, leer, investigar | Nadie: es el modo por defecto |
| E1 | Borradores, notas, mensajes internos | Zonas libres; nada más |
| E2 | Cambios reversibles en rama local, pruebas | Tú, una vez, al aprobar el contrato |
| E3 | Remoto, publicación, terceros | Tú, por efecto |
| E4 | Dinero, derechos, irreversibles | Fuera del alcance de Yema |

Ejemplo completo: [`ejemplos/contrato-ejemplo.json`](ejemplos/contrato-ejemplo.json). Detalle: [`docs/gobernanza.md`](docs/gobernanza.md).

---

## La CLI de gobierno

Pensada para la persona; Yema la usa en la conversación y la puerta decide qué puede lanzar ella sola.

| Orden | Qué hace | ¿Yema sola? |
|---|---|---|
| `yema estado` | Trabajando, Comprobando, Lista o Necesita tu decisión | Sí |
| `yema checkpoint <id>` | Abre el documento de reanudación (requisitos, tareas, log) | Sí |
| `yema resumen <id>` | El contrato en lenguaje llano | Sí |
| `yema validar <ruta>` | Comprueba el esquema | Sí |
| `yema admitir <borrador>` | Pasa un borrador a candidato | Sí |
| `yema aprobar <id> <huella>` | Aprueba y activa | **No: diálogo de permisos o tu terminal** |
| `yema suspender / revocar <id>` | Para el trabajo | Sí (parar siempre se permite) |
| `yema evidencia <id>` | Verifica la cadena de recibos | Sí |
| `yema prueba <carpeta> [--parche f.diff] -- <orden>` | Ejecuta en una copia aislada (bwrap de root, sin red, sin hogar, con límites); el original no cambia | Sí |
| `yema cuidado` | Permisos, copias, disco, descanso | Sí |
| `yema copia` | Copia del estado privado (rota las viejas) | Sí |

---

## Qué garantiza y qué no

**Garantiza** (con pruebas en `pruebas/`, incluidas las negativas, y mutaciones comprobadas):

- Sin contrato vigente, solo lectura y zonas libres.
- Nada fuera del ámbito, de los efectos, de las órdenes o del presupuesto del contrato.
- Órdenes compuestas, redirecciones y sustituciones: rechazadas siempre. Push forzado, borrado o masivo: nunca.
- Yema no aprueba, no activa ni amplía sus contratos; no toca su núcleo, su gobierno, su identidad ni su evidencia.
- Lecturas vetadas por la política; cúpulas solo por nombre permitido.
- Evidencia encadenada por hash: cualquier manipulación se detecta.
- Los tests que ya existían no se cambian para que algo pase, salvo enmienda.
- Cada rechazo dice qué hacer.
- Ante cualquier error, la puerta bloquea.
- Las garantías se prueban a través del hook real, tal como está registrado.

**No garantiza** (y lo dice): una orden permitida puede hacer más de lo que su nombre sugiere (por eso la frontera fuerte es el sandbox del sistema operativo en Savia Space); la puerta solo ve lo que el arnés le enseña; el presupuesto cuenta efectos, no tokens. Detalle en [`docs/seguridad.md`](docs/seguridad.md).

---

## Cuidar de nosotras

Yema cuida de la persona y de la casa, no solo del trabajo:

- **Tu atención**: te trae decisiones agrupadas, con contexto llano y su recomendación; nada de diffs sueltos.
- **Tu descanso**: en horas de descanso solo pregunta lo urgente; el resto va al resumen de la mañana.
- **La casa**: copias diarias del estado privado, permisos, disco y memoria en orden (`yema cuidado`).
- **Savia**: vigila su salud y su memoria, y le devuelve lo aprendido por el buzón y las cúpulas.

Ver [`docs/cuidado.md`](docs/cuidado.md).

---

## Arquitectura en una imagen

```
 persona ── conversa ── Yema (modelo) ── propone contrato ── persona aprueba (diálogo nativo)
                           │
                           ▼ cada herramienta
                 ┌─────────────────────┐
                 │ puerta (hook)        │ contrato vigente · ámbito · órdenes · presupuesto
                 │ falla cerrado        │──► recibo encadenado (evidencia)
                 └─────────────────────┘
                           │
       repo de trabajo · cúpulas (MCP) · buzón con Savia · Savia Space (casa)
```

- **Repo público** (`/`): código, documentos, ejemplos.
- **Estado privado** (`~/.yema`): contratos reales, evidencia, memoria, buzón, casa. Nunca se versiona.
- **Núcleo**: Python estándar, sin dependencias ni proveedor. Cualquier arnés que entregue `{tool_name, tool_input, cwd}` puede usarlo.

Detalle en [`docs/arquitectura.md`](docs/arquitectura.md).

---

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/guia.md`](docs/guia.md) | Manual de uso: instalación, primer contrato, día a día, recuperación |
| [`docs/conversacion.md`](docs/conversacion.md) | Cómo habla Yema y cómo convierte peticiones en contratos |
| [`docs/gobernanza.md`](docs/gobernanza.md) | Niveles, contrato, ciclo de vida, garantías |
| [`docs/seguridad.md`](docs/seguridad.md) | Modelo de amenazas, límites y cómo informar de un fallo |
| [`docs/arquitectura.md`](docs/arquitectura.md) | Piezas, presupuesto de contexto, ciclos largos, arneses |
| [`docs/relevo.md`](docs/relevo.md) | Cómo toma el relevo de Savia, capacidad a capacidad |
| [`docs/cuidado.md`](docs/cuidado.md) | Cuidado de la persona, de la casa y de Savia |
| [`docs/criterio.md`](docs/criterio.md) | Cómo decide, cuándo para, lecciones heredadas |
| [`docs/capacidades.md`](docs/capacidades.md) | Qué sabe hacer hoy y qué nunca |
| [`docs/comunicacion.md`](docs/comunicacion.md) | Persona, Savia (buzón) y cúpulas |
| [`docs/casa-space.md`](docs/casa-space.md) | Savia Space, la casa |
| [`docs/poda.md`](docs/poda.md) | Qué heredó de Savia y con qué criterio |
| [`docs/evaluacion.md`](docs/evaluacion.md) | Evaluación a ciegas frente a Savia y lecciones |
| [`ALMA.md`](ALMA.md) | Nombre, linaje, valores, voz |
| [`ROADMAP.md`](ROADMAP.md) | Fases con criterios de salida y de abandono |

---

## Preguntas frecuentes

**¿Tengo que escribir JSON?** No. Yema redacta el contrato contigo y te lo enseña en lenguaje llano. El JSON es para la puerta.

**¿Y si me equivoco al aprobar?** `yema revocar <id>` (o «Yema, para») corta al instante. Lo hecho queda en la evidencia para deshacerlo.

**¿Puede Yema saltarse la puerta?** No por diseño ni en las pruebas que tenemos. Si encuentras una forma, es un fallo de seguridad: ver [`docs/seguridad.md`](docs/seguridad.md).

**¿Funciona sin Claude Code?** El núcleo sí; hace falta un arnés que pase cada herramienta por el hook. El destino es Savia Space.

**¿Sustituye ya a Savia?** Todavía no en todo. [`docs/relevo.md`](docs/relevo.md) dice qué cubre hoy, qué cubre usando a Savia como herramienta y qué falta.

---

## Resultados frente a Savia

En una evaluación a ciegas con tres tareas y el mismo modelo, Yema sacó 24 de 24 frente a 20,8 de Savia, con menos coste. En la tarea de código entregó 5 de 5 parches que pasan los tests, frente a 0 de 5, aunque tardó unos segundos más porque verifica. Detalle y límites en [`docs/evaluacion.md`](docs/evaluacion.md).

## Estado

Versión 0.1.0. F0 completa; F1 (línea base) con primeros resultados. Ver [`ROADMAP.md`](ROADMAP.md) y [`CHANGELOG.md`](CHANGELOG.md).

## Licencia

MIT. Ver [`LICENSE`](LICENSE).
