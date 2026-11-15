# Plan de construcción

Cómo construir la etapa 2 (la aplicación base) rápido y sin rehacer trabajo, repartiendo el
trabajo entre varios agentes de Claude Code con **ultracode**. Las tareas son las de
`docs/05-tareas.md`; aquí se define en qué orden van, cómo se reparten y qué se le pide a
Claude Code en cada paso.

## Cómo se trabaja con varios agentes

Con ultracode encendido, Claude Code puede repartir una tarea grande entre varios agentes
que trabajan al mismo tiempo y revisar el resultado antes de entregarlo. Eso acelera mucho,
pero solo si los agentes no se pisan. Por eso este plan tiene tres papeles:

- **Coordinador:** la sesión principal de Claude Code. Reparte el trabajo, une los
  resultados y es el único que toca los archivos compartidos.
- **Agentes de carril:** cada uno construye una parte y solo toca los archivos de su carril.
- **Revisor:** un agente que no escribió el código y que revisa cada carril antes de unirlo.

Un **carril** es un grupo de tareas con archivos propios, que se puede hacer al mismo tiempo
que los demás carriles de su tanda.

### Encender ultracode

1. En Claude Code, escribir `/effort` y activar ultracode (o escribir `/effort ultracode`).
   En el plan Pro, antes hay que activar los flujos de trabajo en `/config`.
2. La primera vez que vaya a repartir trabajo, Claude Code muestra lo que va a ejecutar y
   pide confirmación. Leerlo antes de aceptar.
3. Para ver cómo van los agentes: `/workflows`.

Si alguno de estos comandos no aparece, actualizar Claude Code y revisar su documentación:
los nombres pueden cambiar entre versiones.

### Dónde usarlo y dónde no

Ultracode gasta bastante más del plan que una sesión normal, porque cada agente consume por
su cuenta. Por eso:

| Tanda | ¿Varios agentes? | Por qué |
|---|---|---|
| 1. Cimientos | No | Cada tarea depende de la anterior. Repartir no acelera |
| 2. Datos y esqueleto | No para construir. Sí un revisor al final | Todo lo demás se apoya aquí; conviene una sola mano |
| 3. Pedidos | Sí, 4 carriles | Partes independientes de una misma zona |
| 4. Plata y Hoy | Sí, 3 carriles | Pantallas independientes |
| 5. Lo que falta | Sí, 6 carriles | Pantallas independientes |
| 6. Cierre | Sí, para la revisión final | Un revisor por pantalla, al tiempo |

En las tandas 1 y 2 se puede apagar ultracode y trabajar con el esfuerzo normal.

## Las ideas que ahorran tiempo

1. **Primero las piezas, después las pantallas.** La hoja de estilos, el marco, el menú y
   las piezas (tarjeta, botón, etiqueta, tabla, campo) se hacen una sola vez en T02. Después,
   cada pantalla es armar con piezas que ya existen.
2. **Todos los datos de una vez.** Los modelos de `docs/02-modelo-de-datos.md` se crean en
   una sola pasada, no uno por tarea.
3. **Los cálculos en un solo lugar.** Saldo, atrasados, por cobrar, vendido, cobrado y los
   demás viven en `pedidos/calculos.py` con sus pruebas. Las pantallas solo los usan.
4. **Datos de ejemplo desde temprano.** El comando `cargar_ejemplos` carga los mismos
   pedidos de las páginas de `diseno/`. Así cada pantalla se compara con su referencia
   apenas se construye.
5. **Esqueleto antes de repartir.** Antes de soltar a los agentes, el coordinador deja
   creadas todas las direcciones, las vistas vacías y la plantilla de cada pantalla con sus
   partes vacías. Cada agente solo rellena lo suyo.
6. **Copiar, no reinventar.** Cada plantilla empieza copiando el HTML de su página de
   `diseno/`. Lo que cambia: los estilos en línea pasan a clases y los ejemplos a datos.
7. **Probar por tandas.** Al final de cada tanda, Claude Code hace las pruebas a mano con un
   navegador automático, deja las capturas y sigue solo. David revisa cuando quiera.

## Estructura del proyecto

Se crea en las tandas 1 y 2 y no se cambia sin preguntar. Está pensada para que cada agente
tenga archivos propios.

