# Tanda 4. Plata y Hoy — resumen

## El plan

Tres agentes al mismo tiempo, cada uno en su propia copia y con su propia base de datos:

| Carril | Tareas | Qué construyó |
|---|---|---|
| A | T17, T18 | Resumen del mes con sus cifras, la gráfica, los gastos (registrar y quitar), ventas por tipo de cliente y "Quién tiene qué"; y la descarga para Excel con cuatro hojas. |
| B | T06 | La pantalla Hoy: las cuatro cifras, "Qué hacer hoy" con sus acciones sin recargar, la gráfica, "Quién te debe" y "Pedidos por etapa". |
| C | T13 | La foto de cada pedido (subir, cambiar y quitar; se achica al subirla y se revisa que sea una foto) y la tarjeta "Trabajos del taller" de Hoy con las fotos que pasan. |

Cada carril pasó por un revisor, se corrigió lo que encontró y se revisó otra vez. Cada tarea
tiene su explicación en `docs/bitacora/TNN.md`.

**Lo que preparó el coordinador antes:**

- **La gráfica como pieza** (`{% grafica_barras %}`), porque la usan Hoy y Resumen. Con los
  valores del diseño dibuja exactamente las mismas barras; tiene su prueba.
- **openpyxl** para el Excel (estaba en el stack aprobado).
- **Dos mensajes nuevos para Hoy**: "Preguntar si confirma" y el aviso de atraso. El diseño
  tiene esos botones, pero la demo no tenía sus textos. **Revísalos tú** en
  `pedidos/mensajes.py` (`texto_confirmar` y `texto_atraso`): los escribí en el mismo tono de
  los demás.

## Lo que hizo el coordinador al unir

Los tres carriles se unieron uno por uno, con todas las pruebas después de cada uno.

**Un tropiezo al unir:** un agente había creado por error dos archivos de prueba vacíos en la
copia principal (no en la suya). Estaban vacíos, así que no se perdió nada: se borraron y se
unió.

Después:

- **Hoy recibe sus fotos:** la tarjeta "Trabajos del taller" ya muestra las de los pedidos.
- **En celular, Hoy queda como el diseño:**
  - las cifras en el orden de `diseno/hoy-celular.html` (Atrasados arriba);
  - los botones con sus textos cortos ("Entregado", "Preguntar").
- **"Pedidos por etapa" en sus seis casillas.** También van en negrita los nombres de "Quién te
  debe", y la tarjeta de la gráfica queda con sus espacios.
- **En celular se puede cambiar de mes en Resumen:** arriba solo cabe un botón, así que "Mes
  anterior" y "Mes siguiente" van en su propia fila. Sirve también para el Calendario.
- **"Descargar para Excel" es una sola pieza:** blanca en Hoy y Pedidos, negra en Resumen
  (como el diseño).
- **El campo de pesos es uno solo** para abonos y gastos (y para el cotizador, en la tanda 5).
- **"Copiar" ya no daña los botones** que tienen texto de computador y de celular.
- **El botón para elegir una foto** se ve como los demás botones.
- 5 pruebas nuevas de la unión.

## Qué se probó a mano

- `uv run pytest`: 770 pruebas, todas pasan.
- Capturas de todas las pantallas en 1280 px y 390 px en `docs/capturas/tanda-4/`. Ninguna
  se sale del ancho, ningún archivo falla y no hay errores en el navegador.
- **Hoy** coincide con `diseno/hoy.html`: las cuatro cifras, "Qué hacer hoy" con sus tres
  pendientes y sus botones, "Quién te debe" con el atrasado en rojo, "Pedidos por etapa" con
  "1 atrasado" y "Pagado". En celular, igual que `diseno/hoy-celular.html`.
- **Resumen** coincide con `diseno/resumen.html`:
  - las cifras de noviembre (7.320.000, 4.460.000, 939.000 y 3.521.000);
  - los cinco gastos en el orden del diseño;
  - ventas por tipo;
  - Marta 2, Carmen 1 y Yolima 1.
- **En el navegador**, sin recargar la página y sin errores:
  - en Hoy, "Marcar como listo" actualiza la tarjeta y las cifras;
  - en Resumen, un gasto de 61.000 sube lo gastado a 1.000.000 y baja "Te quedó";
  - en el pedido del Restaurante, una foto de 3000 × 2000 se sube y queda de 1600 × 1067.

  Después se volvieron a cargar los ejemplos.

## Diferencias con el diseño que quedan, y por qué

- **La gráfica de junio a septiembre sale vacía, y octubre sin gastos:** en el diseño esos
  meses son inventados (ver T22).
- **La primera foto es el vestido de grado, no las polleras:** van del pedido más reciente al
  más antiguo.
- **Las notas** debajo de la gráfica y de las fotos dicen otra cosa que el diseño ("Valores
  de ejemplo..." y "Fotos de ejemplo hechas con IA" eran notas del diseño). La de las fotos
  ("Son las fotos de tus pedidos. Cada pedido tiene la suya: se sube dentro del pedido.") la
  escribió el carril C: **revisa si te gusta**.
- **Cada gasto lleva una ✕ para quitarlo**, que el diseño no dibuja (viene de la demo).

## Qué no se pudo comprobar

- El Excel no se abrió en Excel, LibreOffice ni Google Sheets (no están instalados). Se
  revisó leyéndolo de vuelta en las pruebas: cuatro hojas, encabezados, una fila por registro,
  plata como números y fechas como fechas.
- En el servidor, NGINX debe aceptar fotos de hasta 10 MB (`client_max_body_size`): queda
  anotado para T24.
- Un celular de verdad, otros navegadores y los permisos de la costurera (T21).
