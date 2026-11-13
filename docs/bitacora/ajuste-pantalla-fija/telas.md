# Ajuste de Telas: pantalla fija y animaciones

Carril G. Parte del ajuste que pediste: en el computador la pantalla se queda quieta (solo se
mueve la lista larga, por dentro de su tarjeta) y los cambios se ven con animaciones cortas.
En el celular Telas sigue exactamente igual (comparé la captura nueva con la de la tanda 6 y
son idénticas).

## Qué cambió y por qué

### 1. La tabla llega hasta abajo y, si hay muchas telas, solo ella se desplaza

Con las 4 telas de ejemplo Telas ya cabía, pero un taller de verdad puede tener 20 o 30 telas.
Antes, con tantas, la página entera se alargaba y había que bajar, y al bajar se perdían de
vista las tres cifras de arriba. Ahora:

- La tarjeta de la tabla ocupa todo el alto que queda debajo de las cifras, hasta el fondo
  de la hoja. No queda un hueco gris al final.
- Si las telas no caben, **solo la tabla se desplaza, por dentro de su tarjeta**. El
  encabezado de la tabla ("Tela, Quedan, Avisar cuando queden, Estado, Acción") se queda
  pegado arriba mientras bajas, para que siempre sepas qué es cada columna.
- Las tres cifras (Telas, Metros en total, Se están acabando), el título y el botón "Nueva
  tela" se quedan quietos arriba.
- La nota "Toca el nombre de una tela para ver su historial..." sigue justo debajo de la
  tabla cuando hay pocas telas (como antes). Cuando hay muchas, se queda fija abajo de la
  tarjeta, siempre a la vista.

