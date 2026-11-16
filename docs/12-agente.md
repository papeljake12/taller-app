# El agente del taller

**Estado:** propuesta del 15 de noviembre de 2026, **aprobada por David el mismo día**, con
las recomendaciones de «Decisiones que necesito de David»: el agente propone y ella guarda con
un toque; los cuatro cambios al modelo; el resumen con una tarea programada; tocar Guardar no
cuenta como pregunta; y se empieza por lo mínimo (T38, T39, T40 y T43). Voz, WhatsApp
automático y foto del cuaderno siguen sin decidir. Solo la dueña usa la aplicación.
Al aprobar la maqueta (el mismo día) David decidió además: la tela va en el borrador, con la
tarjeta "Tela del pedido" solo para ver; una tabla `BorradorUsado` para que cada borrador sirva
una sola vez; y el pedido con abono nace Confirmado (`docs/13-plan-tanda-8.md`, sección 6).

Amplía `docs/10-asistente.md` (lo que ya hace el asistente) y reemplaza el bosquejo de la
tanda 8 de `docs/11-plan-tanda-7.md` (sección 7). Los ejemplos con nombres son inventados y
van marcados como ejemplo.

## Por qué

Hoy la aplicación es un lugar ordenado para anotar: ella escribe cada pedido, cada abono y
cada metro de tela, y el asistente le contesta preguntas. Para alguien que lleva años con el
cuaderno, eso se siente como **más trabajo**, no como ayuda.

Lo que se quiere vender es lo contrario: **un agente que hace el trabajo**, y la aplicación es
donde ella ve lo que el agente hizo.

## La idea en una frase

> **Tú le cuentas, el agente lo hace. Tú solo confirmas.**

Ella le habla como le hablaría a una ayudante de confianza. El agente entiende, busca lo que
haga falta, arma todo y se lo muestra listo. Ella toca **Guardar** y queda hecho. Además, el
agente le avisa lo importante sin que ella pregunte.

## Un día con el agente (ejemplo)

**7:00 a. m.** Ella abre la aplicación. Arriba de Hoy, el agente ya le dejó el resumen:

> Buenos días. Hoy entregas los 12 vestidos de *Comparsa Ejemplo*. Van atrasadas las
> camisas de *Empresa Ejemplo* (eran para el martes). *Colegio Ejemplo* te debe $ 840.000
> desde hace 15 días: te dejé el mensaje de cobro listo. Te quedan 4 metros de lino
> blanco y el pedido de la próxima semana necesita 18.

Cada línea trae su botón: «Ver pedido», «Abrir en WhatsApp», «Anotar compra de tela».

**10:30 a. m.** Llega una clienta. Ella escribe (o, más adelante, dicta):

> «Vino la profe del *Colegio Ejemplo*, quiere 30 uniformes de diario para el 15 de
> diciembre y dejó 500 mil.»

El agente le muestra un borrador:

- **Pedido nuevo:** *Colegio Ejemplo* · 30 uniformes de diario · tallaje de niño · entrega
  el 15 de diciembre · total $ 2.700.000 (sale del Cotizador con sus precios guardados).
- **Abono:** $ 500.000 hoy. Falta $ 2.200.000.
- **Tela:** se necesitan 36 m de dacrón azul y hay 20. *Te faltan 16 m.*
- **Tallas:** el enlace queda listo para que la profe lo mande a los papás.

Ella revisa, corrige si algo está mal y toca **Guardar**. Queda todo hecho con un toque.

**3:00 p. m.** «Ya terminé los vestidos de la comparsa.» El agente propone pasarlo a
*Listo* y le deja el mensaje «ya está listo, te faltan $ 300.000» para mandar.

**5:00 p. m.** «Compré 30 metros de lino blanco a 18 mil el metro.» El agente propone sumar
los 30 m en Telas y anotar el gasto de $ 540.000 en *Telas*.

## Qué hace el agente

### 1. Hace las tareas por ella (con su visto bueno)

