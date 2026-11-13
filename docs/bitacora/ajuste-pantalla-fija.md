# Ajuste: pantalla fija y animaciones

Rama `ajuste-pantalla-fija-y-animaciones`. Dos cambios de diseño que pidió David:

1. **Pantalla fija en computador.** El marco mide exactamente el alto de la ventana y la página
   nunca se desplaza: el menú y el título con sus botones quedan siempre a la vista. Cada
   pantalla tiene que verse completa en 1366 x 768. Si una lista de verdad no cabe, se desplaza
   solo esa lista, dentro de su tarjeta. En celular todo sigue igual.
2. **Animaciones.** Cortas (150 a 250 ms), definidas una sola vez en `app.css`, y ninguna si la
   persona pidió menos movimiento en su equipo.

## El plan

Primero el coordinador hace lo compartido, una sola vez para todas las pantallas. Después,
un agente por pantalla ajusta la suya, cada uno en su propia copia y con su propia base de
datos, y un revisor que no escribió el código revisa cada una antes de unirla.

| Carril | Pantalla | Archivos propios |
|---|---|---|
| A | Hoy (también con el menú contraído y como costurera) | `hoy.html` y sus partes, `vistas/hoy.py`, `test_hoy.py` |
| B | Pedidos, Buscar y Nuevo pedido | `lista.html`, `buscar.html`, `_lista_*`, `_nuevo.html`, `vistas/lista.py`, `test_lista.py` |
| C | Pedido por dentro | `pedido.html` y sus partes, `vistas/detalle.py`, `abonos.py`, `tallas.py`, `materiales.py`, `fotos.py` y sus pruebas |
| D | Calendario | `calendario.html` y sus partes, `vistas/calendario.py`, `test_calendario.py` |
| E | Clientes | `clientes.html` y sus partes, `vistas/clientes.py` y sus pruebas |
| F | Cotizador | la app `cotizador/` (menos `models.py` y `urls.py`) |
| G | Telas | la app `telas/` (menos `models.py` y `urls.py`) |
| H | Resumen | la app `finanzas/` (menos `models.py` y `urls.py`) |
| I | Mi taller | las plantillas y vistas de "Mi taller" en `cuentas/` |

Cada carril escribe sus reglas de CSS solo dentro de su apartado de `static/css/app.css`
(sección 8, "Ajustes de cada pantalla"), que el coordinador dejó marcado; el resto de los
archivos compartidos no los toca. Su explicación va en `docs/bitacora/ajuste-pantalla-fija/`.

## Lo compartido (lo hizo el coordinador)

- **`static/css/app.css`**
  - Variables de movimiento en `:root`: `--duracion-corta` (150 ms), `--duracion` (200 ms),
    `--duracion-larga` (250 ms), dos curvas, la espera antes de "cargando" y el tiempo del
    aviso.
  - Sección 6, pantalla fija: el marco mide el alto de la ventana; si algo no cabe, se
    desplaza el contenido de la hoja, nunca la página. Dos piezas nuevas para armar cada
    pantalla:
    - `.llenar`: el bloque toma el alto que queda;
    - `.desplazable`: la parte que se desplaza por dentro, con el encabezado de la tabla fijo.
  - En pantallas de poca altura (hasta 900 px) hay menos relleno.
  - Sección 7, animaciones: botones, "cargando", barras y gráficas que crecen, pasos de etapa,
    ventana, panel "Más", menú, aviso corto y cambio de sección.
  - Sección 9: con menos movimiento, todo en 0.
- **`static/js/app.js`**
  - Lee las duraciones de `app.css`.
  - Botones que esperan.
  - Lo que entra y sale con HTMX: se reconoce por el `id`. Lo que se va se desvanece y, si
    es una fila, se cierra.
  - Ventana y panel "Más" que se cierran con transición; menú que se contrae con transición.
  - El aviso corto.
- **`config/avisos.py`**: `avisar(request, respuesta, "Abono registrado.")`. Si la página se
  queda, el texto va en la cabecera de HTMX; si se va a otra, como mensaje de Django.
- **`templates/base.html`**: la caja del aviso corto y los avisos que llegan de la página
  anterior.
- **Piezas**
  - Cada paso de etapa tiene su id y su visto bueno siempre puesto, para que el cambio se
    vea con transición.
  - La gráfica tiene una versión más baja para el computador
    (`{% grafica_barras meses alto_computador=130 %}`).
- **`/piezas/`**: una tarjeta "Animaciones" y tres de ejemplo (filas que entran y salen,
  cambio de etapa, barras que crecen y una ventana), con acciones que tardan un segundo a
  propósito.