Para esto usé las dos piezas que dejó el coordinador: a la tarjeta le puse `llenar` ("toma el
alto que queda") y a la caja de la tabla `desplazable` ("si no cabe, se desplaza por dentro").
En mi apartado de `app.css` agregué una sola regla: que la tabla mida lo que miden sus filas
(y no se estire), para que la nota quede pegada a la tabla cuando hay pocas telas.

No cambié colores, textos ni el orden de nada, y no quité información.

### 2. Cada fila de la tabla tiene su "nombre" fijo

Cada fila lleva ahora un identificador que no cambia: `tela-12` (el número es el de la tela).
Es como ponerle una etiqueta con nombre a cada fila. Así, cuando la tabla se cambia sin
recargar la página, el navegador sabe cuál fila es cuál:

- La fila de la tela que moviste ("Entró" o "Usé") **no parpadea**: es la misma fila, solo
  cambian sus metros y su estado.
- Una tela nueva **aparece con un desvanecido suave**.
- Una tela que quitas **se desvanece** antes de irse (en unos 150 milisegundos).
- Las demás filas se quedan quietas.

### 3. Avisos cortos al guardar

Después de guardar sale abajo, en el centro, una píldora negra con un texto corto que se va
sola en unos 3 segundos. Los textos son los de la demo:

| Acción | Aviso | ¿De dónde sale? |
|---|---|---|
| Entró / Usé | "Piqué blanco: quedan 6 m." (el nombre de la tela y lo que quedó) | De la demo |
| Nueva tela | "Tela agregada." | De la demo |
| Quitar una tela | "Tela quitada." | **La demo no tenía.** Lo escribí corto y en el mismo estilo que "Foto quitada." y "Prenda quitada de tu lista." |

- Los avisos dicen metros, no plata, así que la costurera también los ve cuando registra
  "Usé" (los permisos dicen que ella no puede ver plata, y esto no lo es).
- Si algo sale mal (por ejemplo, usar más metros de los que quedan), no sale aviso: sale el
  mensaje de error en la ventana, como siempre.
- Sin JavaScript (o si la ventana se abrió como página aparte), el aviso sale en la página de
  Telas a la que vuelves.

## Cuánto mide ahora Telas

Con los datos de ejemplo (4 telas):

| Tamaño de pantalla | Lo que ocupa el contenido | El espacio que hay | ¿Cabe? | ¿La página se desplaza? |
|---|---|---|---|---|
| 1366 x 768 | 408 px | 682 px | Sí | No |
| 1920 x 1080 | 446 px | 972 px | Sí | No |

La tarjeta de la tabla se estira hasta abajo, así que la hoja queda llena (682 de 682 y
972 de 972).

**Desde cuántas telas se desplaza la tabla por dentro:** en 1366 x 768 caben 8 filas a la
vista; desde la novena, la tabla se desplaza. En 1920 x 1080 caben 12; desde la 13, se
desplaza. Lo probé con 30 telas: la tabla mide 1.686 px y se ven 505 (en 1366 x 768), o mide
1.870 px y se ven 805 (en 1920 x 1080). La página y la hoja siguen sin moverse.

## Qué probé

- **Pruebas automáticas nuevas** (en `telas/tests/test_telas.py`): que la tarjeta lleva
  `llenar` y la tabla `desplazable`; que cada fila lleva el id de su tela y lo conserva
  después de "Entró" o "Usé"; que una tela nueva llega con su id y la quitada ya no viene;
  un aviso por cada acción (Entró, Usé, Nueva tela, Quitar), también para la costurera, sin
  JavaScript y desde otra página; y que lo que no se guarda no avisa.
- **Una prueba en Chrome** (en `telas/tests/test_telas_pantalla_fija.py`): un taller con 30
  telas, en 1366 x 768 y en 1920 x 1080. Comprueba que la página y la hoja no se desplazan,
  que solo la tabla lo hace, que el encabezado queda fijo arriba al bajar, que las cifras no
  se mueven y que la tarjeta llega hasta abajo.
- **A mano, con un navegador automático** (Chrome), en computador y en celular, como dueña y
  como costurera: "Usé", "Entró", "Nueva tela", abrir el historial y "Quitar tela". Vi el
  aviso de cada una, que la tela nueva entra con desvanecido, que la quitada se desvanece y
  que las otras filas no parpadean. No hubo errores de JavaScript. También lo probé con
  "menos movimiento" activado en el equipo: todo funciona, sin animaciones.
- Todas las pruebas del proyecto pasan.

## Lo que encontré y no pude arreglar desde aquí

1. **El cursor ya no vuelve al botón "Usé" o "Entró" después de guardar** (solo con
   animaciones; con "menos movimiento" sí vuelve). Antes del ajuste, al guardar, el cursor
   quedaba en el botón que habías tocado, para quien usa el teclado. Ahora la ventana se
   cierra con una animación corta y, mientras se cierra, todavía "tapa" la página, así que el
   navegador no deja poner el cursor en el botón; al terminar de cerrarse, el botón original
   ya fue reemplazado y el cursor se pierde. El arreglo va en `static/js/app.js`, que es un
   archivo compartido: se lo pedí al coordinador (lo probé inyectándolo solo en el navegador
   de prueba y funciona).
2. **Una fila de tabla que se quita se desvanece, pero no se "cierra"**: las filas de abajo
   suben de golpe al final. Así lo decidió el coordinador para las filas de tabla (en
   `app.js`, solo las filas que no son de tabla se cierran suavemente). Lo dejo anotado por si
   quieres que también se cierren.
3. **El historial con muchos movimientos** (hasta 30) se desplaza entero dentro de la
   ventana, con el título y los botones "Cerrar" y "Quitar tela" incluidos: hay que bajar
   hasta el final para verlos. Es como funcionan todas las ventanas desde antes; no lo cambié
   porque la ventana es una pieza compartida.

## Lo que no pude comprobar

- No lo probé en un celular ni en un computador de verdad, solo en Chrome automático con
  esos tamaños de pantalla.
- No probé otros navegadores (Firefox, Safari).
