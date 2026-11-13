# Tanda 5. Lo que falta — resumen

## El plan

Seis agentes al mismo tiempo, cada uno en su propia copia y con su propia base de datos:

| Carril | Tarea | Qué construyó |
|---|---|---|
| A | T14 | El calendario: el mes con las entregas, tocar un día para filtrar, "Entregas del mes" y "Semana más cargada". |
| B | T16 | Telas: cifras, la tabla con "Entró" y "Usé", el historial de cada tela, agregar y quitar. |
| C | T15 | El cotizador: el precio mientras se escribe, "Mis prendas", copiar o enviar la cotización y crear el pedido. |
| D | T19 | El aviso de dotación en Clientes y los botones "Escribirle" con el mensaje ya escrito. |
| E | T11 | El formulario público de tallas: con su enlace, cerrado cuando la dueña lo cierra y con un límite de envíos por minuto. |
| F | T20 | Mi taller: nombre, teléfono y logo del taller, y las costureras (agregar, cambiar el nombre, desactivar). |

Cada carril pasó por un revisor, se corrigió lo que encontró y se revisó otra vez. Cada tarea
tiene su explicación en `docs/bitacora/TNN.md`.

## Lo que hizo el coordinador al unir

Los seis carriles se unieron uno por uno, con todas las pruebas después de cada uno (de 812 a
1065 pruebas, todas pasan). Después:

- **Telas que se acaban, en ámbar.** `diseno/telas.html` pinta de rojo la cifra "Se están
  acabando" y los metros de esas telas. Pero la regla 7 de `CLAUDE.md`, `docs/08-diseno.md` y
  `docs/03-pantallas.md` dicen que el rojo es solo para atrasos y deudas, y que una tela que
  se acaba va en ámbar. Se siguieron las tres reglas escritas. **Si prefieres el rojo del
  diseño, dímelo:** es un cambio de dos líneas.
- **El calendario en celular:** cada día mide unos 50 px, y los nombres se partían letra por
  letra ("Ferret-ería"). Ahora cada entrega es una barrita de su color dentro del día; el
  detalle está en "Entregas del mes", justo debajo, y el lector de pantalla dice "9 de nov,
  1 entrega". El diseño no tiene calendario de celular.
- **Lo que pidieron los carriles:**
  - las columnas del calendario con el ancho del diseño, y cada color de la leyenda junto a
    su palabra;
  - los botones "Entró" y "Usé" en una línea;
  - la tarjeta del resultado del cotizador con las medidas del diseño;
  - "Editar" y "Escribirle" en una línea;
  - el texto de la tarjeta negra de dotación.
- **Cerrar la ventana desde el servidor:** después de guardar, la vista manda un aviso
  (`HX-Trigger: cerrar-ventana`) y la ventana se cierra sola. Telas lo usa; antes copiaba la
  ventana de `base.html`.
- **"Cerrar" en vez de "Cancelar"** en las ventanas que no tienen nada que cancelar (la lista
  de empresas para escribirles).
- **La pestaña del formulario público** dice el nombre del taller del pedido, aunque quien lo
  abra tenga sesión en otro taller.
- **El nombre del taller en el menú tiene un nombre fijo** (`id="menu-taller"`), para que Mi
  taller lo cambie sin recargar.
- **`cargar_ejemplos` es todo o nada.** En la revisión a mano, al recargar los ejemplos con el
  taller renombrado, el comando falló bien (avisó), pero dejó creado un taller vacío. Ahora,
  si falla, no deja nada. Tiene su prueba. El taller vacío se borró y el tuyo volvió a
  llamarse "Taller de ejemplo".

## Qué se probó a mano

- `uv run pytest`: 1070 pruebas, todas pasan. **Una vez** salió "1 failed" y no se alcanzó a
  ver cuál; en cuatro corridas completas después no volvió a pasar. Puede ser una prueba que
  depende de la hora; queda anotado para la revisión final (T23).
- Capturas de todas las pantallas en 1280 px y 390 px en `docs/capturas/tanda-5/`. Ninguna
  se sale del ancho, ningún archivo falla y no hay errores en el navegador.
- **Calendario, Telas, Cotizador y Clientes** coinciden con sus páginas de `diseno/`, salvo lo
  dicho del ámbar y las fechas (los ejemplos se cuentan desde hoy).
- **En el navegador**, sin recargar la página y sin errores de JavaScript:
  - **Cotizador:** elegir "Camisa polo bordada" y escribir 20 da exactamente lo del diseño:
    $ 1.090.000, $ 54.500, $ 41.600, $ 21.600, $ 258.000 y $ 545.000.
  - **Telas:** "Usé" 2 m de Piqué blanco lo deja en 4 m y la ventana se cierra sola.
  - **Calendario:** tocar el 8 de noviembre deja "Entregas del 8 de nov".
  - **Mi taller:** cambiar el nombre lo cambia también en el menú.
  - **Formulario público, en un celular y sin sesión:** se envía una talla, sale la
    confirmación y no aparece ningún precio.

  Después se volvieron a cargar los ejemplos.

## Para que tú decidas

- **El ámbar de las telas** (arriba).
- **Telas:** el nombre de cada tela es un enlace subrayado que abre su historial, y hay una
  nota debajo de la tabla ("Toca el nombre de una tela..."). El diseño no los tiene; el
  carril los agregó porque `docs/03` pide el historial.
- **Calendario:** el texto "No hay entregas ese día." (solo sale si alguien escribe a mano un
  día sin entregas en la dirección).

## Qué no se pudo comprobar, y queda para T24 (publicar)

- **El límite de envíos del formulario público** cuenta por proceso; en el servidor, con varios
  procesos de Gunicorn, hace falta una caché compartida. También hay que leer la dirección
  real de quien envía detrás de NGINX.
- **El enlace de tallas copiado** debe empezar por `https://` en el servidor
  (`SECURE_PROXY_SSL_HEADER`).
- **NGINX debe aceptar fotos y logos de hasta 10 MB.**
- Un celular de verdad, otros navegadores y los permisos de la costurera (T21).
