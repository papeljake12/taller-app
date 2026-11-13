# Ajuste de la pantalla Hoy: pantalla fija y animaciones

Carril A. Pantalla Hoy (`/`), también con el menú contraído y como costurera.

## El problema

Hoy era la pantalla con más cosas: las cuatro cifras, "Qué hacer hoy", "Trabajos del taller",
la gráfica, "Quién te debe" y "Pedidos por etapa". En una pantalla de 1366 x 768 tenía 968 px
de contenido en un espacio de 682 px: la hoja tenía que desplazarse. En 1920 x 1080, 1102 px en
972. Con el menú contraído, un poco más (1004 y 1137 px), porque la gráfica crece con el ancho.

## Qué cambió

Nada se quitó ni cambió de orden ni de color. Lo que cambió es cómo se reparte el alto.

1. **El tablero toma el alto de la hoja** y lo reparte así:
   - las cifras, la fila de la gráfica y "Pedidos por etapa" miden lo que su contenido;
   - la fila de "Qué hacer hoy" y "Trabajos del taller" toma **todo lo que queda**.
2. **"Qué hacer hoy" se desplaza por dentro.** Si los pendientes no caben, se desplaza solo esa
   lista, con el título de la tarjeta quieto. La foto de "Trabajos del taller" crece o se achica
   para que las dos tarjetas terminen a la misma altura (nunca baja de 120 px).
3. **La gráfica es más baja en el computador.** Se dibuja con 114 de alto en vez de 200. En
   celular sigue la de siempre. En pantallas bajas no pasa de 114 px: si su tarjeta es más
   ancha (menú contraído), la gráfica queda centrada en vez de crecer. En pantallas altas crece
   con el ancho hasta 190 px.
4. **"Quién te debe" mide lo que mide la gráfica** de al lado y, si hay muchos clientes que
   deben, su lista se desplaza por dentro.
5. **Más apretado en pantallas bajas** (hasta 900 px de alto): las cifras, las cabezas de las
   tarjetas, la nota de las fotos, las filas de "Quién te debe" y "Pedidos por etapa" tienen
   un poco menos de relleno y renglones más juntos.
6. **"Pedidos por etapa": el número y su etiqueta van en la misma línea** ("1" y "1 atrasado"),
   en vez de una debajo de la otra. Ahorra un renglón entero.
7. **Si la hoja es angosta** (una tableta, o la ventana a medio ancho) y las tarjetas de una
   fila ya no caben de lado a lado, Hoy se apila como antes y se desplaza la hoja. Para saberlo
   se mide el ancho del tablero, no el de la ventana, porque depende de si el menú está
   contraído.
8. **Si la ventana es muy baja** (por ejemplo 1280 x 600), no se monta nada encima de nada: se
   desplaza la hoja, debajo del título. La página sigue quieta.

En celular no cambia nada: comparé la captura de antes y la de después, píxel por píxel, como
dueña y como costurera, y son iguales (solo cambia el brillo de la foto que va apareciendo).
Para que siga igual, dos reglas pequeñas compensan que ahora las listas van dentro de una caja:
la cabeza de "Quién te debe" conserva su relleno apretado de celular, y la nota "No hay nada
por hacer hoy." sigue sin relleno de más arriba.

## Cuánto mide ahora

| Tamaño | Antes | Ahora |
|---|---|---|
| 1366 x 768 | 968 px en 682 | 682 en 682: cabe |
| 1366 x 768, menú contraído | 1004 en 682 | 682 en 682: cabe |
| 1920 x 1080 | 1102 en 972 | 972 en 972: cabe |
| 1920 x 1080, menú contraído | 1137 en 972 | 972 en 972: cabe |
| Costurera (1366 y 1920) | ya cabía | cabe |

Así se reparten los 682 px de 1366 x 768 (dueña): cifras 85, "Qué hacer hoy" y fotos 226,
gráfica y "Quién te debe" 223, "Pedidos por etapa" 104, y 12 px entre cada bloque. La página
nunca se desplaza y no queda hueco al final. Las dos tarjetas de cada fila terminan parejas.

También lo medí en 1280 x 800, 1440 x 900 y 1600 x 900: cabe en todas. En 1024 x 768 cabe con
el menú contraído; con el menú abierto la hoja es angosta y Hoy se apila (punto 7).