| Ella dice algo como… | El agente prepara | Se guarda con |
|---|---|---|
| «Pedido de 30 uniformes para el 15» | Cliente (nuevo o existente), pedido, total cotizado | La misma regla de «Nuevo pedido» |
| «Me abonaron 500 mil» | Abono en el pedido correcto | La misma regla de «Registrar abono» |
| «Ya pasé las camisas a confección» | Cambio de etapa | La misma regla de «Pasar a…» |
| «Compré 30 m de lino» | «Entró» en Telas y el gasto | Las reglas de Telas y Gastos |
| «Corté las camisas, usé 24 m» | «Usé» en Telas, unido al pedido | La regla de «Usé» |
| «Pagué la luz, 180 mil» | Gasto en *Servicios* | La regla de Gastos |
| «Agrega 60 botones a la lista» | Material del pedido | La regla de Materiales |

**Varias cosas de una vez.** Un solo mensaje puede traer pedido, abono y tela juntos, como en
el ejemplo de las 10:30. El borrador las muestra juntas y se guardan juntas: o todo, o nada.

### 2. Lleva el inventario solo

- **Cada pedido sabe qué tela usa** y cuántos metros. El agente lo calcula con los metros por
  prenda del Cotizador por la cantidad, y ella lo puede corregir.
- **Avisa si no alcanza**, desde que se crea el pedido: compara lo que hay con lo que piden
  todos los pedidos que todavía no se han cortado.
- **Descuenta la tela cuando el pedido pasa a Corte.** Al cambiar la etapa (desde la pantalla
  o con el agente) sale marcado «Descontar 24 m de dacrón azul». Si ella lo deja marcado, se
  anota el «Usé» unido a ese pedido.
- **Lista de compras:** «¿Qué tengo que comprar?» junta la tela que falta y los materiales sin
  comprar de los pedidos abiertos.

### 3. Avisa sin que le pregunten

- **Resumen de la mañana**, arriba de Hoy: qué entrega hoy, qué va atrasado, a quién cobrar,
  qué tela no alcanza y qué pedidos aún esperan tallas.
- **Avisos con el trabajo hecho:** cada aviso trae lista la acción (el mensaje de cobro, el
  «ya está listo», el recordatorio para mandar las tallas, la compra de tela).
- Lo arma una tarea programada en el servidor cada madrugada (como la copia de seguridad que
  ya corre de noche). **Las cifras las calcula la aplicación** con `pedidos/calculos.py`; Claude
  solo escribe el párrafo. Así ninguna cifra del resumen puede ser inventada.

### 4. Deja listo lo que hay que mandar

Ya existe (`preparar_mensaje`): cobros, «ya está listo» y pedir tallas, con el botón «Abrir
en WhatsApp». Lo nuevo es que el agente los ofrece solo, desde los avisos, sin que ella los
pida. Ella todavía toca «Enviar» en su celular (ver «Lo que no hace»).

## Las reglas de confianza

1. **Nada se guarda sin su toque.** El agente propone; ella decide. Esto no cambia.
2. **Nunca borra.** No existe herramienta para borrar, ni en esta tanda ni después.
3. **Las mismas reglas que las pantallas.** Lo que guarda el agente pasa por los mismos
   formularios y cálculos. Si la pantalla no lo deja, el agente tampoco.
4. **Las cifras son de la aplicación.** Totales, saldos, metros y cotizaciones salen de los
   cálculos, nunca del texto de Claude.
5. **Se ve quién lo hizo.** La cronología del pedido marca lo que se guardó con el agente.
6. **Si no está seguro, pregunta.** Si hay dos clientes parecidos o falta la fecha, el
   borrador lo dice y le pide escoger en vez de adivinar.

## Lo que ve ella

Las piezas nuevas se dibujan primero en la maqueta (`diseno/asistente.html`,
`diseno/hoy.html` y `diseno/pedido.html`) y David las aprueba antes de construir, como en la tanda 7.

- **Hoy:** el resumen del agente va arriba, con la esfera de Lucy, antes de las tarjetas de
  siempre. Debajo sigue la caja grande para hablarle.
- **Tarjeta de borrador:** en el panel del asistente, con cada cosa que se va a guardar en su
  propia fila, lo que falta o no alcanza en ámbar, y dos botones: **Guardar** (negro) y
  **Corregir**. Al guardar cambia a «Listo» con enlaces a lo que creó.
