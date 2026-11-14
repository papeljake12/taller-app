# Rediseño: Clientes

## Qué cambió en la pantalla

- **Encabezado:** "Clientes" y al lado "6 clientes · 4 te deben" (con los números reales). El
  botón "Nuevo cliente" es negro; en celular se vuelve un círculo con un "+".
- **Aviso de dotación:** antes era una tarjeta negra. Ahora es un cuadro azul claro con el
  ícono de calendario, el título ("Dotación del 20 de diciembre: faltan 37 días"), la frase y
  el botón "Escribirles a los N", que abre la misma ventana de antes.
- **Lista:** una sola tarjeta con el buscador arriba (a todo el ancho, sigue buscando mientras
  escribes), la tabla y abajo "N clientes". La hoja se desplaza completa; ya no hay una tabla
  que se mueve por dentro.
- **Columna "Debe":** el monto va en negro; sin deuda dice "Al día" en gris (antes verde). Si
  el cliente debe por un pedido que ya pasó su fecha de entrega, el monto va en rojo con la
  insignia roja "Vencida". "Cotización abierta" y "Sin compras" siguen en gris.
- **Sin clientes:** se muestra la pantalla vacía con dibujo, "Aquí vas a ver tus clientes", el
  botón "Nuevo cliente" y "Cómo llevar los clientes del taller".
- Siguen igual: crear, editar, "Escribirle" (WhatsApp o copiar), el orden por lo que más han
  comprado, el buscador y los ids de cada fila (para las animaciones).

## Archivos

- `pedidos/templates/pedidos/clientes.html`, `_clientes_dotacion.html`, `_clientes_tabla.html`,
  `_clientes_acciones.html`: copian el HTML de `diseno/clientes.html`.
- `pedidos/vistas/clientes.py`: el texto "6 clientes · 4 te deben" y el cálculo de qué
  clientes tienen deuda vencida (un pedido atrasado con saldo).
- `pedidos/tests/test_clientes.py` y `test_mensajes_clientes.py`: revisan el diseño nuevo y
  agregan pruebas del pie, la insignia "Vencida", el botón redondo y la pantalla vacía.

## Decisiones

- "Vencida" se calcula en la vista y no en `calculos.py` (que es compartido): se mira si el
  cliente tiene un pedido en producción con la fecha de entrega pasada y saldo por pagar.
- Con cero clientes se muestra solo la pantalla vacía (sin el aviso de dotación, que no
  tendría a quién escribirle).
- No hizo falta CSS nuevo: todo sale de las piezas de `app.css`.

## Qué se probó

- Pruebas de los dos archivos: 66 pasan.
- Capturas en 1366, 1920 y celular comparadas con `diseno/clientes.html`: iguales.
- No se vio con captura la pantalla vacía (solo por pruebas) ni la ventana de "Escribirles".
