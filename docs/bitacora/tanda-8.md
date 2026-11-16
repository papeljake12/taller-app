# Tanda 8: el agente del taller (lo mínimo)

## Plan (antes de escribir código)

Hasta ahora el asistente solo contestaba preguntas. En esta tanda empieza a **hacer el
trabajo**: ella le cuenta "vino la profe, quiere 30 uniformes y dejó 500 mil" y el agente le
deja listo el pedido, el abono y la tela en una tarjeta. Ella revisa y toca **Guardar**. Nada
se guarda sin ese toque. Además, cada madrugada el agente le deja un resumen arriba de Hoy.

Qué se crea o cambia, y por qué (el detalle está en `docs/13-plan-tanda-8.md`):

- **T38 (la base, la hago yo):** los documentos al día; la maqueta nueva (aprobada por David el
  15 de noviembre); cinco cambios al modelo (la tela de cada pedido, quién lo anotó, el resumen
  del día y la tabla que evita guardar dos veces el mismo borrador); los cálculos de "¿alcanza
  la tela?"; el borrador firmado y la dirección que lo guarda.
- **T39, T40 y T43 (tres agentes al mismo tiempo, cada uno en su copia):** proponer pedido y
  cliente; proponer abono y gasto; y el resumen de la mañana.
- **Al final:** pruebas de punta a punta, capturas en 1280 y 390 px, y una prueba real con la
  clave para medir costo y tiempo.

Lo que se deja para después de mostrárselo a ella: T41, T42, T44 y T45.

## Resumen de la tanda (al cerrar)

### Qué se hizo

- **T38 (la base, coordinador):** el borrador firmado, guardar todo o nada con las reglas de las
  pantallas, la tela de cada pedido, "Lo anotó el asistente", cinco cambios al modelo y la
  maqueta nueva (aprobada por David).
- **T39 (carril A):** el agente propone el pedido nuevo con su cliente, el abono y la tela.
- **T40 (carril B):** el agente propone abonos y gastos.
- **T43 (carril C):** el resumen de la mañana arriba de Hoy, con el comando `preparar_resumen`.

Los tres carriles trabajaron al mismo tiempo, cada uno en su propia copia
(`C:\Users\Administrador\taller-carriles\`) y con su propia base de pruebas. Un revisor los
revisó antes de unirlos: los tres se podían unir. Se unieron en orden A, B, C, con todas las
pruebas después de cada uno.

### Qué se probó

- **Pruebas automáticas:** 2.034, todas pasan. Ninguna llama a la API de verdad.
- **De punta a punta** (con un Claude de mentira y todo lo demás de verdad): el pedido de las
  10:30 se propone, se guarda con un toque y aparece en el pedido con su abono, su tela y "Lo
  anotó el asistente"; un abono desde la pantalla del pedido; el resumen de la mañana en Hoy.
- **Capturas** de todas las pantallas en 1280 y 390 px (`docs/capturas/tanda-8/`), sin nada que
  se salga del ancho. Las nuevas: `hoy-agente`, `asistente-agente` y `pedido-agente`, iguales a
  sus páginas de `diseno/`.
- **Prueba real con la clave** (`herramientas/probar_agente.py`, sobre los datos de ejemplo, sin
  tocar Guardar):

| Qué | Resultado |
|---|---|
| 4 pedidos | 3 borradores bien armados. En el cuarto ("una señora quiere un vestido de grado") preguntó el nombre en vez de inventarlo |
| 3 abonos | 3 borradores con el "Falta" correcto, uno desde la pantalla del pedido |
| 3 gastos | 3 borradores, con la categoría bien puesta y uno unido a su pedido |
| 3 resúmenes | Los 3 se guardaron: todas sus cifras pasaron la revisión |
| Costo por tarea | 2,4 centavos de dólar en promedio; el más caro, 7 (la primera, que llena la caché) |
| Tiempo por tarea | 9 segundos en promedio; el más largo, 15,6 |

### Qué se corrigió

- **El límite de la API:** con las herramientas nuevas había 26 datos opcionales y la API acepta
  16. Ahora "no hay" se dice con 0 o con texto vacío (T38).
- **Lo que encontró el revisor:** el mensaje para pedir tallas pasó a `pedidos/mensajes.py`; la
  revisión de cifras ahora también ve "480 mil" y "1,8 millones"; y un pedido sin abono (que nace
  Cotizado) dice "Cuando lo confirmes, te faltarán 48 m".
- **En las capturas:** la cifra "$ 450.000" ya no se parte entre dos líneas en el borrador, y la
  hora del resumen ya no lleva un espacio doble.

### Lo que no se pudo comprobar, o queda para David

- **La tela no aparece si ella no la nombra.** En la prueba real, con "30 uniformes de diario",
  Claude no puso la tela porque nadie dijo cuál (bien: no inventa). Para que salga sola, la
  prenda guardada tendría que decir qué tela usa: es un cambio al modelo para pensar en T42.
- **Un abono a un pedido Cotizado lo deja Cotizado**, igual que la pantalla. ¿Debería pasarlo a
  Confirmado, como el pedido nuevo con abono? Es decisión de David.
- **La tarea de las 5:00 a. m.** la instala David al publicar
  (`herramientas/servidor/cron-resumen.txt` y `docs/guia-publicacion.md`).
- **Los botones de WhatsApp del resumen** dicen "Ver pedido" con los datos de ejemplo, porque los
  ejemplos no traen números de teléfono (no se inventan).
- No se probó con la usuaria real. Eso es el paso 2 de `docs/12-agente.md`: presentárselo.
