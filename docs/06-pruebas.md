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
