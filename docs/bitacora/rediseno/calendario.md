# Rediseño: Calendario

## Qué cambió en la pantalla

- El encabezado ahora solo tiene el título "Calendario" y el botón "Nuevo pedido". Los botones
  "Mes anterior" y "Mes siguiente" ya no están arriba: pasaron a la tarjeta del mes.
- La tarjeta del mes tiene en su cabeza el nombre del mes ("Noviembre de 2026"), un botón "Hoy"
  (lleva al mes actual) y dos flechas para ir al mes anterior o al siguiente.
- Cada entrega dentro de un día es una insignia con su circulito: ámbar con circulito vacío si
  está por entregar, roja con alerta si está atrasada y gris con circulito lleno si ya se
  entregó. Antes lo entregado era verde; ahora es gris, porque el verde quedó solo para "Listo".
- En celular cada entrega es una barrita del color de su insignia (esto ya lo hace el CSS).
- A la derecha, "Entregas de noviembre" muestra cuántas son en la cabeza; cada fila lleva la
  fecha en negrita, el cliente debajo y la insignia a la derecha. "Semana más cargada" quedó
  como una tarjeta con su nota.
- Ya no hay pantalla fija: la hoja se desplaza por dentro y se quitó todo lo que servía para
  que el calendario cupiera en 1366 x 768.

## Lo que sigue igual

Tocar un día filtra la lista (con HTMX y también sin JavaScript), "Ver todo el mes" vuelve al
mes entero y conserva los identificadores de cada día (`dia-AAAA-MM-DD`) y de cada entrega
para las animaciones y el foco. Cada fila abre su pedido. Todo se filtra por el taller.

## Archivos

- `pedidos/templates/pedidos/calendario.html`, `_calendario_dias.html`, `_calendario_entregas.html`:
  copian el HTML de `diseno/calendario.html`.
- `pedidos/vistas/calendario.py`: la entrega entregada ahora es gris y cada tono sabe su circulito.
- `pedidos/tests/test_calendario.py`: revisan el diseño nuevo. Se quitó la prueba con Chrome
  que medía la pantalla fija (ya no existe esa regla); el resto de comportamientos se siguen
  comprobando, y se agregaron pruebas de la tarjeta del mes, la leyenda, los tonos, la cuenta
  de la lista y la costurera.

## Qué se probó

52 pruebas del calendario pasan. Capturas en 1366, 1920 y celular comparadas con
`diseno/calendario.html`: en computador quedan iguales. En celular se ve como la referencia.
No se probó en un teléfono real.

## Decisiones

- Los días sin entregas siguen siendo un cuadro que no es botón (en el diseño todos son botones,
  pero aquí un botón sin acción no serviría).
- No hizo falta CSS nuevo: las piezas compartidas alcanzaron.
