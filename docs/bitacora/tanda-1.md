# Tanda 1. Cimientos — resumen

Tareas: T00, T01, T03 y T02. David aprobó la tanda el 12 de noviembre de 2026. Desde aquí,
Claude Code hace también las pruebas a mano (ver `docs/07-forma-de-trabajo.md`).

## Qué se probó

- `uv run pytest`: 90 pruebas, todas pasan.
- Con la herramienta nueva de capturas (`herramientas/capturas.py`), en 1280 px y en 390 px:
  la página de entrada, Hoy, Hoy con el menú contraído y la página interna Piezas. Las
  capturas están en `docs/capturas/tanda-1/`.
- Comparación con `diseno/hoy.html`, `diseno/hoy-menu-contraido.html` y
  `diseno/hoy-celular.html`: el marco, el menú, la tira de íconos y la barra de abajo
  coinciden. Las tarjetas de Hoy todavía no existen (llegan con T06), así que la hoja se ve
  vacía.
- Ninguna página se sale del ancho en 390 px.
- Teclado: Tab y Enter en la entrada, el menú, el menú contraído y "Más". El foco siempre
  se ve (detalle en `docs/bitacora/T02.md`).
- Entrar con usuario y contraseña y salir: probado con las pruebas automáticas.

## Qué se corrigió

- **Ícono de la pestaña.** Ninguna página lo traía, y el navegador lo pedía por su cuenta
  (`/favicon.ico`) y recibía "no existe". Ahora todas usan las tijeras del logo, en blanco
  sobre negro (`static/iconos/favicon.svg`). Tiene su prueba.
- Los arreglos de celular de Piezas y el borde de los campos quedaron en T02.

## Herramienta de capturas

`uv run python herramientas/capturas.py --tanda N` levanta el servidor, entra con la primera
dueña (o con `--usuario`), abre cada pantalla en Chrome sin ventana y guarda la captura de
la página completa. También avisa si algo se sale del ancho, si un archivo no cargó o si hubo
un error en el navegador.

Usa **Playwright**, agregado solo como dependencia de desarrollo (no se instala en el
servidor). Maneja el Google Chrome que ya está instalado, así que no descarga otro
navegador. Con `--referencias carpeta/` captura también las páginas de `diseno/` en los
mismos tamaños, para compararlas lado a lado.

## Qué no se pudo comprobar

- **Un celular de verdad.** Las capturas de 390 px se toman con Chrome imitando un celular
  (pantalla táctil y ancho de celular). No se probó en un iPhone ni en un Android reales,
  por ejemplo que el campo de 16 px evite que el iPhone agrande la pantalla.
- **Otros navegadores** (Safari, Firefox): solo se probó en Chrome.
