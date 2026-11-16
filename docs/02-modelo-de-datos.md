# Modelo de datos

Qué guarda la aplicación y cómo se relaciona. Sale de la demo, con los cambios necesarios
para que funcione con varios talleres y varios usuarios.

Convenciones:

- Todos los modelos tienen `creado` (fecha y hora) y, donde aplica, `actualizado`.
- La plata va en enteros de pesos colombianos.
- Los nombres van en español, sin tildes ni ñ.

## Mapa general

```
Taller
 ├── Usuario            (dueña o costurera)
 ├── Cliente
 │    └── Pedido
 │         ├── Abono
 │         ├── Talla
 │         ├── Material
 │         └── TelaPedido   (qué tela usa y cuántos metros, tanda 8)
 ├── Tela
 │    └── MovimientoTela    (puede decir de qué pedido fue, tanda 8)
 ├── Gasto
 ├── PrendaGuardada     (precios base del cotizador)
 ├── UsoAsistente       (preguntas y tokens del asistente por día, tanda 7)
 ├── ResumenDelDia      (el párrafo de la mañana del agente, tanda 8)
 └── BorradorUsado      (borradores del agente que ya se guardaron, tanda 8)
```

**Tanda 8 (el agente, `docs/12-agente.md`).** Pedido, Abono, Gasto y MovimientoTela llevan
además `por_asistente`: dice si se guardó con el agente (ella tocó Guardar en un borrador) o
desde una pantalla. Ningún cambio de esta tanda borra datos ni migraciones, y las cifras
siguen sin guardarse: se calculan.

## Taller

El negocio. Todo lo demás cuelga de aquí.

| Campo | Tipo | Notas |
|---|---|---|
| nombre | texto, 50 | Sale arriba, en mensajes y en recibos |
| telefono | texto, 40, opcional | |
| logo | imagen, opcional | |
| asistente_limite_mes | entero, 0 por defecto | Preguntas al asistente por mes. 0 lo apaga. Lo pone David en `/admin` (lo normal: 600). Tanda 7 |
| asistente_limite_dia | entero, 0 por defecto | Preguntas al asistente por día. 0 lo apaga (lo normal: 40). Tanda 7 |

## Usuario

Usuario propio del proyecto, basado en el de Django (`AbstractUser`). Se define en la
primera migración; cambiarlo después es difícil.

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación con Taller | Obligatorio para dueñas y costureras |
| rol | opción | `duena` o `costurera` |
| nombre_visible | texto, 40 | Como aparece en "¿Quién lo está haciendo?" |

El usuario administrador de David (`is_superuser`) no pertenece a ningún taller.

## Cliente

En la demo los clientes se sacaban del nombre escrito en cada pedido. Aquí son una tabla.

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| nombre | texto, 80 | Único dentro del taller, sin distinguir mayúsculas |
| tipo | opción | `comparsa`, `empresa`, `colegio`, `particular` |
| whatsapp | texto, 40, opcional | Solo dígitos al armar el enlace |
| notas | texto, opcional | |

## Pedido

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| cliente | relación con Cliente | |
| detalle | texto, 160 | "Qué pidió" |
| cantidad | entero, 1 a 2000 | Para cuántas personas |
| tallaje | opción | `adulto` (XS a XXL) o `nino` (4 a 16) |
| fecha_entrega | fecha | |
| total | entero, pesos | |
| estado | opción | Ver lista abajo |
| encargada | relación con Usuario, opcional | |
| foto | imagen, opcional | Foto del pedido. Sale en su tarjeta de Hoy y en la lista de pedidos |
| token_tallas | texto único, 32 | Para el enlace público de tallas. Se genera solo |
| tallas_abiertas | sí o no | Si el enlace público acepta envíos. Por defecto sí |
| creado_por | relación con Usuario | |
| por_asistente | sí o no, no por defecto | Se guardó con el agente. La cronología lo marca con "Lo anotó el asistente". Tanda 8 |

Estados, en orden: `cotizado`, `confirmado`, `corte`, `confeccion`, `listo`, `entregado`.

Un pedido nuevo nace `cotizado`. Si se guarda con el agente y ella dejó abono, nace
`confirmado`, con la misma regla de "Pasar a Confirmado" de la pantalla (decisión de David
del 15 de noviembre de 2026).

## Abono

| Campo | Tipo | Notas |
|---|---|---|
| pedido | relación | |
| fecha | fecha | |
| valor | entero, pesos, mayor que 0 | |
| registrado_por | relación con Usuario | |
| por_asistente | sí o no, no por defecto | Se guardó con el agente. Tanda 8 |