- **Insignia:** la insignia «Solo consulta» del panel desaparece.
- **Cronología del pedido:** «Lo anotó el asistente» en gris, con la esfera pequeña.
- **Pedido por dentro:** una sección nueva «Tela del pedido» (qué tela, cuántos metros, si
  alcanza).
- **Celular:** lo mismo, con el panel a pantalla completa como hoy.
- **Colores:** los de siempre. Ámbar para lo que falta, rojo solo para atrasos y deudas
  vencidas, verde solo para «Listo».

## Cambios al modelo de datos

| Cambio | Para qué |
|---|---|
| Tabla nueva `TelaPedido`: pedido, tela, metros | Qué tela usa cada pedido y cuánta. Con esto se sabe si alcanza |
| `MovimientoTela.pedido` (opcional) | Unir el «Usé» al pedido que lo gastó. Sirve después para la ganancia por pedido |
| `por_asistente` (sí o no) en Pedido, Abono, Gasto y MovimientoTela | Marcar en la cronología lo que se guardó con el agente |
| Tabla nueva `ResumenDelDia`: taller, fecha, texto | Guardar el párrafo de la mañana para no pagarlo cada vez que ella abre Hoy |

Ningún cambio borra datos ni migraciones. Las cifras siguen sin guardarse: se calculan.
Cálculos nuevos en `pedidos/calculos.py`: **tela comprometida** (metros de los pedidos que
aún no pasan de Corte, por tela), **¿alcanza?** (metros que hay menos comprometidos) y
**lista de compras**.

## Permisos

Por ahora solo ella usa la aplicación, así que el agente se construye solo para la dueña. La
tabla deja escrito qué podría hacer una costurera si algún día entran, para no tener que
pensarlo otra vez; esa parte no se construye en esta tanda.

| Con el agente… | Dueña | Costurera |
|---|---|---|
| Consultar | Todo | Sin plata (como en sus pantallas) |
| Crear pedidos y clientes | Sí | No |
| Anotar abonos y gastos | Sí | No |
| Cambiar la etapa | Sí | Solo si es la encargada |
| «Usé» de tela | Sí | Sí |
| «Entró» de tela y lista de compras | Sí | No |
| Ver el resumen de la mañana | Completo | Sin plata: entregas, atrasos y tela |
| Borrar | Nunca | Nunca |

El permiso se revisa en el servidor al tocar **Guardar**, igual que en las pantallas. Si
algún día entran costureras, usarían su propio juego de herramientas, sin las de plata (como
decía el bosquejo de la tanda 8).

## Seguridad y privacidad

- **El borrador va firmado.** Lo que ella confirma es exactamente lo que se mostró: lleva una
  firma con el taller, la usuaria y un vencimiento, y sirve una sola vez. Un borrador ajeno,
  vencido o repetido se rechaza.
- **El agente no escribe en la base.** Igual que hoy, Claude solo pide herramientas; las que
  proponen no guardan nada. Guarda la aplicación, después del toque.
- **Lo que va a Anthropic no cambia:** sin teléfonos, notas, nombres ni medidas de tallas, ni
  el token del enlace. En los borradores van el nombre del cliente y del pedido, como ya van
  en las consultas.
- **El resumen de la mañana** manda a Claude solo las cifras y los nombres de clientes y
  pedidos que ya se usan en las consultas.

## Costo (estimado, se mide en la prueba real)

Con lo medido en la tanda 7 (1,3 centavos de dólar por pregunta y unos 3 por mensaje):

- **Cada tarea con borrador:** unos 2 a 4 centavos, porque el agente busca el cliente o el
  pedido antes de proponer.
- **Resumen de la mañana:** 1 o 2 centavos al día, unos 0,5 USD al mes.
- **En total, para ella** (la única que usa la aplicación), con unas 300 preguntas y tareas al
  mes: unos **6 a 9 USD al mes**. Alcanza de sobra con los 100 USD de crédito, y se debe
  cobrar dentro de la mensualidad.
- Los límites de preguntas siguen igual. Por decidir: si tocar **Guardar** cuenta como
  pregunta (se recomienda que no).

## Lo que no hace (y por qué)

