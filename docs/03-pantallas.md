# Pantallas

Qué hace cada pantalla y cómo se comprueba que quedó lista.

- **Cómo se ve:** carpeta `diseno/` y `docs/08-diseno.md`. Es la fuente de verdad visual.
- **Cómo se comporta y qué dice:** `demo/index.html`, salvo donde este documento diga otra cosa.

Reglas para todas las pantallas:

- Funciona en 390 px de ancho sin barra horizontal.
- Una usuaria nunca ve datos de otro taller.
- Las tarjetas de una misma fila terminan a la misma altura (ver "Alineación" en
  `docs/08-diseno.md`).

## Menú

Referencia: `diseno/hoy.html`, `diseno/hoy-menu-contraido.html` y `diseno/hoy-celular.html`.

Secciones: Hoy, Pedidos, Calendario, Clientes, Cotizador, Telas y Resumen. "Mi taller" va al
fondo del menú.

Lista cuando:
- En computador el menú va a la izquierda, sobre el marco negro, y resalta la sección actual.
- El botón de contraer deja una tira de íconos, y el logo la vuelve a abrir. La elección se
  recuerda en ese navegador.
- Pedidos muestra cuántos van atrasados y Telas cuántas se están acabando. Sin pendientes,
  no se muestra el contador.
- El buscador del menú encuentra pedidos y clientes, sin importar tildes ni mayúsculas.
- En celular el menú es una barra abajo con Hoy, Pedidos, Calendario, Clientes y Más.

## Inicio de sesión

Sin página de referencia: una tarjeta centrada sobre el marco, con las piezas del diseño.

Usuario y contraseña. Bloqueo temporal después de varios intentos fallidos (`django-axes`).

Lista cuando:
- Con datos correctos entra a Hoy.
- Con datos incorrectos muestra un mensaje claro, sin decir cuál de los dos falló.
- Después de 5 intentos fallidos bloquea el acceso por un tiempo.
- Sin sesión, cualquier pantalla interna redirige aquí.

## Hoy

Referencia: `diseno/hoy.html` y `diseno/hoy-celular.html`. Es la pantalla de entrada.

Reemplaza la portada "Hoy en el taller" de la demo: ya no hay foto de portada ni frase del día.

Bloques, en orden: cuatro cifras, "Qué hacer hoy" junto a "Trabajos del taller", "Cobrado y
gastado por mes" junto a "Quién te debe", y "Pedidos por etapa".

Lista cuando:
- Las cuatro cifras (en producción, entregas en 7 días, atrasados y por cobrar) coinciden con
  los cálculos de `docs/02-modelo-de-datos.md`. Atrasados va en rojo solo si hay alguno.
- Tocar una cifra abre Pedidos con ese filtro.
- "Qué hacer hoy" lista, en este orden: los pedidos atrasados, los que están listos sin
  entregar, los que se entregan en 7 días y los cotizados sin confirmar. Dice cuántos son.
- Cada fila ofrece la acción que sigue:
  - atrasado: "Marcar como listo" y "Avisar al cliente";
  - listo con saldo: "Cobrar el saldo" y "Marcar como entregado";
  - cotizado: "Preguntar si confirma".
- Las acciones cambian el pedido sin recargar la página y la fila se actualiza o desaparece.
- Sin pendientes, dice que no hay nada por hacer hoy.
- "Trabajos del taller" pasa las fotos de los pedidos como describe `docs/08-diseno.md`.
  Sin fotos, invita a subir la primera.
- La gráfica muestra lo cobrado y lo gastado de los últimos seis meses, y arriba la cifra
  cobrada del mes actual.
- "Quién te debe" lista los clientes con saldo, del que más debe al que menos, con una barra
  proporcional. El que tiene un pedido atrasado va en rojo.
- "Pedidos por etapa" muestra cuántos pedidos hay en cada etapa y cuántos van atrasados.
- "Descargar para Excel" baja el mismo archivo que el de Resumen.

## Pedidos

Referencia: `diseno/pedidos.html`.

Lista de pedidos con filtros y buscador.

Lista cuando:
- Los filtros Todos, En producción, Esta semana, Atrasados, Con saldo y Entregados
  funcionan y muestran su conteo.
- El buscador encuentra por cliente, prenda o encargada, sin importar tildes ni mayúsculas.
- Cada fila muestra cliente, detalle, etapa, fecha de entrega con su etiqueta de urgencia,
  encargada, tallas recibidas y saldo.
- Las etiquetas usan los tonos de `docs/08-diseno.md`: rojo para atrasado, ámbar para
  "faltan N días", azul para en corte y en confección, verde para entregado y pagado.
- La lista se ordena por fecha de entrega, con los entregados al final.
- Tocar una fila abre el pedido.
- En celular la tabla se desplaza dentro de su tarjeta.

## Nuevo pedido

Sin página de referencia: una ventana con campos, usando las piezas del diseño.

Cliente, tipo, qué pidió, para cuántas personas, tallas, fecha de entrega, valor total y
WhatsApp.

Lista cuando:
- Se abre desde el botón "Nuevo pedido" de cualquier pantalla.
- Si el cliente ya existe lo reutiliza; si no, lo crea.
- Valida cada campo y dice qué falta en lenguaje claro.
- El pedido nace en estado `cotizado` y abre su pantalla de detalle.

El cuadro "pega el mensaje del cliente y la IA lo llena" es de la etapa 3.

## Pedido por dentro

Referencia: `diseno/pedido.html`.

