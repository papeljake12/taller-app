# Ajuste de Mi taller: pantalla fija y animaciones

Carril I. Pantalla **Mi taller** (`/mi-taller/`, solo la dueña). No tiene página en
`diseno/`: se comparó con sus capturas de la tanda 6 (`docs/capturas/tanda-6/mi-taller-*.png`).

## Qué cambió y por qué

### La pantalla fija

Con los datos de ejemplo (3 costureras) Mi taller ya cabía completa. El problema aparecía
con muchas costureras: con 21, la tarjeta "Costureras" medía casi 1800 px y la hoja entera
se tenía que desplazar (en 1366 x 768 eran 1759 px de contenido en 682 px de espacio).

Ahora:

- **Las dos tarjetas ocupan el alto que queda en la pantalla y terminan parejas**, abajo,
  sin hueco. Con los ejemplos se ven exactamente igual que antes (se compararon las capturas
  píxel por píxel: no cambió ninguno).
- **En "Costureras", la cabeza ("Costureras", "3 activas") y la nota de arriba quedan
  quietas.** Debajo van la lista y el formulario "Nueva costurera", uno detrás del otro, como
  siempre.
- **Si son muchas, solo la lista se desplaza**, por dentro de su tarjeta, y el formulario
  para agregar queda siempre a la vista debajo. Así nunca hay que bajar hasta el final de una
  lista larga para agregar a alguien.
- **La lista nunca se encoge a menos de 140 px** (dos filas, más o menos). Si la ventana es
  tan baja que ni así cabe todo, se desplaza la lista junto con el formulario. Nada se corta.
- **"Tu taller" también está protegida**: si la ventana es muy baja, su formulario se
  desplaza por dentro de la tarjeta en vez de cortarse. En 1366 x 768 eso no pasa, ni
  siquiera con el logo puesto.
- **En una ventana angosta** (de 768 a 899 px de ancho, como una tableta parada), las dos
  tarjetas no caben una al lado de la otra: van una debajo de la otra, como antes, y se
  desplaza la hoja (el título y el botón "Agregar costurera" siguen quietos arriba).
- **Entre 900 y unos 1050 px de ancho** las dos tarjetas se angostan un poco para caber una
  al lado de la otra. Antes de este arreglo, en 1024 px la tarjeta "Costureras" se salía por
  la derecha y se cortaba.
- **En celular no cambió nada** (también se comparó píxel por píxel).

### Animaciones

- Cada cosa que aparece o se va sin recargar tiene su marca propia (un `id`) que no cambia:
  - cada costurera (`costurera-12`). Al tocar "Cambiar nombre", el formulario toma el lugar
    de la fila **con la misma marca**, así la fila no se cierra y se vuelve a abrir: solo el
    campo aparece con un desvanecido;
  - una costurera nueva aparece en la lista con un desvanecido;
  - los "Listo: ..." de las dos tarjetas, el logo y la casilla "Quitar el logo" aparecen con
    un desvanecido y, cuando se van, se cierran suave (por ejemplo, al quitar el logo).
- El nombre del taller en el menú se sigue cambiando aparte, sin animarse (el menú está
  marcado para no animarse).
- Si en el equipo se pidió menos movimiento, no se anima nada; los avisos salen igual.

### Avisos cortos al guardar

| Acción | Aviso | ¿De la demo? |
|---|---|---|
| Guardar "Tu taller" cuando solo cambió el nombre | Nombre guardado. | Sí |
| Guardar "Tu taller" con otro cambio (teléfono, logo, quitar el logo o varias cosas) | Cambios guardados. | No, nuevo |
| Agregar costurera | Costurera agregada. | No, nuevo (como "Tela agregada.") |
| Cambiar el nombre de una costurera | Nombre guardado. | Sí |
| Desactivar | Costurera desactivada. | No, nuevo |
| Activar | Costurera activada. | No, nuevo |

- La demo solo tenía "Nombre guardado." (su ventana de Mi taller solo cambiaba el nombre).
  Los demás son nuevos, cortos y con punto final, como los de la demo.
- **Por qué desactivar y activar sí avisan**, aunque la regla dice que lo que ya se ve donde
  se tocó no lleva aviso: la fila no se queda en su lugar. Las activas van primero, así que
  al desactivar a alguien su fila salta al final de la lista (y con muchas, puede quedar
  lejos). El aviso dice qué pasó.
- No avisan: abrir o cancelar el cambio de nombre, ni un formulario con errores.
- Sin JavaScript, el aviso sale en la página a la que se vuelve.
- Los "Listo: ..." que ya había en las tarjetas se quedan: dicen cosas que el aviso no dice
  (por ejemplo, con qué usuario entra la costurera nueva).

## Cuánto mide ahora

| Tamaño | Con los ejemplos (3 costureras) | Con 21 costureras |
|---|---|---|
| 1366 x 768 | Cabe: 682 px de contenido en 682 px | Cabe: 682 en 682. La lista muestra 350 px de 1427 |
| 1920 x 1080 | Cabe: 972 en 972 | Cabe: 972 en 972. La lista muestra 672 px de 1492 |

En ningún tamaño la página se desplaza. **La lista empieza a desplazarse desde 6
costureras en 1366 x 768 y desde 10 en 1920 x 1080.** También se midió 1280 x 800,
1024 x 768, 900 x 700, 1366 x 600 y 1366 x 480: nada se sale ni se corta.

## Qué se probó

- **Pruebas automáticas nuevas** (en `cuentas/tests/test_mi_taller.py`): cada aviso con su
  texto; que abrir, cancelar y los errores no avisan; que sin JavaScript el aviso sale en la
  página siguiente; que la fila y su formulario de nombre tienen la misma marca; que lo que
  aparece y se va tiene una marca que no cambia; y una prueba en Chrome con 18 costureras,
  en 1366 x 768 y 1920 x 1080: la página y la hoja no se desplazan, la lista sí, el botón
  "Agregar costurera" se ve, y las dos tarjetas terminan parejas y llegan hasta abajo.
- **A mano, en Chrome con un navegador automático**, con 21 costureras: cambiar el nombre de
  una que estaba abajo en la lista (el campo queda a la vista y con el cursor), cancelar,
  guardar el nombre, desactivar y activar (la fila salta a su grupo y la lista la muestra),
  agregar (la fila nueva y el "Listo" aparecen con desvanecido), cambiar el teléfono y el
  nombre del taller (el menú y la pestaña cambian), subir un logo y quitarlo (se cierra
  suave), y un nombre vacío (sin aviso). Sin errores de JavaScript. Todo otra vez con
  "menos movimiento": nada se anima y los avisos salen.
- **Capturas** en 1366 x 768, 1920 x 1080 y celular, con los ejemplos y con 5, 6, 10 y 21
  costureras.

## Qué no se pudo comprobar

- En una tableta de verdad (solo se simuló el tamaño en Chrome).
- Cuando HTMX trae la tarjeta "Costureras" otra vez, la lista vuelve a empezar arriba. Lo
  compensa el cursor: después de cada acción queda en la fila que se tocó, y la lista se mueve
  sola hasta mostrarla. Que la lista recuerde dónde iba necesitaría un cambio en
  `static/js/app.js`, que es compartido; se le propuso al coordinador.
- El aviso corto sale abajo en el centro y, en 1366 x 768, tapa por un momento parte del
  botón "Agregar costurera" (se puede tocar igual: el aviso no recibe clics). Es la posición
  común de todos los avisos; se le contó al coordinador.