```
config/        Ajustes del proyecto, por entorno
cuentas/       Taller y Usuario. Inicio de sesión y "Mi taller"
pedidos/       Cliente, Pedido, Abono, Talla y Material
  calculos.py  Todas las cuentas
  recibo.py    El PDF del recibo
  urls.py      Todas las direcciones de la app
  vistas/      Un archivo por zona: hoy, lista, detalle, abonos, tallas, materiales,
               fotos, calendario, clientes, publico
  templates/pedidos/
               Una plantilla por pantalla y una parte por tarjeta (nombre con "_"):
               pedido.html trae _etapa, _tallas, _materiales, _pagos, _entrega, _cliente;
               hoy.html trae _cifras, _que_hacer, _trabajos, _grafica, _quien_debe, _etapas
  tests/       Un archivo de pruebas por zona
cotizador/     PrendaGuardada y la pantalla Cotizador
telas/         Tela y MovimientoTela, y la pantalla Telas
finanzas/      Gasto, la pantalla Resumen y la descarga para Excel
templates/     base.html, _menu.html y la carpeta piezas/
static/        css/app.css, js/app.js, fuentes/ (Inter), htmx y los íconos
docs/bitacora/ Una explicación por tarea: T00.md, T01.md...
               y un resumen por tanda: tanda-1.md, tanda-2.md...
docs/capturas/ Capturas finales de cada tanda, en computador y en celular
herramientas/  capturas.py: recorre las pantallas con un navegador automático
diseno/        Referencia visual (no es código de la aplicación)
```

## Reglas para los agentes

1. **Cada agente toca solo los archivos de su carril.** Están listados en cada tanda.
2. **Archivos congelados** desde el final de la tanda 2. Solo los cambia el coordinador:
   - `config/`, todos los `models.py` y las migraciones;
   - `pedidos/calculos.py`;
   - todos los `urls.py`;
   - `static/css/app.css`, `static/js/app.js`, `templates/base.html`, `templates/_menu.html`
     y `templates/piezas/`;
   - las plantillas de pantalla que solo reúnen partes (`pedido.html`, `hoy.html`);
   - `docs/05-tareas.md`.
3. **Si a un agente le falta algo en un archivo congelado** (una clase de CSS, un cálculo,
   un campo), no lo cambia: se lo pide al coordinador, que lo hace una sola vez para todos.
4. **Nadie crea migraciones en paralelo.** Si aparece la necesidad de cambiar un modelo, se
   detiene el carril y se le pregunta a David.
5. **Cada agente trabaja en su propia copia** (un *worktree* de Git), para no escribir sobre
   el trabajo de otro.
6. **Un commit por tarea**, y una explicación por tarea en `docs/bitacora/TNN.md`.
7. **El revisor** comprueba cada carril antes de unirlo: que las pruebas pasan, que cada
   vista filtra por taller, que la pantalla se ve como su página de `diseno/` en 1280 px y
   en 390 px, que las tarjetas terminan parejas y que los textos coinciden.
8. **El coordinador une los carriles uno por uno** en la rama de la tanda y corre todas las
   pruebas después de cada unión. Si algo se rompe, lo arregla antes de unir el siguiente.

## Receta de una pantalla

La sigue cada agente de carril:

1. **Leer** su sección en `docs/03-pantallas.md` y abrir su página de `diseno/`.
2. **Vista:** reúne los datos con las funciones de `calculos.py`, siempre filtrando por el
   taller de la usuaria.
3. **Plantilla:** copiar el HTML de la referencia, quitar el marco y el menú (ya están en
   `base.html`), cambiar estilos en línea por clases y ejemplos por datos.
4. **Acciones:** cada botón que cambia algo usa HTMX y recibe de vuelta solo la parte que
   cambió.
5. **Pruebas:** que la página responde con los datos correctos, que otro taller no la ve y
   que cada acción hace lo que dice.
6. **Comparar** con la referencia en 1280 px y en 390 px.

## Las tandas

Cada tanda termina con algo que David puede abrir y probar.

### Tanda 1. Cimientos (un solo agente)

Tareas, en orden: T00, T01, T03, T02.

Al terminar: se puede entrar con usuario y contraseña y se ve el marco con el menú, que se
contrae y funciona en celular. Existe la página "Piezas" con todas las piezas del diseño.

### Tanda 2. Datos y esqueleto (un solo agente, más un revisor)

En orden:

1. Todos los modelos de `docs/02-modelo-de-datos.md` en una sola pasada (adelanta la parte
   de modelos de T04, T05, T08, T10, T12, T15, T16 y T17).
2. `pedidos/calculos.py` con las pruebas de todos los cálculos.
3. T22, datos de ejemplo.
4. El esqueleto: todos los `urls.py` con sus direcciones, las vistas vacías, y la plantilla
   de cada pantalla con sus partes vacías. El menú ya lleva a cada pantalla.

