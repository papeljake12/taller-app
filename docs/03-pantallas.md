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

Referencia: `diseno/hoy.html` y `diseno/hoy-menu-contraido.html` (en 390 px, el celular).

Secciones: Hoy, Pedidos, Calendario, Clientes, Cotizador, Telas y Resumen. "Mi taller" va al
fondo del menú, con el logo (o las iniciales) y el nombre del taller y el botón para salir.
Dentro de Pedidos, cuando es la sección actual, van "Atrasados" y "Con saldo".

Lista cuando:
- En computador el menú va a la izquierda, sobre el marco negro, y resalta la sección actual.
- El botón de contraer deja una tira de íconos, y el logo la vuelve a abrir. La elección se
  recuerda en ese navegador.
- Pedidos muestra cuántos van atrasados y Telas cuántas se están acabando. Sin pendientes,
  no se muestra el contador.
- El buscador del menú encuentra pedidos y clientes, sin importar tildes ni mayúsculas.
  Ctrl K (o Cmd K en Mac) lo enfoca desde cualquier pantalla.
- En celular el menú es una barra abajo con Hoy, Pedidos, Calendario, Clientes y Más.

## Inicio de sesión

Referencia: `diseno/entrar.html`. Una tarjeta blanca centrada sobre el marco.

Usuario y contraseña. Bloqueo temporal después de varios intentos fallidos (`django-axes`).

Lista cuando:
- Con datos correctos entra a Hoy.
- Con datos incorrectos muestra un mensaje claro, sin decir cuál de los dos falló.
- Después de 5 intentos fallidos bloquea el acceso por un tiempo.
- Sin sesión, cualquier pantalla interna redirige aquí.

## Hoy

Referencia: `diseno/hoy.html` (en 390 px, el celular). Es la pantalla de entrada.

Reemplaza la portada "Hoy en el taller" de la demo: ya no hay foto de portada ni frase del día.

Bloques, en orden: arriba, "N pedidos atrasados" (si hay) y la fecha; el saludo ("¡Buenas
tardes!") con el nombre del taller; una caja grande para buscar con atajos (Nuevo pedido,
Registrar abono, Cotizar); las tarjetas de lo que hay que hacer hoy, con la foto de cada
pedido; "Tu mes" (cobrado, gastado, por cobrar y en producción); "Cobrado y gastado por mes"
junto a "Quién te debe"; y los pedidos por etapa.

Lista cuando:
- El saludo cambia con la hora: "¡Buenos días!" hasta las 12, "¡Buenas tardes!" hasta las 6
  y "¡Buenas noches!" después (hora de Bogotá).
- Las cifras de "Tu mes" coinciden con los cálculos de `docs/02-modelo-de-datos.md` y cada
  una abre la pantalla de donde sale (Resumen o Pedidos con su filtro).
- Las tarjetas de lo que hay que hacer hoy van en este orden: los pedidos atrasados, los que
  están listos sin entregar, los que se entregan en 7 días y los cotizados sin confirmar.
  Cada una lleva la foto del pedido (o un dibujo de prenda), su insignia de urgencia y la
  acción que sigue:
  - atrasado: "Marcar como listo" y "Avisar";
  - listo: "Marcar como entregado" y "Avisar";
  - cotizado: "Confirmar pedido" y "Avisar" (el mensaje para preguntar si confirma);
  - se entrega pronto y no le toca nada: "Ver el pedido".
- Las acciones cambian el pedido sin recargar la página y la tarjeta se actualiza o desaparece.
- Sin pendientes, dice que no hay nada por hacer hoy.
- La gráfica muestra lo cobrado y lo gastado de los últimos seis meses.
- "Quién te debe" lista los clientes con saldo, del que más debe al que menos, con una barra
  proporcional. El que tiene un pedido atrasado lleva la insignia "Vencida" y su barra en rojo.
- Los pedidos por etapa muestran cuántos hay en cada etapa y cuántos van atrasados.
- La costurera no ve la plata: ni la gráfica, ni "Quién te debe", ni las cifras en pesos.

## Pedidos

Referencia: `diseno/pedidos.html`.

Lista de pedidos con filtros y buscador.

Lista cuando:
- Arriba, una barra de cifras: activos, en producción, se entregan esta semana, atrasados y
  por cobrar.
- Las pestañas Todos, En producción, Esta semana, Atrasados, Con saldo y Entregados
  funcionan y muestran su conteo.
- El buscador (la lupa) encuentra por cliente, prenda o encargada, sin importar tildes ni
  mayúsculas.
- Cada fila muestra la foto del pedido, cliente, prenda, entrega (con los días de atraso en
  rojo), total, pago, etapa, tallas recibidas y encargada.
- Las insignias de pago y de etapa usan los tonos y circulitos de `docs/08-diseno.md`:
  "Vencido" en rojo, "Abonado N %" en naranja, "Pagado" y "Entregado" en gris, "Listo" en
  verde, "En corte" y "En confección" en azul, "Confirmado" en ámbar.
- La lista se ordena por fecha de entrega, con los entregados al final.
- Tocar una fila abre el pedido.
- En celular cada pedido es una fila con su foto, nombre, total, fecha, encargada y sus dos
  insignias.

## Nuevo pedido

Referencia: `diseno/nuevo-pedido.html`. Una ventana con campos.

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

