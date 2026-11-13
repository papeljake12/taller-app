# Ajuste de pantalla fija y animaciones: Calendario

Carril D. Pantalla: **Calendario** (`/calendario/`). Referencia: `diseno/calendario.html`.

## Qué cambió y por qué

### En el computador, la pantalla queda fija y sin hueco

Con lo compartido el Calendario ya cabía con los datos de ejemplo, pero tenía dos problemas:

- **Quedaba un espacio vacío** debajo de la leyenda ("Por entregar · Atrasado · Entregado"):
  unos 40 px en 1366 x 768 y unos 350 px en 1920 x 1080. Los cuadros de los días medían
  siempre lo mismo (92 px), sin importar el tamaño de la ventana.
- **Con muchas entregas no cabía**: con 39 entregas en noviembre, la hoja medía 2.471 px y
  se desplazaba entera (el mes, la lista y todo). Y un día con varias entregas estiraba su
  semana hasta que el mes se salía de la pantalla.

Ahora:

- **El mes llena su tarjeta.** Las semanas del mes (pueden ser 4, 5 o 6) se reparten el alto
  que queda, todas del mismo alto, y la leyenda queda abajo. En 1366 x 768 cada semana mide
  98 px en un mes de seis semanas; en 1920 x 1080, 147 px. Así no queda hueco y el mes se ve
  completo, como un calendario de pared.
