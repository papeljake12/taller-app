# Plan de la tanda 8: el agente del taller (lo mínimo)

Plan hecho por el coordinador el 15 de noviembre de 2026. Qué se construye y por qué está en
`docs/12-agente.md` (aprobado por David el mismo día). Las reglas de trabajo con varios
agentes son las de `docs/09-plan-de-construccion.md` ("Reglas para los agentes"), y el molde
es el de la tanda 7 (`docs/11-plan-tanda-7.md`): lo que este plan no cambia, sigue igual.

Esta tanda hace **solo lo mínimo** (paso 1 del "Orden recomendado" de `docs/12-agente.md`):
**T38, T39, T40 y T43**. Con eso funcionan de verdad el pedido de las 10:30 y el resumen de las
7:00. T41, T42, T44 y T45 quedan escritas para después de presentárselo a ella (sección 7).

Rama: `tanda-8-agente`, sacada de `main`.

## 0. Lo que choca con el repo actual (y cómo se resuelve)

1. **"Solo consulta" en todas partes.** `docs/10-asistente.md` ("No crea, no cambia y no borra
   nada"), la insignia "Solo consulta" del panel, la nota "Solo lee tus datos, no cambia nada",
   las instrucciones de Claude (`asistente/instrucciones.py`) y la lista del revisor de la
   tanda 7 ("Ninguna herramienta escribe en la base"). Se corrigen en T38. La regla del
   revisor sigue valiendo así: **ninguna herramienta escribe**; escribe solo la vista
   `confirmar`, después del toque.
2. **Archivos congelados del asistente.** `contratos.py`, `esquemas.py`, `falso.py`,
   `herramientas/__init__.py` y `urls.py` los cambia solo el coordinador, en T38. También
   `instrucciones.py` y `esfuerzo.py`, que en la tanda 7 eran del carril B y ahora son de la
   base.
3. **La huella de la conversación cambia** con las herramientas nuevas: al publicar, las
   conversaciones guardadas empiezan de nuevo (ya pasa en cada despliegue que cambia
   herramientas; no se pierde nada guardado).
4. **El pedido nuevo nace "Cotizado"** (`pedidos/vistas/lista.py`, `crear_pedido`). Si ella
   dejó abono, el agente lo deja Confirmado (decisión 4 de la sección 6).
5. **La receta del Cotizador no dice qué tela usa.** `PrendaGuardada` tiene los metros por
   prenda, pero no la tela. Claude escoge la tela por su nombre con la herramienta `telas` y
   la aplicación la busca en el inventario del taller; si hay dos parecidas, pregunta.
6. **Sin descuento automático de tela todavía.** "Descontar tela al pasar a Corte" es T41. En
   esta tanda la tela comprometida cuenta solo los pedidos **Confirmados**; cuando un pedido
   pasa a Corte ella anota el "Usé" a mano, como hoy. Queda escrito en la bitácora.
7. **El servidor no tiene una tarea de madrugada para el resumen.** Se agrega como la copia de
   seguridad: `herramientas/servidor/cron-resumen.txt` y un paso en
   `docs/guia-publicacion.md`. **Lo instala David** al publicar; Claude Code no toca el
   servidor.
8. **`ClienteAnthropic.enviar` siempre manda herramientas.** El resumen no usa herramientas:
   con `herramientas=[]` no se envían ni `tools` ni `tool_choice` (cambio de la base en T38,
   con su prueba).
9. **Hoy ya tiene las cartas "Lo que hay que hacer hoy"** (atrasos y entregas, con su botón).
   Para no repetirlas, el resumen las menciona en el párrafo, pero sus filas con botón son solo
   de lo que las cartas no muestran: a quién cobrar, tela que no alcanza o está baja y tallas
   que faltan.
10. **`docs/12-agente.md` pide las piezas en `diseno/hoy.html`**, pero esa página es Hoy con el
    asistente apagado (la caja grande es el buscador). El resumen solo existe con el asistente
    prendido, así que va en una página nueva, `diseno/hoy-agente.html`. Los borradores van en
    otra página nueva, `diseno/asistente-agente.html`, para no tapar las tarjetas de la
    tanda 7 de `diseno/asistente.html` (que solo pierde la insignia y cambia su nota).

## 1. Arquitectura y contratos

```
asistente/
  contratos.py        (congelado) + Fila; Resultado y Tarjeta no cambian
  esquemas.py         (congelado) + proponer_pedido, proponer_abono, proponer_gasto
  herramientas/
    __init__.py       (congelado) REGISTRO con las tres nuevas, DE_PLATA, RANGOS
    pedido_nuevo.py   A: proponer_pedido
    anotar.py         B: proponer_abono, proponer_gasto
  borradores.py       (base) firmar, abrir, acciones y filas
  guardar.py          (base) un guardador por tipo de acción, con los formularios de pantalla
  resumen.py          C: los puntos del día, el párrafo y lo que se pinta en Hoy
  instrucciones.py    (base) ya no dice "solo consulta"
  esfuerzo.py         (base) las tareas con plata caen en high
  vistas.py           (base) + confirmar
  management/commands/preparar_resumen.py   C
  models.py           (base) + ResumenDelDia y BorradorUsado
  templates/asistente/
    tarjetas/borrador.html, tarjetas/opciones.html   (base)
    _resumen_hoy.html                                C
  tests/              un archivo por carril
```

### 1.1 El borrador

Lo que el agente propone es un **borrador**: una lista de acciones que se guardan juntas, o
todas o ninguna. Ninguna herramienta escribe en la base; arman el borrador y la aplicación lo
muestra en una tarjeta con **Guardar** y **Corregir**.

```python
# asistente/contratos.py (nuevo)
@dataclass(frozen=True)
class Fila:                 # una cosa del borrador, como se ve en la tarjeta
    titulo: str             # "Pedido nuevo", "Abono de hoy", "Tela", "Tallas", "Gasto"
    detalle: str            # "Colegio Nuevo Amanecer · 30 uniformes de diario · ..."
    valor: int | None = None    # pesos, a la derecha
    aviso: str = ""         # en ámbar: lo que falta o no alcanza ("Te faltan 48 m")
```

```python
# asistente/borradores.py (base)
TIPOS = ("cliente", "pedido", "etapa", "abono", "gasto", "tela_pedido")   # T41 agrega más

def armar(ctx, acciones: list[dict], filas: list[Fila], titulo="Para guardar") -> Tarjeta
    # acciones: [{"tipo": "pedido", "datos": {...}}, ...]; una acción puede apuntar a una
    # anterior del mismo borrador con "@0", "@1" (el abono del pedido nuevo: "pedido": "@1").
    # La Tarjeta("borrador", ...) lleva en datos: filas, estado "pendiente" y la firma.
def abrir(firma, ctx) -> list[dict]   # lanza BorradorInvalido("vencido" | "ajeno" | "usado")
```

**La firma.** `django.core.signing.dumps` con `salt="asistente.borrador"` y comprimido. Lleva
el taller, la usuaria, una clave al azar de 16 bytes y las acciones. Se abre con
`max_age=BORRADOR_VIGENCIA` (2 horas). La firma vive en la tarjeta (en la sesión y en el campo
oculto del botón Guardar) y **nunca va a Claude**. Lo que ella confirma es exactamente lo que
se mostró, porque las acciones van dentro de la firma: no se pueden cambiar en el navegador.

**Un solo uso.** Al guardar se anota la clave del borrador dentro de la misma transacción. Un
borrador ya guardado, vencido, de otro taller o de otra usuaria se rechaza y no guarda nada.
La clave se anota en la tabla `BorradorUsado` (decisión 3 de la sección 6).

**Corregir.** No abre otra pantalla: pone el cursor en la caja del panel con el texto de ayuda
"Dime qué corrijo", y la siguiente pregunta lleva un campo oculto `corrige` con la clave de
ese borrador. Ella escribe ("no, son 35") y Claude arma un borrador nuevo; si llega, el que se
estaba corrigiendo pasa a "Reemplazado" (sin botones) y su firma deja de servir. Así nunca
quedan dos borradores vivos del mismo pedido, y un borrador pendiente de otra cosa (un abono
mientras anota un gasto) no se toca.

**Lo que ve Claude.** `Resultado.datos` de una herramienta `proponer_*` dice que el borrador
quedó listo, con sus filas en texto y lo que falta (`{"borrador": "listo", "filas": [...],
"avisos": [...]}`), sin la firma. Las instrucciones le dicen que **nunca diga que algo quedó
guardado**: le pide que revise y toque Guardar.

**Lo guardado se le cuenta a Claude** sin editar el historial: la vista guarda en la sesión
una nota ("La dueña guardó: pedido 123, abono de $ 500.000 al pedido 123") y el mensaje
`role: "system"` de la siguiente pregunta la lleva junto a la fecha y la pantalla. Así el
historial sigue siendo solo-agregar y la caché no se rompe.

### 1.2 Herramientas nuevas (`asistente/esquemas.py`)

Con las mismas reglas de la tanda 7: `strict`, todo en `required`, lo opcional anulable, la
lista ordenada por nombre. Los rangos van en `RANGOS`.

| Herramienta | Entrada | Qué arma | Se apoya en |
|---|---|---|---|
| `proponer_pedido` | `cliente: str`, `cliente_id: int\|null`, `tipo_cliente: enum\|null`, `detalle: str`, `cantidad: int`, `tallaje: enum[adulto, nino]`, `fecha_entrega: date`, `prenda: str\|null`, `total: int\|null`, `abono: int\|null`, `tela: str\|null`, `metros: str\|null` | Cliente (si es nuevo), pedido, abono inicial (si hay), tela del pedido (si hay) y la fila "Tallas" con el enlace | `NuevoPedidoForm`, `crear_pedido`, `calculos.cotizar`, `PrendaGuardada`, `FormularioAbono`, `calculos.tela_comprometida` |
| `proponer_abono` | `pedido_id: int\|null` (null = el de la pantalla), `cliente: str\|null`, `valor: int`, `fecha: date\|null` | Un abono a un pedido que ya existe, con "Falta" después del abono | `FormularioAbono`, `calculos.saldo` |
| `proponer_gasto` | `concepto: str`, `categoria: enum[telas, insumos, servicios, otros]`, `valor: int`, `fecha: date\|null`, `pedido_id: int\|null` | Un gasto | `FormularioGasto` |

Reglas de las tres:

- **Las mismas validaciones de la pantalla.** La herramienta llena el formulario de la
  pantalla con lo que mandó Claude y lo valida. Si no pasa, lanza `ErrorDeHerramienta` con el
  mensaje del formulario ("Elige la fecha de entrega") para que Claude pregunte o corrija.
- **Las cifras son de la aplicación.** Sin `total`, el total sale de `calculos.cotizar` con la
  prenda guardada y los valores por defecto del Cotizador (30 % de ganancia). Sin `metros`,
  salen de `prenda.metros × cantidad`. El "Falta" sale de `calculos.saldo`. Claude nunca
  escribe una cifra en la tarjeta.
- **Si no está seguro, pregunta.** Cliente, pedido, prenda o tela con dos o más coincidencias
  no arman borrador: devuelven `{"escoger": "cliente", "opciones": [{id, nombre}]}` y una
  `Tarjeta("opciones", ...)` con un chip por opción (los chips mandan esa opción como
  pregunta, con `data-asistente-sugerencia`, que ya existe). Un cliente que no existe es
  cliente nuevo; sin `tipo_cliente`, error para que pregunte el tipo.
- **Pedido o cliente de otro taller:** "No encontré ese pedido.", igual que en la tanda 7.
- **Nunca van a Claude** el WhatsApp, el token de tallas ni las notas (regla de la tanda 7).
- **Esfuerzo.** Las tres caen en `high` (tocan plata). `esfuerzo.py` suma las palabras
  "anot", "pag", "compr", "dej", "pedido" y `DE_PLATA` suma las tres herramientas.

### 1.3 Guardar (`asistente/guardar.py` y la vista `confirmar`)

```python
# asistente/guardar.py (base)
GUARDADORES = {"cliente": ..., "pedido": ..., "etapa": ..., "abono": ..., "gasto": ...,
               "tela_pedido": ...}
def guardar(ctx, acciones) -> list[Enlace]   # dentro de transaction.atomic; lanza NoSeGuardo
```

- Cada guardador **vuelve a validar** con el formulario de la pantalla (los datos pudieron
  cambiar en estas dos horas) y crea el registro con `por_asistente=True`. El pedido usa
  `crear_pedido`; el abono, `FormularioAbono` con `registrado_por`; el gasto,
  `FormularioGasto`; la etapa, la misma regla de `puede_mover_etapa`.
- Si cualquiera falla, no se guarda **nada** (`transaction.atomic`) y la tarjeta muestra en
  ámbar "No se guardó nada: <el mensaje del formulario>".
- Devuelve los enlaces a lo que creó ("Ver el pedido", con `reverse`).

| URL | Nombre | Devuelve |
|---|---|---|
| `POST asistente/confirmar/` | `asistente:confirmar` | La tarjeta del borrador otra vez, en su estado nuevo (`hx-swap="outerHTML"` sobre la tarjeta), y el aviso corto "Guardado." Siempre 200 |

Flujo de `confirmar`:

1. `@solo_duena`, `@require_POST`, `@never_cache` y 404 si `not disponible(request)`.
2. `borradores.abrir(firma, ctx)`. Vencido: "Este borrador venció. Pídemelo otra vez." Ajeno o
   usado: "Este borrador ya no sirve." Nada se guarda.
3. `guardar.guardar(ctx, acciones)` y la clave del borrador anotada como usada, en la misma
   transacción.
4. En la sesión: la tarjeta de ese turno pasa a estado `guardado` con sus enlaces (al recargar
   el panel se ve "Listo") y queda la nota para la siguiente pregunta (sección 1.1).
5. **No cuenta como pregunta** (decisión aprobada): no llama a `uso.reservar` ni a Claude.
6. Log `asistente`: taller, tipos de acción y resultado. Nunca los datos.

Sin JavaScript, el botón es un formulario normal que vuelve a `asistente:panel`.

**La tarjeta (`tarjetas/borrador.html`)** tiene cuatro estados: `pendiente` (insignia ámbar
"Sin guardar", Corregir y Guardar), `guardado` (insignia verde "Listo", enlaces a lo creado),
`reemplazado` (insignia gris, sin botones) y `fallido` (el aviso ámbar y Guardar otra vez, si
el error se puede arreglar sin cambiar el borrador). Cada fila: título en negrita, detalle en
gris, valor en pesos a la derecha y el aviso ámbar debajo si lo hay.

**JavaScript (sección 14 de `static/js/app.js`):** Guardar lleva `hx-post`,
`hx-target="closest .borrador"`, `hx-swap="outerHTML"` y `hx-disabled-elt="this"` (dos toques
seguidos no mandan dos veces). `[data-asistente-corregir]` pone el cursor en la caja con el
texto de ayuda "Dime qué corrijo".

### 1.4 Modelo de datos (los cuatro cambios de `docs/12-agente.md` y uno más)

| Cambio | Dónde | Detalle |
|---|---|---|
| `TelaPedido` | `telas/models.py` | `pedido` (FK, CASCADE, `related_name="telas"`), `tela` (FK, CASCADE), `metros` (Decimal 8,2, mayor que 0). Único por (pedido, tela). `ruta_taller = "pedido__taller"`; `clean` revisa que tela y pedido sean del mismo taller |
| `MovimientoTela.pedido` | `telas/models.py` | FK opcional a `pedidos.Pedido`, `SET_NULL`, `related_name="movimientos_de_tela"`. Esta tanda no lo llena (lo usa T41) |
| `por_asistente` | `Pedido`, `Abono`, `Gasto`, `MovimientoTela` | `BooleanField(default=False)` |
| `ResumenDelDia` | `asistente/models.py` | `ModeloDeTaller` con `fecha`, `texto` y `creado`. Único por (taller, fecha). Admin de solo lectura |
| `BorradorUsado` (decisión 3) | `asistente/models.py` | `ModeloDeTaller` con `clave` (32, única) y `creado`. Se anota al guardar, dentro de la misma transacción |

Tres migraciones nuevas (pedidos, finanzas y telas) y una del asistente, todas del
coordinador. Ninguna borra datos. `cargar_ejemplos` agrega la tela del pedido de El Fogón (22 m
de piqué y 16 m de dril), como en `diseno/pedido.html`. Como ya está en corte, no aparta tela, y
el ejemplo de las 10:30 da lo mismo que la maqueta (66 m de dril, hay 18, faltan 48).

**Cálculos nuevos en `pedidos/calculos.py`** (base):

```python
def tela_comprometida(taller, sin_pedido=None) -> dict[int, Decimal]
    # metros de TelaPedido de los pedidos Confirmados, por tela (sin contar `sin_pedido`)
def falta_tela(tela, metros, comprometida) -> Decimal
    # cuánto falta para cubrir `metros` más lo comprometido; Decimal("0") si alcanza
def telas_que_no_alcanzan(taller) -> list[(tela, comprometidos, faltan)]
```

La lista de compras es de T42 y no entra en esta tanda.

**Cronología (`pedidos/cronologia.py`)**: `Evento` suma `por_asistente: bool`. El pedido
creado y los abonos guardados con el agente llevan debajo, en gris y con la esfera pequeña,
"Lo anotó el asistente" (`pedidos/_cronologia.html`).

### 1.5 El resumen de la mañana

```python
# asistente/resumen.py (carril C)
@dataclass(frozen=True)
class PuntoDelDia:
    tipo: str        # entrega | atraso | cobro | tela | tallas
    texto: str       # "Ferretería La Esquina · Debe $ 480.000 desde hace 20 días"
    etiqueta: dict | None   # {"texto", "color"}: rojo solo para atraso y deuda vencida
    boton: Enlace | None    # "Cobrar" (WhatsApp), "Pedir tallas", "Ver telas", "Ver pedido"
    cifras: tuple[int, ...] # los pesos que el párrafo puede mencionar

def puntos_del_dia(taller, hoy) -> list[PuntoDelDia]   # todo sale de pedidos/calculos.py
def escribir(taller, hoy, cliente) -> ResumenDelDia | None   # una llamada a Claude, sin herramientas
def para_hoy(request) -> dict | None   # lo que pinta Hoy; None si el asistente no está disponible
```

- **Qué entra:** entregas de hoy y de mañana, atrasados, a quién cobrar (`quien_te_debe`, con
  "vencida" en rojo), telas que no alcanzan (`telas_que_no_alcanzan`) o están bajas
  (`telas_bajas`) y pedidos sin entregar (Confirmados, en corte o en confección) con el enlace
  abierto y menos tallas que personas.
- **El párrafo lo escribe Claude** con un `system` propio (`INSTRUCCIONES_RESUMEN`, fijo), sin
  herramientas, esfuerzo `medium`, a partir de los puntos en JSON. Se revisa como
  `preparar_mensaje`: **toda cifra `$ n.nnn` del texto debe estar en las `cifras` de algún
  punto**. Si no, no se guarda el párrafo y queda en el registro.
- **Los tokens se anotan** en `UsoAsistente` (con `uso.anotar`), pero **no cuenta como
  pregunta**.
- **Lo que va a Anthropic:** los puntos, con nombres de clientes y detalle de pedidos, como en
  las consultas. Nunca teléfonos, notas, tallas con nombre ni el token.
- **El comando:** `uv run python manage.py preparar_resumen [--taller ID] [--de-nuevo]`. Recorre
  los talleres con el asistente prendido; si ya existe el de hoy, no lo repite (salvo
  `--de-nuevo`). Sin clave no hace nada y lo dice.
- **La tarea de la madrugada:** `herramientas/servidor/cron-resumen.txt`, a las 5:00 (hora de
  Bogotá), como la copia de seguridad. La instala David.
- **En Hoy:** arriba, después del saludo y antes de la caja grande. Una tarjeta con la esfera,
  "Tu resumen de hoy", la hora en que se preparó, el párrafo guardado y debajo las filas
  (`fila--compacta`) de cobros, tela y tallas, **calculadas al abrir Hoy** (siempre frescas),
  cada una con su botón. Sin resumen de hoy (la tarea no corrió o falló), se ven solo las
  filas. Sin nada pendiente, la tarjeta no sale. Con el asistente apagado, Hoy queda igual
  que hoy.
- Los botones de WhatsApp usan los textos que ya existen (`pedidos/mensajes.py`: cobro y
  pedir tallas). No llaman a Claude.

### 1.6 Cómo quedó la base (ajustes del coordinador en T38)

Lo que cambió respecto a lo de arriba al construir la base. **Manda esto si algo choca.**

- **Sin `null` en las herramientas nuevas.** La prueba corta con la clave dio 400: con `strict`
  la API acepta como mucho **16 parámetros anulables sumando todas las herramientas**, y con
  las nuevas había 26. Las `proponer_*` dicen "no hay" con `0` (ids, total, abono) o `""`
  (textos, `tipo_cliente`, `metros`, `fecha`). `herramientas.validar()` los convierte en `None`
  (`VACIOS`) y las fechas de texto en `date` (`FECHAS_DE_TEXTO`): **la herramienta recibe
  `None` como dice la tabla de 1.2**. `test_contratos.py` vigila que no se pase de 16.
- **No hay acción `cliente`.** El cliente va dentro de la acción `pedido` (`cliente`,
  `cliente_id`, `tipo`): el guardador usa `crear_pedido`, que lo busca por nombre o lo crea, como
  la pantalla. `TIPOS = ("pedido", "etapa", "abono", "gasto", "tela_pedido")`.
- **Datos de cada acción** (lo que guarda `asistente/guardar.py`):
  - `pedido`: `cliente`, `cliente_id` (o None), `tipo`, `detalle`, `cantidad`, `tallaje`,
    `fecha_entrega` (ISO), `total`.
  - `etapa`: `pedido` ("@0" o id), `estado`. El pedido con abono lleva `etapa` "confirmado"
    después del `pedido` (decisión 4).
  - `abono`: `pedido`, `valor`, `fecha` (ISO o None = hoy).
  - `gasto`: `concepto`, `categoria`, `valor`, `fecha` (ISO o None), `pedido` (id o None).
  - `tela_pedido`: `pedido`, `tela` (id), `metros` (texto, "66.00").
- **Ayudas de `asistente/borradores.py` para los carriles:** `resultado(ctx, acciones, filas,
  revisado)` devuelve el `Resultado` con la tarjeta y, para Claude, las filas sin firma;
  `opciones(que, [(id, nombre)], revisado)` devuelve el "¿a cuál?" sin borrador.
- **"Reemplazado"** se decide en la sesión: la pregunta trae `corrige` (la clave) y, si su
  respuesta trae un borrador nuevo, el viejo queda reemplazado y `confirmar` ya no lo guarda.
  `BorradorUsado` cubre el doble toque.
- **`confirmar` solo guarda un borrador que esté en la conversación** de esa sesión (busca la
  tarjeta por su firma); una firma válida que no se le mostró no sirve.
- **La nota de lo guardado** (`conv["notas"]`) va en el `system` de la siguiente pregunta
  (`conversacion.preguntar(..., nota=...)`) y se borra cuando esa pregunta sale bien.
- **Esfuerzo:** "pedido" no cuenta como palabra de plata ("¿qué pedidos están atrasados?" sigue
  en `medium`); sí "anot", "pag", "compr", "dej", "encarg", "mil", "nuevo pedido" y "pedido
  nuevo".
- **Lo que mostró la prueba corta (15 de noviembre de 2026,** `herramientas/humo_agente.py`,
  5 llamadas, US$ 0,10 en total):
  - con el pedido de las 10:30, Claude pidió `buscar_clientes`, `cotizar` y `telas` juntas, y
    después `proponer_pedido` con los vacíos bien puestos (`total: 0`, `metros: ""`). Dijo
    "Revísalo y toca Guardar" y comentó la tela que falta. Tres llamadas, unos 6,5 centavos (la
    primera escribe la caché);
  - la nota de lo guardado en el `system` de la siguiente pregunta se acepta y Claude la usa;
  - sin herramientas (como el resumen) contesta un párrafo corto sin 400.

## 2. Base del coordinador (T38, sin carriles)

**T38. Base: documentos, maqueta, modelo, cálculos, borrador firmado y `confirmar`**

1. **Documentos:** `docs/01-plan.md` (etapa 3 alrededor del agente), `docs/02-modelo-de-datos.md`
   (sección 1.4), `docs/03-pantallas.md` (resumen en Hoy, tarjeta de borrador, cronología y "Tela del
   pedido"), `docs/04-permisos.md` (tabla del agente),
   `docs/06-pruebas.md`, `docs/08-diseno.md` (piezas nuevas), `docs/09-plan-de-construccion.md`
   (tanda 8), `docs/10-asistente.md` (ya no es "solo consulta"), `docs/11-plan-tanda-7.md`
   (la sección 7 apunta a `docs/12-agente.md`), `CLAUDE.md` (lista de documentos),
   `docs/guia-publicacion.md` y `herramientas/servidor/cron-resumen.txt`.
2. **Maqueta:** `diseno/asistente-agente.html` (borradores), `diseno/hoy-agente.html`
   (resumen), `diseno/pedido.html` (cronología y "Tela del pedido"), `diseno/asistente.html`
   (sin la insignia, nota nueva) y `diseno/index.html`; estilos en la sección 7 de
   `diseno/estilo.css`. **Aprobadas por David el 15 de noviembre de 2026.**
3. **Modelo y migraciones** (sección 1.4), admin de `ResumenDelDia`, `tests/fabricas.py`
   (`crear_tela_pedido`, `crear_resumen`) y `tests/test_aislamiento.py` (los modelos nuevos).
4. **Cálculos** `tela_comprometida`, `falta_tela`, `telas_que_no_alcanzan`, con pruebas en
   `pedidos/tests/test_calculos.py`.
5. **Cronología** con "Lo anotó el asistente" y la tarjeta "Tela del pedido" (solo para ver)
   en `pedidos/templates/pedidos/detalle.html`.
6. **Contratos y esquemas:** `Fila`; los tres esquemas nuevos; `REGISTRO` con stubs;
   `DE_PLATA` y `RANGOS`; `test_contratos.py` al día.
7. **`borradores.py`, `guardar.py` y la vista `confirmar`**, con la URL, las dos tarjetas
   (`borrador`, `opciones`), los estilos copiados idénticos a `static/css/app.css`, la sección
   14 de `app.js`, y sus pruebas (`asistente/tests/test_borradores.py`,
   `test_confirmar.py`).
8. **`instrucciones.py`** (puede proponer, nunca dice que guardó, si duda pregunta) y
   **`esfuerzo.py`**; el panel sin la insignia y con la nota nueva (`_panel.html`).
9. **Cliente sin herramientas:** `ClienteAnthropic.enviar` con `herramientas=[]` no manda
   `tools` ni `tool_choice`; `falso.py` lo acepta.
10. **Hoy:** `pedidos/vistas/hoy.py` pasa `resumen = asistente.resumen.para_hoy(request)`
    (stub que devuelve None) y `pedidos/hoy.html` incluye `asistente/_resumen_hoy.html`
    (vacío) arriba de la caja grande.
11. **Prueba corta con la clave** (`herramientas/humo_asistente.py`): un borrador de pedido de
    punta a punta (proponer, la nota de lo guardado en el `system` de la siguiente pregunta)
    y un resumen sin herramientas, para confirmar que no hay 400 antes de lanzar los carriles.

## 3. Carriles (subagentes Opus 5.5, cada uno en su worktree)

Cada carril escribe su bitácora (`docs/bitacora/TNN.md`) y no toca archivos congelados (los de
la sección 1 marcados así, `borradores.py`, `guardar.py`, `vistas.py`, `models.py`,
`instrucciones.py`, `esfuerzo.py`, ni los de `CLAUDE.md`).

| Carril | Tarea | Archivos propios |
|---|---|---|
| A. Pedido nuevo | T39 | `herramientas/pedido_nuevo.py`; `tests/test_proponer_pedido.py` |
| B. Abonos y gastos | T40 | `herramientas/anotar.py`; `tests/test_proponer_abono_gasto.py` |
| C. Resumen | T43 | `resumen.py`; `management/commands/preparar_resumen.py`; `_resumen_hoy.html`; `tests/test_resumen.py` |

**T39 (A). `proponer_pedido`.** Pruebas: cliente que ya existe (con otras mayúsculas) no crea
otro; cliente nuevo sin tipo da error que pide el tipo; dos clientes parecidos dan `opciones`
sin borrador; el total sin `total` es igual al de `FormularioCotizacion` con esa prenda y 30 %
(y al que muestra el Cotizador); con `total` manda el de ella; fecha o cantidad que la
pantalla no acepta dan el mismo mensaje que la pantalla; la tela que no alcanza sale en el
aviso con los metros de `falta_tela`; dos telas parecidas dan `opciones`; **sin tocar Guardar
no se crea nada** (cuenta de registros igual); al confirmar se crean cliente, pedido, abono y
tela juntos con `por_asistente=True`, y si el abono falla no queda ni el pedido; la cronología
muestra "Lo anotó el asistente"; `Resultado.datos` no trae la firma, ni WhatsApp, ni token;
aislamiento: el cliente de otro taller con el mismo nombre no se toca.

**T40 (B). `proponer_abono` y `proponer_gasto`.** Pruebas: `pedido_id=None` usa el pedido en
pantalla; por nombre de cliente con un solo pedido con saldo lo escoge; con dos, `opciones`;
el "Falta" es `calculos.saldo` menos el abono, y después de guardar coincide con la tarjeta
Pagos del pedido; valor 0, negativo o con decimales da el mensaje de la pantalla; el gasto
guardado sale en el Resumen del mes con el mismo total que si se anotara en la pantalla;
gasto con pedido de otro taller, no encontrado; sin tocar Guardar no cambia nada; aislamiento.

**T43 (C). Resumen de la mañana.** Pruebas: con `cargar_ejemplos`, los cobros coinciden con
"Quién te debe" de Hoy y la deuda vencida va en rojo; la tela que no alcanza coincide con
`telas_que_no_alcanzan`; un párrafo con una cifra que no está en los puntos no se guarda; el
comando no repite el resumen del día y con `--de-nuevo` sí; sin clave no llama y lo dice; un
taller con el asistente apagado no recibe resumen; un taller nunca ve el resumen ni los puntos
de otro; sin resumen guardado, Hoy muestra solo las filas; los tokens se anotan y las
preguntas no suben; lo que se manda al cliente falso no trae teléfonos, notas ni tallas con
nombre; Hoy en 390 px no se desborda.

## 4. Lista del revisor

Todo lo de la tanda 7 (sección 4 de `docs/11-plan-tanda-7.md`), y además:

- Ninguna herramienta `proponer_*` escribe en la base: solo `asistente.guardar`, llamado desde
  `confirmar`.
- No existe ninguna herramienta ni guardador que borre.
- Las validaciones salen de los formularios de pantalla; ninguna regla copiada a mano.
- Todo guardado va en `transaction.atomic`: o todo, o nada.
- La firma nunca aparece en `Resultado.datos` ni en lo que se manda al cliente falso.
- Toda cifra de una tarjeta o del resumen sale de `pedidos/calculos.py`.
- `confirmar` no llama a Claude ni gasta preguntas.
- Lo guardado con el agente lleva `por_asistente=True`; lo de las pantallas, `False`.

## 5. Unión y cierre de la tanda

Orden de unión: A, B, C, con `uv run pytest` después de cada uno.

**Cierre (coordinador), como en todas las tandas:**

- `asistente/tests/test_punta_a_punta.py` suma tres casos sobre `cargar_ejemplos`: el pedido de
  las 10:30 (proponer, guardar, ver el pedido con su abono y su tela), un abono desde la
  pantalla del pedido y el resumen en Hoy.
- `herramientas/capturas.py`: `PANTALLAS[8]` (Hoy con el resumen, el panel con un borrador
  pendiente y uno guardado, el pedido con la cronología), en 1280 y 390 px. Capturas en
  `docs/capturas/tanda-8/` y resumen en `docs/bitacora/tanda-8.md`.
- **Prueba real con la clave** (a mano, con `herramientas/probar_asistente.py`): 10 tareas
  (4 pedidos, 3 abonos, 3 gastos) y 3 resúmenes. Por cada una: si el borrador quedó bien,
  vueltas, segundos y costo. La tabla va en la bitácora de la tanda. Esta es la parte corta de
  T45; el resto de T45 (con T41, T42 y T44) queda para después.

## 6. Decisiones

Aprobadas por David (15 de noviembre de 2026, `docs/12-agente.md`): el agente propone y ella
guarda con un toque; los cuatro cambios al modelo; el resumen con una tarea programada; tocar
Guardar no cuenta como pregunta; empezar por T38, T39, T40 y T43.

Decididas por David al aprobar la maqueta (15 de noviembre de 2026):

1. **Las piezas nuevas de la maqueta, aprobadas** tal como están (sección 2, paso 2).
2. **La tela va en el borrador del pedido**, y el pedido muestra la tarjeta "Tela del pedido"
   **solo para ver** (qué tela, cuántos metros, si alcanza). Corregirla desde la pantalla y la
   lista de compras siguen en T42.
3. **Un quinto cambio al modelo: `BorradorUsado`** (taller, clave única, fecha). Al guardar un
   borrador se anota su clave en la misma transacción; así dos toques casi al mismo tiempo no
   guardan dos veces.
4. **El pedido con abono nace Confirmado.** El borrador lo dice en la fila del pedido
   ("Confirmado, porque dejó abono") y al guardar se aplica la misma regla de "Pasar a
   Confirmado" de la pantalla. Sin abono, nace Cotizado, como en "Nuevo pedido".

## 7. Lo que queda para después (sin construir en esta tanda)

Se arman cuando ella haya probado lo mínimo y diga qué más quiere (paso 2 de
`docs/12-agente.md`):

- **T41.** Proponer etapa, "Usé" y "Entró", y "Descontar tela" al pasar a Corte, también desde
  la pantalla del pedido. Llena `MovimientoTela.pedido`.
- **T42.** Inventario: corregir la tela del pedido desde la pantalla y la lista de compras.
- **T44.** Avisos con la acción lista (cobro quieto, entrega cerca, tela que no alcanza,
  tallas que faltan).
- **T45.** Integración completa y prueba real de todo el agente.

## 8. Riesgos

- **El mensaje `system` con la nota de lo guardado** debe aceptarse como en la tanda 7; lo
  confirma la prueba corta (T38, paso 11) antes de los carriles.
- **Claude puede proponer con datos que ella no dijo** (inventar la fecha). Las instrucciones
  le piden preguntar lo que falta, y la tarjeta muestra todo antes de guardar. La prueba real
  lo mide.
- **Dos pestañas a la vez:** cada una ve sus borradores; la firma de un solo uso evita guardar
  dos veces el mismo.
- **El resumen depende del servidor:** si la tarea de la madrugada no corre, Hoy muestra las
  filas sin el párrafo. Nada se rompe.
- **Costo:** se mide en la prueba real; lo estimado está en `docs/12-agente.md`.
