# Rediseño: Resumen del mes

## Qué cambió en la pantalla

- **Encabezado:** solo dice "Resumen" y, a la derecha, "Descargar para Excel" (ahora blanco, no
  negro, y sin ícono). Los botones de texto "Mes anterior" y "Mes siguiente" salieron de ahí.
- **Selector del mes:** arriba del contenido hay un grupo de tres piezas pegadas: flecha hacia
  atrás, el mes en el medio ("Noviembre de 2026") y flecha hacia adelante. Son enlaces
  normales, así que funciona igual sin JavaScript.
- **Las cuatro cifras** (Vendido, Cobrado, Gastado, Te quedó) están en una sola tarjeta dividida
  en cuatro. "Te quedó" ya no va en verde; si es negativo, lo dice con palabras ("Gastaste más
  de lo que cobraste") y sin rojo, porque el rojo es solo para atrasos y deudas.
- **Gráfica y gastos** van lado a lado. La gráfica es una sola (antes había una baja para
  "pantalla fija" y otra normal) y ya no lleva la nota de abajo. En "Gastos de noviembre",
  "Registrar gasto" queda a la derecha del título; cada gasto muestra el concepto, "11 de nov ·
  servicios" en gris, el valor y una X para quitarlo (que sigue preguntando antes).
- **Ventas por tipo de cliente y Quién tiene qué** son dos tarjetas del mismo tamaño. Cada fila
  tiene el nombre, el valor y la barra delgada debajo. "En producción hoy" quedó en la cabeza
  de la segunda tarjeta, en vez de una frase suelta adentro.
- Ya no hay "pantalla fija": la hoja se desplaza completa, y la lista de gastos no tiene
  barra de desplazamiento propia.

## Archivos que cambiaron

- `finanzas/templates/finanzas/resumen.html`: la pantalla, con el orden de la referencia.
- `_cifras.html`, `_grafica.html`, `_gastos.html`, `_gastos_cabeza.html`, `_gastos_lista.html`
  (sin cambio de fondo), `_gasto_fila.html`, `_gasto_form.html`, `_gasto_confirmar.html`,
  `_barra.html`: las piezas que se cambian solas al registrar o quitar un gasto, con las
  clases nuevas.
- `finanzas/tests/test_resumen.py` y `test_gastos.py`: las pruebas ahora revisan el diseño
  nuevo. No se borró ninguna comprobación que siga teniendo sentido; se quitaron solo las de
  cosas que ya no existen (pantalla fija, las dos gráficas, la nota de la gráfica).
- No hizo falta tocar `vistas.py`, ni el CSS: todo salió con las piezas compartidas.

## Qué se conservó

Cambiar de mes, registrar un gasto (con aviso "Gasto registrado."), quitarlo con pregunta (aviso
"Gasto quitado."), el Excel, los ids que usan las animaciones y las pruebas
(`gastos-registrar`, `gasto-N-quitar`, `data-foco-despues`), y que la costurera no entre
(recibe "sin permiso").

## Pruebas

- Pruebas del carril (`finanzas/`) pasan. Se agregó una de que el selector del mes va arriba y
  son enlaces simples, otra de que el Excel es botón secundario y otra de que la costurera no
  entra. Ya existía la de que otro taller no se ve en las cuentas.
- A mano, con capturas en 1366, 1920 y celular, comparadas con `diseno/resumen.html`: se ven
  igual. Las dos tarjetas de cada fila terminan a la misma altura y nada se sale en celular.

## Decisiones

- "Descargar para Excel" va sin ícono porque la pieza compartida así lo trae (la referencia
  muestra un ícono de descarga; es la única diferencia).
- Se quitó la nota "De junio a noviembre, en miles de pesos" bajo la gráfica porque la
  referencia no la tiene; las líneas de la gráfica ya dicen "2 M", "4 M".
