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
 │         └── Material
 ├── Tela
 │    └── MovimientoTela
 ├── Gasto
 └── PrendaGuardada     (precios base del cotizador)
```

## Taller

El negocio. Todo lo demás cuelga de aquí.

| Campo | Tipo | Notas |
|---|---|---|
| nombre | texto, 50 | Sale arriba, en mensajes y en recibos |
| telefono | texto, 40, opcional | |
| logo | imagen, opcional | |

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

Estados, en orden: `cotizado`, `confirmado`, `corte`, `confeccion`, `listo`, `entregado`.

## Abono

| Campo | Tipo | Notas |
|---|---|---|
| pedido | relación | |
| fecha | fecha | |
| valor | entero, pesos, mayor que 0 | |
| registrado_por | relación con Usuario | |

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

## Gasto

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| fecha | fecha | |
| concepto | texto, 80 | |
| categoria | opción | `telas`, `insumos`, `servicios`, `otros` |
| valor | entero, pesos, mayor que 0 | |
| pedido | relación con Pedido, opcional | Para calcular la ganancia por pedido en la etapa 3 |

## PrendaGuardada

Precios base del cotizador.

| Campo | Tipo | Notas |
|---|---|---|
| taller | relación | |
| nombre | texto, 80 | Único dentro del taller |
| metros | número con dos decimales | Metros de tela por prenda |
| precio_metro, insumos, mano_obra, extra | enteros, pesos | |

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
- **Te quedó:** cobrado menos gastado.
- **Tela baja:** `minimo > 0` y `metros <= minimo`.
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

- Borrar un pedido borra sus abonos, tallas y materiales.
- Un cliente con pedidos no se puede borrar.
- Una usuaria solo puede leer y escribir datos de su taller.
- El enlace público de tallas solo permite crear tallas del pedido de ese `token_tallas`.
  No permite leer ni cambiar nada más.

## Pendiente por decidir con la clienta

- Si necesita facturación electrónica.
- Si paga a las costureras por prenda (define el modelo de pagos de la etapa 3).
