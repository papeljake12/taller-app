# Rediseño: Telas

## Qué cambió en la pantalla

- **Encabezado:** solo dice "Telas". Se quitó el dato "4 telas, 60 m en total", porque las
  cifras de abajo ya lo dicen. El botón ahora se llama "Agregar tela" (antes "Nueva tela"); en
  celular es el círculo negro con el "+". Sigue abriendo la misma ventana y solo lo ve la dueña.
- **Cifras:** las tres (Telas, Metros en total, Se están acabando) van juntas en una sola
  tarjeta, con una línea de apoyo cada una. Ya no tienen borde ni número de color.
- **Tabla:** en una tarjeta de bordes redondeados. "Quedan" en negrita, "Avisar cuando queden"
  en gris. El estado "Suficiente" pasó de verde a **gris** con el circulito lleno (el verde
  queda solo para pagado y entregado); "Se está acabando" sigue ámbar, con el circulito a
  medias. Abajo, el pie "Toca el nombre de una tela para ver su historial o quitarla."
- **Sin telas:** ahora se ve la pantalla vacía de la maqueta (dibujo del rollo de tela, "Aquí
  vas a ver tus telas", el botón "Agregar tela" y el enlace "Cómo llevar las telas del taller").
  Las cifras no se muestran hasta que haya una tela.
- Ya no hay "pantalla fija": la hoja se desplaza sola si hay muchas telas.

## Archivos

- `telas/templates/telas/inicio.html`: encabezado nuevo.
- `telas/templates/telas/_cifras.html`: la tarjeta de cifras. Sin telas deja un marcador
  escondido para que, al agregar la primera, las cifras aparezcan sin recargar.
- `telas/templates/telas/_tabla.html` y `_fila.html`: la tabla nueva y la pantalla vacía.
- `telas/templates/telas/_apoyo.html`: se borró (ya no hay dato de apoyo en el encabezado).
- `telas/vistas.py`: el estado "Suficiente" cambia a gris con circulito; ya no se manda el
  dato de apoyo después de cada acción.
- `telas/tests/test_telas.py`: pruebas al día con el diseño nuevo. Se quitaron las dos de
  "pantalla fija" (ya no existe) y se agregaron: pantalla vacía (dueña y costurera), la primera
  tela reemplaza la pantalla vacía, quitar la última vuelve a ella, y la costurera ve la
  pantalla sin "Agregar tela" ni "Entró".

## Qué se probó

- Las 81 pruebas de Telas pasan.
- Capturas en 1366 x 768, 1920 x 1080 y celular: idénticas a `diseno/telas.html`.
- No se capturó la pantalla vacía en navegador (los datos de ejemplo traen telas); se probó con
  pruebas automáticas del HTML.

## Decisiones

- En celular la tabla es igual a la referencia: las columnas de la derecha ("Avisar cuando
  queden", estado y los botones "Entró" y "Usé") quedan a un deslizamiento de dedo. Se copió
  tal cual la referencia; si David quiere los botones siempre a la vista, hay que ajustar el
  diseño.
- Para la costurera, la pantalla vacía no tiene botón y dice "Cuando la dueña del taller anote
  una tela, aparecerá aquí con los metros que quedan.", porque ella no puede agregar telas.