| No hace | Por qué | Qué haría falta |
|---|---|---|
| Borrar | Regla fija: lo borrado no se recupera | Nada; no se hará |
| Guardar sin su toque | Un error con plata le quita la confianza | Se puede reconsiderar para tareas sin plata cuando lleve un tiempo usándolo |
| Mandar WhatsApp por su cuenta | Hace falta la API oficial de Meta, con costo y trámite | Decisión de David (etapa 4, como el agente de WhatsApp) |
| Entender notas de voz | Hace falta un servicio para pasar la voz a texto | Decisión de David: librería o servicio nuevo (regla 6) |
| Leer una foto del cuaderno | Claude puede leerla, pero la foto trae nombres y tallas que hoy no van a Anthropic | Decisión de David sobre esa regla de privacidad |
| Cobrar o mover plata | Fuera del alcance de la aplicación | Pagos en línea (etapa 4) |

## Cómo se construye

Una tanda (la 8), con la misma forma de trabajo de la tanda 7: un plan con contratos y
carriles (`docs/13-plan-tanda-8.md`), un commit por tarea, pruebas que nunca llaman a la API y
capturas al final.

- **T38. Base** (coordinador): documentos al día, maqueta de las piezas nuevas (las aprueba
  David), modelo y migraciones, cálculos nuevos, el borrador firmado y la dirección
  `asistente/confirmar/`.
- **T39. Proponer pedido y cliente**, con el total del Cotizador y «si no está seguro,
  pregunta».
- **T40. Proponer abono y gasto.**
- **T41. Proponer etapa, «Usé» y «Entró».** Incluye «Descontar tela» al pasar a Corte, también
  desde la pantalla del pedido.
- **T42. Inventario:** «Tela del pedido», «¿alcanza?» y lista de compras.
- **T43. Resumen de la mañana:** el comando, la tarea programada del servidor y su lugar en Hoy.
- **T44. Avisos con la acción lista** (cobro quieto, entrega cerca, tela que no alcanza,
  tallas que faltan).
- **T45. Integración:** prueba de punta a punta, capturas y prueba real con la clave
  (costo y tiempo).

**Pruebas clave:** sin tocar Guardar no cambia nada; varias cosas se guardan todas o
ninguna; el permiso es igual al de la pantalla; un taller nunca ve ni toca datos de otro; las
cifras del borrador y del resumen coinciden con las de las pantallas; nunca hay herramienta de
borrar.

## Orden recomendado

1. **Lo mínimo que ya se siente como agente:** T38, T39, T40 y T43. Con eso, el pedido de las
   10:30 y el resumen de las 7:00 funcionan de verdad.
2. **Presentárselo a ella** y preguntarle qué más le gustaría que hiciera el agente (la
   pregunta que quedó pendiente). El video se hace sobre esto, con escenas reales.
3. **Lo demás según lo que ella diga:** T41, T42 y T44, y si pide voz o WhatsApp
   automático, se decide aparte. Las costureras con el agente quedan para cuando las haya.

## Decisiones que necesito de David

1. Aprobar la idea general: el agente propone y ella guarda con un toque.
2. Los cuatro cambios al modelo de datos.
3. Que el resumen de la mañana use una tarea programada en el servidor (como la copia de
   seguridad).
4. Si tocar **Guardar** cuenta como pregunta en el límite (se recomienda que no).
5. El orden: empezar por lo mínimo (paso 1) y presentárselo antes de seguir.
6. Para después: voz, WhatsApp automático y foto del cuaderno (cada una pide algo nuevo).

## Qué cambia en los otros documentos (al aprobarse)

- `docs/01-plan.md`: la etapa 3 se ordena alrededor del agente.
- `docs/02-modelo-de-datos.md`: `TelaPedido`, `MovimientoTela.pedido`, `por_asistente` y
  `ResumenDelDia`, y los cálculos nuevos.
- `docs/03-pantallas.md`: el resumen en Hoy, la tarjeta de borrador y «Tela del pedido».
- `docs/04-permisos.md`: la tabla del agente.
- `docs/05-tareas.md`: la tanda 8 con T38 a T45.
- `docs/10-asistente.md`: ya no es «solo consulta».
- `docs/11-plan-tanda-7.md`: el bosquejo de la tanda 8 apunta a este documento.