- **`herramientas/capturas.py --formatos fijo`**:
  - toma 1366 x 768, 1920 x 1080 y celular;
  - avisa si la página se desplaza;
  - dice qué pantallas no caben y qué listas se desplazan por dentro.
- **Pruebas**
  - `tests/test_animaciones.py`: duraciones, menos movimiento, aviso, piezas y ejemplos.
  - `tests/test_pantalla_fija.py`: abre cada pantalla en Chrome y comprueba que la página no
    se desplaza y cuáles caben.
- **`docs/08-diseno.md`**: las dos reglas nuevas.

Antes de repartir, el coordinador probó las animaciones en Chrome con un navegador automático
(en `/piezas/`, con y sin "menos movimiento"): botón "cargando", aviso, fila que entra y que
sale, cambio de etapa, ventana (también con Escape), menú y panel "Más". Encontró y corrigió
un error: si el servidor cerraba la ventana y respondía vacío, la ventana se volvía a abrir
vacía.

## Cómo quedaron las pantallas antes de los carriles

Con solo lo compartido, en 1366 x 768 la página ya no se desplaza en ninguna pantalla y todas
caben, menos dos que tienen mucho contenido: **Hoy** (968 px de contenido en 682) y **Pedido
por dentro** (1108 px en 682). En 1920 x 1080 tampoco caben esas dos.

## Cómo terminó

Los nueve carriles terminaron y pasaron por su revisor. Los nueve revisores los aprobaron sin
problemas graves. El coordinador los unió uno por uno y corrió todas las pruebas después de
cada unión. Al final pasan **1348 pruebas** (había 1215 antes del ajuste).

### ¿Cabe cada pantalla?

Medido con los datos de ejemplo. **En computador la página no se desplaza en ninguna
pantalla**, en ningún tamaño.

| Pantalla | 1366 x 768 | 1920 x 1080 | Lo que se desplaza por dentro con muchos datos |
|---|---|---|---|
| Hoy (también menú contraído y costurera) | Cabe | Cabe | "Qué hacer hoy" y "Quién te debe" |
| Pedidos y sus filtros | Cabe | Cabe | La tabla, con el encabezado fijo |
| Buscar | Cabe | Cabe | La lista más larga; si las dos son largas, mitad y mitad |
| Nuevo pedido | Cabe | Cabe | — |
| **Pedido por dentro** | **No cabe** | Cabe (justo) | Materiales y las personas de Tallas |
| Calendario | Cabe | Cabe | "Entregas del mes" |
| Clientes | Cabe | Cabe | La tabla, con el encabezado fijo |
| Cotizador | Cabe | Cabe | — |
| Telas | Cabe | Cabe | La tabla, con el encabezado fijo |
| Resumen | Cabe | Cabe | Los gastos del mes |
| Mi taller | Cabe | Cabe | Las costureras |

### Lo que no cupo y por qué

- **Pedido por dentro en 1366 x 768.**
  - Como dueña faltan unos 315 px (997 de contenido en 682).
  - Como costurera faltan unos 80 px (761 en 682).
  - La razón:
    - la columna derecha (Pagos, Entrega, Cliente y Foto) mide unos 915 px aun apretada;
    - no tiene ninguna lista larga que se pueda desplazar por dentro;
    - para que quepa habría que mover o plegar tarjetas, y eso es un cambio de diseño.
  - Lo que pasa hoy: la página no se mueve. Lo que no cabe se desplaza dentro de la hoja,
    debajo del título y sus botones.
  - En 1920 x 1080 cabe el pedido de ejemplo, pero uno con foto y dos abonos o más tampoco cabe.
  - Las opciones para que decidas están en `ajuste-pantalla-fija/pedido.md`:
    - dejarlo así;
    - plegar "Cliente" y "Foto" y llevar "Eliminar" a un botón arriba;
    - dos pestañas.
- **Dos momentos pasajeros del Cotizador en 1366 x 768.**
  - La pregunta "¿Quitar … de tus prendas guardadas?" se pasa 82 px.
  - Un error de dos renglones bajo un campo se pasa 7 px.
  - Mientras duran se desplaza la hoja. Desde 1440 x 900 caben.
- **La página interna `/piezas/`.** Es el muestrario de todas las piezas, solo existe en
  desarrollo y es larga a propósito: se desplaza su hoja.

### Lo que el coordinador agregó al unir (pedidos de los carriles)

- **En una ventana larga se desplaza solo su cuerpo.** El título con la X y los botones quedan a
  la vista (lo notaron Clientes y Telas).
- **El cursor vuelve al botón correcto** después de cerrar una ventana con transición (Telas).
- **"Copiado. Ya lo puedes pegar en WhatsApp."** ahora se ve como aviso corto, como en la demo
  (Cotizador y Hoy).
