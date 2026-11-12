# Diseño

El diseño aprobado está en la carpeta `diseno/`, una página por pantalla. Esas páginas son
la fuente de verdad de cómo se ve la aplicación: medidas, colores, textos y orden de los
elementos se copian de ahí. Este documento resume las reglas para no tener que deducirlas.

`demo/index.html` ya **no** es la referencia visual. Solo sirve para el comportamiento y los
textos de las funciones (ver `CLAUDE.md`).

## Pantallas de referencia

| Archivo | Pantalla |
|---|---|
| `diseno/hoy.html` | Hoy, en computador |
| `diseno/hoy-menu-contraido.html` | Hoy con el menú contraído |
| `diseno/hoy-celular.html` | Hoy, en celular (390 px) |
| `diseno/pedidos.html` | Lista de pedidos |
| `diseno/pedido.html` | Pedido por dentro |
| `diseno/calendario.html` | Calendario |
| `diseno/clientes.html` | Clientes |
| `diseno/cotizador.html` | Cotizador |
| `diseno/telas.html` | Telas |
| `diseno/resumen.html` | Resumen del mes |

Para verlas, abre el archivo en el navegador. Los datos son de ejemplo.

Pantallas sin página de referencia: inicio de sesión, ventana "Nuevo pedido", formulario
público de tallas y "Mi taller". Se construyen con las mismas piezas de este documento
(tarjeta, campo, botón) y se le muestran a David antes de darlas por terminadas.

## Idea general

Un panel de administración sobrio. El negro manda y los demás colores solo acompañan:

- La pantalla completa tiene un **marco negro** que termina en azul abajo.
- A la izquierda, sobre ese marco, va el **menú**.
- El contenido va en una **hoja gris claro** con esquinas redondeadas, encima del marco.
- Dentro de la hoja, todo va en **tarjetas blancas**.

## Colores

Se definen una sola vez como variables de CSS y no se escriben a mano en cada pantalla.

| Variable | Valor | Uso |
|---|---|---|
| `--negro` | `#1A1A1A` | Texto, botones principales, pasos de etapa, día de hoy |
| `--texto-2` | `#555555` | Texto secundario |
| `--texto-3` | `#8A8A8A` | Texto apagado (días de otro mes) |
| `--hoja` | `#F1F1F1` | Fondo de la hoja de contenido y etiqueta gris |
| `--tarjeta` | `#FFFFFF` | Fondo de tarjetas |
| `--suave` | `#F7F7F7` | Encabezado de tablas, celdas apagadas |
| `--linea` | `#E1E1E1` | Borde de tarjetas y divisores |
| `--borde-control` | `#C9C9C9` | Borde de botones secundarios y campos |
| `--riel` | `#EDEDED` | Fondo de las barras de progreso |
| `--azul` | `#2563C9` | Barras de gráficas, barras de progreso, final del marco |
| `--gris-grafica` | `#A6A6A6` | Segunda serie de las gráficas ("Gastado") |
| `--rojo` | `#B3261E` | Atrasos y deudas vencidas |
| `--verde` | `#1B6E3C` | Pagado y "Te quedó" |

Etiquetas (fondo y texto):

| Tono | Fondo | Texto | Cuándo |
|---|---|---|---|
| Rojo | `#FBE9E7` | `#8C1D18` | Atrasado, deuda vencida |
| Verde | `#E2F1E7` | `#14532D` | Pagado, entregado, tela suficiente |
| Ámbar | `#FFF0C2` | `#5C4500` | Hay que estar pendiente: faltan pocos días, por confirmar, tela que se acaba |
| Azul | `#E3EEFC` | `#0B4A8F` | En proceso: en corte, en confección |
| Gris | `#F1F1F1` | `#1A1A1A` | Sin urgencia: cotizado, confirmado, listo |

Reglas de color:

1. Los botones principales son negros. Nunca de color.
2. Rojo solo para atrasos y deudas. Verde solo para pagado y entregado.
3. El azul es el único color de las gráficas y barras. No se agregan más colores.
4. Un color nunca va solo: siempre lo acompaña un texto que dice lo mismo ("Atrasado 2 días").
5. El marco es `linear-gradient(180deg, #000000 0%, #000000 70%, #2563C9 100%)`. El azul
   apenas se asoma abajo. En celular la franja de arriba es
   `linear-gradient(90deg, #000000 0%, #000000 55%, #2563C9 100%)`.

## Tipografía

Una sola fuente: **Inter**, pesos 400, 500, 600 y 700. Va guardada en el proyecto
(`static/fuentes/`), no se carga desde internet.

| Uso | Tamaño | Peso |
|---|---|---|
| Texto base | 14 px, interlineado 1.45 | 400 |
| Título de pantalla (`h1`) | 20 px | 700 |
| Título de tarjeta (`h2`) | 15 px | 700 |
| Cifra grande | 24 px | 700 |
| Nota y texto pequeño | 13 px | 400 |
| Etiqueta | 12 px | 600 |
| Botón | 14 px | 600 |

Los valores en pesos no se parten en dos líneas (`white-space: nowrap`).

## Estructura de la página

- **Marco:** ocupa toda la pantalla. Relleno de 8 px arriba, a la derecha y abajo; 0 a la
  izquierda.