El revisor comprueba los modelos contra `docs/02-modelo-de-datos.md` y los cálculos contra
los valores de las páginas de `diseno/`.

Al terminar: la base tiene los ejemplos, las cuentas están probadas y cada sección del menú
abre una pantalla vacía. Desde aquí los archivos compartidos quedan congelados.

### Tanda 3. Pedidos (4 carriles)

| Carril | Tareas | Archivos propios |
|---|---|---|
| A. Lista y pedido nuevo | T05 | `vistas/lista.py`, `lista.html` y sus partes, `tests/test_lista.py` |
| B. Etapa, entrega y materiales | T07, T12 | `vistas/detalle.py`, `vistas/materiales.py`, `_etapa`, `_entrega`, `_cliente`, `_materiales`, sus pruebas |
| C. Pagos y recibo | T08, T09 | `vistas/abonos.py`, `recibo.py`, `_pagos`, sus pruebas |
| D. Tallas y clientes | T10, T04 | `vistas/tallas.py`, `_tallas`, `vistas/clientes.py`, `clientes.html`, sus pruebas |

Al terminar: funcionan Pedidos, Nuevo pedido, Pedido por dentro (con abonos, recibo en PDF,
tallas y materiales) y la lista de clientes.

### Tanda 4. Plata y Hoy (3 carriles)

| Carril | Tareas | Archivos propios |
|---|---|---|
| A. Resumen, gastos y Excel | T17, T18 | Toda la app `finanzas/`, menos `models.py` y `urls.py` |
| B. Hoy | T06 | `vistas/hoy.py`, `_cifras`, `_que_hacer`, `_grafica`, `_quien_debe`, `_etapas`, sus pruebas |
| C. Fotos | T13 | `vistas/fotos.py`, `_trabajos`, la parte de foto del pedido, sus pruebas |

Al terminar: funcionan Resumen del mes con su Excel y la pantalla Hoy completa, con las
fotos que pasan. Hoy queda como pantalla de entrada.

### Tanda 5. Lo que falta (6 carriles)

| Carril | Tareas | Archivos propios |
|---|---|---|
| A. Calendario | T14 | `vistas/calendario.py`, `calendario.html` y sus partes, sus pruebas |
| B. Telas | T16 | Toda la app `telas/`, menos `models.py` y `urls.py` |
| C. Cotizador | T15 | Toda la app `cotizador/`, menos `models.py` y `urls.py` |
| D. Mensajes y dotación | T19 | `pedidos/mensajes.py`, el aviso de dotación de `clientes.html`, sus pruebas |
| E. Formulario público | T11 | `vistas/publico.py`, `publico.html`, sus pruebas |
| F. Mi taller | T20 | Las vistas y plantillas de "Mi taller" en `cuentas/`, sus pruebas |

El carril D toca `clientes.html`, que nació en la tanda 3: para entonces ya está unido, así
que no choca con nadie.

Al terminar: funcionan Calendario, Telas, Cotizador, Clientes con sus mensajes de WhatsApp,
el formulario público de tallas y Mi taller.

### Tanda 6. Cierre

1. T21, permisos por rol: un solo agente, porque toca todas las vistas.
2. T23, revisión final: un revisor por pantalla, todos al tiempo, solo leyendo. Cada uno
   entrega la lista de diferencias con su página de `diseno/`. Después el coordinador
   reparte los arreglos.
3. T24, la guía para publicar. Claude Code la escribe; no toca el servidor.

Al terminar: permisos aplicados y probados, todas las pantallas revisadas contra `diseno/`,
y la guía lista para que David la ejecute.

### Tanda 7. Asistente del taller (base y 4 carriles)

El plan completo, con los contratos que comparten los carriles, está en
`docs/11-plan-tanda-7.md`. Rama: `tanda-7-asistente`.

1. Base, un solo agente (el coordinador): T25 y T26. Antes de lanzar los carriles, David
   aprueba las piezas nuevas de la maqueta y pone la clave en `.env` para una prueba corta de
   3 llamadas.
2. Carriles, cada uno en su copia:

