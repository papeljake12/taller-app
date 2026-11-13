# Ajuste "pantalla fija y animaciones": Cotizador

Carril F. Pantalla `/cotizador/` (solo la dueña). Referencia: `diseno/cotizador.html`.

## Qué pidió David y qué quería decir para esta pantalla

1. **Pantalla fija en computador:** el Cotizador se ve completo en 1366 x 768 sin que nada se
   desplace, el menú y el título quedan quietos, las dos columnas terminan a la misma altura y
   no queda un espacio vacío al final de la hoja.
2. **Animaciones:** el resultado se calcula mientras se escribe, así que **no puede
   parpadear** con cada tecla. Y al guardar algo sale el **aviso corto** de la demo (la
   píldora negra de abajo).

## Pantalla fija: cómo quedó

Antes del ajuste el Cotizador se pasaba 35 px en 1366 x 768. Con el relleno más pequeño que
puso el coordinador para las pantallas bajitas, **ya cabe sin tocar nada más**. Lo medí con
Chrome, en cuatro tamaños y en varios momentos de uso (vacío, con una de "Mis prendas
guardadas" elegida, con el resultado lleno y con el WhatsApp escrito):

| Tamaño | Espacio para el contenido | Lo que ocupa | ¿Cabe? | ¿La página se desplaza? |
|---|---|---|---|---|
| 1366 x 768 | 682 px | 646 px (sobran 36) | Sí | No |
| 1280 x 800 | 714 px | 646 px (sobran 68) | Sí | No |
| 1440 x 900 | 814 px | 646 px (sobran 168) | Sí | No |
| 1920 x 1080 | 972 px | 694 px (sobran 278) | Sí | No |

(En 1920 x 1080 ocupa más porque allí se usan los espacios de siempre, que son un poco más
grandes.)

- Elegir una prenda guardada no agranda nada: el botón "Quitar de mi lista" cabe en la misma
  fila de "Mis prendas guardadas".
- **Las dos columnas terminan juntas y llegan hasta abajo.** Lo que sobra lo toman la última
  tarjeta de la izquierda ("Tu ganancia") y la tarjeta del resultado, que se estiran hasta el
  final de la hoja. Es la regla común para todas las pantallas: la última tarjeta llega hasta
  abajo y no queda hueco.
- **No hizo falta ninguna regla de estilo propia** ni las piezas `.llenar` / `.desplazable`:
  el Cotizador no tiene listas largas ("Mis prendas guardadas" es una lista desplegable que
  abre el navegador encima, no ocupa alto en la hoja). En mi apartado de `app.css` dejé solo
  una nota que lo explica.
- En **celular** no cambió nada: comparé la captura nueva con la de la tanda 6.

### En 1920 x 1080

Cabe con mucho espacio de sobra, así que "Tu ganancia" queda bastante alta (con unos 280 px
en blanco debajo del botón "Guardar esta prenda en mi lista") y el resultado también. Es lo
mismo que ya pasaba en el diseño con la tarjeta del resultado, ahora también en la izquierda.
Si a David no le gusta, otra opción sería repartir ese espacio entre las cuatro tarjetas de
la izquierda (cada una con unos 70 px en blanco abajo), pero me pareció peor: todas se verían
medio vacías.

### Dos momentos que no caben en 1366 x 768 (pasan y se van)

1. **La pregunta "¿Quitar «Camisa polo bordada» de tus prendas guardadas?"** con sus botones
   "Sí, quitar la prenda" y "Cancelar" agrega 116 px a la tarjeta "Qué prenda". En 1366 x 768
   se pasa **82 px** (en 1280 x 800, 50 px). Mientras la pregunta está a la vista, la hoja se
   desplaza un poco por dentro (el menú y el título siguen quietos, la página no se mueve) y
   la pregunta queda arriba, completa. En 1440 x 900 y más grandes cabe. Para que quepa
   habría que cambiar el diseño; opciones para David:
   - dejarlo así (es lo que hice);
   - hacer la pregunta en una ventanita encima de la pantalla, como en otras partes;
   - poner los dos botones al lado del texto (ahorra unos 46 px; sola no alcanza).
2. **Un mensaje de error de dos renglones debajo de un campo** (por ejemplo, tocar "Guardar
   esta prenda en mi lista" sin escribir la prenda: "Escribe el nombre de la prenda para
   guardarla.") agrega 42 px y se pasa **7 px** en 1366 x 768. Desde 1280 x 800 cabe. No lo
   apreté más porque habría que achicar espacios solo en esta pantalla y dejaría de verse
   igual que las demás. Cuando se corrige el campo, el mensaje se va y vuelve a caber.

## Animaciones

### El resultado no parpadea al escribir

La tarjeta del resultado se cambia entera cada vez que dejas de escribir un momento. Le puse
la marca `data-sin-animar`: así el programa de animaciones la deja quieta, sin desvanecerla,
aunque cambie con cada tecla. Además, sus partes tienen siempre los mismos nombres (ids), que
es lo que el programa mira para saber si algo "llegó" o "se fue".

Lo probé en Chrome escribiendo con pausas (el resultado cambió 5 veces): **ninguna
animación** y la tarjeta nunca dejó de verse completa.

### Lo que entra y sale

- **"Quitar de mi lista"** aparece con un desvanecido cuando eliges una prenda guardada.
- **La pregunta "¿Quitar…?"** entra con un desvanecido; al tocar "Cancelar" o "Sí, quitar la
  prenda" se cierra suave (se encoge y desaparece) en vez de borrarse de golpe.
- Para eso les puse un nombre fijo (id): `quitar-de-mi-lista`, `pregunta-quitar` y
  `pregunta-quitar-botones`. Todo lo demás del formulario ya tenía nombres fijos, así que se
  queda quieto.
- Algo que mejoré de paso: si usas el teclado, al tocar "Cancelar" el cursor vuelve a "Quitar
  de mi lista", y al quitar la prenda queda en "Mis prendas guardadas". Antes se perdía,
  porque el botón que tocaste desaparece.

### Avisos cortos

| Acción | Aviso | ¿De la demo? |
|---|---|---|
| Guardar esta prenda en mi lista | "Prenda guardada en tu lista." | Sí |
| Sí, quitar la prenda | "Prenda quitada de tu lista." | Sí |
| Crear pedido con esta cotización | "Pedido creado como cotizado." | Sí |

- El de crear el pedido sale **en la página del pedido nuevo**, porque esa acción te lleva
  allá.
- Antes, "Prenda guardada en tu lista." y "Prenda quitada de tu lista." salían como una nota
  gris dentro de la tarjeta "Qué prenda". Ahora salen en el aviso corto, como en la demo, y
  la nota ya no sale (si salieran los dos, diría lo mismo dos veces y la tarjeta crecería).
  La nota **solo** sale si el teléfono o el computador no tienen JavaScript, porque ahí no
  hay aviso corto.
- No hay aviso al hacer la pregunta, al cancelar, cuando hay errores ni mientras se escribe:
  ahí no se guardó nada.
- La demo también tiene "Copiado. Ya lo puedes pegar en WhatsApp." al copiar la cotización.
  Copiar no guarda nada y el botón ya dice "Copiado" un momento, así que no lo agregué. Si
  David lo quiere, es un cambio en `static/js/app.js` (lo hace el coordinador).

## Qué archivos cambiaron

- `cotizador/vistas.py`: los tres avisos (con `avisar`), y la nota de la prenda solo sin
  JavaScript.
- `cotizador/templates/cotizador/_resultado.html`: la marca `data-sin-animar`.
- `cotizador/templates/cotizador/_que_prenda.html`: los nombres fijos (ids) de "Quitar de mi
  lista" y de la pregunta, y a dónde va el cursor después.
- `cotizador/tests/test_cotizador.py`: pruebas de los avisos y de los ids.
- `cotizador/tests/test_pantalla_fija_cotizador.py` (nueva): abre el Cotizador en Chrome, en
  1366 x 768 y 1920 x 1080, elige la camisa polo de "Mis prendas guardadas", llena el
  resultado y comprueba que cabe, que la página no se desplaza, que las dos columnas terminan
  juntas al final de la hoja y que el resultado no se anima al escribir.
- `static/css/app.css`: solo una nota en el apartado del Cotizador.

## Qué probé

- `uv run pytest` completo.
- En Chrome, con un navegador automático: escribir (el resultado no parpadea), elegir una
  prenda, preguntar, cancelar, guardar, quitar y crear el pedido. Salen los tres avisos, la
  pregunta se cierra suave, el cursor queda donde debe y no hay errores de JavaScript.
- Lo mismo con "menos movimiento" encendido: nada se anima y los avisos igual salen.
- Las capturas de `herramientas/capturas.py --formatos fijo` en 1366 x 768, 1920 x 1080 y
  celular: "bien" en los tres.

## Qué no pude comprobar

- Un Chrome con ventana de verdad en Windows: el navegador automático esconde las barras de
  desplazamiento. En los dos momentos que no caben (la pregunta y un error), en un Chrome
  normal aparecerá la barra de la hoja mientras duren.
- Un celular o una tableta de verdad, y otros navegadores (Firefox, Safari).