- **Menú:** entre 220 y 236 px de ancho. Logo (tijeras) y nombre del taller, botón para
  contraer, buscador, secciones y "Mi taller" al fondo. La sección actual lleva un fondo
  blanco al 18 %. Los contadores van en una píldora blanca con texto negro.
- **Menú contraído:** tira de 60 px con el logo (abre el menú), la lupa y un ícono por
  sección. Cada ícono muestra el nombre al pasar el mouse. La elección se recuerda en ese
  navegador.
- **Hoja:** fondo `--hoja`, esquinas de 14 px, relleno 20 px arriba, 24 px a los lados y
  28 px abajo. Separación de 16 px entre bloques.
- **Encabezado de la hoja:** título y dato de apoyo a la izquierda; botones a la derecha, el
  principal de último.

Secciones del menú, en orden: Hoy, Pedidos, Calendario, Clientes, Cotizador, Telas, Resumen.

### En celular

- No hay menú lateral. Arriba, una franja con el título y el botón principal.
- Abajo, una barra fija con cinco entradas: Hoy, Pedidos, Calendario, Clientes y Más
  (Cotizador, Telas, Resumen y Mi taller).
- Botones de al menos 44 px de alto.
- Las tarjetas se apilan en una sola columna. Las tablas anchas se desplazan dentro de su
  tarjeta, nunca la página completa.

## Piezas

Cada pieza se construye una vez (clase de CSS y, si aplica, plantilla parcial) y se reutiliza.

| Pieza | Regla |
|---|---|
| Tarjeta | Fondo blanco, borde de 1 px `--linea`, esquinas de 12 px, relleno 14 px por 16 px |
| Botón principal | Fondo `--negro`, texto blanco, alto mínimo 36 px, esquinas de 8 px. Uno por zona |
| Botón secundario | Fondo blanco, borde `--borde-control`, texto negro, mismas medidas |
| Cifra | Tarjeta con nombre (600, `--texto-2`), número de 24 px y una línea de apoyo |
| Etiqueta | Píldora de 12 px con uno de los cinco tonos |
| Fila de lista | Relleno 10 a 14 px por 16 px y una línea `--linea` arriba |
| Tabla | Encabezado `--suave`, filas con línea, dentro de una tarjeta con desplazamiento horizontal |
| Campo | Etiqueta visible arriba, borde `--borde-control`, esquinas de 8 px |
| Filtro | Botón con su conteo; el elegido va en negro |
| Barra de progreso | Riel `--riel`, relleno `--azul` (rojo si está atrasado) |
| Gráfica de barras | Barras `--azul` y `--gris-grafica`, esquinas de 4 px, ejes discretos, con leyenda |
| Pasos de etapa | Seis círculos; los cumplidos en negro con visto bueno, el actual con punto |
| Fotos que pasan | Ver abajo |

### Fotos que pasan ("Trabajos del taller")

- Tarjeta en la pantalla Hoy con las fotos de los pedidos, una a la vez.
- Cada foto dura 4 segundos y cambia con un desvanecido. Los puntos de arriba marcan cuál va.
- Alto fijo de 264 px; la foto se recorta para llenar (`object-fit: cover`).
- Sobre la foto, abajo a la izquierda, una etiqueta blanca con el nombre del trabajo.
- Si la persona pidió menos movimiento en su equipo (`prefers-reduced-motion`), se queda en
  la primera foto.
- Si el taller no tiene fotos, la tarjeta invita a subir la primera en vez de quedar vacía.
- Las fotos de `diseno/img/` son de ejemplo, hechas con IA. En la aplicación salen de los
  pedidos del taller.

## Alineación

Esta regla se aprobó de forma expresa: nada de tarjetas de distinto alto en una misma fila.

- Las tarjetas de una misma fila miden lo mismo de alto (`align-items: stretch`).
- Cuando hay dos columnas de tarjetas, las dos terminan a la misma altura: la última tarjeta
  de cada columna crece para llenar (`flex-grow: 1`).
- Las filas de dos tarjetas se reparten 3 a 2 (`flex: 3 1 440px` y `flex: 2 1 300px`) y se
  apilan solas cuando no caben.
- Las cifras van en una rejilla `repeat(auto-fit, minmax(170px, 1fr))` con 12 px de separación.
- No debe quedar un hueco grande vacío al final de la hoja.

## Íconos

Íconos de línea propios, de 18 px, trazo de 1.75, guardados en el proyecto. Están dibujados
dentro de las páginas de `diseno/`; se copian de ahí. No se usan emojis ni librerías de
íconos externas.

## Accesibilidad

- Todo lo que se toca es un `<button>` o un `<a>` de verdad.
- Cada campo tiene su `<label>`.
- Los botones que solo tienen ícono llevan `aria-label`.
- El texto cumple contraste de 4.5 a 1 contra su fondo.
- El foco del teclado siempre se ve.

## Lo que no se hace

- No copiar el diseño de otra aplicación. Este panel tiene íconos, colores y reglas propias.
- No agregar colores, sombras ni degradados fuera de los de este documento.
- No cambiar el diseño sin proponérselo primero a David con un ejemplo.
