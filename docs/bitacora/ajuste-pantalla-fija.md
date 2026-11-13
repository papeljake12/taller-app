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