Arriba: cliente, etiqueta de etapa, detalle y los botones "Avisar al cliente" y "Registrar
abono". Columna izquierda: Etapa, Tallas y Materiales. Columna derecha: Pagos, Entrega y
Cliente. Las dos columnas terminan a la misma altura.

Lista cuando:
- Tocar una etapa la guarda y se ve sin recargar la página.
- Se puede elegir la encargada entre las usuarias del taller.
- Se puede cambiar la fecha de entrega y el WhatsApp del cliente. Dice en cuántos días se
  entrega, o cuántos lleva de atraso.
- Registrar un abono baja el saldo y mueve la barra sin recargar la página.
- Con saldo en 0 dice "Pedido pagado" en verde.
- Cada abono tiene un botón "Recibo" que descarga un PDF.
- Con WhatsApp guardado aparecen los botones para enviar el recordatorio de saldo y, si la
  etapa es `listo`, el aviso de pedido listo. Sin WhatsApp, botones para copiar el texto.
- Tallas: muestra "N de M recibidas" y una barra por talla.
- Hay un botón para copiar el enlace público de tallas y otro para copiar el resumen.
- Materiales: agregar, marcar como comprado, quitar. Muestra "N de M comprados".

Estas partes no están dibujadas en la referencia. Se agregan con las mismas piezas y se le
muestran a David:
- La lista de tallas persona por persona y el formulario para agregar una a mano, con
  medidas si es "A la medida".
- Subir, cambiar y quitar la foto del pedido (es la que sale en "Trabajos del taller").
- Eliminar el pedido, con confirmación.

## Formulario público de tallas

Sin página de referencia: una tarjeta centrada, pensada para celular.

Lo abre cada persona del grupo con un enlace. No requiere cuenta.

Lista cuando:
- Abre con el enlace del pedido y muestra cliente y detalle, sin precios ni datos de otros.
- Pide nombre, talla y observaciones. Si elige "Medida", pide pecho, cintura y cadera.
- Al enviar muestra la confirmación y permite registrar a otra persona.
- Un enlace inexistente o cerrado muestra un mensaje claro.
- Limita la cantidad de envíos por minuto para evitar abuso.
- No permite ver las tallas de los demás.
- No muestra el menú ni nada del panel.

## Calendario

Referencia: `diseno/calendario.html`.

Mes con las entregas marcadas. Al lado, "Entregas del mes" y "Semana más cargada".

Lista cuando:
- Se puede ir al mes anterior y al siguiente.
- El día de hoy va marcado con un círculo negro.
- Cada entrega se ve en su día: por entregar (ámbar), atrasada (rojo) o entregada (verde),
  con la leyenda debajo.
- Tocar un día filtra la lista de entregas.
- "Semana más cargada" dice cuál es la semana con más entregas, o que no se juntan.

## Clientes

Referencia: `diseno/clientes.html`.

Aviso de la próxima fecha de dotación y tabla de clientes.

Lista cuando:
- El aviso dice cuántos días faltan para la próxima fecha de dotación y cuántos clientes
  empresa hay. Su botón prepara el mensaje para ellos.
- La tabla muestra tipo, número de pedidos, cuánto ha comprado y cuánto debe. Sin deuda dice
  "Al día".
- La lista se ordena por lo que más han comprado.
- "Escribirle" abre WhatsApp si hay número; si no, copia el mensaje.
- Se puede crear y editar un cliente.

## Cotizador

Referencia: `diseno/cotizador.html`.

A la izquierda los datos (para quién, qué prenda, cuánto cuesta hacer una, tu ganancia). A
la derecha el resultado.

Lista cuando:
- El resultado se actualiza mientras se escribe.
- Los resultados coinciden con las fórmulas de `docs/02-modelo-de-datos.md`.
- Muestra total, precio por unidad, costo de hacer una, cuánto de eso es tela, ganancia en
  el pedido y abono para empezar.
- Se puede guardar una prenda en "Mis prendas", elegirla después y quitarla.
- "Crear pedido con esta cotización" crea el pedido en `cotizado` con el total calculado y
  un material "Tela" con los metros totales.
- Se puede copiar la cotización y, con WhatsApp, enviarla.
- "Empezar de nuevo" limpia los campos.

## Telas

Referencia: `diseno/telas.html`.

Lista cuando:
- Las tres cifras dicen cuántas telas hay, cuántos metros suman y cuáles se están acabando.
- La tabla muestra cada tela con los metros que quedan, el mínimo para avisar y su estado:
  "Se está acabando" en ámbar o "Suficiente" en verde.
- "Entró" suma metros y "Usé" resta, sin bajar de 0. Cada movimiento queda en el historial.
- Se puede agregar y quitar una tela.

## Resumen del mes

Referencia: `diseno/resumen.html`.

Lista cuando:
- Muestra vendido, cobrado, gastado y "te quedó" del mes elegido. "Te quedó" va en verde.
- Se puede cambiar de mes.
- La gráfica muestra lo cobrado y lo gastado de los últimos seis meses.
- Se puede registrar y quitar un gasto, con concepto, tipo, valor y fecha.
- Muestra ventas por tipo de cliente y pedidos en producción por persona.
- "Descargar para Excel" baja un archivo con cuatro hojas: Pedidos, Abonos, Gastos y Telas.

## Mi taller

Sin página de referencia: tarjetas con campos, usando las piezas del diseño.

Lista cuando:
- La dueña cambia el nombre y el logo del taller.
- La dueña crea, desactiva y cambia el nombre de las costureras.
- El nombre del taller aparece en el menú, en los mensajes y en los recibos.
