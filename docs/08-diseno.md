# Diseño

El diseño aprobado está en la carpeta `diseno/`, una página por pantalla, con sus estilos en
`diseno/estilo.css`. Esas páginas son la fuente de verdad de cómo se ve la aplicación:
medidas, colores, textos y orden de los elementos se copian de ahí. Este documento resume las
reglas para no tener que deducirlas.

El 13 de noviembre de 2026 David aprobó rediseñar todo el panel con el **lenguaje visual del
panel de administración de Shopify**, adaptado a lo que hace este CRM (maqueta en
https://claude.ai/artifact/9yNAtEHnQi6GEEM1cWJPB8). Ese cambio reemplazó las reglas anteriores
(hoja gris, bordes, "pantalla fija", verde para pagado y entregado).

`demo/index.html` **no** es la referencia visual. Solo sirve para el comportamiento y los
textos de las funciones (ver `CLAUDE.md`).

## Pantallas de referencia

Cada página se ve bien en computador y en celular: para ver el celular, ábrela en una ventana
de 390 px de ancho, o abre `diseno/index.html`, que las muestra todas en 390 px.

| Archivo | Pantalla |
|---|---|
| `diseno/hoy.html` | Hoy |
| `diseno/hoy-menu-contraido.html` | Hoy con el menú contraído |
| `diseno/pedidos.html` | Lista de pedidos |
| `diseno/nuevo-pedido.html` | Ventana "Nuevo pedido" |
| `diseno/pedido.html` | Pedido por dentro |
| `diseno/calendario.html` | Calendario |
| `diseno/clientes.html` | Clientes |
| `diseno/cotizador.html` | Cotizador |
| `diseno/telas.html` | Telas |
| `diseno/telas-vacia.html` | Telas sin datos (modelo de pantalla vacía) |
| `diseno/resumen.html` | Resumen del mes |
| `diseno/mi-taller.html` | Mi taller |
| `diseno/entrar.html` | Inicio de sesión |
| `diseno/tallas-publico.html` | Formulario público de tallas |
| `diseno/tallas-publico-listo.html` | Formulario público de tallas, ya enviado |
| `diseno/asistente.html` | Asistente abierto encima de Hoy, y Hoy con su caja para preguntarle (tanda 7) |
| `diseno/asistente-limite.html` | Asistente sin preguntas por hoy (tanda 7) |

Hoy, Pedidos, Pedido por dentro, la pantalla vacía y el celular de Hoy y de Pedidos salen
tal cual de la maqueta aprobada. Las demás se adaptaron con el mismo lenguaje y se le muestran
a David antes de darlas por terminadas.

Los nombres de las clases de `diseno/estilo.css` son los de la aplicación: una plantilla copia
el HTML de su página sin traducir nada. Los datos son los de ejemplo (`cargar_ejemplos`).

## Idea general

Un panel limpio, con mucho aire, donde solo se pinta lo que pide atención:

- La pantalla tiene un **marco negro** con un **brillo azul** que asoma abajo a la izquierda.
- A la izquierda, sobre el marco, va el **menú**.
- El contenido va en una **hoja blanca** con esquinas de 16 px, separada 4 px del borde.
- Dentro de la hoja, las **tarjetas** son blancas con una **sombra suave** (no un borde).
- **La página no se mueve.** Arriba de la hoja queda quieto el encabezado (título y botones);
  lo de abajo se desplaza por dentro de la hoja. Ya no hay que hacer caber cada pantalla.
- Cada estado lleva una **insignia con su circulito**. **Lo que está bien va en gris.**

## Colores

Se definen una sola vez como variables de CSS (sección 1 de `diseno/estilo.css` y de
`static/css/app.css`) y no se escriben a mano en cada pantalla.

| Variable | Valor | Uso |
|---|---|---|
| `--marco` | `#0A0A0A` | Marco y menú |
| `--brillo` | degradado azul `#2563C9` | Brillo abajo a la izquierda del marco |
| `--menu-texto` / `--menu-icono` / `--menu-apagado` | `#DCDCDC` / `#B5B5B5` / `#A6A6A6` | Textos e íconos del menú |
| `--menu-actual` | `#2B2B2B` | Fondo de la sección actual |
| `--menu-campo` | `#262626` | Buscador del menú |
| `--hoja` | `#FFFFFF` | Hoja y tarjetas |
| `--negro` | `#1A1A1A` | Texto, pasos cumplidos, día de hoy |
| `--texto-2` | `#616161` | Texto secundario |
| `--texto-3` | `#8A8A8A` | Solo ejemplos de campos, días de otro mes y adornos (no alcanza el contraste de texto) |
| `--linea` | `#EBEBEB` | Divisores dentro de las tarjetas |
| `--borde` | `#E3E3E3` | Borde de botones y pasos que faltan |
| `--borde-campo` | `#8A8A8A` | Borde de campos y buscadores |
| `--suave` | `#F7F7F7` | Encabezado de tablas, fila con el mouse encima, celdas apagadas |
| `--gris` | `#F1F1F1` | Chips, miniaturas, botones redondos del celular |
| `--riel` | `#EDEDED` | Fondo de las barras de progreso |
| `--enlace` | `#005BD3` | Enlaces y anillo del foco |
| `--azul` | `#2563C9` | Gráficas, barras, paso actual |
| `--gris-grafica` | `#B5B5B5` | Segunda serie de las gráficas ("Gastado") |
| `--rojo` | `#C5280C` | Punto de "pedido atrasado" y barras de deuda vencida |

Sombras: `--sombra-tarjeta` (tarjetas), `--sombra-boton` (botón secundario),
`--sombra-principal` (botón principal), `--sombra-flotante` (caja de Hoy), `--sombra-menu`
(menús desplegables) y `--sombra-ventana`. El botón principal es un degradado de `#3A3A3A` a
`#1A1A1A`.

### Insignias

Píldora de 20 px de alto, esquinas de 8 px, letra de 12 px. Seis tonos:

| Tono | Fondo | Texto | Cuándo |
|---|---|---|---|
| `gris` | `#EBEBEB` | `#303030` | Lo que está bien o no pide nada: pagado, entregado, cotizado, sin abonos de un cotizado, suficiente, enlace abierto |
| `azul` | `#E0F0FF` | `#00527C` | En proceso: en corte, en confección |
| `verde` | `#CDFEE1` | `#0C5132` | Solo "Listo": ya se puede entregar |
| `ambar` | `#FFEF9D` | `#4F4700` | Estar pendiente: faltan pocos días, confirmado, tela que se acaba |
| `naranja` | `#FFD6A4` | `#5E4200` | Pago a medias: "Abonado 50 %", sin abonos de un pedido confirmado |
| `rojo` | `#FEDAD9` | `#8E0B21` | Atrasado, deuda vencida |

El **circulito** (`etiqueta--vacio`, `--medio`, `--lleno`, `--alerta`) dice cómo va:

| Circulito | Significa | Ejemplos |
|---|---|---|
| Vacío (punteado) | No ha empezado | Cotizado, Confirmado, Por confirmar, Sin abonos, Faltan 3 días |
| A medias | Va por la mitad | En corte, En confección, Abonado 50 %, Se está acabando |
| Lleno | Completo | Listo, Entregado, Pagado, Suficiente |
| Alerta (!) | Se pasó la fecha | Atrasado 2 días, Vencido |

Las etiquetas cortas que acompañan un número ("1 atrasado", "Vencida", "Enlace abierto") van
sin circulito.

### Reglas de color

1. Los botones principales son negros. Nunca de color. Uno por zona.
2. **Lo que está bien va en gris.** Solo se pinta lo que pide atención.
3. Rojo solo para atrasos y deudas vencidas.
4. Verde solo para "Listo" (el pedido ya se puede entregar).
5. El azul es el color de las gráficas, las barras y lo que está en proceso.
6. Un color nunca va solo: siempre lo acompaña un texto que dice lo mismo.
7. No se agregan colores, sombras ni degradados fuera de los de este documento.

## Tipografía

Una sola fuente: **Inter**, en su versión variable (todos los pesos de 400 a 700 en un solo
archivo), guardada en `static/fuentes/`. No se carga desde internet.

| Uso | Tamaño / interlineado | Peso |
|---|---|---|
| Texto base (computador) | 13 / 20 px | 450 |
| Texto base (celular) | 14 px | 450 |
| Nombre de la sección en el encabezado | 13 px | 550 |
| Título dentro de la página (`.titulo-pagina h1`) | 20 / 28 px | 650 |
| Saludo de Hoy | 26 / 34 px | 600 |
| Título de tarjeta (`h2`) | 13 px | 650 |
| Título de sección ("Tu mes") | 15 px | 650 |
| Cifra | 20 / 28 px | 650 |
| Cifra de una barra de cifras | 15 px | 650 |
| Botón | 12,5 px | 600 |
| Insignia | 12 px | 550 |
| Encabezado de tabla, nota | 12 px | 550 / 450 |
| Título grande en celular | 28 / 34 px | 700 |

Los números usan cifras del mismo ancho (`tabular-nums`). Los valores en pesos no se parten en
dos líneas (`.dinero`).

## Estructura de la página

- **Marco:** ocupa exactamente la ventana. La página no se desplaza.
- **Menú (220 px):**
  - arriba, el logo (las tijeras en un cuadrito blanco de 26 px) y el botón para contraer;
  - el buscador de 28 px con "Ctrl K" a la derecha (Ctrl K o ⌘ K lo enfocan);
  - las secciones, de 30 px de alto, con su ícono de 18 px. La actual lleva fondo `#2B2B2B`,
    letra blanca y peso 650. Los contadores son un número gris a la derecha;
  - dentro de Pedidos, cuando es la sección actual, dos subsecciones: "Atrasados" y "Con
    saldo" (la costurera solo ve "Atrasados");
  - al fondo, "Mi taller" y una fila con el logo del taller (o sus iniciales en un cuadrito
    azul), su nombre y el botón para salir.
- **Menú contraído:** tira de 60 px con el logo (abre el menú), la lupa, un ícono por sección
  (con su contador encima, en blanco) y, al fondo, Mi taller, el logo del taller y salir. Cada
  ícono dice su nombre al pasar el mouse. La elección se recuerda en ese navegador.
- **Hoja:** blanca, esquinas de 16 px, 4 px de margen arriba, a la derecha y abajo.
- **Encabezado de la hoja (52 px, quieto):** a la izquierda, el ícono y el nombre de la sección
  (o la miga para volver, en el pedido); a la derecha, los botones, el principal de último.
- **Contenido:** relleno de 4 px arriba, 16 px a los lados y 24 px abajo, 16 px entre bloques.
  Se desplaza por dentro. No pasa de 1200 px de ancho (en pantallas grandes queda centrado, y
  el encabezado se alinea con él). Hoy usa una columna de 940 px; Pedidos usa todo el ancho
  (`hoja--completa`).

Secciones del menú, en orden: Hoy, Pedidos, Calendario, Clientes, Cotizador, Telas, Resumen.

### En celular (menos de 768 px)

Como la app de Shopify:

- Hoja blanca de borde a borde, sin marco ni menú lateral. La página se desliza normal.
- Arriba, una fila de botones redondos de 36 px (gris; el principal en negro) y, debajo, el
  **título grande** (28 px). En Hoy, a la izquierda va el logo; en el pedido, la flecha para
  volver. Los botones de solo texto del encabezado no van arriba.
- Abajo, una **barra blanca** fija con cinco entradas (ícono de 22 px y nombre de 11 px): Hoy,
  Pedidos, Calendario, Clientes y Más (Buscar, Cotizador, Telas, Resumen, Mi taller y Salir).
  La sección actual va en negro.
- Botones de al menos 40 px de alto, campos de 44 px con letra de 16 px.
- Las tarjetas van en una sola columna. Pedidos se vuelve una lista: foto, nombre, total,
  fecha y encargada, y sus dos insignias. Las demás tablas se desplazan de lado dentro de su
  tarjeta, nunca la página.
- Las pestañas de una lista son píldoras que se deslizan de lado; la elegida en negro.
- En Hoy, lo que hay que hacer se desliza de lado (tarjetas de 280 px).

## Piezas

Cada pieza está una vez en `diseno/estilo.css` (y en `static/css/app.css`) y, si aplica, en
una plantilla de `templates/piezas/`.

| Pieza | Clase | Regla |
|---|---|---|
| Botón principal | `.boton.boton--principal` | Negro con degradado, 28 px, esquinas de 10 px |
| Botón secundario | `.boton` | Blanco con su sombra |
| Botón plano | `.boton--plano` | Sin fondo, texto gris ("Avisar", "Editar") |
| Botón de ícono | `.boton--icono` | Cuadrado de 28 px; lleva `aria-label` |
| Flechas | `.boton--flecha` | Gris, 28 px (pedido anterior y siguiente) |
| Botones pegados | `.grupo-botones` | Mes anterior y siguiente |
| Botón redondo en celular | `.boton--redondo-celular` | En celular se vuelve un círculo con ícono (`.boton__icono-celular`); el texto queda para lectores |
| Chip | `.chip` | Atajo gris de 26 px ("Nuevo pedido", "Noviembre") |
| Tarjeta | `.tarjeta` | Blanca, esquinas de 12 px, sombra suave, sin relleno |
| Cabeza, cuerpo y pie de tarjeta | `.tarjeta__cabeza`, `__cuerpo`, `__pie` | 12/16/4 px; 8/16/16 px; el pie con línea arriba y los botones a la derecha |
| Insignia | `.etiqueta.etiqueta--{tono}.etiqueta--{circulito}` | Ver "Insignias" |
| Miniatura | `.mini`, `.mini--grande` | Foto del pedido (o ícono de prenda) en 32 o 40 px |
| Cifras | `.cifras` > `.cifra` | Casillas separadas por una línea; nombre gris (punteado si tiene `title`), número de 20 px |
| Barra de cifras | `.cifras--barra` | Más baja, con un chip al comienzo (Pedidos) |
| Pestañas | `.filtros` > `.filtro` | Dentro de la tarjeta, arriba de la tabla; la elegida en gris |
| Tabla | `.tabla` | Encabezado `--suave` de 12 px; filas de 44 px; la fila entera abre (`.tabla__enlace`) |
| Pie de lista | `.paginas` | Cuántos hay |
| Campo | `.campo` > `.campo__control` | Etiqueta arriba, 32 px, borde `--borde-campo`, esquinas de 8 px |
| Buscador | `.buscador` | Campo con lupa |
| Aviso de formulario | `.aviso` | Ámbar |
| Banner | `.banner` | Aviso grande, azul claro (dotación en Clientes) |
| Riel de progreso | `.progreso` | 6 px, relleno azul (rojo si está atrasado) |
| Barra proporcional | `.fila-proporcion` > `.proporcion` | "Quién te debe", ventas por tipo |
| Pasos de etapa | `.pasos` > `.paso` | Seis barritas de 4 px con su nombre; cumplidas en negro, la actual en azul; cada una es un botón |
| Cuentas | `.cuentas` > `.cuentas__fila` | Nombre y valor; la de total con línea arriba y en negrita |
| Cronología | `.cronologia` | Días y lo que pasó, con circulito y línea |
| Subir foto | `.subir` | Zona con borde punteado |
| Casilla | `.casilla` | 16 px; negra con visto bueno al marcarla |
| Menú desplegable | `.desplegable` | Un `<details>`: el botón y una tarjeta flotante con opciones |
| Pantalla vacía | `.vacio` | Dibujo, título, para qué sirve y botón; debajo, `.mas-info` |
| Título de página | `.titulo-pagina` | Nombre de 20 px con sus insignias al lado y una línea de apoyo |
| Columnas | `.columnas` | Principal y una de 300 px; cada una es una pila (`.columna`) |
| Dos tarjetas | `.dos-columnas` | Se reparten 1,6 a 1 (o iguales con `--iguales`) |
| Gráfica de barras | `.grafica` | Azul y `--gris-grafica`, esquinas de 4 px, líneas guía `#F1F1F1`, con leyenda |
| Ventana | `.ventana` | Tarjeta flotante de 620 px: cabeza gris, cuerpo y pie con los botones. En celular sube desde abajo |
| Aviso corto | `.aviso-corto` | Negro, esquinas de 12 px, abajo en el centro |

## Alineación

- Las tarjetas que van **lado a lado en una fila** (`.dos-columnas`, las cartas de Hoy, las
  cifras) terminan a la misma altura.
- En **dos columnas de tarjetas apiladas** (`.columnas`: el pedido, el cotizador, el
  calendario), cada columna mide lo que mide su contenido, como en Shopify. La última tarjeta
  ya no se estira hasta abajo.
- La hoja termina donde termina el contenido. Ya no se llena el alto de la pantalla.

## Desplazamiento (reemplaza la "pantalla fija")

Regla aprobada por David con la maqueta, el 13 de noviembre de 2026:

- En computador, el marco mide el alto de la ventana y **la página no se desplaza**: el menú y
  el encabezado de la hoja quedan quietos. **El contenido de la hoja se desplaza por dentro**,
  debajo del encabezado, como en Shopify.
- **Ya no hay que hacer caber cada pantalla** en 1366 x 768. Las listas largas se ven
  completas, sin desplazarse dentro de su tarjeta (se quitaron `.llenar` y `.desplazable`).
- Las tablas anchas se desplazan de lado dentro de su tarjeta.
- En celular, la página se desliza normal.

## Pantallas vacías

Cuando un taller está empezando y una sección no tiene nada (Pedidos, Clientes, Telas, las
prendas guardadas del Cotizador), sale una tarjeta con:

- un dibujo propio de 168 x 150 px con los colores del taller (gris claro, azul y un toque de
  amarillo), como el rollo de tela de `diseno/telas-vacia.html`;
- un título de 15 px que dice qué va a aparecer ahí ("Aquí vas a ver tus telas");
- una frase que explica para qué sirve;
- el botón principal para agregar el primero.

Debajo de la tarjeta, un enlace "Cómo llevar ..." que abre ahí mismo una explicación corta.

## Cronología del pedido

Se arma solo con lo que ya se guarda, sin cambiar el modelo de datos:

- cuándo se creó el pedido, por cuánto y quién lo creó;
- cada abono (fecha, valor y quién lo registró);
- las tallas: las que llegaron por el enlace se juntan por día ("12 personas enviaron su talla
  por el enlace"); las que se agregaron a mano dicen de quién son.

Va del más reciente al más antiguo, agrupado por día ("Hoy", "Ayer", "7 de noviembre"). Los
cambios de etapa no aparecen porque hoy no se guardan; guardarlos cambiaría el modelo de datos
y hay que preguntarle a David antes.

## Animaciones

Cortas, sobrias y con un propósito: decir qué pasó. Solo CSS y JavaScript propio, sin
librerías.

| Variable (`:root` de `app.css`) | Valor | Para qué |
|---|---|---|
| `--duracion-corta` | 150 ms | Pasar el mouse, presionar, lo que sale |
| `--duracion` | 200 ms | Lo que entra, ventanas, panel "Más", menú, cambio de sección |
| `--duracion-larga` | 250 ms | Barras y gráficas que crecen |
| `--curva` / `--curva-salida` | | Entra rápido y frena suave / sale acelerando |
| `--espera-cargando` | 300 ms | Si una acción tarda más, el botón muestra "cargando" |
| `--tiempo-aviso` | 2,8 s | Cuánto se queda a la vista el aviso de confirmación |

Las duraciones se definen **una sola vez**, ahí. Ninguna regla ni el JavaScript escriben una
duración a mano.

- **Botones:** al pasar el mouse el secundario se aclara un poco; al presionar se hunden. Si
  la acción tarda, el botón muestra un círculo que gira en lugar de su texto, sin cambiar de
  ancho (`.esta-cargando`).
- **Cambios sin recargar (HTMX):** lo que entra aparece con un desvanecido; lo que sale se
  desvanece, y una fila que se quita se cierra suavemente. Se reconoce por el `id`: lo que
  tiene el mismo id antes y después no se anima. Una parte que se actualiza mientras se
  escribe y no debe parpadear lleva `data-sin-animar`.
- **Ventanas** ("Nuevo pedido"), **menús desplegables** y el **panel "Más"** abren y cierran
  con transición. En celular la ventana sube desde abajo. Al cerrarse, el cursor vuelve al
  botón que la abrió.
- **Barras de progreso, "Quién te debe" y las gráficas** crecen hasta su valor al aparecer.
- **Cambio de etapa:** la barrita del paso cambia de color con una transición (cada paso tiene
  su id).
- **Aviso corto** al guardar ("Abono registrado."): abajo, en el centro (en celular, encima de
  la barra), y se va solo. El servidor lo manda con `config/avisos.py`.
- **Menú:** se contrae y se abre con transición.
- **Cambio entre secciones:** el contenido pasa con un desvanecido corto; el menú queda quieto
  (View Transitions del navegador).
- **Menos movimiento:** si la persona lo pidió en su equipo (`prefers-reduced-motion`), no ve
  ninguna animación.

Todas se ven funcionando en la página `/piezas/`.

## Íconos

Íconos de línea propios, de 18 px (16 y 14 en botones), trazo de 1.75, guardados en
`static/iconos/iconos.svg` y dibujados igual dentro de las páginas de `diseno/`. No se usan
emojis ni librerías de íconos, ni los íconos de Shopify.

## Accesibilidad

- Todo lo que se toca es un `<button>` o un `<a>` de verdad.
- Cada campo tiene su `<label>`.
- Los botones que solo tienen ícono llevan `aria-label` (y `title` para verlo con el mouse).
- El texto cumple contraste de 4.5 a 1 contra su fondo: por eso el texto secundario es
  `#616161` y `#8A8A8A` queda solo para ejemplos de campos y adornos.
- El foco del teclado siempre se ve (anillo `--enlace`).
- Cada insignia dice con palabras lo mismo que su color y su circulito.

## Asistente

Referencia: `diseno/asistente.html` y `diseno/asistente-limite.html`. Estilos en la sección 7
de `diseno/estilo.css`. Qué dice y qué hace: `docs/10-asistente.md`.

- **Ícono: la esfera de Lucy** (pedido de David del 15 de noviembre de 2026; reemplaza al
  botón de costura con carita del día 14). Es el mismo circulito azul de Lucy, el producto de
  David: tinta azul que se mueve en agua, mate, con un filo claro alrededor. Pieza
  `templates/piezas/esfera.html`, la dibuja `static/js/esfera.js` y sus estilos están en la
  sección 7 ("La esfera"). Sin JavaScript se ve el azul de fondo (`#1463FF`). Mide 24 px como
  **avatar** (`.avatar-asistente`: la caja de Hoy y arriba del panel), 20 px en el botón
  redondo del celular y 16 px en el botón "Asistente" del encabezado y en el título de su
  página. Se mueven la de arriba del panel y la de la caja de Hoy (pedido de David, el mismo
  día); las del botón quedan quietas. Mientras el asistente revisa los datos, la del panel late
  despacio y la tinta corre más rápido. Con "menos movimiento" queda quieta. Es la única
  excepción al azul de "gráficas y en proceso": es la marca del asistente, no un estado.
- **Botón:** "Asistente" con su ícono, en el encabezado, a la izquierda del botón principal.
  Mientras el panel está abierto queda gris (presionado). Atajo: Ctrl J (Cmd J en Mac).
- **La caja grande de Hoy** (como en Shopify, pedido de David): con el asistente prendido le
  pregunta al asistente. Arriba "Pregúntale algo a tu asistente"; abajo el avatar, los atajos
  de siempre (Nuevo pedido, Registrar abono, Cotizar) y el botón negro de enviar. En celular
  va en una sola fila: avatar, texto y enviar. Lo que se escribe abre el panel con esa
  pregunta. Con el asistente apagado es el buscador de `diseno/hoy.html`, como antes.
- **Computador (1024 px o más):** un panel blanco de 360 px a la derecha de la hoja, con el
  mismo margen de 4 px y las mismas esquinas de 16 px. La hoja se angosta para dejarle sitio.
  Con el panel abierto y una pantalla de menos de 1440 px, las columnas de la hoja pasan a
  una, como en las pantallas medianas, para que nada se apriete.
- **Pantallas medianas (768 a 1023 px):** el panel flota encima de la hoja, a la derecha, con
  la sombra de las ventanas.
- **Celular:** un botón redondo con el ícono. El panel ocupa toda la pantalla, encima de la
  barra de abajo, con el título grande y botones de 40 px.
- **Conversación:** lo que pregunta la usuaria va en una burbuja gris a la derecha; lo que
  contesta va suelto, sin burbuja. Arriba de cada respuesta, en gris y con un visto, qué
  revisó. Al final, un enlace a la pantalla donde se ve completo.
- **Tarjetas dentro de una respuesta:** las mismas tarjetas de la aplicación, con sombra
  suave. "Quién te debe" usa filas como las de Hoy; la cotización usa el total grande y las
  filas del Cotizador; el mensaje de WhatsApp muestra a quién va, el texto en un recuadro
  gris claro y los botones "Copiar" y "Abrir en WhatsApp" (el principal, negro).
- **Mientras busca:** tres puntos que laten y "Revisando tus datos…". Con "menos movimiento"
  los puntos se quedan quietos.
- **Quedan pocas preguntas:** una línea ámbar encima de la caja. Mientras vaya bien no se ve
  nada.
- **Sin preguntas:** el aviso va en la conversación en un recuadro gris con un reloj, y la
  caja queda apagada ("Vuelvo a contestar mañana").
- **Mi taller:** un bloque "Asistente" con "N de 600" y el riel azul de siempre.
- **Colores:** los de siempre. Rojo solo para lo vencido o atrasado, igual que en las
  pantallas.

## Lo que se tomó de Shopify y lo que no

- **Se tomó:** la forma de cada pantalla (inicio con saludo y tarjetas, lista con barra de
  cifras y pestañas, pedido en dos columnas con cronología, pantalla vacía con dibujo), las
  medidas, las insignias con circulito, la regla de "lo que está bien va en gris", el menú
  negro con subsecciones, el buscador con "Ctrl K" y, en celular, el título grande y la barra
  de abajo.
- **No se tomó:** su logo, sus íconos, sus dibujos ni su letra (ShopifyInter). Aquí van
  íconos propios, Inter y dibujos propios. Tampoco las casillas para elegir varios pedidos a
  la vez.
- **Se tomó después (tanda 7, 14 de noviembre de 2026):** el asistente, a la manera del
  "Sidekick" de Shopify: un panel al lado de la hoja que contesta con las cifras del taller.
  Ver "Asistente" arriba y `docs/10-asistente.md`.

## Lo que no se hace

- No cambiar el diseño sin proponérselo primero a David con un ejemplo (una maqueta).
- No agregar colores, sombras ni degradados fuera de los de este documento.
- No usar el rojo para nada que no sea un atraso o una deuda vencida, ni el verde para nada
  que no sea "Listo".
