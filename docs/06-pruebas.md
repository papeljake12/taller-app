# Pruebas

Las pruebas son pequeños programas que revisan solos que la aplicación hace lo que debe.
Sirven para que un cambio nuevo no dañe algo que ya funcionaba.

## Reglas

1. Cada tarea trae sus pruebas en el mismo commit.
2. Una tarea no está terminada si alguna prueba falla, sea nueva o vieja.
3. Se corre `uv run pytest` antes de cada commit.
4. Las pruebas usan datos creados dentro de la prueba, nunca la base de datos real.
5. Si se corrige un error, primero se escribe la prueba que lo demuestra y luego el arreglo.

## Herramientas

- `pytest` y `pytest-django`.
- Fábricas de datos escritas a mano en `tests/fabricas.py` (crear taller, usuaria, cliente,
  pedido). Sin librerías adicionales por ahora.

## Lo que siempre se prueba

### Aislamiento entre talleres (lo más importante)

Para cada modelo con datos de un taller:

- La usuaria del taller A no ve en ninguna lista datos del taller B.
- Pedir por URL un dato del taller B responde 404.
- Intentar editar o borrar un dato del taller B responde 404 y no cambia nada.

### Cálculos de plata

Con los casos de la demo como referencia:

- Pedido de 2.520.000 con un abono de 1.260.000: saldo 1.260.000.
- Abonos que suman más que el total: saldo 0, nunca negativo.
- "Por cobrar" no incluye pedidos en `cotizado`.
- Cotizador con camisa polo de ejemplo (1,2 m a 18.000, insumos 3.000, mano de obra 12.000,
  extra 5.000, ganancia 30 %): costo 41.600, precio por unidad 54.500, y 20 unidades dan
  1.090.000.
- Resumen del mes: vendido, cobrado, gastado y "te quedó" con abonos y gastos de dos meses
  distintos.

### Fechas

- Un pedido en producción con entrega ayer está atrasado.
- Un pedido `cotizado` o `entregado` nunca está atrasado.
- Entrega hoy y entrega en 7 días cuentan como "pronto"; en 8 días, no.
- La próxima fecha de dotación se calcula bien antes y después de cada una de las tres
  fechas, y al cambiar de año.

### Enlace público de tallas

- Con un token válido se puede enviar una talla y queda en ese pedido.
- Con un token inventado responde 404.
- Con el enlace cerrado no acepta envíos.
- Talla "medida" sin pecho, cintura o cadera se rechaza.
- La respuesta no incluye precios ni tallas de otras personas.
- Pasado el límite de envíos por minuto, rechaza los siguientes.

### Permisos

Una prueba por cada fila de la tabla de `docs/04-permisos.md`, como dueña y como costurera.
En particular:

- Una costurera no recibe en ninguna página el total, los abonos ni el saldo.
- Una costurera no puede registrar abonos aunque envíe el formulario a mano.
- Sin sesión, las pantallas internas redirigen al inicio de sesión.

### Asistente (tanda 7)

- `uv run pytest` nunca llama a la API de Claude: los ajustes de pruebas borran la clave y
  ponen un cliente que falla si alguien lo usa. Las respuestas de Claude se simulan con
  `asistente.falso.ClienteFalso` y un guion.
- Cada herramienta, con dos talleres: nunca devuelve lo del otro, y un id ajeno da el mismo
  error que uno que no existe.
- Lo que va a Claude (`Resultado.datos`) no lleva teléfonos, notas, nombres ni medidas de
  tallas, ni el token del enlace, y no tiene números con decimales sueltos (float).
- Las cifras del asistente coinciden con las de las pantallas: "Quién te debe" con Hoy, las
  cuentas del mes con Resumen, la cotización con el Cotizador.
- El límite de preguntas frena antes de llamar a Claude, y un error del servicio no gasta una
  pregunta.
- Lo que escribe Claude se muestra escapado: un `<script>` en su texto sale como texto.
- La prueba con preguntas reales (T36) se hace a mano, con la clave, fuera de pytest.

### El agente (tanda 8)

El detalle de cada tarea está en `docs/13-plan-tanda-8.md` (secciones 2 y 3). Lo que siempre
se prueba:

- **Sin tocar Guardar no cambia nada.** Proponer un pedido, un abono o un gasto deja la misma
  cantidad de registros en la base que antes.
- **Todo o nada.** Si una cosa del borrador falla (por ejemplo el abono), no queda ninguna:
  ni el pedido, ni el cliente, ni la tela.
- **Un solo uso.** Un borrador ya guardado, vencido (más de 2 horas), de otro taller o de otra
  usuaria se rechaza y no guarda nada. Dos toques seguidos guardan una sola vez.
- **Las mismas reglas que las pantallas.** Una fecha, una cantidad o un valor que la pantalla
  no acepta da el mismo mensaje con el agente. El permiso se revisa en el servidor al guardar.
- **Aislamiento.** Un cliente o pedido de otro taller, aunque tenga el mismo nombre, no se ve
  ni se toca; un id ajeno da "No encontré ese pedido.". Cada modelo nuevo (`TelaPedido`,
  `ResumenDelDia`, `BorradorUsado`) está en `tests/test_aislamiento.py`.
- **Las cifras coinciden con las pantallas.** El total del borrador es el del Cotizador; el
  "Falta" es el saldo del pedido y, después de guardar, coincide con la tarjeta Pagos; un
  gasto guardado da el mismo total en el Resumen del mes que si se anotara en la pantalla;
  los cobros del resumen de la mañana coinciden con "Quién te debe" de Hoy, y la tela que no
  alcanza, con `telas_que_no_alcanzan`.
- **El párrafo de la mañana no inventa cifras.** Si trae una cifra en pesos que no está en los
  cálculos, no se guarda.
- **Se ve quién lo hizo.** Lo guardado con el agente lleva `por_asistente` y la cronología
  dice "Lo anotó el asistente"; lo de las pantallas, no.
- **No hay herramienta de borrar**, ni guardador que borre.
- **Lo que va a Claude** no trae la firma del borrador, ni teléfonos, ni notas, ni tallas con
  nombre, ni el token del enlace.
- **Tocar Guardar no gasta preguntas** y no llama a Claude.
- **Las pruebas nunca llaman a la API**, igual que en la tanda 7: Claude se simula con
  `ClienteFalso`. La prueba real con la clave se hace a mano, fuera de pytest.

### Archivos

- El recibo se genera como PDF válido y contiene cliente, valor, total y saldo.
- El Excel tiene las cuatro hojas con sus encabezados y una fila por registro.
- Subir un archivo que no es imagen como foto se rechaza.

## Lo que se revisa a mano

Las pruebas automáticas no ven el diseño. Antes de cerrar una tarea con pantalla:

- Abrirla en 390 px y en 1280 px de ancho.
- Compararla con su página de `diseno/` (la tabla está en `docs/08-diseno.md`): colores,
  tamaños, textos y orden.
- Revisar que las tarjetas de cada fila terminen a la misma altura.
- Probar el recorrido completo con el teclado.
