---
name: contrato
description: Redactar, enseñar, enmendar y pedir la aprobación de un contrato de ejecución a partir de lo que la persona pide en la conversación. Úsala cuando un encargo vaya a cambiar algo (escribir, ejecutar, git, red, publicar) o cuando la persona pregunte por un contrato.
---

# Contrato

## Rutas

- Borrador: `~/.yema/contratos/borradores/<id>.json` (zona libre).
- Ejemplo completo: `ejemplos/contrato-ejemplo.json`.
- Esquema y niveles: `docs/gobernanza.md`.

## Pasos

1. **Entiende el encargo.** Como mucho dos preguntas, y solo si cambian el alcance. Lo deducible, dedúcelo y dilo.
2. **Elige el id**: `C-` + siguiente número libre en `~/.yema/contratos/` y `borradores/`.
3. **Redacta lo mínimo suficiente**:
   - `proposito`: una frase que entienda cualquiera.
   - `responsable`: la persona (de `gobierno/politica.json`, `aprobadoras`); `ejecutora`: `yema`.
   - `nivel`: E2 si es local y reversible; E3 si toca remoto o terceros.
   - `ambito.raiz` absoluta; `escritura` con globs relativos lo más estrechos posible; `vetadas` para lo sensible.
   - `autoridad.efectos` solo los necesarios; `prohibidos` con lo que la persona no querría (`publicar`, `git-remoto`, `escribir-cupula`…).
   - `autoridad.ordenes`: órdenes exactas (`cargo test`, `git merge --no-ff agent/*`). Nunca un intérprete suelto.
   - `autoridad.caduca`: lo que dure el encargo más un margen, con zona horaria.
   - `recursos.efectos_max`: estimación honesta (unos 3 efectos por fichero tocado, más las órdenes).
   - `condiciones.post`: órdenes con lo que deben devolver, más un informe en `~/.yema/memoria/<id>.md`.
4. **Valida**: `yema validar ~/.yema/contratos/borradores/<id>.json`. Si falla, corrige y repite.
5. **Enseña**: `yema resumen <id>`, y pega la salida en la conversación. Añade una línea sobre por qué ese alcance y no otro.
6. **Si la persona dice que sí**: `yema aprobar <id> <huella8>`. El arnés le mostrará el diálogo. Si el modo no pregunta, díselo y no busques otra vía.
7. **Si pide cambios**: edita el borrador; la huella cambia; vuelve al paso 5.

## Enmiendas

Si a mitad del trabajo necesitas algo que el contrato no concede: no lo intentes. Copia el contrato vigente a un borrador con `version` +1 e id nuevo (`C-0002` → `C-0003`), cambia solo lo necesario, explica la diferencia en una línea, y sigue los pasos 4-6. Al aprobar el nuevo, revoca el viejo (`yema revocar <id viejo> --por yema --motivo "sustituido por …"`).

## Lista de comprobación antes de enseñar

- [ ] ¿Cada efecto y cada orden hacen falta de verdad?
- [ ] ¿Hay algo irreversible? Entonces es E3 y la persona decide ese efecto aparte.
- [ ] ¿La caducidad es corta?
- [ ] ¿Las postcondiciones se pueden comprobar sin fe?
- [ ] ¿Nada privado va a ir a un sitio público?