## Talla

Una fila por persona.

| Campo | Tipo | Notas |
|---|---|---|
| pedido | relación | |
| nombre | texto, 60 | |
| talla | texto, 12 | Una del tallaje del pedido, o `medida` |
| pecho, cintura, cadera, largo | número con un decimal, opcional | En centímetros. Solo si la talla es `medida` |
| nota | texto, 200, opcional | |
| origen | opción | `enlace` (la envió el cliente) o `manual` |

Regla: si la talla es `medida`, pecho, cintura y cadera son obligatorios.

## Material

Lista de compras de un pedido.

| Campo | Tipo | Notas |
|---|---|---|
| pedido | relación | |
| nombre | texto, 60 | |
| cantidad | texto, 30, opcional | Texto libre: "24 m", "60" |
| comprado | sí o no | |

## Tela

Inventario del taller.

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| nombre | texto, 60 | |
| metros | número con dos decimales, 0 o más | Lo que queda |
| minimo | número con dos decimales | Avisa cuando `metros` es menor o igual. 0 = sin aviso |

## MovimientoTela

Nuevo respecto a la demo: guarda el historial de "Entró" y "Usé".

| Campo | Tipo | Notas |
|---|---|---|
| tela | relación | |
| metros | número con dos decimales | Positivo si entró, negativo si se usó |
| fecha | fecha y hora | |
| usuario | relación con Usuario | |
| pedido | relación con Pedido, opcional | El pedido que gastó esa tela (un "Usé"). Si se borra el pedido, el movimiento queda sin pedido. Sirve después para la ganancia por pedido. Llega en la tanda 8, pero la llena T41 |
| por_asistente | sí o no, no por defecto | Se guardó con el agente. Tanda 8 |

## TelaPedido

Tanda 8. Qué tela del inventario usa un pedido y cuántos metros. Con esto se sabe si la tela
alcanza. No mueve los metros de la tela: eso lo sigue haciendo el "Usé".

| Campo | Tipo | Notas |
|---|---|---|
| pedido | relación con Pedido | Si se borra el pedido, se borra su tela |
| tela | relación con Tela | Debe ser del mismo taller que el pedido |
| metros | número con dos decimales, mayor que 0 | |

Regla: una tela aparece una sola vez en cada pedido. En esta tanda la anota el agente al
guardar un pedido nuevo; corregirla desde la pantalla llega con T42.

## Gasto

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| fecha | fecha | |
| concepto | texto, 80 | |
| categoria | opción | `telas`, `insumos`, `servicios`, `otros` |
| valor | entero, pesos, mayor que 0 | |
| pedido | relación con Pedido, opcional | Para calcular la ganancia por pedido en la etapa 3 |
| por_asistente | sí o no, no por defecto | Se guardó con el agente. Tanda 8 |

## PrendaGuardada

Precios base del cotizador.

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| nombre | texto, 80 | Único dentro del taller |
| metros | número con dos decimales | Metros de tela por prenda |
| precio_metro, insumos, mano_obra, extra | enteros, pesos | |

## UsoAsistente

Tanda 7 (`docs/10-asistente.md`). Cuántas preguntas le hizo cada taller al asistente cada día
y cuántos tokens gastaron. La conversación no se guarda aquí: vive en la sesión. El costo en
dólares se calcula con los precios de los ajustes (`ASISTENTE_PRECIOS_USD`); no se guarda.

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| fecha | fecha | Día en la hora de Bogotá. Uno solo por taller y día |
| preguntas | entero, 0 por defecto | |
| tokens_entrada, tokens_salida | enteros grandes, 0 por defecto | |
| tokens_cache_escritura, tokens_cache_lectura | enteros grandes, 0 por defecto | |

## ResumenDelDia

Tanda 8 (T43). El párrafo de la mañana que el agente deja arriba de Hoy. Se guarda para no
pagarle a Claude cada vez que ella abre Hoy. Las filas con botón (a quién cobrar, tela,
tallas) no se guardan aquí: se calculan al abrir Hoy, así siempre están al día.

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| fecha | fecha | Día en la hora de Bogotá. Uno solo por taller y día |
| texto | texto | El párrafo. Solo se guarda si cada cifra en pesos coincide con las de la aplicación |
| creado | fecha y hora | A qué hora se preparó ("Lo preparé a las 5:00 a. m.") |

## BorradorUsado

Tanda 8. La clave de cada borrador del agente que ya se guardó. Como la clave es única, un
borrador sirve **una sola vez**: si llegan dos toques de Guardar casi al mismo tiempo, el
segundo se rechaza y no guarda nada dos veces (decisión de David del 15 de noviembre de 2026).

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| clave | texto, 32, única | Sale de la firma del borrador. Se anota en la misma transacción que lo guardado |
| creado | fecha y hora | |

