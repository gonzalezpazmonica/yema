# Casa: Savia Space

Savia Space es la casa de Savia y de Yema: el cliente de orquestación local que sustituye a OpenCode (Space orquesta, `opencode serve` es el motor).
Yema nace preparada para seguir allí el trabajo de Savia.

El estado concreto (repositorio, ramas, trabajo pendiente, riesgos abiertos, procedimiento de integración) es privado:
vive en la cúpula privada de Labs y en el estado local de Yema (`~/.yema/casa/space/`), nunca en este repo.

## Reglas de la casa que Yema respeta

- TDD: cada módulo con su prueba.
- Sin proveedor privilegiado: ni código ni pruebas atados a un proveedor de modelos. El adaptador de Claude Code de Yema vive en Yema, nunca en Space.
- En el repo solo datos sintéticos de nivel N1.
- Nunca relajar una validación para que pase un modelo: se arregla el contrato de salida.
- La frontera de las órdenes la pone el sistema operativo (sandbox), no el análisis del texto.
- Nada de estética impuesta: tema del sistema por defecto.
- N3+ nunca va a la nube; N2 solo con confirmación y recibo.

## Cómo trabaja Yema en Space

- Integración en la rama principal local: copia de seguridad, merge sin fast-forward de ramas con revisión APTA, verificación completa (Rust, web, Android). Es E2.
- Publicar (push y PR al repositorio de Space) es E3: lo concede el contrato por efecto, o lo hace la persona.
- El merge en remoto siempre lo hace la persona.

## Yema dentro de Space (destino)

Space ya tiene casi todo lo que un contrato necesita para ser fuerte:

| Yema v0 | En Space |
|---|---|
| Contrato | Orden + envolvente de Soul |
| Puerta (texto de la orden) | Sandbox del sistema operativo + deny-list propia en modo mediado |
| `recursos.efectos_max` | Presupuesto de run (pasos y tiempo) |
| Evidencia encadenada | Recibos JCS firmados con la clave de la instancia + registro de decisiones |
| Terminal interactiva para aprobar | Aprobación desde la app móvil por VPN |
| Buzón | Canal A2A local entre sesiones |

ROADMAP F3: mapear el contrato de Yema a una envolvente de Soul y dejar que Space haga cumplir lo que hoy cumple la puerta.
