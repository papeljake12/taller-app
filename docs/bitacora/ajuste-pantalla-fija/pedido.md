# Ajuste: Pedido por dentro (pantalla fija y animaciones)

Carril C. La pantalla de un pedido (`/pedidos/<número>/`), como dueña y como costurera.

## En pocas palabras

- **En 1920 x 1080 ya cabe completa**, como dueña y como costurera: no hay que desplazar
  nada para ver de "Etapa" a "Eliminar el pedido".
- **En 1366 x 768 todavía no cabe.** Quedó bastante más corta (111 px menos como dueña, 131
  px menos como costurera), pero le faltan unos 315 px como dueña y unos 80 px como
  costurera. Ahí la hoja se desplaza por dentro, debajo del título; el menú, el título y los
  botones de arriba se quedan quietos y la página entera no se mueve. Para que quepa hay que
  cambiar el diseño, y eso lo decides tú: abajo están las opciones.
- Al guardar sale un aviso corto abajo, en el centro: "Abono registrado.", "Foto guardada.",
  etc.
- Lo que entra o sale sin recargar (un abono, un material, una persona de Tallas, la foto)
  aparece con un desvanecido o se cierra suave.

## Cuánto mide ahora

"Contenido" es lo que mide todo lo que va debajo del título; "espacio", lo que deja la
ventana. Si el contenido es más grande, la hoja se desplaza por dentro.

| Tamaño | Quién | Antes | Ahora |
|---|---|---|---|
| 1366 x 768 | dueña | 1108 en 682 (no cabe) | 997 en 682 (no cabe, faltan 315) |
| 1920 x 1080 | dueña | 1160 en 972 (no cabe) | **972 en 972 (cabe)** |
| 1366 x 768 | costurera | 892 en 682 (no cabe) | 761 en 682 (no cabe, faltan 79) |
| 1920 x 1080 | costurera | 972 en 972 (cabía) | **972 en 972 (cabe)** |

En ningún tamaño se desplaza la página entera: eso ya lo hacía lo compartido.

Ojo: en 1920 x 1080 cabe el pedido del ejemplo (el del Restaurante: un abono, sin foto y sin
WhatsApp). Le sobran unos 20 px. Un pedido con más cosas en la columna de la derecha no cabe
ni en 1920 x 1080: por ejemplo el del Grupo de danza (dos abonos, foto y el aviso de pedido
listo) mide 1199 en 972, y el del Restaurante con seis abonos mide 1218. Cada abono suma
unos 53 px y la foto, unos 80 más que el recuadro de "no tiene foto". En esos casos la hoja
se desplaza por dentro, como en 1366 x 768.

## Qué cambió y por qué

### Las dos columnas llenan la hoja

Antes las dos columnas medían lo que medía su contenido y "Eliminar el pedido" se estiraba
hasta abajo para tapar el hueco. Ahora es al revés: "Eliminar el pedido" mide lo suyo y las
dos columnas toman todo el alto que queda (`.llenar`). Las dos siguen terminando a la misma
altura.

Si el contenido no cabe (1366 x 768), las columnas no se encogen por debajo de lo que
necesitan: así ninguna tarjeta se monta encima de "Eliminar el pedido" y lo que pasa es que
la hoja se desplaza. Eso lo comprobé con el navegador automático, bajando la hoja hasta el
final.

### Tarjetas más apretadas, solo en esta pantalla

Es la pantalla con más cosas de toda la aplicación, así que en computador (en cualquier
alto) sus tarjetas usan menos aire que las demás. Nada cambia de color, de texto ni de
orden; en celular no cambia nada (comparé las capturas del celular de antes y de ahora y
son idénticas, píxel por píxel).

- Cabeza de cada tarjeta: 10 px arriba y abajo (en las demás pantallas, 14 o 11).
- Dentro de cada tarjeta: 8 px entre una cosa y otra y 12 px al final (antes 12 y 16).
- 12 px entre tarjetas.
- Los pasos de "Etapa" con menos aire arriba y abajo.
- Los números grandes ("14 de 18", "$ 1.260.000") con el renglón más justo.
- Las filas plegables ("Ver las 14 personas", "Registrar un abono") de 8 px.
- El campo para elegir la foto mide 36 px, como los demás campos (antes unos 46).

