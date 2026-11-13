# Tanda 2. Datos y esqueleto — resumen

## El plan

Un solo agente, en cuatro pasos (`docs/09-plan-de-construccion.md`), y un revisor al final:

1. Todos los modelos de `docs/02-modelo-de-datos.md` de una vez.
2. `pedidos/calculos.py`: todas las cuentas, con sus pruebas.
3. T22: los datos de ejemplo de `diseno/`.
4. El esqueleto: todas las direcciones, las vistas vacías y la plantilla de cada pantalla
   con sus partes vacías. Desde aquí los archivos compartidos quedan congelados.

## Qué hace ahora la aplicación

- **Cada sección del menú abre su pantalla**, todavía vacía: cada tarjeta dice con qué tarea
  llega ("Llega con T06."). Los contadores del menú ya cuentan de verdad: Pedidos muestra
  los atrasados y Telas las que se están acabando.
- **El buscador del menú ya se puede usar**: lleva a una página de resultados, que se llena
  con T05.
- **"Nuevo pedido" abre una ventana** desde cualquier pantalla. En celular sube desde abajo.
  Se cierra con Escape, con "Cancelar" o tocando fuera.
- **Los datos de ejemplo** (`uv run python manage.py cargar_ejemplos`) llenan el "Taller de
  ejemplo" con los mismos pedidos de `diseno/` (detalle en `docs/bitacora/T22.md`).
- **En el panel `/admin/`** se ven y se corrigen clientes, pedidos (con sus abonos, tallas y
  materiales), telas, gastos y prendas guardadas, para dar soporte.

## Qué se construyó y para qué sirve

| Archivo | Para qué sirve |
|---|---|
| `pedidos/models.py` | Cliente, Pedido, Abono, Talla y Material. |
| `telas/`, `finanzas/`, `cotizador/` | Tres apps nuevas: Tela y su historial, Gasto, y PrendaGuardada. |
| `*/migrations/0001_initial.py` | Las tablas de la base de datos. Una por app. |
| `*/admin.py` | Cada modelo en el panel de administración. |
| `pedidos/calculos.py` | Todas las cuentas: saldo, atrasados, por cobrar, qué hacer hoy, quién te debe, resumen del mes, gráfica, clientes, telas, calendario, cotizador. |
| `pedidos/ejemplos.py` y el comando `cargar_ejemplos` | Los datos de ejemplo (T22). |
| `pedidos/urls.py` y los `urls.py` de cada app | Todas las direcciones de la aplicación base. |
| `pedidos/vistas/*.py`, `*/vistas.py`, `cuentas/mi_taller.py` | Las vistas, todavía vacías: un archivo por zona, para que cada carril de la tanda 3 en adelante toque solo el suyo. |
| Plantillas de cada pantalla | `hoy.html` y `pedido.html` solo reúnen partes; cada tarjeta es una parte aparte (`_que_hacer.html`, `_pagos.html`...). |
| `config/ventanas.py`, `templates/piezas/ventana.html` | La ventana para formularios cortos. |
| `config/esqueleto.py` | La respuesta "todavía no" de las acciones que aún no existen. |
| `static/css/app.css`, `static/js/app.js` | Ventana, botones "Copiar", cuadrícula del calendario y el orden de Hoy en celular. |
| `tests/test_modelos.py`, `pedidos/tests/test_calculos.py`, `tests/test_esqueleto.py` | Las pruebas nuevas. |

## Decisiones y por qué

- **Cada dato sabe de qué taller es**, y el panel no deja crear datos de un taller desde
  `/admin/`: el taller siempre lo pone la aplicación, nunca se elige a mano.
- **Lo que no se puede borrar:** un cliente con pedidos, y una usuaria que creó pedidos o
  registró abonos (se desactiva, y sus registros se conservan). Si se borra una encargada,
  el pedido queda "sin asignar".
- **La base de datos también cuida las reglas**, no solo los formularios: abonos y gastos
  mayores que 0, cantidad entre 1 y 2000, metros de tela nunca negativos, "a la medida" con
  pecho, cintura y cadera, y un cliente no se repite en el taller aunque cambien las
  mayúsculas.
