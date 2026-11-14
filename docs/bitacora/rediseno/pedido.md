# Rediseño: Pedido por dentro

Esta es la pantalla de un pedido. Quedó igual a `diseno/pedido.html` y, además, tiene
cronología.

## Qué cambió en la pantalla

- **Arriba**: la flecha para volver (en celular), la miga "Pedidos" (en computador), el botón
  "Avisar al cliente", el menú "Más acciones" (ahí está "Eliminar el pedido", solo para la
  dueña) y dos flechas para pasar al pedido anterior o al siguiente, en el mismo orden de la
  lista de Pedidos. En el primero y en el último, la flecha que no sirve se ve apagada.
  "Registrar abono" ya no está arriba: está en la tarjeta del pago. La tarjeta grande de
  "Eliminar el pedido" de abajo desapareció.
- **Título**: el nombre del cliente con dos insignias (el pago, solo la dueña, y la etapa) y
  debajo cuándo se creó y cuándo se entrega ("en 33 días", o cuántos días lleva de atraso).
- **Columna de la izquierda**:
  - la prenda y su etapa: la foto (o un dibujo de prenda), qué es, el tallaje, cuántas
    personas y el total (solo la dueña); las seis barritas de la etapa; y abajo "Cambiar etapa"
    y el botón negro "Pasar a …" con la etapa que sigue. La costurera que no es la encargada
    ve las barritas apagadas y una nota que dice quién puede moverlo;
  - el pago (solo la dueña): valor total, cada abono con su "Recibo" y su "Quitar", y lo que
    falta por pagar, o "Pagado" cuando no falta nada. Abajo, el recordatorio de saldo y
    "Registrar abono", que abre el formulario ahí mismo;
  - las tallas: cuántas personas enviaron su talla, una barra por talla y tres botones: "Ver
    las N personas" (muestra la lista y el formulario para agregar a mano), "Copiar resumen" y
    "Copiar enlace para el cliente". Abrir o cerrar el enlace sigue siendo de la dueña;
  - la **cronología** (nueva): lo que ha pasado en el pedido, día por día.
- **Columna de la derecha**: cliente (su nombre lleva a Clientes), entrega ("Cambiar" muestra
  el campo de la fecha), foto (con "Sale en Hoy y en la lista de pedidos") y materiales con su
  casilla para marcar lo comprado.

## Archivos que cambiaron y para qué

- `pedidos/templates/pedidos/pedido.html`, `_pedido_apoyo.html`, `_pedido_acciones.html`,
  `_detalle_avisar.html`: el encabezado, el título y la forma de las dos columnas.
- `_etapa.html`, `_pagos.html`, `_abono_*.html`, `_tallas.html`, `_talla_*.html`,
  `_cliente.html`, `_entrega.html`, `_foto*.html`, `_materiales.html`: cada tarjeta, copiando
  el HTML de la referencia. `_eliminar.html` se borró (ahora está en "Más acciones").
- `_cronologia.html` y `pedidos/cronologia.py` (nuevos): arman la cronología sin guardar nada
  nuevo; usan lo que ya existe (cuándo se creó el pedido, los abonos y las tallas).
- `pedidos/vistas/detalle.py`, `abonos.py`, `tallas.py`, `fotos.py`: calculan lo nuevo (pedido
  anterior y siguiente, etapa que sigue, frases de fechas) y mandan a refrescar lo que depende
  (por ejemplo, un abono nuevo actualiza la insignia del título y la cronología sin recargar).
- `static/css/app.css`, apartado "Pedido por dentro": unos pocos estilos propios.
- Pruebas: se actualizaron `test_detalle.py`, `test_abonos.py`, `test_tallas.py`,
  `test_materiales.py` y `test_fotos.py`, y se agregó `test_cronologia.py`.

## Decisiones y por qué

- **La cronología de la costurera** no muestra abonos ni el valor del pedido, porque la
  costurera no ve plata.
- **Quién hizo cada cosa**: las tallas no guardan quién las agregó. Las del enlace dicen
  "Enlace" y se juntan por día ("12 personas enviaron su talla"). Las agregadas a mano dicen de
  quién es la talla.
- **Sin JavaScript** todo sigue funcionando: "Cambiar" (fecha), "Agregar" (WhatsApp) y "Ver las
  N personas" son enlaces que recargan la página con esa parte a la vista.
- **El formulario del abono** es un recuadro sin título visible que se abre con "Registrar
  abono"; así se conserva el campo con su identificador de siempre.
- No se borró `pedidos.fotos.trabajos`: Hoy todavía lo usa.

## Qué se probó

Pruebas automáticas de todos los archivos de la pantalla, como dueña y como costurera, y que
otro taller no aparezca. Capturas en 1366, 1920 y 390 px comparadas con `diseno/pedido.html`,
como dueña y como costurera (la que es encargada y otra que no).