## Cálculos (no se guardan)

Estas reglas ya están probadas en la demo. Deben dar los mismos resultados.

- **Abonado:** suma de los abonos del pedido.
- **Saldo:** `total - abonado`, nunca menor que 0.
- **En producción:** estado distinto de `cotizado` y de `entregado`.
- **Atrasado:** en producción y con `fecha_entrega` anterior a hoy.
- **Pronto:** en producción y con entrega entre hoy y 7 días.
- **Por cobrar:** suma de saldos de los pedidos que no están en `cotizado`.
- **Vendido en el mes:** suma del total de los pedidos no cotizados creados ese mes.
- **Cobrado en el mes:** suma de los abonos con fecha en ese mes.
- **Gastado en el mes:** suma de los gastos con fecha en ese mes.
- **Gastos entre dos fechas** (tanda 7, para el asistente): los gastos con fecha entre las
  dos, ambas incluidas, del más nuevo al más viejo; opcionalmente de un solo tipo. **Por
  tipo:** la suma de cada tipo en esas fechas, de mayor a menor, sin los tipos vacíos.
- **Te quedó:** cobrado menos gastado.
- **Tela baja:** `minimo > 0` y `metros <= minimo`.
- **Tela comprometida** (tanda 8, `tela_comprometida`): por cada tela, la suma de los metros
  de `TelaPedido` de los pedidos en `confirmado`. Son metros "apartados": el pedido ya está
  confirmado pero todavía no se cortó. Los cotizados no apartan nada (el cliente aún no dijo
  que sí) y los que ya pasaron a corte tampoco (esa tela ya se gastó con un "Usé"). Se puede
  dejar fuera un pedido, para no contarlo dos veces al revisar el suyo.
- **Falta tela** (tanda 8, `falta_tela`): metros que se necesitan más los comprometidos,
  menos los que hay. Si da 0 o menos, alcanza (0).
- **Telas que no alcanzan** (tanda 8, `telas_que_no_alcanzan`): las telas cuyos metros no
  cubren lo comprometido, con cuántos metros están apartados y cuántos faltan, ordenadas por
  nombre sin importar tildes.
- **Tela del pedido** (tanda 8, `tela_del_pedido`): para la tarjeta del mismo nombre, cada
  tela del pedido con sus metros y cuánto falta. Solo a un pedido `confirmado` le puede
  faltar tela, porque es el único que la aparta.
- **Cobrado y gastado por mes (gráfica):** los dos cálculos anteriores para cada uno de los
  últimos seis meses, incluido el actual.
- **Quién te debe:** por cliente, la suma de los saldos de sus pedidos que no están en
  `cotizado`. Solo clientes con saldo mayor que 0, del que más debe al que menos. Va en rojo
  el cliente que tenga al menos un pedido atrasado.
- **Pedidos por etapa:** cuántos pedidos hay en cada estado, y cuántos de ellos van atrasados.
- **Qué hacer hoy:** pedidos atrasados, luego los que están en `listo`, luego los de entrega
  en 7 días, luego los que están en `cotizado`. Un pedido aparece una sola vez, en el primer
  grupo que le corresponda.
- **Cotizador:**
  - costo por prenda = `metros × precio_metro + insumos + mano_obra + extra`
  - precio por unidad = costo × (1 + ganancia % ÷ 100), redondeado hacia arriba a los 500 pesos
  - total = precio por unidad × cantidad
  - abono para empezar = total × porcentaje de abono ÷ 100
- **Fechas de dotación:** 30 de abril, 31 de agosto y 20 de diciembre (artículos 230 y 232
  del Código Sustantivo del Trabajo de Colombia). Fuente consultada:
  https://actualicese.com/cual-debe-ser-el-valor-minimo-de-la-dotacion/

## Reglas de integridad

- Borrar un pedido borra sus abonos, tallas, materiales y su tela del pedido (`TelaPedido`).
  Sus movimientos de tela se conservan, sin pedido.
- El agente nunca borra nada: no tiene herramienta para eso (tanda 8).
- Un cliente con pedidos no se puede borrar.
- Una usuaria solo puede leer y escribir datos de su taller.
- El enlace público de tallas solo permite crear tallas del pedido de ese `token_tallas`.
  No permite leer ni cambiar nada más.

## Pendiente por decidir con la clienta

- Si necesita facturación electrónica.
- Si paga a las costureras por prenda (define el modelo de pagos de la etapa 3).
