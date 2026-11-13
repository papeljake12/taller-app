# Ajuste de la pantalla fija y las animaciones: Resumen

Carril H. Pantalla **Resumen** (`/resumen/` y un mes anterior con `?mes=AAAA-MM`). Solo la ve
la dueña.

## Cómo estaba

Con lo que el coordinador ya había hecho para todas las pantallas (menos relleno en
pantallas bajas), Resumen ya cabía en 1366 x 768, pero muy justo: las cosas medían 638 px y
había 682 px de espacio. Además tenía un problema escondido: la lista de gastos crecía con
cada gasto. Con 6 gastos o más en el mes ya no cabía, y la hoja entera se desplazaba.

## Qué cambió en la pantalla (computador)

- **La fila de la gráfica y los gastos ocupa el alto que sobra.** Las cifras de arriba y la
  fila de abajo ("Ventas por tipo de cliente" y "Quién tiene qué") miden lo justo. Lo que
  queda es para la fila del medio. Así nunca queda un hueco al final de la hoja.
- **La lista de gastos se desplaza dentro de su tarjeta.** Si hay más gastos de los que
  caben, se mueve solo la lista. La cabeza de la tarjeta ("Gastos de noviembre" y el botón
  "Registrar gasto"), las cifras y la gráfica no se mueven.
- **Esa fila nunca queda más baja que la gráfica.** Si la ventana es muy baja, se desplaza
  la hoja, como en las demás pantallas, y la gráfica no se corta.
- **La gráfica va un poco más baja en pantallas de poca altura** (hasta 900 px de alto,
  como 1366 x 768). Allí mide 160 de alto en vez de 200: las barras quedan un poco más
  cortas, pero cabe más gente en "Quién tiene qué" sin que se desborde. En pantallas más
  altas (como 1920 x 1080) sobra espacio y va la gráfica de siempre, igual a la del diseño.
  En celular también va la de siempre.
- Las dos tarjetas de cada fila siguen terminando a la misma altura.
- Si la hoja es angosta (una ventana de menos de unos 1050 px de ancho), las dos tarjetas
  del medio se encogen para caber lado a lado, sin salirse por la derecha.

No se quitó nada, no cambió ningún color, ningún texto ni el orden.

### Cuánto mide ahora

| Tamaño | Espacio de la hoja | Lo mínimo que necesita | Holgura | ¿Se desplaza la página? |
|---|---|---|---|---|
| 1366 x 768 | 682 px | 539 px | 143 px | No |
| 1920 x 1080 | 972 px | 727 px | 245 px | No |

"Lo mínimo que necesita" es todo menos la lista de gastos, que se acomoda en el espacio que
queda. La holgura es lo que sobra para los gastos (y para que "Quién tiene qué" pueda crecer
sin que nada se desborde). Probé también 1366 x 657, que es lo que queda de una pantalla de
1366 x 768 con el navegador abierto: también cabe, con 32 px de holgura.

### Desde cuántos gastos se desplaza la lista

- En 1366 x 768 se ven 5 gastos. Desde el sexto, la lista se desplaza dentro de su tarjeta.
- En 1920 x 1080 se ven 9 gastos. Desde el décimo, la lista se desplaza.

Lo probé con 37 gastos en el mes: la lista se desplaza por dentro y todo lo demás queda
quieto. Después volví a cargar los datos de ejemplo.

## Para que la lista no vuelva al principio

Antes, registrar o quitar un gasto cambiaba la tarjeta entera. Ahora la lista se desplaza
dentro de su tarjeta. Si se cambiara la tarjeta entera, la lista volvería al principio cada
vez que se toca una ✕, aunque la persona estuviera viendo el gasto número 25. Por eso
ahora:

- La tarjeta y la caja de la lista se quedan siempre en la página. Las acciones cambian solo
  lo que hay dentro de la lista y traen aparte la cabeza de la tarjeta, las cifras y la
  gráfica.
- Al abrir "Registrar gasto" (y después de registrar uno), la lista baja hasta el final para
  que se vea el formulario entero con sus botones. En celular eso no hace nada, porque allí
  la lista no se desplaza sola.

## Animaciones

Cada parte que entra o sale tiene su nombre fijo (un "id"). Así la aplicación reconoce qué
llegó, qué se fue y qué sigue igual:

- Cada gasto tiene su id (`gasto-12`). **El gasto que se registra aparece suave** y el que se
  quita **se cierra suave**.
- La pregunta "¿Quitar el gasto…?" va en el lugar del gasto y **conserva su mismo id**: el
  gasto se convierte en la pregunta sin cerrarse y volverse a abrir. Solo la ✕ se desvanece.
- El formulario "Registrar gasto" tiene su id: **aparece suave al abrirlo y se cierra suave**
  con "Cancelar". Al registrar un gasto, el formulario queda quieto y solo aparece el gasto
  nuevo.