## Qué listas se desplazan por dentro

- **"Qué hacer hoy".** En 1366 x 768 se ven una fila y media (184 px): con los 3 pendientes de
  los ejemplos ya se desplaza. En 1920 x 1080 caben unos 3 pendientes (331 px). Con 40 pedidos
  de prueba, solo la lista se desplaza; la página y la hoja se quedan quietas.
- **"Quién te debe".** En 1366 x 768 caben 4 clientes; desde el quinto se desplaza. En
  1920 x 1080 caben 4 completos y se asoma el quinto.

La costurera no tiene la fila de la plata, así que su "Qué hacer hoy" es mucho más alto (419 px
en 1366 x 768) y no se desplaza con los ejemplos. En 1920 x 1080 su foto queda grande y su
lista con espacio en blanco abajo: es lo que pide la regla de que la última tarjeta llegue
hasta abajo y que las dos de la fila terminen parejas.

## Animaciones

- **Las filas de "Qué hacer hoy" ya tenían su id** (`pendiente-12`). Lo nuevo es que las
  acciones ("Marcar como listo", "Marcar como entregado") ya no cambian la tarjeta entera: solo
  lo de adentro de la lista. Así:
  - la lista **no vuelve arriba** si estaba desplazada (antes volvía, porque la tarjeta era
    nueva);
  - la fila que se entrega **se cierra suave**;
  - la que se marca como lista sigue en su lugar, sin parpadear, y solo cambian sus botones.

  La cuenta de pendientes ("3 pendientes") llega aparte, en su propia parte
  (`_hoy_cuenta.html`).
- **Las filas de "Quién te debe" ahora tienen id** (`deudor-` y el número del cliente), el
  mismo en la página y cuando la tarjeta llega otra vez después de una acción: las filas que
  siguen no parpadean.
- **Avisos cortos: no agregué ninguno.** Las dos acciones de Hoy cambian la etapa de un pedido.
  La demo no muestra aviso al cambiar de etapa, y el cambio se ve justo donde se tocó: la fila
  cambia sus botones o se cierra, y las cifras se actualizan. Por la regla del encargo
  ("no avisar lo que ya se ve donde se tocó, salvo que la demo lo tenga") se queda sin aviso.
  Hay una prueba que lo deja dicho.

## Qué probé

- `uv run pytest`: todas las pruebas pasan, también `tests/test_pantalla_fija.py` (abre Chrome
  y mide cada pantalla). Saqué `hoy` y `hoy-menu-contraido` de la lista de las que no caben.
- Pruebas nuevas en `pedidos/tests/test_hoy.py`: que Hoy viene armado para la pantalla fija
  (las piezas `llenar` y `desplazable`, la gráfica baja y la de celular), que las filas
  conservan su id después de una acción, que al entregar el último pendiente queda la nota
  dentro de la lista, y que las acciones no llevan aviso. Cambié las que esperaban la tarjeta
  entera como respuesta.
- Capturas con `herramientas/capturas.py --formatos fijo`, como dueña y como costurera, con y
  sin menú contraído: "Todas las pantallas caben completas" y "Sin problemas".
- En Chrome, con un navegador automático y 40 pedidos de prueba: desplacé la lista, marqué uno
  como entregado y comprobé que la fila se cerró suave (su alto bajó de 111 a 0 px), que la
  lista se quedó donde estaba, que cambió la cuenta, que el menú no se movió y que no hubo
  errores de JavaScript. Marqué otro como listo: siguió en su lugar con "Cobrar el saldo" y
  "Marcar como entregado". Lo mismo con "menos movimiento" pedido (todo directo, sin
  animación) y como costurera (sin plata en la página).
- Sin fotos en el taller: la invitación "Subir la primera foto" llena su espacio y cabe.
- Después de las pruebas volví a cargar los ejemplos (`cargar_ejemplos`).

## Lo que no pude comprobar

- Cómo se ve la barra para desplazar la lista en un Windows de verdad: el navegador automático
  no la dibuja en las capturas.
- Safari y Firefox: probé solo en Chrome. Lo de medir el ancho del tablero (punto 7) usa una
  función que esos navegadores tienen desde 2023.
- Una tableta de verdad.