### Lo que se desplaza por dentro de su tarjeta

- **Materiales**: es la última tarjeta de la columna izquierda y toma el alto que queda.
  Si los materiales no caben, se desplaza solo su lista; la cabeza ("2 de 4 comprados") y
  el formulario de "Agregar material" se quedan quietos. Nunca muestra menos de unos dos
  materiales (con uno o dos, siempre se ven enteros). Si sobra alto, el blanco queda al
  final de la tarjeta, debajo del formulario, como antes. Con los datos de ejemplo empieza
  a desplazarse desde unos 5 materiales en 1920 x 1080 (dueña) y desde 7 como costurera; en
  1366 x 768 como costurera ya se desplaza con los 4 del ejemplo. Lo probé con 24
  materiales: la hoja no cambió de alto, solo se desplazó la lista.
- **Personas de Tallas**: al abrir "Ver las 14 personas", si son más de tres se desplaza la
  lista por dentro (se asoma la mitad de la cuarta, para que se note que hay más). Antes
  abrirla alargaba la tarjeta unos 800 px.
- **Foto del pedido**: es la última tarjeta de la columna derecha y llega hasta abajo. La
  foto mide 264 px, como antes, y si falta espacio se achica hasta 120 px (no se estira en
  pantallas grandes). Sin foto, el recuadro gris mide 120 px, como antes, y si falta espacio
  se achica hasta lo que mide su frase. Lo que sobre queda en blanco al final de la tarjeta,
  no en gris.

**Los abonos todavía no se desplazan por dentro.** Para hacerlo hay que envolverlos en una
caja, y esa caja cambiaría el espacio entre abonos en el celular. Necesita una regla en la
parte compartida de `app.css`, que no es de este carril: se la pedí al coordinador (abajo).

## Avisos cortos

| Acción | Aviso | De dónde sale el texto |
|---|---|---|
| Registrar un abono | "Abono registrado." | de la demo |
| Quitar un abono | "Abono quitado." | nuevo (la demo no avisa) |
| Subir o cambiar la foto | "Foto guardada." | de la demo |
| Quitar la foto | "Foto quitada." | de la demo |
| Eliminar el pedido | "Pedido eliminado." (sale en Pedidos, la página a la que se llega) | de la demo |
| Agregar un material | "Material agregado." | nuevo (la demo no avisa) |
| Quitar un material | "Material quitado." | nuevo (la demo no avisa) |
| Agregar una persona a mano en Tallas | "Talla agregada." | nuevo (la demo no avisa) |
| Quitar una persona de Tallas | "Talla quitada." | nuevo (la demo no avisa) |

También salen sin JavaScript: en ese caso aparecen en la página a la que se vuelve.

**Sin aviso**, porque el cambio se ve justo donde se tocó: mover la etapa, marcar un material
como comprado, abrir o cerrar el enlace de tallas, cambiar la fecha de entrega, elegir quién
lo está haciendo y guardar el WhatsApp (que ya dice "Número guardado." debajo). Tampoco
avisan los errores de un formulario, preguntar "¿Quitar?" ni "Cancelar". Ningún aviso dice
plata, así que la costurera puede recibir los suyos (agregar tallas y materiales, subir la
foto).

## Animaciones

Lo general ya lo hacía lo compartido. Para aprovecharlo, cada cosa que entra o sale sin
recargar tiene ahora un nombre fijo (un `id`):

- cada abono (`abono-12`), y su pregunta "¿Quitar el abono...?" conserva el mismo nombre,
  para que la fila no se cierre y se vuelva a abrir al preguntar;
- cada material (`material-12`);
- cada persona de Tallas (`talla-12`);
- la foto y el recuadro de "no tiene foto": al subir la primera, el recuadro se cierra y la
  foto aparece; al quitarla, al revés;
