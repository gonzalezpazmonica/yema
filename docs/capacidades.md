# Capacidades

Capacidad no es autoridad: esto es lo que Yema sabe hacer; lo que puede hacer en cada momento lo dice el contrato.

## Hoy (v0)

| Capacidad | Cómo | Efecto que necesita |
|---|---|---|
| Explorar y razonar | Lectura de ficheros y cúpulas permitidas | `leer` (sin contrato) |
| Proponer contratos y enmiendas | Borradores JSON en `contratos/borradores/` | Zona libre |
| Hablar con Savia | Buzón | Zona libre |
| Recordar | `memoria/` (checkpoints y notas) | Zona libre |
| Implementar con pruebas | Edición en el ámbito + órdenes listadas | `escribir`, `ejecutar` |
| Trabajar con git local | Ramas, commits | `git-local` |
| Entregar | Push de ramas propias, PR | `git-remoto`, `publicar` (E3) |
| Integrar en Space | Procedimiento de `docs/casa-space.md` | Según contrato |
| Delegar a una revisora | Otra instancia, contrato de solo lectura | `delegar` |

## Nunca (por diseño)

Aprobar, activar o ampliar contratos; mergear; tocar su núcleo, su gobierno o su evidencia; leer secretos; leer cúpulas no nombradas.

## Cómo crece una capacidad

Solo por F1-F2 del roadmap: hipótesis, medición contra la línea base, y la persona decide si entra.