- **Una fila de tabla que se quita** se desvanece, y las de abajo suben suave a su lugar (Telas).
- **Columnas en una hoja angosta:** las que llenan se angostan en vez de salirse por la derecha
  (Resumen, Calendario y Mi taller).
- **Las listas que se desplazan por dentro** ya no vuelven arriba cuando se actualiza su tarjeta
  (Mi taller).
- **En la gráfica baja** las barras aprovechan mejor el alto (Hoy).

### Avisos cortos que se agregaron

- **De la demo:**
  - "Abono registrado.", "Foto guardada.", "Foto quitada.", "Pedido eliminado.";
  - "Pedido guardado.", "Pedido creado como cotizado.";
  - "Prenda guardada en tu lista.", "Prenda quitada de tu lista.";
  - "Tela agregada.", "<tela>: quedan N m.", "Gasto registrado.", "Nombre guardado.";
  - "Copiado. Ya lo puedes pegar en WhatsApp."
- **Nuevos, del mismo estilo, porque la demo no tenía** (cada carril los anotó en su bitácora):
  - "Abono quitado.";
  - "Material agregado.", "Material quitado.";
  - "Talla agregada.", "Talla quitada.";
  - "Tela quitada.", "Gasto quitado.";
  - "Cliente creado.", "Cliente guardado.";
  - "Cambios guardados.";
  - "Costurera agregada.", "Costurera desactivada.", "Costurera activada.".
- **Sin aviso, a propósito:**
  - mover la etapa y marcar como listo o entregado en Hoy: la demo no lo tiene y el cambio se ve
    donde se tocó;
  - marcar un material como comprado;
  - filtros y búsquedas;
  - errores de formulario.
- **Ningún aviso muestra plata a la costurera.**

### Qué se probó

- `uv run pytest`: 1348 pruebas, todas pasan. Entre ellas:
  - `tests/test_pantalla_fija.py`: abre todas las pantallas en Chrome, en los dos tamaños, como
    dueña y como costurera;
  - una prueba con Chrome y muchos datos en Pedidos, Calendario, Telas, Cotizador y Mi taller.
- **Capturas finales** en `docs/capturas/ajuste-pantalla-fija/` (1366 x 768, 1920 x 1080 y
  celular), y las de la costurera en `costurera/`.
  - La herramienta comprobó en cada captura de computador que la página no se desplaza.
  - Ninguna lo hace.
- **El celular, comparado con `main` el mismo día y con los mismos datos.** Es igual. Solo
  cambia el suavizado del texto de la barra de abajo, por la transición entre secciones; no se
  nota a simple vista.
- **Las animaciones en Chrome**, en `/piezas/` y en Telas, con y sin "menos movimiento":
  - el botón "cargando";
  - el aviso;
  - la fila que entra y la que sale;
  - el cambio de etapa;
  - la ventana (también con Escape);
  - el menú, el panel "Más" y el cursor después de guardar.

  Sin errores de JavaScript.

### Un tropiezo

Una de mis pruebas desactivó por error a la costurera de ejemplo Yolima en la base de trabajo:
iba a desactivar una costurera de prueba y tocó otra. Lo noté porque la captura de Mi taller en
celular salía distinta. La volví a activar y repetí todas las capturas.

### Qué no se pudo comprobar

- Un computador de 1366 x 768 de verdad. Ahí la ventana del navegador mide unos 650 px de
  alto, no 768, porque se come las barras del navegador y de Windows. En esa ventana más baja
  se desplazan por dentro más listas, y en algunas pantallas la hoja.
- Firefox, Safari, un celular o una tableta de verdad. Todo se probó en Chrome.
- Cómo se ve la barra de desplazamiento de las listas: el Chrome automático no la dibuja.

### Para que tú decidas

1. **Pedido por dentro en 1366 x 768:** cuál de las tres opciones prefieres (o dejarlo así).
2. **La pregunta "¿Quitar …?" del Cotizador:** dejarla así o llevarla a una ventana.
3. **Los avisos nuevos** que no estaban en la demo (la lista de arriba).
4. **Calendario:** un día con muchas entregas muestra las primeras y la última queda cortada.
   Un "+2 más" se vería más limpio, pero es un cambio de diseño.
5. **Pedidos entre 768 y unos 1100 px de ancho** (una tableta): la columna "Cliente y pedido"
   queda muy angosta. Ya pasaba antes del ajuste.
6. **"Pedidos por etapa" en Hoy:** en computador, el número y su etiqueta ("1 atrasado") ahora
   van en la misma línea, para ahorrar alto.
7. **Mucho blanco dentro de algunas tarjetas en 1920 x 1080** (Telas, Pedidos o Clientes con
   pocos datos). Sale de la regla "la última tarjeta llega hasta abajo".
