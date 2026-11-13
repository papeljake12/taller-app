# Ajuste de Clientes: pantalla fija y animaciones

Carril E. Pantalla: Clientes (`/clientes/`, solo la dueña).

## Qué cambió y por qué

### La lista larga se desplaza sola, dentro de su tarjeta

Con los seis clientes de ejemplo, Clientes ya cabía completa en el computador. El problema
aparecía con muchos clientes: la tabla crecía hacia abajo y, con la pantalla fija, la que se
desplazaba era toda la hoja; el aviso de dotación y el buscador se perdían de vista.

Ahora la tarjeta de la lista toma exactamente el alto que queda debajo del aviso de dotación
(la clase `llenar`), y la caja de la tabla es la única parte que se desplaza (la clase
`desplazable`). Así:

- la tarjeta negra del aviso de dotación y el buscador se quedan quietos arriba;
- al bajar por la lista, la fila de títulos (Cliente, Tipo, Pedidos...) se queda fija arriba
  de la tabla, para no perder de vista qué es cada columna;
- la página y la hoja nunca se desplazan.

No hizo falta ninguna regla de estilo propia: bastó con poner las dos piezas compartidas en
el lugar correcto (`clientes.html` y `_clientes_tabla.html`). Por eso el apartado "Clientes"
de `app.css` solo tiene un comentario que lo explica.

En celular no cambia nada: la captura de celular de antes y la de después son idénticas, píxel
por píxel. En computador lo único que se mueve es 1 píxel: la línea de arriba de la fila de
títulos ahora va pintada (para que se vea bien cuando queda fija), y las filas suben 1 píxel.

### Cuánto mide ahora

| Tamaño | Lo que ocupa el contenido | Espacio de la hoja | ¿Cabe? |
|---|---|---|---|
| 1366 x 768 | 529 px | 682 px | Sí; la tarjeta de la lista crece hasta abajo |
| 1920 x 1080 | 573 px | 972 px | Sí; la tarjeta de la lista crece hasta abajo |

(Medido con los datos de ejemplo. La página no se desplaza en ningún tamaño, y no queda hueco
al final: la tarjeta de la lista llega hasta abajo.)

### Desde cuántos clientes se desplaza la tabla

- En 1366 x 768 caben 8 clientes a la vista; desde 9, la tabla se desplaza por dentro.
- En 1920 x 1080 caben 12; desde 13, se desplaza por dentro.

Lo probé con 50 clientes: la tabla mide 2.786 px y se ve por una ventanita de 519 px (en
1366 x 768). Al bajar hasta el final, el aviso de dotación, el buscador y la fila de títulos
no se movieron ni un píxel.

### El buscador: solo entran y salen las filas que cambian

Mientras se escribe en el buscador, la lista cambia sin recargar la página. Antes cambiaba de
golpe: las filas que sobraban desaparecían y las nuevas aparecían sin transición. Para animar
solo lo que cambia, sin que las demás filas parpadeen, cada fila lleva ahora el número de su
cliente como nombre
(`id="cliente-12"`), y la tabla y las notas tienen el suyo (`clientes-tabla`,
`clientes-ninguno`, `clientes-vacio`). Con eso, el programa de animaciones compartido sabe qué
filas son las mismas de antes:

- las que siguen se quedan quietas (no parpadean);
- las que ya no coinciden se desvanecen;
- las que vuelven a coincidir (al borrar letras) aparecen con un desvanecido;
- si no queda ningún cliente, la tabla se desvanece entera y entra la nota "Ningún cliente
  coincide con «...»"; si se sigue escribiendo, la nota solo cambia su texto, sin parpadear.

No le puse `data-sin-animar` a la lista: justamente queremos que las filas que entran y salen
se vean entrar y salir, y las que siguen ya no parpadean gracias a sus nombres fijos.

### Aviso corto al guardar

