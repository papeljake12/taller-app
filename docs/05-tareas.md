# Tareas de la etapa 2: aplicación base

Cada tarea se hace completa, con sus pruebas. El orden en que se construyen y cómo se agrupan
en tandas está en `docs/09-plan-de-construccion.md`; el paso a paso de cada una, en
`docs/07-forma-de-trabajo.md`. Las pantallas se nombran como en `docs/03-pantallas.md`.

Para marcar el avance, cambia `[ ]` por `[x]`.

## Cimientos

- [x] **T00. Preparar el proyecto.** Proyecto Django 5.2 con `uv`, configuración por entorno
  leída de `.env`, PostgreSQL local, `pytest` funcionando, zona horaria `America/Bogota`,
  idioma `es-co`. Completar la sección "Comandos" de `CLAUDE.md`.
  Lista cuando: `uv run pytest` pasa con una prueba de humo y la página de inicio responde.

- [x] **T01. Talleres y usuarias.** Modelos `Taller` y `Usuario` (propio, desde la primera
  migración), panel de administración para crearlos, inicio y cierre de sesión con
  `django-axes`.
  Lista cuando: se cumple la pantalla "Inicio de sesión" de `docs/03-pantallas.md`.

- [x] **T02. Base visual.** Según `docs/08-diseno.md`: hoja de estilos con las variables de
  color y todas las piezas (tarjeta, botones, cifra, etiqueta, tabla, campo, filtro, barra),
  plantilla base con el marco, el menú lateral que se contrae y la barra de abajo en celular.
  Inter, HTMX y los íconos guardados en el proyecto, sin CDN. Incluye una página interna
  "Piezas" que muestra todas las piezas juntas, para revisarlas de un vistazo.
  Lista cuando: una página vacía con el menú se ve igual que `diseno/hoy.html` en 1280 px,
  igual que `diseno/hoy-menu-contraido.html` al contraer, e igual que
  `diseno/hoy-celular.html` en 390 px; y se cumple "Menú" de `docs/03-pantallas.md`, salvo el
  buscador, que llega con T05.

- [x] **T03. Aislamiento entre talleres.** Una forma única y reutilizable de filtrar por el
  taller de la usuaria, y una prueba que cree dos talleres y confirme que ninguno ve al otro.
  Lista cuando: la prueba de aislamiento pasa y queda como plantilla para las tareas siguientes.

## Pedidos

- [x] **T04. Clientes.** Modelo `Cliente`, lista con buscador, crear y editar.
- [x] **T05. Pedidos: crear y listar.** Modelo `Pedido`, ventana "Nuevo pedido", lista con
  filtros, buscador y orden, y el buscador del menú. Pantallas "Pedidos" y "Nuevo pedido".
- [x] **T06. Pantalla Hoy.** Cifras, "Qué hacer hoy" con sus acciones, gráfica de cobrado y
  gastado, "Quién te debe" y "Pedidos por etapa". Pantalla "Hoy", sin las fotos (llegan con
  T13). Usa los cálculos de abonos y gastos, que ya existen desde la tanda 2.
- [x] **T07. Pedido por dentro: ficha y etapa.** Cambiar etapa, encargada, fecha y WhatsApp
  sin recargar la página.
- [x] **T08. Abonos.** Modelo `Abono`, registrar y quitar, saldo y barra.
- [x] **T09. Recibo en PDF.** Con ReportLab, mismo contenido que el de la demo.
- [x] **T10. Tallas internas.** Modelo `Talla`, agregar a mano con medidas, totales por talla,
  copiar resumen.
- [x] **T11. Enlace público de tallas.** Pantalla "Formulario público de tallas" completa,
  con token, cierre del enlace y límite de envíos.
- [x] **T12. Materiales.** Modelo `Material`, agregar, marcar y quitar.
- [x] **T13. Fotos.** Foto por pedido: subir, cambiar y quitar. Reducir el tamaño al subir y
  validar que sea una imagen. Tarjeta "Trabajos del taller" en Hoy, con las fotos que pasan
  como describe `docs/08-diseno.md`.

## Las demás secciones

- [x] **T14. Calendario.** Pantalla "Calendario".
- [x] **T15. Cotizador.** Modelo `PrendaGuardada` y pantalla "Cotizador".
- [x] **T16. Telas.** Modelos `Tela` y `MovimientoTela`, pantalla "Telas".
- [x] **T17. Gastos y resumen del mes.** Modelo `Gasto` y pantalla "Resumen del mes", sin el Excel.
- [x] **T18. Descarga para Excel.** Con openpyxl, cuatro hojas.
- [x] **T19. Mensajes de WhatsApp y avisos de dotación.** Enlaces que abren el chat con el
  texto escrito, y pantalla "Clientes" completa.
- [x] **T20. Mi taller.** Pantalla "Mi taller".

## Cierre

- [x] **T21. Permisos por rol.** Aplicar la tabla de `docs/04-permisos.md` en todas las
  vistas, con una prueba por cada fila de la tabla.
- [x] **T22. Datos de ejemplo.** Comando `cargar_ejemplos` con los mismos pedidos, tallas,
  telas y gastos de las páginas de `diseno/`, marcados como ejemplo. Se construye temprano
  (ver el plan de construcción) y se completa a medida que aparecen los modelos.
- [x] **T23. Revisión final.** Recorrer todas las pantallas en 390 px y en 1280 px, comparar
  cada una con su página de `diseno/` y corregir: colores, alineación de tarjetas y textos.
- [x] **T24. Preparar la publicación.** Configuración de producción, archivos estáticos con
  Whitenoise, guía paso a paso para el VPS (NGINX y Gunicorn) y copia de seguridad diaria de
  la base de datos. La guía la ejecuta David; Claude Code no toca el servidor.

## Etapas siguientes (todavía sin partir en tareas)

- **Etapa 3, ahorro de trabajo:** IA para crear pedidos desde un mensaje o dictado, avisos
  automáticos, ficha de producción para imprimir, lista de compras, repetir pedido, medidas
  guardadas por persona, pago a costureras, ganancia por pedido.
- **Etapa 4, más ventas:** portal del cliente, catálogo público, pagos en línea, agente de
  WhatsApp.
- **Etapa 5, otros talleres:** registro de talleres nuevos, planes de precio, facturación
  electrónica.

Cada etapa se parte en tareas cuando termine la anterior, con lo que se haya aprendido.