- el formulario de la foto y su pregunta "¿Quitar la foto?" comparten nombre;
- "Número guardado." aparece con un desvanecido.

El cambio de etapa ya se animaba solo.

## Qué probé

- Todas las pruebas (`uv run pytest`), con las nuevas: una por cada aviso, que los errores
  no avisan, que lo que se ve donde se toca no avisa, los avisos sin JavaScript y los
  nombres (`id`) de abonos, materiales, personas y foto.
- Con la herramienta de capturas, en 1366 x 768, 1920 x 1080 y celular, como dueña y como
  la costurera encargada (Marta).
- Con un navegador automático (Chrome), en 1366 x 768: registrar un abono (sale el aviso y
  solo el abono nuevo aparece con desvanecido), preguntar por quitarlo (la fila no se
  cierra), quitarlo (la fila se cierra), agregar y quitar un material, marcar una casilla
  (sin aviso), agregar y quitar una persona de Tallas (la lista abierta se desplaza por
  dentro), cambiar la etapa, subir y quitar la foto, guardar el WhatsApp y eliminar un
  pedido (el aviso sale en Pedidos). Como costurera: no ve Pagos y recibe "Material
  agregado.". Sin errores de JavaScript. Lo repetí con "menos movimiento" activado: los
  avisos salen igual y nada se anima.
- Con 24 materiales y con 6 abonos en el pedido del Restaurante (después volví a cargar los
  ejemplos).

## Qué no pude comprobar

- En un celular de verdad (solo en el navegador automático a 390 px).
- Con la letra del navegador agrandada.
- En Firefox y Safari: solo lo probé en Chrome.

## Opciones para David (1366 x 768)

En 1366 x 768 quedan unos 600 px para las dos columnas (lo demás es el título y "Eliminar el
pedido"). Apretadas al máximo, la izquierda mide unos 760 y la derecha unos 915. La de la
derecha (Pagos, Entrega, Cliente y Foto) no tiene ninguna lista larga que pueda desplazarse:
son formularios y cifras. Por eso no cabe sin cambiar el diseño.

1. **Dejarla así.** En 1366 x 768 la hoja se desplaza unos 315 px por dentro (el título, los
   botones y el menú quedan quietos); en 1920 x 1080 cabe. No cambia nada del diseño
   aprobado. Es la única pantalla que se desplazaría.
2. **Plegar lo que se usa menos.** "Cliente" y "Foto del pedido" pasan a ser filas que se
   abren al tocarlas (como "Registrar un abono"), y "Eliminar el pedido" pasa a ser un botón
   arriba, junto a "Avisar al cliente". Ahorra unos 300 px a la derecha y 75 a las dos.
   Cabría la derecha; la izquierda todavía necesitaría unos 85 px más (por ejemplo, las
   barras de tallas en dos columnas, S y M al lado de L y XL).
3. **Dos pestañas dentro del pedido:** "Producción" (Etapa, Tallas y Materiales) y "Cobro y
   entrega" (Pagos, Entrega, Cliente y Foto), cada una a lo ancho con sus dos columnas.
   Cabría todo con espacio de sobra, pero lo de una pestaña no se ve desde la otra.

A la costurera le faltan 79 px en la columna izquierda: cabría con la opción 3, o con las
barras de tallas en dos columnas (unos 56 px) y un solo material a la vista en vez de dos
(unos 45 px).

## Pedido al coordinador

Para que los abonos se desplacen por dentro de la tarjeta Pagos sin cambiar nada en el
celular, una regla en la sección 4 de `static/css/app.css`, junto a `.pagos__abono`:

```css
/* La lista de abonos de la tarjeta Pagos: el mismo espacio entre abonos que la tarjeta */
.pagos__abonos {
  display: flex;
  flex-direction: column;
  gap: inherit;
}
```

Con ella, este carril envolvería los abonos en `<div class="pagos__abonos desplazable">` y les
pondría un alto máximo en su apartado. Ojo: en 1920 x 1080 al pedido del ejemplo le sobran
solo unos 20 px, así que con dos abonos o más igual se pasaría un poco aunque la lista se
desplace.
