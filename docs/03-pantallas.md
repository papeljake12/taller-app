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

### Tu resumen de hoy (tanda 8, T43)

Referencia: `diseno/hoy-agente.html`. Solo sale con el asistente prendido; con el asistente
apagado, Hoy queda como en `diseno/hoy.html`. Qué es y por qué: `docs/12-agente.md`
("Avisa sin que le pregunten").

Una tarjeta arriba, después del saludo y antes de la caja grande: la esfera, "Tu resumen de
hoy", la hora en que se preparó ("Lo preparé a las 5:00 a. m."), un párrafo que escribió el
agente en la madrugada y, debajo, una fila por cada cosa que pide una acción, con su botón.

Lista cuando:
- El párrafo lo escribe Claude cada madrugada con el comando `preparar_resumen` (lo corre el
  servidor a las 5:00 a. m., hora de Bogotá) y se guarda en `ResumenDelDia`. Ella no espera
  ni gasta preguntas al abrir Hoy.
- Toda cifra en pesos del párrafo coincide con las de la aplicación. Si Claude escribe una
  cifra que no está en los cálculos, el párrafo no se guarda.
- Las filas se calculan al abrir Hoy (siempre al día) y son solo de lo que las tarjetas de
  "lo que hay que hacer hoy" no muestran:
  - a quién cobrar: el cliente, cuánto debe y hace cuánto fue su último abono; la deuda de un
    pedido atrasado lleva la insignia roja "Vencida". Botón "Cobrar" (abre WhatsApp con el
    mensaje de cobro que ya existe);
  - tela que se está acabando o que no alcanza para los pedidos confirmados. Botón "Ver
    telas";
  - pedidos sin entregar que esperan tallas ("Faltan 31 de 40 tallas", ejemplo). Botón
    "Pedir tallas" (el mensaje que ya existe).
- Las cifras de las filas coinciden con "Quién te debe" de Hoy y con Telas.
- Sin párrafo de hoy (la tarea no corrió o falló), se ven solo las filas. Sin nada pendiente,
  la tarjeta no sale.
- Los botones no llaman a Claude.
- En 390 px no se desborda: el botón de cada fila va a la derecha.

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

El cuadro "pega el mensaje del cliente y la IA lo llena" es de la etapa 3. Desde la tanda 8
eso lo hace el agente en su panel (ver "Asistente", abajo); esta ventana no cambia.

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
- **Tela del pedido** (tanda 8): una tarjeta solo para ver, con cada tela que usa el pedido y
  sus metros (el nombre lleva a Telas). La anota el agente al guardar un pedido nuevo;
  corregirla desde aquí llega con T42.
  - Si el pedido está Confirmado y la tela no alcanza: la insignia ámbar "Falta tela" y, debajo
    de esa tela, el aviso "Te faltan N m de X: tienes M m.".
  - Si el pedido ya está en corte o después: la insignia gris "Ya se cortó".
  - Si está Cotizado: sin insignia, porque todavía no aparta tela.
  - Sin tela anotada, la tarjeta no sale.
- **Cronología** (tanda 8): lo que se guardó con el agente (el pedido y sus abonos) lleva
  debajo, en gris y con la esfera pequeña, "Lo anotó el asistente". Lo hecho desde las
  pantallas no lleva nada.

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
- En Hoy, la caja grande le pregunta al asistente (con su avatar y los atajos de siempre):
  lo que se escribe abre el panel con esa pregunta. Con el asistente apagado sigue buscando.
- Con la conversación vacía se ve el saludo y tres sugerencias que se pueden tocar.
- Una pregunta muestra la burbuja enseguida, los tres puntos mientras busca y luego la
  respuesta, con lo que revisó arriba, las tarjetas con cifras y un enlace a la pantalla.
- Las cifras de las tarjetas son las mismas de las pantallas (Hoy, Pedidos, Resumen).
- Sabe en qué pantalla está: "este pedido" dentro de un pedido es ese pedido.
- "Escríbele…" deja un mensaje para revisar, con "Abrir en WhatsApp" (o "Copiar" si el
  cliente no tiene número). No envía nada solo.
- "¿Cuánto cobro por…?" da la cotización con los precios guardados y abre el Cotizador con
  las mismas cifras.
