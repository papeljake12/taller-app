# Ajuste de Pedidos, Buscar y Nuevo pedido: pantalla fija y animaciones

Carril B. Pantallas: **Pedidos** (con sus filtros), **Buscar** (el buscador del menú) y
**Nuevo pedido** (la ventana y su página sin JavaScript).

## Cómo estaban

Con los 6 pedidos de ejemplo ya cabían en 1366 x 768 y en 1920 x 1080. El problema era con
muchos datos: con 48 pedidos, la hoja de Pedidos medía 3033 px en un espacio de 682 px, y se
desplazaba toda la hoja, incluidos los filtros y el buscador, que se perdían de vista. En
Buscar pasaba lo mismo con muchos resultados.

## Qué cambió

### Pedidos: solo la tabla se desplaza

- La tarjeta de la tabla ahora **llega hasta abajo y no más** (`llenar`). Los filtros y el
  buscador quedan quietos arriba.
- Si los pedidos no caben, **la tabla se desplaza por dentro de su tarjeta** (`desplazable`),
  con su encabezado ("Cliente y pedido", "Etapa"...) fijo arriba, para que siempre se sepa qué
  es cada columna.
- Entre la tarjeta y la tabla hay una cajita que es la que cambia el buscador mientras se
  escribe (`zona-tabla`). Tuvo que aprender a pasarle el alto de la tarjeta a la tabla; si no,
  la tabla no sabía hasta dónde llegar.

Con los ejemplos se ve igual que antes. La tabla empieza a desplazarse por dentro desde unos
**9 pedidos en 1366 x 768** y unos **13 en 1920 x 1080** (en pantallas altas las filas tienen
un poco más de aire).

### Buscar: cómo se reparten el alto las dos tarjetas

Buscar puede traer dos tarjetas de resultados, una de Pedidos y otra de Clientes. Había que
decidir qué pasa si no caben. La regla que elegí es la de "llenar vasos de agua por igual":

- Si las dos caben, cada una mide lo que necesita y **la última llega hasta abajo** (como antes).
- Si una es corta y la otra larga, **la corta se ve entera** y la larga toma todo el resto y se
  desplaza por dentro. Por ejemplo, 40 pedidos de un colegio y 1 cliente: el cliente se ve
  completo abajo y los pedidos ocupan lo demás.
- Si las dos son largas, **mitad y mitad**, y cada una se desplaza por dentro.

Para lograrlo, en esa pantalla la hoja se arma como una rejilla (CSS *grid*), que es la única
forma de hacer este reparto sin JavaScript. Solo aplica en Buscar y solo cuando hay
resultados. La lista de clientes quedó dentro de una cajita `desplazable` para poder
desplazarse; en el celular esa cajita no cambia nada.

### Nuevo pedido

- **No necesitó cambios de tamaño.** La ventana mide 519 px de alto en una pantalla de
  768 px; aun con todos los campos en rojo (todos los errores a la vez) mide 682 px y cabe
  entera, con el botón "Guardar pedido" a la vista. Abierta como página (sin JavaScript), con
  o sin errores, también cabe.
- **Aviso corto al guardar.** Después de crear el pedido, la aplicación lleva al pedido nuevo
  y ahí aparece la píldora negra **"Pedido guardado."**. El texto es el de la demo: en
  `demo/index.html`, la ventana "Nuevo pedido" dice `toast('Pedido guardado.')`. (El otro
  texto, "Pedido creado como cotizado.", es el del Cotizador, que es de otro carril.) Como la
  respuesta lleva a otra página, el aviso viaja como "mensaje" y se muestra al llegar. Si el
  formulario tiene errores no hay aviso: no se guardó nada. Sin JavaScript también avisa.

## Animaciones

- **Cada fila de la tabla tiene su nombre fijo** (`id="pedido-12"`, con el número del pedido).
  Así, mientras se escribe en el buscador, la aplicación sabe qué filas siguen y cuáles se
  van: **solo se desvanecen las que salen y solo aparecen suave las que entran**; las que se
  quedan no se mueven ni parpadean, y la tabla entera tampoco.
- La tabla y el aviso "Ningún pedido coincide con lo que buscas." también tienen su nombre
  (`lista-pedidos-tabla` y `lista-pedidos-vacia`): cuando ya nada coincide, la tabla se
  desvanece y el aviso aparece suave; al borrar lo escrito, al revés.