- **Un día con más entregas de las que caben en su cuadro** muestra las primeras (la última
  suele verse a medias, y eso avisa que hay más) y ya no estira su semana. No se pierde nada:
  tocar el día muestra todas sus entregas en la lista de la derecha, el nombre completo de
  cada una está siempre en esa lista, y el lector de pantalla dice cuántas son ("20 de nov,
  5 entregas"). Cada entrega conserva su tamaño (hasta tres líneas, como en el diseño): no
  se aplasta para caber.
  Primero hice que las de más se desplazaran dentro del día, pero al probar con el teclado
  vi que Chrome convierte esa parte en una parada más del tabulador *dentro* del botón del
  día (el tabulador se detenía en el día y luego en sus entregas). Un botón no puede tener
  otra cosa que se enfoque adentro, así que lo cambié: el día muestra las que caben.
- **A la derecha**, "Entregas del mes" mide lo que sus filas, como en el diseño, y "Semana
  más cargada" llega hasta abajo. Si las entregas son muchas, la tarjeta de entregas se
  encoge hasta donde cabe y **solo su lista se desplaza por dentro**; el título ("Entregas de
  noviembre") y "Semana más cargada" quedan quietos y a la vista.
- **Las dos columnas terminan a la misma altura**, abajo del todo.
- **En una ventana angosta** (de 768 a unos 1.080 px de ancho con el menú abierto) las dos
  columnas se angostan juntas. Sin esto, la de la derecha se saldría de la hoja y quedaría
  cortada (ver "Pedido al coordinador").
- **Una ventana muy baja** no aplasta las semanas: el bloque del mes y la lista mide al menos
  420 px (cada semana sigue midiendo unos 56 px). Si la ventana es más baja que eso, se
  desplaza la hoja, nunca la página.

No cambió ningún color, texto ni el orden de nada. En el celular todo sigue igual: la captura
de 390 px es idéntica, punto por punto, a la de antes del ajuste.

### Animaciones

- **Cada entrega de la lista tiene un nombre fijo** (`entrega-` y el número del pedido). Al
  tocar un día, las entregas de los otros días se cierran suavemente y la del día se queda
  quieta. Al tocar "Ver todo el mes", las demás vuelven a aparecer con un desvanecido.
- **"Ver todo el mes" también tiene su nombre** (`calendario-ver-mes`): aparece y se va con
  un desvanecido, y si se toca otro día se queda quieto.
- **La cuadrícula del mes no parpadea.** Llega aparte (para marcar el día elegido), pero los
  días tienen los mismos nombres que antes, así que no se anima. Encontré un parpadeo
  pequeño: el día que se acaba de tocar queda debajo del mouse, y su fondo gris de "mouse
  encima" se volvía a pintar con una transición, de blanco a gris. Lo quité: en el computador
  ese fondo gris cambia directo (el resto de los botones sigue igual).
- **No lleva aviso corto.** El calendario no guarda nada: tocar un día o cambiar de mes solo
  muestra otra cosa. La demo (`demo/index.html`) tampoco tiene aviso para estas acciones.

## Cuánto mide ahora

Medido en Chrome con los datos de ejemplo (6 pedidos; noviembre de 2026 tiene seis semanas).
"Contenido" es lo que mide lo de adentro de la hoja; "espacio", lo que cabe sin desplazarse.

| Tamaño | Contenido / espacio | ¿Cabe? | ¿Se desplaza la página? | Columnas |
|---|---|---|---|---|
| 1366 x 768 | 682 / 682 px | Sí | No (768 en 768) | Parejas, hasta abajo |
| 1920 x 1080 | 972 / 972 px | Sí | No (1080 en 1080) | Parejas, hasta abajo |
| Celular (390 px) | se desliza como antes | | | Igual que antes |

Con 39 entregas en el mes (6 el mismo día, con nombres largos) también cabe en 1366 x 768,
1920 x 1080, 1280 x 800, 1440 x 900 y 1024 x 768, y en mayo de 2027 (otro mes de seis
semanas, que empieza en sábado).

## Qué se desplaza por dentro, y desde cuándo

- **La lista "Entregas del mes"**: desde unas 9 entregas en 1366 x 768 y unas 13 en
  1920 x 1080 (depende de cuántas líneas ocupe la frase de "Semana más cargada"). Con 39
  entregas, en 1366 x 768 se ven 516 px de una lista de 2.305 px.
- Nada más. Las entregas de un día que no caben en su cuadro no se desplazan (ver arriba):
  se ven en la lista al tocar el día. Cuántas caben en un día: en 1366 x 768, en un mes de
  seis semanas, una con un nombre de tres líneas o dos con nombres cortos; en un mes de cinco
  semanas, algo más. En 1920 x 1080, unas tres.

## Pruebas

En `pedidos/tests/test_calendario.py`, nuevas:

- las dos columnas llevan lo de la pantalla fija y la tarjeta de entregas su clase;
- las filas van dentro de la parte que se desplaza, con el título afuera; un mes sin
  entregas no la lleva;
- cada entrega lleva el número de su pedido, y lo conserva al tocar un día y al volver al mes;
- "Ver todo el mes" lleva su nombre;
- la cuadrícula que llega aparte trae los mismos nombres de días;
- tocar un día no manda aviso;
- **una prueba en Chrome**: un mes con 36 entregas (5 el mismo día) en 1366 x 768 y en
  1920 x 1080. Comprueba que ni la página ni la hoja se desplazan, que la lista sí, que las
  dos columnas terminan parejas y sin hueco, que las 42 casillas del mes miden lo mismo y se
  ven completas con la leyenda debajo, y que el día con 5 entregas muestra las que caben sin
  desplazarse por dentro (para no agregar una parada del tabulador dentro del día).

Y se ajustaron dos pruebas que miraban la clase de la tarjeta y el botón "Ver todo el mes".

## Qué probé a mano (con un navegador automático)

- Capturas con `herramientas/capturas.py --formatos fijo` antes y después, con los ejemplos y
  con 39 entregas: sin "NO CABE".
- En Chrome: tocar un día (se cierran 38 filas, la que sigue no se mueve, la cuadrícula no
  se anima, el día queda marcado y la dirección cambia), "Ver todo el mes" (entran las 38
  con desvanecido, el cursor vuelve al día) y la rueda del mouse sobre un día lleno (no lo
  elige ni mueve la hoja). Sin errores de JavaScript y sin aviso.
- Con el teclado: desde un día, el tabulador pasa al día siguiente, también en un día lleno.
- Lo mismo con "menos movimiento" pedido en el equipo: nada se anima.
- Ventanas angostas (768, 800, 900 y 1024 px, con el menú abierto y contraído): nada se sale
  de la hoja.

## Qué no pude comprobar

- **La barra de desplazamiento de la lista.** El navegador automático no dibuja barras de
  desplazamiento, así que no vi cómo se ve la de "Entregas del mes"; sí medí que la lista se
  desplaza y que el resto queda quieto.
- Safari, Firefox y pantallas táctiles grandes (tabletas): solo probé Chrome.

## Para que David decida (opcional)

Cuando un día tiene más entregas de las que caben, hoy se ven las primeras (la última a
medias) y el resto está en la lista al tocar el día. Otra opción, que cambiaría el diseño y
por eso no la hice, es mostrar las que quepan y una línea "+2 más". Se puede hacer después si
David la prefiere.

## Pedido al coordinador

En `static/css/app.css`, sección 6, la regla `.llenar > * { flex-shrink: 0; }` también se
aplica a las columnas de unas `.dos-columnas.llenar`, que van una al lado de la otra. Ahí
`flex-shrink: 0` impide que las columnas se angosten, y como esas `.dos-columnas` no se
parten en dos filas (`flex-wrap: nowrap`), en una ventana de menos de unos 1.080 px de ancho
con el menú abierto la columna de la derecha se sale de la hoja y queda cortada. Lo corregí
para el Calendario en su apartado (`.dos-columnas--calendario > * { flex-shrink: 1; }`). Para
todas las pantallas bastaría con agregar en la sección 6:

```css
.dos-columnas.llenar > * {
  flex-shrink: 1;
}
```
