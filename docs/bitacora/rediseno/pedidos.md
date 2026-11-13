# Rediseño: Pedidos, Buscar y Nuevo pedido

## Qué cambió en la pantalla

**Pedidos**
- Usa todo el ancho de la hoja y ya no es de "pantalla fija": la hoja se desplaza sola cuando hay
  muchos pedidos.
- Arriba hay una barra con cinco cifras: Activos, En producción, Se entregan esta semana,
  Atrasados (en rojo solo si hay) y Por cobrar. Las tres del medio llevan a la lista ya filtrada.
  Al pasar el mouse, cada cifra explica de dónde sale. La costurera no ve "Por cobrar".
- Debajo, una sola tarjeta con las pestañas (Todos, En producción, Esta semana...) y su conteo, y
  a la derecha una lupa. El buscador ya no está siempre a la vista: sale al tocar la lupa. Si ya
  hay algo buscado, se ve solo. Sin JavaScript, la lupa es un enlace a la misma lista con el
  buscador abierto.
- La tabla tiene las columnas de la referencia: Cliente (con su foto o ícono), Prenda, Entrega,
  Total, Pago, Etapa, Tallas y Encargada. La entrega dice "11 nov · 2 días tarde" en rojo si va
  atrasada, o "16 nov · en 3 días" (también "hoy" y "mañana") si es en la próxima semana.
- En celular cada fila se vuelve una lista: foto, cliente, total, insignias del pago y la etapa, y
  "fecha · encargada".
- Abajo dice cuántos pedidos hay ("6 pedidos").
- Sin ningún pedido sale la pantalla vacía con su dibujo, para qué sirve la pantalla, el botón
  "Nuevo pedido" (solo la dueña) y el enlace "Cómo llevar los pedidos del taller".
- La costurera no ve Total ni Pago, ni "Por cobrar", ni el filtro "Con saldo".

**Buscar** (el buscador del menú): mismo lenguaje. Una tarjeta con el buscador y, debajo, una
tarjeta con los pedidos (la misma tabla) y otra con los clientes (solo la dueña).

**Nuevo pedido**: los campos de a dos como en la referencia, con ejemplos escritos en gris
("Ej.: Colegio San José", "Ej.: 1.200.000"), y los botones "Cancelar" y "Guardar pedido".

## Archivos y para qué

- `pedidos/templates/pedidos/lista.html`, `_lista_tabla.html`, `_lista_fila.html`,
  `_lista_filtros.html`: la pantalla, la tabla, cada fila y las pestañas.
- `pedidos/templates/pedidos/buscar.html`: Buscar.
- `pedidos/templates/pedidos/_nuevo.html`: solo cambió su comentario (ya era como la referencia).
- `pedidos/vistas/lista.py`: calcula las cifras, la fecha corta ("11 nov") y lo que acompaña a la
  entrega, y decide si el buscador se ve.
- `pedidos/formularios/lista.py`: agrega los ejemplos en los campos Cliente y Valor total.
- `static/css/app.css` (solo mi apartado): una fila para el buscador escondido.
- `pedidos/tests/test_lista.py`: pruebas puestas al día.

## Qué se probó

- 95 pruebas de la pantalla pasan: cifras, filtros, buscador (con y sin JavaScript), tabla,
  entrega, lista de celular, pantalla vacía, permisos de la costurera, que otro taller no se vea
  y la ventana de Nuevo pedido. Una prueba en Chrome revisa que nada se desborde en 1280 y 390 px.
- Capturas en 1366, 1920 y celular, comparadas con `diseno/`: Pedidos coincide.
- No se probó a mano la lupa con JavaScript tocándola (la prueba solo mira que el enlace y el
  atributo existan).

## Decisiones

- Quité el "+", el filtro y el orden que traía la referencia junto a la lupa: no hacen nada aquí.
- No hay flechas de páginas: la lista no se divide en páginas, solo se cuenta.
- "Tallas" en Nuevo pedido sigue con las dos opciones del modelo (Adulto y Niño 4 a 16); la
  referencia muestra también "A la medida" y "Niño (2 a 16)", pero eso cambiaría el modelo y
  queda para decidirlo con David.
- Las filas de Clientes en Buscar son una tabla sencilla (Cliente y Tipo), que lleva a Clientes.