| Carril | Tareas | Archivos propios |
|---|---|---|
| A. Consultas | T27, T28 | `asistente/herramientas/pedidos.py`, `plata.py`, `catalogo.py`, sus tarjetas y pruebas |
| B. Motor | T29, T30 | `asistente/cliente.py`, `conversacion.py`, `instrucciones.py`, `pagina.py`, `esfuerzo.py`, sus pruebas |
| C. Mensajes y cotizar | T31, T32 | `asistente/herramientas/mensajes.py`, `cotizar.py`, sus tarjetas y pruebas |
| D. Panel y uso | T33, T34 | `asistente/vistas.py`, `uso.py`, las plantillas del panel, sus pruebas |

Además de los archivos congelados de siempre, en esta tanda quedan congelados
`asistente/contratos.py`, `esquemas.py`, `falso.py`, `herramientas/__init__.py` y `urls.py`.

3. Unión en este orden: A, C, B, D, con `uv run pytest` después de cada uno. Luego T35
   (integración y capturas) y T36 (20 preguntas reales con la clave, a mano).

Al terminar: la dueña de un taller con el asistente prendido le pregunta por sus pedidos,
su plata, sus telas y sus clientes, le pide mensajes y cotizaciones, y David ve en `/admin`
cuántas preguntas y cuánto costaron.

## Cómo trabaja el coordinador dentro de una tanda

1. Anota el plan de la tanda (carriles, agentes y archivos) al comienzo de
   `docs/bitacora/tanda-N.md` y sigue sin esperar.
2. Crea la rama de la tanda: `tanda-3-pedidos`.
3. Lanza un agente por carril, cada uno en su propia copia.
4. Cuando un carril termina, lo pasa al revisor. Si el revisor encuentra algo, vuelve al
   agente del carril.
5. Une los carriles uno por uno y corre `uv run pytest` después de cada unión.
6. Marca las tareas como hechas en `docs/05-tareas.md`.
7. Hace las pruebas a mano de "Al terminar la tanda" de `docs/07-forma-de-trabajo.md`:
   capturas en 1280 px y 390 px con `herramientas/capturas.py`, comparación con `diseno/`,
   arreglos, capturas finales en `docs/capturas/tanda-N/` y resumen en
   `docs/bitacora/tanda-N.md`.
8. Si todas las pruebas pasan, sube la rama, la une a `main` y empieza la tanda siguiente,
   hasta terminar la tanda 6. La tanda 7 la pidió David aparte; se trabaja igual.

Se detiene solo en los casos de "Cuándo detenerse y preguntar" de
`docs/07-forma-de-trabajo.md`, o si algo necesita una clave o una decisión de David.

## En qué no se ahorra

Ir rápido no cambia estas reglas:

- Cada dato se filtra por taller, y hay prueba de que un taller no ve al otro.
- La plata va en enteros y el saldo se calcula, no se guarda.
- Ninguna tarea se da por hecha con pruebas fallando o desactivadas.
- No se agregan librerías ni se cambia el diseño sin preguntar.
- No se dice que algo funciona sin haberlo probado.

## Antes de la tanda 1 (lo hace David)

- [ ] Tener instalados Git, Python 3.12, `uv` y PostgreSQL en el computador.
- [ ] Crear el repositorio privado en GitHub y subir esta carpeta.
- [ ] Abrir cada página de `diseno/` en el navegador y confirmar que es el diseño aprobado.
- [ ] Actualizar Claude Code y comprobar que ultracode aparece en `/effort`.

## Instrucciones listas para pegar

Desde la tanda 2 no hace falta pegar una instrucción por tanda: Claude Code sigue solo de
una tanda a la siguiente. Si hay que retomar en una sesión nueva, pegar:

```
Lee CLAUDE.md, docs/07-forma-de-trabajo.md y docs/09-plan-de-construccion.md completos, y
docs/05-tareas.md para ver dónde vamos. Sigue con la tanda que falta como dice el plan
(desde la tanda 3, un agente por carril según "Reglas para los agentes"), haz tú las
pruebas a mano al final de cada tanda, únela a main y continúa hasta terminar la tanda 6.
Detente solo en los casos de "Cuándo detenerse y preguntar" o si necesitas una clave o
una decisión mía. En T24 escribe la guía; no toques ningún servidor.
```

## Qué queda para revisar al final de cada tanda

Claude Code hace las pruebas a mano y une la rama sin esperar. Para David queda, cuando
quiera:

1. Leer el resumen de la tanda en `docs/bitacora/tanda-N.md` y las explicaciones de cada
   tarea en `docs/bitacora/`.
2. Mirar las capturas en `docs/capturas/tanda-N/` junto a sus páginas de `diseno/`.
3. Si algo no le gusta, decírselo a Claude Code, que lo corrige en una rama nueva.
