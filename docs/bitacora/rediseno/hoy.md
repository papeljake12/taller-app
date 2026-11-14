# Rediseño: la pantalla Hoy

Carril A. Hoy ahora se ve como la página `diseno/hoy.html` (y `diseno/hoy-menu-contraido.html`).

## Qué cambió para quien usa la pantalla

- **Arriba:** a la izquierda, un estado con punto rojo ("1 pedido atrasado") que lleva a
  Pedidos con ese filtro; solo se ve en computador y solo si hay atrasados. En celular, en su
  lugar, el logo de las tijeras. A la derecha: la fecha, la lupa redonda (solo celular) y el
  botón "Nuevo pedido".
- **Saludo:** "¡Buenos días!", "¡Buenas tardes!" o "¡Buenas noches!" según la hora de Bogotá.
  En computador sigue "Esto es lo de hoy en (el taller)". En celular, debajo, "Tienes 3 cosas
  pendientes hoy" (o "No tienes nada pendiente hoy").
- **Caja grande para buscar**, con tres atajos para la dueña: "Nuevo pedido", "Registrar
  abono" (lleva a los pedidos con saldo) y "Cotizar". La costurera solo ve el buscador
  ("Busca un pedido").
- **Tarjetas de lo que hay que hacer:** una por cada pendiente, con la foto del pedido (o un
  cuadrito con una prenda), la insignia de la entrega, el cliente (enlace al pedido), la frase y
  los botones. Atrasado: "Marcar como listo" y "Avisar". Listo: "Marcar como entregado" y
  "Avisar". Cotizado: **"Confirmar pedido"** (nuevo) y "Avisar". Si no le toca nada:
  "Ver el pedido". Ya no está "Cobrar el saldo": para eso está el atajo "Registrar abono".
  En computador van de a tres; en celular se deslizan de lado.
- **Tu mes:** Cobrado y Gastado (del mes), Por cobrar y En producción. Cada cifra abre su
  pantalla y, al pasar el mouse, dice de dónde sale el número. La costurera ve otro título
  ("El taller hoy") y tres cifras sin plata: en producción, se entregan esta semana y atrasados.
- **Gráfica y "Quién te debe"** (solo la dueña): la gráfica ya no lleva la cifra grande ni la
  nota; "Quién te debe" muestra el total por cobrar y marca con "Vencida" (en rojo) al cliente
  con un pedido atrasado.
- **Pedidos por etapa:** seis casillas sin título. Los atrasados salen como "1 atrasado" en
  rojo. Ya no hay nada en verde: se quitó el "Pagado" de Entregado; si hay entregados que aún
  deben, dice "N con saldo" en naranja.
- **Se quitó "Trabajos del taller"** de Hoy.

## Cómo funciona (sin tecnicismos de más)

Al tocar "Marcar como listo", "Marcar como entregado" o "Confirmar pedido", la página no se
recarga: se cambian las tarjetas y, a la vez, lo que depende de ellas (la frase de cosas
pendientes, las cifras, "Quién te debe", las etapas, el estado de arriba y el contador de
atrasados del menú). Si el navegador no puede hacerlo, la acción funciona igual y vuelve a Hoy.

## Archivos

- `pedidos/vistas/hoy.py`: arma los datos de la pantalla; nueva acción "confirmado"
  (cotizado pasa a confirmado, con el mismo permiso que las otras); saludo y frase de
  pendientes; ya no usa las fotos de "Trabajos del taller".
- `pedidos/templates/pedidos/hoy.html`: reúne las partes con el orden de la referencia.
- Partes: `_hoy_estado.html` (nueva), `_hoy_cuenta.html`, `_hoy_pendientes.html`,
  `_hoy_pendiente.html` (la tarjeta), `_hoy_mensaje.html` ("Avisar"), `_cifras.html`,
  `_grafica.html`, `_quien_debe.html`, `_etapas.html`.
- Se borraron `_trabajos.html`, `_que_hacer.html` y `_hoy_nombre_boton.html` (ya no sirven).
- `static/css/app.css`, apartado "Hoy": una regla para el texto de "no hay nada por hacer hoy".
- `pedidos/tests/test_hoy.py`: pruebas rehechas para el diseño nuevo.

## Decisiones

- **La costurera no ve "Avisar" en un pedido listo ni en uno cotizado:** esos mensajes
  dicen el saldo o el precio, y ella no ve plata. En un atrasado sí lo ve (el mensaje no
  tiene plata). Tampoco ve "Confirmar pedido": en los cotizados solo le sale "Ver el pedido".
- **Las casillas de etapas son enlaces a Pedidos** (como en la referencia), sin filtro por
  etapa porque Pedidos todavía no filtra por etapa.
- La frase "Pagado." sigue al final del texto de una tarjeta cuando no se debe nada (texto
  normal, no verde).
- Las acciones no llevan aviso corto, como antes: el cambio se ve en la tarjeta misma.

## Qué se probó

- 73 pruebas de `test_hoy.py`: saludo por hora, frases en singular y plural, encabezado,
  caja grande y atajos, tarjetas (orden, foto, enlaces, "Avisar" con y sin WhatsApp), las tres
  acciones y todo lo que cambia con ellas, que no cambien lo que no corresponde, otro taller
  (404 y no se ve nada), permisos de la costurera (sin plata, solo sus acciones, sin
  gráfica ni "Quién te debe"), gráfica, "Quién te debe" y etapas.
- Capturas con el navegador automático en 1366 x 768, 1920 x 1080 y celular, de la dueña, del
  menú contraído y de Marta (costurera), comparadas con `diseno/`: coinciden. Solo cambia el
  saludo, que depende de la hora real.
- No se probó a mano el botón "Avisar" abriendo WhatsApp de verdad, ni las animaciones de
  salida de una tarjeta en un navegador (solo que la respuesta trae los mismos ids).