- El botón "Registrar gasto" de arriba tiene el mismo id abierto o cerrado. Así no parpadea.
- La nota "No hay gastos anotados en este mes." también tiene su id. Se va suave cuando
  llega el primer gasto.
- Las barras de la gráfica vuelven a crecer cuando la gráfica cambia por un gasto.

### Avisos cortos

| Acción | Aviso | De dónde sale |
|---|---|---|
| Registrar un gasto | "Gasto registrado." | De la demo (`demo/index.html`) |
| Quitar un gasto | "Gasto quitado." | La demo no tiene aviso para quitar un gasto. Lo escribí corto y en su mismo estilo ("Foto quitada.", "Prenda quitada de tu lista.") |

- Si el gasto se registra con una fecha de otro mes, la pantalla se va a ese mes y el aviso
  aparece allá.
- Sin JavaScript pasa lo mismo: el aviso sale en la página a la que se vuelve.
- No hay aviso cuando el formulario tiene errores, ni al abrir o cerrar el formulario, ni al
  preguntar "¿Quitar…?" o cancelar, porque nada se guardó.

## En celular

Todo sigue igual. Comparé las capturas en 390 px de antes y de después, con el mes actual y
con el mes anterior (que no tiene gastos), y son idénticas, píxel por píxel.

Un detalle: la lista ahora está dentro de su propia caja. Sin un ajuste, la nota "No hay
gastos anotados en este mes." habría quedado 10 px más abajo. Le dejé el mismo espacio de
antes con una regla que vale para computador y celular. Es la única regla de mi apartado de
`app.css` que no es solo para computador, y está ahí justamente para que nada cambie.

## Archivos

| Archivo | Qué cambió |
|---|---|
| `finanzas/templates/finanzas/resumen.html` | La fila del medio llena el alto que queda. La de abajo mide lo suyo. |
| `finanzas/templates/finanzas/_gastos.html` | La tarjeta: la cabeza y la caja de la lista, que se desplaza por dentro. |
| `finanzas/templates/finanzas/_gastos_cabeza.html` (nuevo) | La cabeza de la tarjeta, que las acciones traen aparte. |
| `finanzas/templates/finanzas/_gastos_lista.html` (nuevo) | Lo de adentro de la lista: los gastos, la nota y el formulario. |
| `_gasto_fila.html`, `_gasto_confirmar.html`, `_gasto_form.html` | Sus ids, y ahora cambian solo lo de adentro de la lista. |
| `finanzas/templates/finanzas/_grafica.html` | La gráfica con su versión baja para el computador. |
| `finanzas/vistas.py` | Devuelve la lista con la cabeza aparte, y los dos avisos. |
| `static/css/app.css` (apartado "Resumen") | Las reglas de esta pantalla para el computador. |
| `finanzas/tests/` | Pruebas de los ids, los avisos, la caja de la lista y la gráfica baja. |

## Qué probé

- `uv run pytest` completo, incluida la prueba que abre Chrome y mide todas las pantallas.
- `herramientas/capturas.py --formatos fijo` con `resumen` y `resumen-octubre`: caben en
  1366 x 768 y en 1920 x 1080, y la página no se desplaza.
- También medí 1280 x 800, 1440 x 900, 2560 x 1440, 1366 x 657, 1024 x 768 y 800 x 900:
  en todos cabe.
- Con un navegador automático (Chrome), en 1366 x 768, en celular y con "menos movimiento":
  - bajé por una lista de 37 gastos, toqué la ✕ de uno del medio, cancelé, lo volví a tocar
    y lo quité;
  - abrí el formulario, lo envié con errores y después bien, y lo cerré.

  Comprobé que:
  - la lista no vuelve al principio;
  - la pregunta conserva el id del gasto;
  - el gasto quitado se cierra suave y el nuevo aparece suave;
  - el formulario se ve entero;
  - salen los avisos y no sale ninguno con errores;
  - el cursor vuelve a donde debe;
  - con "menos movimiento" no hay animaciones;
  - no hay errores de JavaScript.

## Qué no pude comprobar

- En un teléfono de verdad: solo lo probé con el navegador automático en tamaño de celular.
  No pude ver, por ejemplo, cómo se comporta el teclado del teléfono al abrir el formulario.
- Las barras de desplazamiento: el navegador automático no las dibuja. En Windows, la lista
  de gastos mostrará su barra gris a la derecha cuando haya muchos gastos.
- En ventanas angostas de computador (unos 800 px de ancho), la gráfica queda pequeña porque
  las dos tarjetas del medio quedan lado a lado. Así lo decide la regla compartida de la
  pantalla fija. Si a David no le gusta, se puede hacer que en ventanas angostas las dos
  tarjetas vayan una debajo de la otra y que se desplace la hoja.
