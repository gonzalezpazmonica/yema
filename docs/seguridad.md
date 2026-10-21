# Seguridad

Yema parte de una idea: el modelo puede equivocarse o dejarse convencer por lo que lee (un repo, una página, un mensaje). Por eso sus límites no viven en el modelo, sino en la puerta, que es código corriente, pequeño y con pruebas.

## Qué cuida la puerta

- **Quién concede**: solo una persona aprueba, con el diálogo nativo del arnés o en su terminal. La huella ata lo aprobado a lo que se enseñó, y el ticket es de un solo uso.
- **Hasta dónde**: rutas reales dentro del ámbito, órdenes exactas del contrato, efectos concedidos, presupuesto y caducidad.
- **Lo que nunca**: órdenes encadenadas, push destructivo, cambiar su propio núcleo, su gobierno o su evidencia, y leer lo que la política veta.
- **Lo confidencial**: solo lee las cúpulas que tiene nombradas.
- **La memoria de lo ocurrido**: recibos encadenados que delatan cualquier cambio.
- **Probar sin riesgo**: `yema prueba` ejecuta en una copia desechable dentro de un sandbox bwrap de root (sin red, sin el hogar, solo /usr, /etc y la copia, con tiempo y tamaño limitados); lo vetado no se copia. Si no hay un bwrap de confianza, no ejecuta.
- **Ante la duda**: bloquea.

Cada «nunca» tiene una prueba que intenta hacerlo (`pruebas/`), y se comprueba que romper un control a propósito hace fallar alguna prueba.

## Lo que todavía no cubre

- Una orden permitida ejecuta lo que ejecute: por eso el destino es el sandbox de Savia Space.
- La puerta solo ve lo que el arnés le pasa.
- El diálogo de permisos vale lo que valga el arnés; en modos que no preguntan, aprobar se deniega.
- El ticket prueba que se preguntó, no quién contestó.
- El presupuesto cuenta efectos, no tokens.

## Si encuentras un fallo

Abre un aviso privado de seguridad en GitHub con la versión, un contrato de ejemplo y la entrada exacta que lo provoca. No lo publiques hasta que esté arreglado.
