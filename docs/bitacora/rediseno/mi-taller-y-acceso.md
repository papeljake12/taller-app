# Rediseño: Mi taller, Entrar, formulario público de tallas y página de aviso

## Qué cambió en las pantallas

- **Mi taller** ahora se ve como los ajustes de Shopify: cada bloque tiene su explicación a la
  izquierda y sus tarjetas a la derecha (en el celular, la explicación va arriba).
  - "Tu taller": nombre, teléfono y logo. Al lado del campo del logo hay un cuadrito que muestra
    cómo se verá en el menú (el logo, o las iniciales del taller si no tiene). "Guardar" va en
    el pie de la tarjeta.
  - "Costureras": una tarjeta "Activas" con una fila por persona (iniciales, nombre, usuario y los
    botones planos "Cambiar nombre" y "Desactivar"), una tarjeta "Desactivadas" que solo sale si
    hay alguien desactivada (con "Activar"), y la tarjeta "Nueva costurera".
  - Se quitó el botón "Agregar costurera" de arriba: el formulario ya está a la vista.
  - Se quitó la "pantalla fija": la hoja se desplaza normal y la lista no se desplaza por dentro.
- Al guardar el nombre del taller, el menú lo cambia sin recargar (ahora con la forma del menú
  nuevo: `menu__nombre`).
- **Entrar** y **Acceso bloqueado**: marca con el cuadrito blanco de las tijeras, tarjeta blanca,
  "Entrar", la línea "Con el usuario y la contraseña de tu taller." y botón ancho.
- **Formulario público de tallas**: arriba el logo del taller (o sus iniciales) y su nombre; el
  pedido en una cajita con la foto (o la prenda); campos y botón ancho "Enviar mi talla"; y debajo
  "Solo el taller ve tu talla.". La confirmación ahora dice "¡Gracias, Nombre!" con un visto y el
  botón "Enviar la talla de otra persona". El enlace cerrado, "espera un minuto" y "no existe"
  tienen el mismo estilo.
- **Sin permiso (403)**: una tarjeta con el texto y los botones "Ver los pedidos" y "Volver a Hoy".

## Archivos

- `cuentas/templates/cuentas/`: `mi_taller.html` y los `_mi_taller_*.html`, `entrar.html`, `bloqueado.html`.
- `cuentas/mi_taller.py`: manda las iniciales del taller y de cada costurera, y separa activas y desactivadas.
- `cuentas/formularios_mi_taller.py`: se quitó la ayuda del nombre del taller (ya está en la explicación de la izquierda).
- `pedidos/templates/pedidos/publico.html` y los `_publico_*.html`; `pedidos/vistas/publico.py` (manda logo e iniciales del taller).
- `templates/403.html`.
- `static/css/app.css`: solo mi apartado (cuadrito del logo, formulario de cambiar nombre, tarjeta centrada de la confirmación).
- Pruebas: `cuentas/tests/test_mi_taller.py` y `pedidos/tests/test_publico.py`.

## Decisiones

- **No puse la nota "¿Olvidaste la contraseña? Pídele a la dueña…"** de la referencia de Entrar: en la
  aplicación la dueña no puede cambiar contraseñas, así que no sería verdad.
- **"Solo el taller ve tu talla."** sí quedó: la talla la ven solo las usuarias del taller.
- En Mi taller conservé la ayuda real de la aplicación «¿Quién lo está haciendo?» (la referencia decía «Encargada»).
- Las pruebas de "pantalla fija" (que medían con Chrome que la lista se desplazaba por dentro) se reemplazaron
  por pruebas de la estructura nueva, porque ese comportamiento ya no existe.

## Qué se probó

- Pruebas de los 4 archivos de mi carril: todas pasan.
- Capturas en 1366 x 768, 1920 x 1080 y celular de Mi taller, Entrar y el formulario público, comparadas con `diseno/`: coinciden.
- No pude comprobar con captura la confirmación ("¡Gracias…!") ni las páginas de enlace cerrado/espera, porque la herramienta de capturas no las incluye; las revisé con pruebas.
