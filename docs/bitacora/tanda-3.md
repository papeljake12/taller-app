# Tanda 3. Pedidos — resumen

## El plan

Cuatro agentes al mismo tiempo, cada uno en su propia copia del proyecto (`.claude/worktrees/carril-a`
a `carril-d`) y con su propia base de datos (`taller_carril_a`...), para no pisarse:

| Carril | Tareas | Qué construyó |
|---|---|---|
| A | T05 | La lista de pedidos con filtros y buscador, la ventana "Nuevo pedido" y el buscador del menú. |
| B | T07, T12 | El pedido por dentro: etapa, entrega, encargada, cliente, eliminar, y los materiales. |
| C | T08, T09 | La tarjeta Pagos (registrar y quitar abonos) y el recibo de cada abono en PDF. |
| D | T10, T04 | La tarjeta Tallas del pedido (con la lista de personas y el formulario a mano) y la pantalla Clientes. |

Cada carril pasó por un revisor que no lo escribió. Lo que encontró se corrigió y el mismo
revisor lo volvió a mirar. Cada tarea tiene su explicación en `docs/bitacora/TNN.md`.

Antes de soltar a los agentes, el coordinador dejó listo lo que iban a compartir: los textos
de los mensajes de WhatsApp (`pedidos/mensajes.py`), ReportLab para el PDF (ya estaba en el
stack aprobado), una carpeta de formularios por zona y las capturas de la tanda.

## Un tropiezo al empezar

La herramienta que crea las copias de trabajo solas las rechazó: en Windows la letra del
disco salía como `c:` en un lado y `C:` en el otro, y la tomó como si fueran carpetas
distintas. Además las había creado a partir de `main`, sin la preparación de la tanda. No se
alcanzó a hacer nada. Se borraron y el coordinador creó las cuatro copias a mano, desde la
rama de la tanda.

## Lo que hizo el coordinador al unir

Los cuatro carriles se unieron uno por uno, corriendo todas las pruebas después de cada uno
(384, 455, 510 y 575 pruebas, todas pasan). Después:

- **El pedido por dentro dibuja las tarjetas Pagos y Tallas completas.** Cada carril hizo su
  tarjeta, pero la página la arma el carril B; al unir se conectaron.
- **Una acción actualiza lo que depende de ella:** cambiar la etapa o el WhatsApp también
  cambia la tarjeta Pagos (el botón "Recordar el saldo"), y registrar un abono cambia el
  botón "Avisar al cliente" de arriba.
- **Una sola forma de leer la plata** (`pedidos/formularios/comun.py`): el nuevo pedido y
  los abonos aceptan lo mismo ("380000", "1.260.000", "$ 380.000") y rechazan lo mismo
  ("380.5", "1,5"). Los gastos y el cotizador la usarán también.
- **Lo que pidieron los carriles en archivos congelados:**
  - estilos para que toda la fila de la tabla abra el pedido y el nombre no salga
    subrayado, como en el diseño;
  - el botón de solo ícono para quitar;
  - la tarjeta Pagos;
  - el número de cada talla a la derecha;
  - una flecha en las filas que se despliegan.
- **La pieza Pasos** ahora envía la etapa también sin JavaScript, y la tarjeta Etapa la usa en
  vez de tener su propia copia.
- **"Pedidos" queda resaltado en el menú** también dentro de un pedido, como en el diseño.
- **El buscador del menú** solo muestra lo buscado en su propia página; antes, al filtrar la
  lista de pedidos, el texto aparecía también en el menú.
- **En celular** el menú lateral no se ve, así que "Buscar pedidos y clientes" quedó de primero
  en el panel "Más".
- **El recibo conserva las tildes** aunque el nombre llegue con la tilde "suelta" (pasa al
  copiar de algunos celulares); antes salía "Jose?".
- 15 pruebas nuevas de la unión (`pedidos/tests/test_pedido_completo.py` y el menú).

## Qué se probó a mano

- `uv run pytest`: 591 pruebas, todas pasan.
- Capturas de todas las pantallas en 1280 px y 390 px en `docs/capturas/tanda-3/`. Ninguna
  se sale del ancho, ningún archivo falla y no hay errores en el navegador.
- **Pedidos** coincide con `diseno/pedidos.html`: filtros con sus conteos, etiquetas,
  encargadas, tallas y saldos con sus colores.
- **Pedido por dentro** coincide con `diseno/pedido.html`, con las dos columnas terminando a la
  misma altura.
- **Clientes** coincide con `diseno/clientes.html`, salvo el aviso de dotación y "Escribirle",
  que llegan con T19.
- **En el navegador, en el pedido del Restaurante**, sin recargar la página:
  - tocar "En confección" cambia la etiqueta de arriba;
  - registrar un abono de 260.000 deja "Falta por pagar $ 1.000.000";
  - marcar "Hilo para bordar" deja "3 de 4 comprados";
  - agregar una persona a mano deja "15 de 18 recibidas";
  - ningún error de JavaScript.
  Después se volvieron a cargar los ejemplos.

## Diferencias con el diseño que quedan, y por qué

- **Fechas un día o dos después de las del diseño** ("11 de nov" en vez de "9 de nov"): los
  ejemplos se cuentan desde hoy. Las etiquetas sí coinciden ("Atrasado 2 días").
- **Sin el botón de WhatsApp**: los ejemplos no tienen número (ver T22). Sale "Copiar
  recordatorio de saldo" en su lugar.
- **Filas de materiales un poco más altas** que en el diseño, porque llevan el botón para
  quitarlas; en celular más, porque los botones miden 44 px para el dedo.
- **Partes que el diseño no dibuja pero `docs/03-pantallas.md` pide**:
  - el control del enlace público de tallas;
  - la lista de personas;
  - el formulario para agregar una persona a mano;
  - el formulario de materiales;
  - el de abonos;
  - "Eliminar el pedido";
  - la tarjeta de la foto, que llega con T13.
- **En celular, el pedido por dentro** pone primero la columna izquierda (etapa, tallas y
  materiales) y después la derecha (pagos, entrega y cliente). No hay diseño de celular para
  esta pantalla.

## Qué no se pudo comprobar

- Que el enlace copiado empiece por `https://` en el servidor: depende de la configuración de
  producción (queda anotado para T24).
- Un celular de verdad y otros navegadores.
- Los permisos de la costurera (no ve plata): llegan con T21.
