# Rediseño con el lenguaje del panel de Shopify

Rama `rediseno-estilo-shopify`. El 13 de noviembre de 2026 David aprobó una maqueta
(https://claude.ai/artifact/9yNAtEHnQi6GEEM1cWJPB8) que rediseña el panel con el lenguaje del
panel de administración de Shopify, y autorizó cambiar las reglas de diseño: sin "pantalla
fija", hoja blanca, sombras suaves, letra de 13 px, insignias con circulito y gris para lo que
está bien.

Antes de empezar se unió a `main` la rama del ajuste anterior
(`ajuste-pantalla-fija-y-animaciones`, con sus 1348 pruebas pasando) y la rama del rediseño
salió de ahí.

## El plan

Se trabaja como una tanda (`docs/09-plan-de-construccion.md`): primero lo compartido, una sola
vez y por una sola mano; después cada pantalla, en paralelo.

1. **El diseño en papel** (lo hizo el coordinador antes de tocar código):
   - `docs/08-diseno.md` con las reglas nuevas;
   - las páginas de `diseno/`, ahora con una hoja de estilos común (`diseno/estilo.css`) y
     que se ven también en celular;
   - `CLAUDE.md` (regla 7), `docs/03-pantallas.md` y una línea de `docs/02-modelo-de-datos.md`.
2. **Lo compartido** (coordinador): `static/css/app.css`, `templates/base.html`, el menú, las
   piezas de `templates/piezas/`, los íconos, la letra, las insignias de `pedidos/calculos.py`,
   la gráfica, `static/js/app.js`, `/piezas/`, la herramienta de capturas y sus pruebas.
   Explicado en `rediseno/compartido.md`.
3. **Las pantallas**, un agente por carril, cada uno en su propia copia y con su propia base de
   datos. Un revisor que no escribió el código revisa cada carril antes de unirlo.

| Carril | Pantalla | Archivos propios |
|---|---|---|
| A | Hoy (también con el menú contraído y como costurera) | `hoy.html` y sus partes, `vistas/hoy.py`, `test_hoy.py` |
| B | Pedidos, Buscar y Nuevo pedido | `lista.html`, `buscar.html`, `_lista_*`, `_nuevo.html`, `vistas/lista.py`, `test_lista.py` |
| C | Pedido por dentro (con la cronología y las flechas) | `pedido.html` y sus partes, `vistas/detalle.py`, `abonos.py`, `tallas.py`, `materiales.py`, `fotos.py`, `pedidos/fotos.py` y sus pruebas |
| D | Calendario | `calendario.html` y sus partes, `vistas/calendario.py`, `test_calendario.py` |
| E | Clientes | `clientes.html` y sus partes, `vistas/clientes.py` y sus pruebas |
| F | Cotizador | la app `cotizador/` (menos `models.py` y `urls.py`) |
| G | Telas (también sin telas) | la app `telas/` (menos `models.py` y `urls.py`) |
| H | Resumen | la app `finanzas/` (menos `models.py` y `urls.py`) |
| I | Mi taller, Entrar, formulario público de tallas y "Sin permiso" | las plantillas y vistas de `cuentas/`, `vistas/publico.py`, `publico.html` y `_publico_*`, `templates/403.html` y sus pruebas |

Cada carril copia el HTML de su página de `diseno/`, usa las piezas que ya existen y, si le
falta algo de estilo, lo escribe solo en su apartado de la sección 8 de `static/css/app.css`.
Su explicación va en `docs/bitacora/rediseno/<pantalla>.md`.

## Decisiones tomadas al planear

- **La página no se mueve; se desplaza la hoja.** Como en la maqueta y en Shopify: el menú y el
  encabezado de la hoja quedan quietos y el contenido se desplaza por dentro. Ya no hay que
  hacer caber cada pantalla.
- **"Trabajos del taller" sale de Hoy.** La maqueta aprobada no la tiene: la foto de cada
  pedido sale ahora en su tarjeta de Hoy y en la lista de pedidos. Si David la quiere de
  vuelta, cabe debajo de "Tu mes".
- **Lo que la maqueta muestra pero no haría nada no se pone:** la campana del celular, el
  "Recientes" de la caja de Hoy, el "+" para guardar pestañas propias, el filtro y el orden de
  la lista y las flechas de páginas (no hay notificaciones, ni pestañas propias, ni otros
  órdenes, ni páginas).
- **Cronología:** solo con lo que ya se guarda (creación, abonos y tallas). Los cambios de
  etapa no se guardan hoy; guardarlos cambia el modelo de datos y queda para que David decida.
- **Las pestañas de Pedidos siguen diciendo cuántos hay** ("Atrasados 1"), aunque la maqueta
  no lo mostraba: lo pide `docs/03-pantallas.md` y ayuda a decidir.
- **El contador de Pedidos en el menú** sigue contando los atrasados (la maqueta mostraba los
  activos, pero `docs/03-pantallas.md` pide los atrasados).
- **Letra:** la maqueta usa pesos intermedios (450, 550, 650). Se guardó en el proyecto la
  versión variable de la misma Inter (un solo archivo de 48 KB, misma licencia), en vez de los
  cuatro archivos de antes.
- **Contraste:** el gris más claro de la maqueta (`#8A8A8A`) no alcanza el contraste de texto
  pedido; el texto secundario usa `#616161` y ese gris queda para ejemplos y adornos.
- Las pantallas que no estaban en la maqueta (Calendario, Clientes, Cotizador, Telas con datos,
  Resumen, Mi taller, Entrar, Nuevo pedido y el formulario de tallas) se adaptaron con el mismo
  lenguaje y se le muestran a David antes de darlas por terminadas y de unir a `main`.

## Cómo terminó

Los nueve carriles terminaron, cada uno con su revisor (un agente que no escribió el código).
Ningún revisor encontró algo grave. Lo que pidieron arreglar se arregló al unir:

- **Hoy:** "Confirmar pedido" quedó solo para la dueña, aunque la costurera sea la encargada
  (con una petición directa la costurera podía confirmarlo, y confirmar depende del precio,
  que ella no ve). Con su prueba.
- **Mi taller:** en celular, el nombre de cada costurera quedaba pisado por los botones. Era
  un defecto de la pieza compartida `.persona` (también en `diseno/`): ahora los botones bajan
  de línea si no caben. Y el cuadrito del taller en el menú cambia sin recargar al cambiar el
  nombre o el logo.
- **Cotizador:** en celular, "Empezar de nuevo" era un botón redondo con una X, que parece
  "cerrar" y borra lo escrito. Se agregó un ícono propio de "reiniciar" (flecha en círculo).
- **Pedidos:** una prueba más de que la costurera no recibe plata en lo que llega mientras
  escribe en el buscador.
- **Pedido por dentro:** la lista de personas de Tallas usaba la clase vieja `desplazable`;
  ahora tiene la suya. Los botones para quitar materiales pasaron a ser planos (con borde se
  veían pesados).
- **"Trabajos del taller":** se borró lo que quedó sin uso (la pieza de fotos que pasan, su
  parte del JavaScript, el cálculo y sus pruebas).
- Las pruebas compartidas que revisaban el diseño viejo (Hoy, la lista de pedidos, Telas) se
  actualizaron al nuevo.
- `diseno/nuevo-pedido.html` mostraba tallas que no existen ("Niño (2 a 16)" y "A la medida");
  ahora tiene las de verdad.

### Qué se probó

- `uv run pytest`: **todas pasan** (1403 al final; eran 1348 antes del rediseño).
  - `tests/test_desplazamiento.py` abre cada pantalla en Chrome, en 1366 x 768 y 1920 x 1080
    como dueña y como costurera: la página no se mueve y nada se sale de lo ancho, tampoco en
    celular.
  - Una prueba comprueba que `static/css/app.css` copie exacto a `diseno/estilo.css`.
- **Capturas finales** en `docs/capturas/rediseno/` (1366 x 768, 1920 x 1080 y celular, con la
  hoja completa a la vista) y las de la costurera en `costurera/`. La herramienta no marcó
  ningún problema. Las revisé contra `diseno/`.
- **El JavaScript nuevo en Chrome:** Ctrl K enfoca el buscador (y abre el menú contraído); la
  lupa de Pedidos muestra el buscador y filtra al escribir; "Más acciones" y "Cambiar etapa"
  abren, se cierran al tocar afuera y con Escape, y se abre uno a la vez. Sin errores de
  JavaScript. Ahí encontré y corregí un error: la lupa dejaba el cursor en un campo escondido.

### Qué no se pudo comprobar

- Un celular, Firefox o Safari de verdad: todo se probó en Chrome.
- Las pantallas vacías (sin pedidos, sin clientes, sin telas) solo se comprobaron con
  pruebas: los datos de ejemplo traen de todo, así que no salen en las capturas.
- Que "Avisar" abra WhatsApp de verdad.
- El saludo de Hoy depende de la hora: las capturas dicen "¡Buenas noches!" porque se tomaron
  de noche.

### Para que tú decidas

1. **Las pantallas que no estaban en la maqueta** (Calendario, Clientes, Cotizador, Telas con
   datos, Resumen, Mi taller, Entrar, Nuevo pedido y el formulario de tallas): ¿te gustan así?
   No se une a `main` hasta que digas.
2. **"Trabajos del taller"** salió de Hoy porque la maqueta no la tiene. ¿La quieres de vuelta?
3. **La cronología** muestra la creación, los abonos y las tallas. Para que muestre también los
   cambios de etapa habría que empezar a guardarlos (cambia el modelo de datos).
4. **Las tallas agregadas a mano** no guardan quién las agregó, así que en la cronología no
   dicen quién. Guardarlo también cambia el modelo de datos.
5. **Telas en celular:** "Entró" y "Usé" quedan a un deslizamiento lateral dentro de la
   tarjeta (como en la referencia). ¿Los quieres siempre a la vista?
6. **Textos nuevos** que no estaban en ningún lado: las frases de las pantallas vacías y sus
   "Cómo llevar…", "El taller hoy" (lo que ve la costurera en Hoy) y la confirmación del
   formulario de tallas ("¡Gracias, Laura! Ya tenemos tu talla M…").
7. **El formulario público de tallas** ahora muestra la foto del pedido (como en la
   referencia): quien tenga el enlace la ve.
8. **Pequeñas diferencias con la maqueta, a propósito:** "Descargar para Excel" ya no está en
   Hoy (sigue en Pedidos y Resumen); el buscador de Pedidos va detrás de la lupa; "Registrar
   abono" está en la tarjeta del pago y no arriba; la ventana de agregar tela se sigue llamando
   "Nueva tela"; y la costurera no ve "Avisar" en pedidos listos ni cotizados (esos mensajes
   dicen plata).