- **Las cuentas se prueban con las cifras del diseño.** Las pruebas cargan los ejemplos el
  11 de noviembre (el día del diseño) y comprueban que salen exactamente 5.790.000 por
  cobrar, 4.460.000 cobrados, 7.320.000 vendidos, 939.000 gastados, la lista de "Quién te
  debe", los filtros de Pedidos, las tallas del Restaurante (14 de 18), la dotación del 20
  de diciembre (faltan 39 días) y la cotización de la camisa polo (54.500 por unidad).
- **"Vendido en el mes" cuenta el día en hora de Bogotá.** Un pedido creado el 30 de
  noviembre a las 11:30 p. m. es de noviembre, aunque en hora mundial ya sea diciembre.
- **Todas las direcciones se crearon de una vez**, también las de las acciones (registrar
  abono, marcar material, cambiar etapa...). Cada una ya comprueba que el pedido es del
  taller de quien la usa y, por ahora, responde "todavía no". Una prueba recorre sola todas
  las direcciones con número y confirma que, con el número de otro taller, responden "no
  encontrado".
- **Piezas nuevas antes de congelar**, porque después solo las puede cambiar el
  coordinador: la ventana, los botones "Copiar", la cuadrícula del calendario y el ícono
  "cerrar".
- **Hoy en celular** sigue el orden de `diseno/hoy-celular.html`: cifras, qué hacer hoy y
  quién te debe arriba. Las demás tarjetas (trabajos, gráfica y etapas) no se esconden:
  van más abajo.
- **El pedido por dentro** tiene dos partes más que el diseño, que `docs/03-pantallas.md`
  pide: "Foto del pedido" en la columna derecha y "Eliminar" abajo.

## Qué se probó

- `uv run pytest`: 293 pruebas, todas pasan.
- Capturas de todas las pantallas en 1280 px y 390 px en `docs/capturas/tanda-2/`. Ninguna
  se sale del ancho, ningún archivo falla y no hay errores en el navegador.
- En el navegador: "Nuevo pedido" abre la ventana, Escape y "Cancelar" la cierran, en
  computador y en celular.

## Qué se corrigió en la revisión a mano

- **En celular, las tarjetas de Hoy salían altísimas** (casi 450 px cada una, vacías). Al
  abrir las filas para cambiar el orden, el ancho mínimo de cada columna se volvía alto.
  Ahora cada tarjeta mide lo que mide su contenido. Tiene su prueba.
- **La ventana abierta como página** (sin JavaScript) tenía "Cancelar" sin efecto. Ahora
  vuelve a la página anterior.

## Lo que encontró el revisor

Un agente que no escribió el código comparó los modelos con `docs/02-modelo-de-datos.md` y
rehízo a mano cada cifra de las páginas de `diseno/`. Los modelos coinciden y todas las
cifras salen iguales. Encontró estos detalles, ya corregidos y con su prueba:

- **Las barras de "Quién te debe"** se redondeaban hacia abajo (22 % y 14 %); el diseño
  redondea al más cercano (23 % y 15 %). Ahora hay una sola función, `porcentaje`, para
  todas las barras.
- **Los gastos del mismo día** salían en el orden contrario al que se anotaron. Ahora salen
  como en el diseño (Hilos antes que Transporte).
- **El cotizador** redondeaba la tela al peso antes de subir el precio a los 500; la demo
  sube el costo exacto. Ahora es como la demo. Y con un valor raro escrito en un campo
  ("nan", "1e30") se rompía la pantalla; ahora cuenta como vacío.
- **"Con saldo" por etapa** contaba los cotizados; ahora no, igual que el filtro de Pedidos.
- **Cuentas que las pantallas iban a necesitar** y no existían: la etiqueta "Por confirmar"
  o "Entregado" de Hoy y del calendario, las telas con las que se acaban primero, y cuántos
  clientes empresa hay (aviso de dotación).

Se dejaron como están, a propósito: las fotos de Hoy salen del pedido más reciente al más
antiguo, aunque el diseño ponga primero las polleras; y "Sin asignar" va al final de "Quién
tiene qué". También anotó que un taller con usuarias no se puede borrar desde `/admin/` (se
protegen sus datos) y que los nombres cortos del diseño ("Tambores del Río") tendrán que
salir del nombre completo en cada pantalla.

## Qué no se pudo comprobar

- Las pantallas todavía están vacías, así que la comparación con `diseno/` en esta tanda es
  de estructura (encabezados, filas y columnas, alturas parejas), no de contenido.
- Un celular de verdad y otros navegadores, igual que en la tanda 1.
