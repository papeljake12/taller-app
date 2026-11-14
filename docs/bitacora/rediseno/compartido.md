# Rediseño: lo compartido

Lo hizo el coordinador, una sola vez para todas las pantallas, antes de repartir el trabajo.

## Qué cambió y para qué sirve cada archivo

- **`diseno/estilo.css`** (nuevo): todos los estilos del diseño aprobado. Las páginas de
  `diseno/` lo usan, así que se ven igual que la aplicación y también funcionan en celular
  (antes cada página tenía sus estilos escritos a mano dentro de cada elemento).
- **`static/css/app.css`**: se rehízo. Sus secciones 1 a 6 son una copia exacta de
  `diseno/estilo.css`; después vienen las animaciones (las mismas de antes, adaptadas), un
  apartado vacío por pantalla y "menos movimiento". Se fue la sección de la "pantalla fija".
  Una prueba comprueba que la copia sea exacta.
- **`static/fuentes/`**: Inter en su versión variable (`inter-latin-wght-normal.woff2`), en vez
  de cuatro archivos de pesos fijos. Así se ven los pesos intermedios de la maqueta (450, 550,
  650). Es la misma letra y la misma licencia; no es una librería.
- **`static/iconos/iconos.svg`**: 32 íconos propios (antes 15). Los nuevos: sumar, flechas,
  foto, prenda, descargar, subir, WhatsApp, recibo, reloj, copiar, enlace, editar, papelera e
  información. "Más" ahora son tres puntos.
- **`templates/base.html`**: la hoja tiene un encabezado quieto de 52 px (ícono y nombre de la
  sección a la izquierda, botones a la derecha) y el contenido se desplaza por dentro. Cada
  pantalla puede cambiar el lado izquierdo del encabezado (la miga para volver del pedido) o
  usar todo el ancho (`hoja--completa`).
- **`templates/_menu.html`** y **`config/menu.py`**: logo en un cuadrito blanco, buscador con
  "Ctrl K", contadores en gris, subsecciones "Atrasados" y "Con saldo" dentro de Pedidos (la
  costurera solo ve "Atrasados") y, al fondo, el taller con su logo o sus iniciales y el botón
  para salir. El título de cada pantalla lleva el ícono de su sección.
- **`templates/piezas/`**:
  - `_etiqueta.html`: la insignia con su circulito (vacío, a medias, lleno o alerta). Puede
    recibir una insignia ya armada (`insignia=...`) o su texto, tono y circulito;
  - `_cifra.html`: una casilla de la tarjeta de cifras; con `explica`, se lee de dónde sale el
    número al pasar el mouse;
  - `_filtro.html`: una pestaña con su conteo;
  - `_pasos.html`: seis barritas en vez de seis círculos;
  - `_progreso.html`: riel más delgado (`delgado`);
  - `_boton_nuevo_pedido.html`: en celular es el botón redondo negro con un "+";
  - `_mini.html` (nueva): la foto del pedido en miniatura, o una prenda si no tiene;
  - `_vacio.html` (nueva) y `dibujos/` (nuevos): la pantalla vacía con su dibujo. Hay cuatro
    dibujos propios: telas, pedidos, clientes y prendas;
  - `muestrario.html`: la página `/piezas/` con todas las piezas nuevas.
- **`pedidos/calculos.py`**: cada insignia trae su circulito; los tonos siguen la regla nueva
  (gris para lo que está bien, verde solo para "Listo", ámbar para "Confirmado"). Hay una
  insignia nueva para el pago: "Pagado", "Vencido", "Abonado 50 %" o "Sin abonos".
- **`config/piezas.py`**: la gráfica con las medidas y colores de la maqueta (gris más claro
  para "Gastado", líneas guía más suaves). Ya no hace una versión baja para la pantalla fija.
- **`static/js/app.js`**: Ctrl K (o Cmd K) lleva al buscador del menú; los menús desplegables
  ("Más acciones", "Cambiar etapa") se cierran al tocar afuera o con Escape; y un botón con
  `data-mostrar` muestra una parte escondida (el buscador de Pedidos detrás de la lupa).
- **`herramientas/capturas.py`**: el formato `completo` toma 1366 x 768, 1920 x 1080 y celular;
  en computador comprueba que la página no se mueva y guarda la hoja entera.

## Pruebas

- Se actualizaron las de la base visual, las animaciones, el esqueleto, los permisos y los
  cálculos para el diseño nuevo, y se agregaron: las subsecciones de Pedidos, las iniciales del
  taller, el ícono del título, Ctrl K, la insignia del pago, la insignia con circulito y que
  `app.css` copie exacto a `diseno/estilo.css`.
- `tests/test_pantalla_fija.py` pasó a ser `tests/test_desplazamiento.py`: abre cada pantalla
  en Chrome y comprueba que la página no se mueve en computador y que nada se sale de lo ancho,
  tampoco en celular.
- Se quitaron dos archivos de pruebas que solo medían la pantalla fija
  (`cotizador/tests/test_pantalla_fija_cotizador.py` y `telas/tests/test_telas_pantalla_fija.py`).
  Lo que sigue valiendo de ellos (que el resultado del cotizador no parpadee mientras se escribe)
  se les pidió a sus carriles.
- Al terminar lo compartido pasaban 1320 pruebas. Las 35 que fallaban eran todas de pantallas
  (revisan los textos y las clases del diseño anterior) y las arregla cada carril.

## Un error que encontré

La insignia recibía la insignia armada con el nombre `etiqueta`, y la página del pedido ya
tenía una variable con ese nombre: en el pedido, una insignia de texto ("Enlace abierto") salía
con el texto de la etapa. Lo notó una prueba de permisos. Ahora se llama `insignia` y, si se da
el texto, manda el texto.