| Acción | Aviso | ¿De la demo? |
|---|---|---|
| "Crear cliente" en la ventana "Nuevo cliente" | **Cliente creado.** | No |
| "Guardar cambios" en la ventana "Editar cliente" | **Cliente guardado.** | No |

La demo no tiene estas dos acciones (allá los clientes salen solos de los pedidos), así que no
trae texto para ellas. Usé textos cortos del mismo estilo que los de la demo ("Pedido
guardado.", "Nombre guardado.", "Pedido creado como cotizado."), con punto final.

Como después de guardar la página vuelve a la lista, el aviso viaja como un "mensaje para la
página siguiente" (así lo resuelve `config/avisos.py`) y aparece al llegar. También funciona
sin JavaScript. Si el formulario tiene un error (sin nombre, nombre repetido, número que no
sirve), no sale aviso: la ventana se queda abierta mostrando el error, como antes.

No puse aviso al buscar, al abrir la ventana "Escribirles" ni al tocar "Escribirle": ninguna
de esas cosas guarda nada ("Copiar" ya tenía su propio aviso para lectores de pantalla). Los
avisos no dicen plata, y la costurera no entra a Clientes.

## Qué probé

- Todas las pruebas automáticas (`uv run pytest`), incluida la que abre Chrome y mide cada
  pantalla en 1366 x 768 y 1920 x 1080.
- Pruebas nuevas en `pedidos/tests/test_clientes.py`: la tarjeta lleva `llenar` y la tabla
  `desplazable`; el aviso de dotación y el buscador van antes de la parte que se desplaza; cada
  fila lleva el id de su cliente y es el mismo en la página y en la búsqueda; las notas tienen
  su id fijo; "Cliente creado." y "Cliente guardado." salen en la página siguiente (con y sin
  JavaScript) y solo una vez; con errores no hay aviso; buscar no lleva aviso.
- En Chrome, con un navegador automático y 50 clientes de prueba en mi base:
  - la página y la hoja no se desplazan; solo la tabla, con la fila de títulos fija;
  - al buscar "prueba 1" salieron 40 filas desvaneciéndose y las 10 que seguían no se
    animaron; al ampliar a "prueba" entraron solo las 34 nuevas;
  - sin resultados, la tabla salió entera y entró la nota; al seguir escribiendo, la nota no
    parpadeó; el cursor se quedó en el buscador todo el tiempo;
  - "Nuevo cliente": se abrió la ventana, al guardar apareció "Cliente creado."; con el nombre
    repetido la ventana mostró el error y no hubo aviso;
  - "Editar": al guardar apareció "Cliente guardado." y el nombre nuevo en la lista; el aviso
    se fue solo;
  - la ventana "Escribirles" abre y cierra con Escape;
  - sin errores de JavaScript;
  - lo mismo con "menos movimiento" activado: todo funciona y nada se anima;
  - en celular la página se sigue deslizando normal y no se desborda a lo ancho.
- Después volví a cargar los datos de ejemplo (`cargar_ejemplos`), que borran los clientes de
  prueba.

## Qué no pude comprobar o queda para decidir

- Con un celular de verdad no lo probé; solo con el navegador automático en 390 px.
- Ver el desvanecido "a ojo" no se puede en una prueba automática: comprobé que las filas
  correctas tienen una animación andando, no cómo se ve.
- Al crear un cliente con una lista muy larga, el cliente nuevo puede quedar más abajo, fuera
  de la vista (la lista está ordenada por lo que más han comprado y el nuevo no ha comprado
  nada). El aviso confirma que se creó; si David quiere, se podría bajar la lista hasta él.
- Con muchos clientes empresa (probé con 13), la ventana "Escribirles por la dotación" se
  desplaza entera, también su título y el botón de cerrar. Es la ventana compartida
  (`piezas/ventana.html`), no es de este carril; lo dejo anotado por si el coordinador quiere
  que el cuerpo de las ventanas se desplace solo.