Arriba: la miga para volver a Pedidos, "Avisar al cliente", "Más acciones" (eliminar el
pedido) y las flechas para pasar al pedido anterior o al siguiente (en el orden de la lista).
Debajo, el nombre del cliente con las insignias de pago y de etapa, cuándo se creó y cuándo se
entrega. Columna izquierda: la prenda con su etapa (y el botón del paso que sigue), el pago,
las tallas y la cronología. Columna derecha: cliente, entrega, foto y materiales. Cada columna
mide lo que mide su contenido.

Lista cuando:
- Tocar una etapa la guarda y se ve sin recargar la página.
- Se puede elegir la encargada entre las usuarias del taller.
- Se puede cambiar la fecha de entrega y el WhatsApp del cliente. Dice en cuántos días se
  entrega, o cuántos lleva de atraso.
- Registrar un abono baja el saldo y mueve la barra sin recargar la página.
- Con saldo en 0 la insignia dice "Pagado", en gris.
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
- Subir, cambiar y quitar la foto del pedido (es la que sale en Hoy y en la lista).
- Eliminar el pedido, con confirmación.

## Formulario público de tallas

Referencia: `diseno/tallas-publico.html` y `diseno/tallas-publico-listo.html`. Una tarjeta
centrada, pensada para celular.

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
- Cada entrega se ve en su día: por entregar (ámbar), atrasada (rojo) o entregada (gris),
  con la leyenda debajo. En celular cada entrega es una barrita de su color.
- Tocar un día filtra la lista de entregas.
- "Semana más cargada" dice cuál es la semana con más entregas, o que no se juntan.

## Clientes

Referencia: `diseno/clientes.html`.

Aviso de la próxima fecha de dotación y tabla de clientes.

Lista cuando:
- El aviso dice cuántos días faltan para la próxima fecha de dotación y cuántos clientes
  empresa hay. Su botón prepara el mensaje para ellos.
- La tabla muestra tipo, número de pedidos, cuánto ha comprado y cuánto debe. Sin deuda dice
  "Al día", en gris. Una deuda de un pedido atrasado va en rojo, con la insignia "Vencida".
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

Referencia: `diseno/telas.html` y, sin telas, `diseno/telas-vacia.html`.

Lista cuando:
- Las tres cifras dicen cuántas telas hay, cuántos metros suman y cuáles se están acabando.
- La tabla muestra cada tela con los metros que quedan, el mínimo para avisar y su estado:
  "Se está acabando" en ámbar o "Suficiente" en gris.
- Sin telas, se ve la pantalla vacía con su dibujo y el botón para agregar la primera.
- "Entró" suma metros y "Usé" resta, sin bajar de 0. Cada movimiento queda en el historial.
- Se puede agregar y quitar una tela.

## Resumen del mes

Referencia: `diseno/resumen.html`.

Lista cuando:
- Muestra vendido, cobrado, gastado y "te quedó" del mes elegido.
- Se puede cambiar de mes.
- La gráfica muestra lo cobrado y lo gastado de los últimos seis meses.
- Se puede registrar y quitar un gasto, con concepto, tipo, valor y fecha.
- Muestra ventas por tipo de cliente y pedidos en producción por persona.
- "Descargar para Excel" baja un archivo con cuatro hojas: Pedidos, Abonos, Gastos y Telas.

## Mi taller

Referencia: `diseno/mi-taller.html`. Cada bloque con su explicación a la izquierda, como los
ajustes de Shopify.

Lista cuando:
- La dueña cambia el nombre y el logo del taller.
- La dueña crea, desactiva y cambia el nombre de las costureras.
- El nombre del taller aparece en el menú, en los mensajes y en los recibos.
- Con el asistente prendido, el bloque "Asistente" dice "N de 600 preguntas este mes" con el
  riel azul, y cuántas lleva hoy (tanda 7).

## Asistente

Tanda 7. Referencia: `diseno/asistente.html` y, sin preguntas, `diseno/asistente-limite.html`.
Qué es, qué contesta y qué no: `docs/10-asistente.md`.

Lista cuando:
- El botón "Asistente" sale en el encabezado de todas las pantallas, a la izquierda del
  principal, solo para la dueña, solo con la clave puesta y solo si David prendió el asistente
  de su taller. Ctrl J lo abre y lo cierra; Esc lo cierra.
- Con la conversación vacía se ve el saludo y tres sugerencias que se pueden tocar.
- Una pregunta muestra la burbuja enseguida, los tres puntos mientras busca y luego la
  respuesta, con lo que revisó arriba, las tarjetas con cifras y un enlace a la pantalla.
- Las cifras de las tarjetas son las mismas de las pantallas (Hoy, Pedidos, Resumen).
- Sabe en qué pantalla está: "este pedido" dentro de un pedido es ese pedido.
- "Escríbele…" deja un mensaje para revisar, con "Abrir en WhatsApp" (o "Copiar" si el
  cliente no tiene número). No envía nada solo.
- "¿Cuánto cobro por…?" da la cotización con los precios guardados y abre el Cotizador con
  las mismas cifras.
- No crea, no cambia y no borra nada.
- "Nueva conversación" la borra. La conversación sigue al cambiar de pantalla.
- Cuando quedan pocas preguntas sale la línea ámbar; sin preguntas, el aviso dice cuándo
  vuelve y la caja queda apagada.
- Funciona en 1280 px (panel al lado), 900 px (panel flotando) y 390 px (pantalla completa).