- Tanda 7: no crea, no cambia y no borra nada. Desde la tanda 8 propone borradores que ella
  guarda (abajo). Nunca borra.
- "Nueva conversación" la borra. La conversación sigue al cambiar de pantalla.
- Cuando quedan pocas preguntas sale la línea ámbar; sin preguntas, el aviso dice cuándo
  vuelve y la caja queda apagada.
- Funciona en 1280 px (panel al lado), 900 px (panel flotando) y 390 px (pantalla completa).

### El agente en el panel (tanda 8)

Referencia: `diseno/asistente-agente.html` (borradores) y `diseno/asistente.html` (sin la
insignia y con la nota nueva). Qué hace y por qué: `docs/12-agente.md`.

Ella le cuenta lo que pasó ("me abonaron 500 mil", "pagué la luz") y el agente arma un
**borrador**: una tarjeta con cada cosa que se va a guardar. Nada se guarda hasta que ella
toca **Guardar**.

Lista cuando:
- La insignia "Solo consulta" ya no está. La nota de abajo dice "Nada se guarda hasta que
  toques Guardar. Puede equivocarse: revisa antes de guardar."
- El saludo dice "Cuéntame qué pasó o pregúntame algo de tu taller." La caja del panel dice
  "Cuéntame o pregúntame algo" y la caja grande de Hoy, "Cuéntale o pregúntale algo a tu
  asistente".
- Sabe proponer un pedido nuevo (con su cliente, su abono y su tela), un abono a un pedido
  que ya existe y un gasto. Varias cosas de un mismo mensaje van en un solo borrador.
- La tarjeta del borrador tiene una fila por cosa: qué es en negrita ("Pedido nuevo", "Abono
  de hoy", "Tela", "Tallas", "Gasto"), el detalle en gris, el valor en pesos a la derecha y,
  si falta algo o la tela no alcanza, un aviso ámbar debajo ("Te faltan 48 m", ejemplo).
- Las cifras del borrador las pone la aplicación, no Claude: el total sale del Cotizador con
  la prenda guardada (si ella no dijo otro), el "Falta" sale del saldo y la tela que falta,
  del cálculo de tela comprometida.
- Un pedido con abono dice "Confirmado, porque dejó abono"; sin abono nace Cotizado.
- La tarjeta tiene cuatro estados:
  - **pendiente:** insignia ámbar "Sin guardar", y los botones "Corregir" y "Guardar" (el
    principal, negro);
  - **guardado:** el título cambia a "Guardado", insignia verde "Listo", "Guardado a las …" y
    los enlaces a lo que se creó ("Ver el pedido"). Al recargar el panel sigue en "Listo";
  - **reemplazado:** se corrigió con un borrador nuevo. Queda en gris, con la insignia gris
    "Reemplazado" y sin botones;
  - **fallido:** "No se guardó nada: …" en ámbar con el mensaje de la pantalla y, si se puede
    arreglar sin cambiar el borrador, "Guardar" otra vez.
- "Guardar" guarda todo o nada: si una cosa falla (por ejemplo el abono), no queda ni el
  pedido. Usa los mismos formularios y reglas de las pantallas: lo que la pantalla no deja,
  el agente tampoco.
- Dos toques seguidos no guardan dos veces. Un borrador sirve una sola vez y vence a las 2
  horas ("Este borrador venció. Pídemelo otra vez."). Uno ya usado o de otra persona dice
  "Este borrador ya no sirve." y no guarda nada.
- "Guardar" no cuenta como pregunta y no llama a Claude. En la siguiente pregunta, la
  aplicación le cuenta a Claude lo que ella guardó.
- "Corregir" no abre otra pantalla: pone el cursor en la caja del panel con "Dime qué
  corrijo". Ella escribe ("no, son 35", ejemplo), el agente arma un borrador nuevo y el
  anterior pasa a "Reemplazado".
- **Si no está seguro, pregunta.** Si hay dos clientes, pedidos, prendas o telas parecidas,
  no arma borrador: pregunta "¿a cuál?" con un chip por opción, y tocar un chip manda esa
  opción como respuesta.
- Un pedido o cliente de otro taller da "No encontré ese pedido.", igual que en la tanda 7.
- Lo guardado con el agente queda marcado en la cronología del pedido ("Lo anotó el
  asistente").
- En 390 px la tarjeta no se desborda y los botones miden 40 px.