- No usé `data-sin-animar`: el buscador sí debe mostrar qué filas entran y salen, y los
  filtros que llegan con la tabla conservan su nombre (`filtros-pedidos`), así que no se
  animan.
- Lo demás (botones, "cargando", la ventana que abre y cierra) ya venía de lo compartido.

## Cuánto mide cada pantalla ahora

Contenido de la hoja frente al espacio que tiene (si el primero no pasa del segundo, cabe).
La página nunca se desplaza: mide exactamente lo que la ventana.

| Pantalla | 1366 x 768 | 1920 x 1080 |
|---|---|---|
| Pedidos (6 de ejemplo) | 682 en 682, cabe | 972 en 972, cabe |
| Pedidos, filtro Atrasados | 682 en 682, cabe | 972 en 972, cabe |
| Buscar «esquina» | 682 en 682, cabe | 972 en 972, cabe |
| Nuevo pedido (página) | 682 en 682, cabe | 972 en 972, cabe |
| Pedidos con 48 pedidos | cabe; la tabla muestra 560 px de 2910 | cabe; 846 px de 3202 |
| Buscar con 42 pedidos y 31 clientes | cabe; 291 y 291 px | cabe; 432 y 432 px |
| Buscar con 40 pedidos y 1 cliente | cabe; pedidos 499 px, cliente entero (83 px) | cabe; 771 y 93 px |
| Buscar con 2 pedidos y 30 clientes | cabe; pedidos enteros (201 px), clientes 381 px | cabe; 223 y 641 px |

También lo medí en 1280 x 720, 1024 x 768, 800 x 600 y 768 x 1024: en todas cabe y solo se
desplazan las listas.

## Qué probé

- Las pruebas de `pedidos/tests/test_lista.py`, con nuevas:
  - la tarjeta y la tabla llevan `llenar` y `desplazable`;
  - cada fila tiene su id `pedido-N`, el mismo en la página y en la respuesta del buscador;
  - el aviso de "nada coincide" tiene su id;
  - al crear un pedido (con y sin JavaScript) la página del pedido trae "Pedido guardado." una
    sola vez, y con errores no hay aviso;
  - en Buscar, cada lista de resultados está en su tarjeta con su parte que se desplaza;
  - una prueba que abre Chrome con 40 pedidos y 25 clientes más y comprueba, en 1366 x 768 y
    en 1920 x 1080, que la página y la hoja no se desplazan, que la tabla sí (con el
    encabezado fijo), que en Buscar dos listas largas van mitad y mitad y que una corta se ve
    entera; y que en el celular la página se sigue deslizando.
- `uv run pytest` completo, incluida `tests/test_pantalla_fija.py`.
- A mano, con Chrome automático (Playwright), con muchos pedidos: bajar la tabla con la rueda
  del mouse (se mueve solo la tabla, el encabezado queda arriba), escribir en el buscador
  (salen y entran solo las filas que cambian, el cursor no se pierde), llegar a "nada
  coincide" y volver, abrir "Nuevo pedido", guardar vacío (errores sin aviso) y guardar bien
  (sale "Pedido guardado." y lo oye el lector de pantalla). Sin errores de JavaScript. Lo
  repetí con "menos movimiento" activado: nada se anima y todo funciona igual.
- Como costurera (`ejemplo.marta`): sin la columna Saldo ni clientes en Buscar, todo cabe.
- En el celular las capturas de las cuatro pantallas son idénticas, píxel por píxel, a las de
  antes de este cambio.

## Lo que no pude comprobar

- En un iPhone o Android de verdad: solo en Chrome simulando un celular de 390 px.
- En Firefox o Safari: el reparto de Buscar usa `:has()`, que funciona en los navegadores de
  los últimos años; en uno muy viejo, Buscar se vería como antes (la hoja se desplaza entera).

## Algo que encontré y no cambié

Entre 768 y unos 1100 px de ancho (una tableta acostada, o el computador con la ventana a
medio ancho), la columna "Cliente y pedido" de la tabla queda muy angosta: las otras columnas
tienen ancho fijo (el del diseño) y a ella le queda muy poco, así que los nombres se parten
en muchas líneas y el detalle se monta sobre la etiqueta de la etapa. Ya pasaba antes de este
ajuste y no es de la pantalla fija. Una solución sencilla sería darle a la tabla un ancho
mínimo para que en esas pantallas se desplace también hacia el lado dentro de su tarjeta.
Queda para que David decida.
