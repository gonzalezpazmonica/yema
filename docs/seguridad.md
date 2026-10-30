# Seguridad

Yema parte de una idea: el modelo puede equivocarse o dejarse convencer por lo que lee (un repo, una página, un mensaje). Por eso sus límites no viven en el modelo, sino en la puerta, que es código corriente, pequeño y con pruebas.

## Qué cuida la puerta

- **Quién concede**: solo una persona aprueba, con el diálogo nativo del arnés o en su terminal. La huella ata lo aprobado a lo que se enseñó, y el ticket es de un solo uso.
- **Hasta dónde**: rutas reales dentro del ámbito, órdenes exactas del contrato, efectos concedidos, presupuesto y caducidad.
- **Lo que nunca**: órdenes encadenadas, push destructivo, cambiar su propio núcleo, su gobierno o su evidencia, y leer lo que la política veta.
- **Lo confidencial**: solo lee las cúpulas que tiene nombradas.
- **La memoria de lo ocurrido**: recibos encadenados que delatan cualquier cambio.
- **Probar sin riesgo**: `yema prueba` ejecuta en una copia desechable dentro de un sandbox bwrap de root (sin red, sin el hogar, solo /usr, /etc y la copia, con tiempo y tamaño limitados); lo vetado no se copia. Si no hay un bwrap de confianza, no ejecuta.
- **Lo que hace una orden por dentro**: la puerta juzga la orden, no lo que hace el proceso. Por eso cada orden de efecto `ejecutar` que concede un contrato corre bajo Landlock (`nucleo/aislar.py`, sin privilegios ni bwrap): el kernel solo le deja leer el ámbito, `ambito.lectura` y lo del sistema (/usr, /etc, /proc), y escribir en el ámbito y en un /tmp propio que se borra al terminar. Si el kernel no admite Landlock, la orden no corre, salvo que el contrato diga `ambito.aislamiento: "si_hay"`, y `yema resumen` lo muestra.
- **Ante la duda**: bloquea.

Cada «nunca» tiene una prueba que intenta hacerlo (`pruebas/`), y se comprueba que romper un control a propósito hace fallar alguna prueba.

## Lo que todavía no cubre

- El aislamiento cubre ficheros, no la red: una orden concedida aún puede conectarse fuera.
- Solo se aíslan las órdenes de efecto `ejecutar`. git y las órdenes de red (npm, cargo, pip…) corren sin aislar; un hook de git que escriba una orden aislada dentro del ámbito correría fuera de la caja en el siguiente `git commit`.
- El entorno (variables) se hereda tal cual. El destino sigue siendo el sandbox de Savia Space.
- La puerta solo ve lo que el arnés le pasa.
- El diálogo de permisos vale lo que valga el arnés; en modos que no preguntan, aprobar se deniega.
- El ticket prueba que se preguntó, no quién contestó.
- El presupuesto cuenta efectos, no tokens.

## Si encuentras un fallo

Abre un aviso privado de seguridad en GitHub con la versión, un contrato de ejemplo y la entrada exacta que lo provoca. No lo publiques hasta que esté arreglado.

## Alarma de nivel en las cúpulas

Lo que Yema lee sale a un modelo en la nube. Antes de leer una cúpula, la puerta consulta el registro de cúpulas (`registro_cupulas` en la política):
- Si la cúpula es N3 o N4, no se lee aunque esté permitida.
- Si una nota declara `confidentiality: N3` o superior en su cabecera, `vault_read` se para aunque la cúpula sea N1 o N2.
- Una ruta que intente salir de la cúpula también se para.

Es una alarma, no la defensa principal. Si salta, hay que averiguar por qué esa nota está en una cúpula legible, no ampliar la lista. Límite conocido: una búsqueda (`vault_search`) en una cúpula N1 o N2 puede devolver fragmentos de una nota mal clasificada, porque la puerta ve la petición pero no la respuesta.

## Presupuesto de tiempo

`recursos.minutos_max` limita cuánto dura un contrato desde su última activación. Pasado ese tiempo, la puerta deniega los efectos materiales; leer sigue permitido. El presupuesto de efectos (`efectos_max`) sigue igual. Los tokens no son visibles para la puerta.

