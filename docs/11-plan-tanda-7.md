# Plan de la tanda 7: asistente del taller

Plan hecho con Claude Fable 5.2 (solo lectura del repo) el 14 de noviembre de 2026, revisado
por el coordinador y aprobado por David. Qué se construye y por qué está en
`docs/10-asistente.md`. Las reglas de trabajo con varios agentes son las de
`docs/09-plan-de-construccion.md` ("Reglas para los agentes").

Rama: `tanda-7-asistente`, sacada de `bot-propuesta`.

## 0. Lo que choca con el repo actual (y cómo se resuelve)

1. `docs/08-diseno.md` (sección "Lo que se tomó de Shopify y lo que no") dice que no se tomó
   el asistente: se corrige en T25.
2. Los estilos de la maqueta están en un `<style>` dentro de `diseno/asistente.html`.
   `tests/test_base_visual.py::test_la_hoja_de_estilos_de_la_aplicacion_copia_la_del_diseno`
   exige que `static/css/app.css` contenga `diseno/estilo.css` tal cual: los estilos pasan
   primero a `diseno/estilo.css` y se copian idénticos a `app.css`.
3. La maqueta no trae varias piezas decididas: tarjeta de mensaje de WhatsApp, tarjeta de
   cotización, aviso ámbar, estado de límite alcanzado y tarjeta de Mi taller. Se maquetan con
   piezas existentes en T25 y **David las aprueba antes de lanzar los carriles**.
4. Cada pantalla llena `{% block acciones %}` a su manera. Para que el botón "Asistente" quede
   a la izquierda del principal en todas, `templates/base.html` necesita un bloque nuevo
   `acciones_antes`.
5. No hay pantalla de un cliente: el contexto "este cliente" es el cliente del pedido abierto
   o el `?q=` de Clientes.
6. `config/settings/base.py` carga `.env` también en pytest. Con la clave real en `.env`, las
   pruebas la verían: se anula en `config/settings/pruebas.py` y la clave se pasa explícita al
   cliente de Anthropic.
7. El servidor corta a los 60 s (`herramientas/servidor/taller.service`: 3 workers sync,
   `--timeout 60`; NGINX `proxy_read_timeout 60s`). Se sube a 120 s y Gunicorn pasa a
   `gthread`. Lo aplica David al publicar; T25 actualiza `docs/guia-publicacion.md` y
   `herramientas/servidor/`.
8. Los gastos por rango de fechas y por categoría no están en `pedidos/calculos.py` (solo
   `gastado_en` por mes): los agrega el coordinador en T25.
9. `.env.example` ya tiene `ANTHROPIC_API_KEY=`: solo cambia el comentario.

## 1. Arquitectura y contratos

App nueva `asistente/`. El coordinador deja en la base los contratos, los esquemas y los
stubs; cada carril rellena solo sus archivos.

```
asistente/
  contratos.py        (congelado) Contexto, Resultado, Tarjeta, Enlace, Uso, ErrorDeHerramienta
  esquemas.py         (congelado) esquema JSON de las 10 herramientas, lista ordenada por nombre
  herramientas/
    __init__.py       (congelado) REGISTRO, ejecutar(), DE_PLATA
    pedidos.py        A: buscar_pedidos, ver_pedido, entregas
    plata.py          A: quien_debe, cuentas_del_mes, gastos
    catalogo.py       A: telas, buscar_clientes
    mensajes.py       C: preparar_mensaje
    cotizar.py        C: cotizar
  instrucciones.py    B: el system prompt (texto fijo, sin fecha ni taller)
  cliente.py          B: ClienteAnthropic, obtener_cliente()
  falso.py            (congelado, base) ClienteFalso y ayudas de guion
  conversacion.py     B: preguntar() con el ciclo de herramientas
  pagina.py           B: contexto de pantalla validado por taller
  esfuerzo.py         B: regla medium/high
  uso.py              D: cupo, reservar, devolver, anotar, costo_usd
  disponibilidad.py   (base) disponible(request)
  vistas.py           D
  urls.py             (congelado)
  models.py, admin.py, migrations/   (base)
  templates/asistente/  _boton, _panel, _conversacion, _turno, _uso_aviso, _uso_mi_taller,
                        pagina (D); tarjetas/<tipo>.html (A y C, un archivo por tipo)
  tests/              un archivo por carril
```

### 1.1 Contratos (`asistente/contratos.py`)

```python
@dataclass(frozen=True)
class Contexto:
    taller: Taller
    usuaria: Usuario
    hoy: date                      # timezone.localdate()
    pedido_actual: Pedido | None   # ya validado por taller, o None
    url_base: str                  # request.build_absolute_uri("/"), para el enlace de tallas

@dataclass(frozen=True)
class Enlace:
    texto: str
    url: str                       # siempre armada con reverse()

@dataclass(frozen=True)
class Tarjeta:
    tipo: str                      # plantilla asistente/tarjetas/{tipo}.html
    titulo: str
    datos: dict                    # serializable a JSON

@dataclass(frozen=True)
class Resultado:
    datos: dict                    # lo ÚNICO que lee Claude. Sin teléfonos, token, notas ni tallas con nombre
    revisado: str                  # "Revisé los saldos de tus pedidos confirmados"
    tarjeta: Tarjeta | None = None
    enlace: Enlace | None = None

@dataclass(frozen=True)
class Uso:
    entrada: int = 0
    salida: int = 0
    cache_escritura: int = 0
    cache_lectura: int = 0

class ErrorDeHerramienta(Exception): ...   # su texto va a Claude con is_error=True
```

Firma de toda herramienta: `def nombre(ctx: Contexto, **entrada) -> Resultado`.

Reglas de `datos`:

- Plata en enteros COP. Metros como texto decimal (`"6.50"`), nunca float. Fechas ISO.
- Listas con tope (20 pedidos, 30 gastos), con `total` y `mostrados`.
- Los ids de pedido y cliente sí van, para encadenar herramientas. Un id que no es del taller
  lanza `ErrorDeHerramienta("No encontré ese pedido.")`, igual que un 404.
- Nunca van: WhatsApp, `token_tallas`, `Cliente.notas`, nombres ni medidas de las tallas.

`herramientas.ejecutar(nombre, entrada, ctx) -> Resultado` valida tipos y rangos en código
(`strict` no admite `minimum`/`maximum`). Nombre desconocido, `NotImplementedError` y errores
de validación se convierten en `ErrorDeHerramienta`.

### 1.2 Herramientas y esquemas (`asistente/esquemas.py`)

Todas con `strict: true`, `additionalProperties: false` y todas las propiedades en `required`;
lo opcional es anulable (`["string","null"]`).

| Herramienta | Entrada | `datos` que devuelve | Se apoya en | Tarjeta / enlace |
|---|---|---|---|---|
| `buscar_pedidos` | `texto: str\|null`, `filtro: enum[todos, produccion, semana, atrasados, saldo, entregados, cotizados]\|null`, `entrega_desde: date\|null`, `entrega_hasta: date\|null` | `{total, mostrados, pedidos:[{id, cliente, detalle, cantidad, fecha_entrega, estado, encargada, dias_para_entrega, atrasado, total, abonado, saldo}]}` | `con_cuentas`, `filtrar_pedidos`, `coincide`, `ordenar_pedidos` | `pedidos` / `pedidos:lista?filtro=&q=` |
| `ver_pedido` | `pedido_id: int\|null` (null = el de la pantalla) | pedido, `pagos:{total, abonado, saldo, abonos:[{fecha, valor}]}`, `tallas:{recibidas, esperadas, por_talla}`, `materiales:{comprados, total, faltan}`, `cliente:{id, nombre, tipo, tiene_whatsapp}`, `enlace_tallas_abierto` | `saldo`, `abonado`, `tallas_por_talla`, `tallas_recibidas`, `materiales_comprados` | `pedido` / `pedidos:detalle` |
| `entregas` | `desde: date`, `hasta: date` | `{entregas:[…], atrasados:[…]}` | `pedidos_en_produccion`, `pedidos_atrasados` | `entregas` / calendario |
| `quien_debe` | ninguna | `{por_cobrar, deudores:[{cliente_id, cliente, saldo, vencida}]}` | `quien_te_debe`, `por_cobrar` | `quien_debe` / `lista?filtro=saldo` |
| `cuentas_del_mes` | `anio: int\|null`, `mes: int\|null` | `{anio, mes, vendido, cobrado, gastado, te_quedo, ventas_por_tipo}` | `resumen_del_mes`, `ventas_por_tipo` | `cuentas` / `finanzas:resumen?mes=` |
| `gastos` | `desde: date`, `hasta: date`, `categoria: enum[telas, insumos, servicios, otros]\|null` | `{total, por_categoria:[{categoria, total}], gastos:[{fecha, concepto, categoria, valor}]}` | `gastos_entre`, `gastos_por_categoria` (nuevos en `calculos.py`) | `gastos` / resumen |
| `telas` | `solo_bajas: bool` | `{cantidad, metros, telas:[{nombre, metros, minimo, baja}]}` | `telas_en_orden`, `tela_baja`, `resumen_de_telas` | `telas` / `telas:inicio` |
| `buscar_clientes` | `texto: str\|null`, `tipo: enum[comparsa, empresa, colegio, particular]\|null` | `{clientes:[{id, nombre, tipo, pedidos, ha_comprado, debe, cotizacion_abierta, tiene_whatsapp}]}` | `cuentas_de_clientes`, `coincide` | `clientes` / `clientes?q=` |
| `preparar_mensaje` | `pedido_id: int\|null`, `cliente_id: int\|null`, `motivo: enum[cobro, listo, tallas, otro]`, `texto: str` | `{listo: true, tiene_whatsapp: bool}` | `mensajes.enlace_whatsapp`, `calculos.saldo` | `mensaje` (texto final, `enlace_whatsapp`, cliente) |
| `cotizar` | `prenda: str`, `cantidad: int`, `ganancia_pct: int\|null`, `abono_pct: int\|null` | `{prenda, cantidad, costo, precio_unidad, total, abono, ganancia, metros_totales}`, o `{opciones:[nombres]}` si hay varias | `PrendaGuardada.objects.del_taller`, `calculos.cotizar`; valores por defecto de `FormularioCotizacion` (30 y 50) | `cotizacion` / `cotizador:calcular?guardada=&cantidad=&ganancia=&abono=&tipo=empresa` |

Reglas de `preparar_mensaje`:

- El texto lo escribe Claude; la tarjeta lo muestra escapado. Tope de 700 caracteres.
- El número solo entra en `Tarjeta.datos["enlace_whatsapp"]`, que vive en la sesión y nunca va
  en `Resultado.datos`.
- Sin número que sirva, el enlace queda vacío y la tarjeta ofrece "Copiar" (`data-copiar`
  existente).
- Para `tallas`, Claude escribe el marcador literal `[ENLACE]` y la app lo cambia por la URL
  pública. El token nunca va a Anthropic. Con el enlace cerrado, devuelve error.
- Toda cifra `$ n.nnn` del texto debe coincidir con el total, lo abonado o el saldo del
  pedido. Si no, `ErrorDeHerramienta("El saldo es 480000, corrige la cifra")`.

### 1.3 Cliente de Claude y cliente falso

```python
# asistente/cliente.py
@dataclass(frozen=True)
class RespuestaClaude:
    contenido: list[dict]   # [b.to_dict(mode="json") for b in response.content], thinking incluido, sin tocar
    stop_reason: str
    uso: Uso
    modelo: str             # response.model (puede ser el de respaldo)
    id_peticion: str

class ClienteClaude(Protocol):
    def enviar(self, *, sistema: list[dict], herramientas: list[dict],
               mensajes: list[dict], esfuerzo: str, sin_herramientas: bool = False) -> RespuestaClaude: ...

def obtener_cliente() -> ClienteClaude | None   # None sin clave; clase desde settings.ASISTENTE_CLIENTE
```

`ClienteAnthropic.enviar`:

- `anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=45.0, max_retries=1)`.
- `client.beta.messages.create` con `model=settings.ASISTENTE_MODELO` (`claude-opus-5-5`),
  `max_tokens=8000`, `system=sistema`, `tools=herramientas`, `messages=mensajes`,
  `output_config={"effort": esfuerzo}`, `cache_control={"type": "ephemeral"}`.
- Respaldo del servidor encendido: `betas=["server-side-fallback-2026-07-01"]` y
  `fallbacks="default"`, con interruptor `ASISTENTE_FALLBACKS`. Si la beta diera 400, se apaga
  el interruptor y se usa `client.messages.create`.
- `tool_choice` `auto`, o `none` cuando `sin_herramientas`. **No** se envía `thinking`, ni
  `temperature`, ni `tool_choice` `any`/`tool` (en Opus 5.5 dan 400).
- `sistema` = `[{"type": "text", "text": INSTRUCCIONES, "cache_control": {"type": "ephemeral"}}]`.

```python
# asistente/falso.py
class ClienteFalso:
    def __init__(self, guion: list[RespuestaClaude | Exception]): self.llamadas = []
    def enviar(self, **kw): self.llamadas.append(copy.deepcopy(kw)); ...   # siguiente del guion
def texto(t, **uso) -> RespuestaClaude
def usa(*llamadas, pensamiento=True, **uso) -> RespuestaClaude   # llamadas = (nombre, entrada, id)
class ClienteProhibido:   # el de pruebas.py: enviar() lanza AssertionError
```

### 1.4 El ciclo (`asistente/conversacion.py`)

```python
@dataclass(frozen=True)
class Respuesta:
    estado: str                 # ok | error | rechazo | cortado
    texto: str                  # texto de Claude o el mensaje amable; SIEMPRE se muestra escapado
    resultados: list[Resultado]
    uso: Uso                    # suma de todas las llamadas, también si falló
    mensajes: list[dict]        # historial nuevo; si no fue ok, el mismo que entró
    cobrada: bool               # False si ninguna llamada llegó a responder

def preguntar(*, cliente, ctx, mensajes, pregunta, pagina, herramientas=None) -> Respuesta
```

Pasos:

1. Agrega `{"role": "user", "content": pregunta}`.
2. Agrega `{"role": "system", "content": contexto}` (fecha de hoy, nombre del taller, pantalla
   actual). Queda en el historial; nunca se reescribe.
3. **Decide el esfuerzo una sola vez para toda la pregunta** con `esfuerzo.elegir(pregunta)`,
   y lo usa en todas sus vueltas. (Ajuste del coordinador: cambiarlo a mitad de una pregunta
   invalida la caché de los mensajes.)
4. Hasta 5 vueltas de `cliente.enviar(...)`.
5. Revisa `stop_reason` antes de leer el contenido: `refusal` da `rechazo`, `max_tokens` da
   `cortado`.
6. Agrega `{"role": "assistant", "content": r.contenido}` completo, con los bloques thinking
   sin tocar.
7. Con `tool_use`, ejecuta todas las llamadas y devuelve todos los `tool_result` en **un solo**
   mensaje user, con `is_error: true` en los que fallen. Contenido:
   `json.dumps(datos, ensure_ascii=False, sort_keys=True)`.
8. Si tras la 5.ª vuelta sigue pidiendo herramientas: llamada final con
   `sin_herramientas=True` y un bloque de texto después de los `tool_result` ("Contesta con lo
   que ya tienes").
9. Plazo total de 50 s, revisado antes de cada llamada.

Errores, en este orden: `RateLimitError`, `APIStatusError`, `APIConnectionError`, todos con
"No pude contestar ahora. Intenta de nuevo en un rato." Un `BadRequestError` (historial que ya
no vale) pide a la vista borrar la conversación.

**Esfuerzo (`esfuerzo.py`).** `high` si la pregunta, sin tildes, contiene palabras de plata
(debe, saldo, cobr, gast, vend, cotiz, cuanto, precio, abono); si no, `medium`. Se calcula una
vez por pregunta. `DE_PLATA = {quien_debe, cuentas_del_mes, gastos, cotizar}` se usa en las
pruebas para comprobar que las preguntas típicas de esas herramientas caen en `high`.

**Pantalla (`pagina.py`).** `contexto_de_pagina(taller, ruta) -> (texto, pedido | None)` con
`django.urls.resolve`:

- `pedidos:detalle` busca con `Pedido.objects.del_taller(taller).filter(pk=…).first()`. Si es
  de otro taller o no existe, se ignora sin decir nada.
- `finanzas:resumen?mes=`, `pedidos:lista?filtro=&q=` y `pedidos:clientes?q=` dan una frase.
- Lo demás da el nombre de la sección.

**Sesión.**

```python
request.session["asistente"] = {
    "huella": sha256(modelo + INSTRUCCIONES + json(ESQUEMAS)),
    "mensajes": [...],   # historial de la API, solo-agregar
    "turnos": [{"pregunta", "estado", "texto", "revisado": [...], "tarjetas": [{tipo, titulo, datos}], "enlaces": [...]}],
}
```

- Si la huella cambió (despliegue nuevo), conversación nueva. Evita el 400 de bloques thinking
  atados a otro system o a otras herramientas.
- El historial nunca se recorta. Con más de 25 turnos o más de 200 KB, el panel pide "Nueva
  conversación".

### 1.5 Vistas y HTMX

URLs en `asistente/urls.py`, incluidas en `config/urls.py` bajo `asistente/`. Todas con
`@solo_duena`; 404 si `not disponible(request)` (sin clave, o taller con límite 0).

| URL | Nombre | Devuelve |
|---|---|---|
| `GET asistente/` | `asistente:panel` | Con HTMX, `_conversacion.html`; sin JavaScript, `pagina.html` |
| `POST asistente/preguntar/` | `asistente:preguntar` | `_turno.html` más `_uso_aviso.html` con `hx-swap-oob` en `#asistente-uso`. Siempre 200 (`app.js` no pinta 4xx ni 5xx) |
| `POST asistente/nueva/` | `asistente:nueva` | La conversación vacía |

`preguntar` recibe `pregunta` (máximo 500) y `pagina` (ruta más query). Flujo:

1. `uso.reservar(taller)`. Si devuelve False, turno con el mensaje de límite; no se llama a
   Claude.
2. `conversacion.preguntar(...)`.
3. `uso.anotar(taller, r.uso)`. Si `not r.cobrada`, `uso.devolver(taller)`.
4. Guarda la sesión solo si `estado == "ok"`.
5. Log `asistente`: taller, vueltas, tokens, esfuerzo, `stop_reason`. Nunca el texto.

Pintado:

- El `<aside id="asistente">` va en `base.html`, hermano de `<main>`, solo si
  `asistente.disponible`.
- Se llena con `hx-get` al abrir. Con la cookie `asistente=abierto`, el servidor lo dibuja
  abierto y lo carga con `hx-trigger="load"`.
- Formulario: `hx-post`, `hx-target="#asistente-pendiente"`, `hx-swap="outerHTML"`,
  `hx-sync="this:drop"`, `hx-disabled-elt`.
- Antes de enviar, el JS agrega `#asistente-pendiente` con la burbuja (por `textContent`) y los
  tres puntos con "Revisando tus datos…". La respuesta lo reemplaza por el turno entero.
- El texto de Claude sale con `{{ texto|linebreaks }}`, sin `|safe`. Orden: primer párrafo,
  tarjetas, resto, enlaces.

Contrato JS (sección 14 de `static/js/app.js`):

- `[data-asistente-abrir]`, `[data-asistente-cerrar]`, `[data-asistente-form]`,
  `[data-asistente-sugerencia]`.
- Ctrl/Cmd+J abre y cierra. Esc cierra solo si no hay `dialog` ni desplegable abierto.
- Enter envía; Shift+Enter hace salto de línea. El textarea crece hasta 120 px.
- Llena el campo oculto `pagina`, baja al final y devuelve el foco.

### 1.6 Uso

**Modelo `asistente.UsoAsistente(ModeloDeTaller)`:** `fecha`, `preguntas`, `tokens_entrada`,
`tokens_salida`, `tokens_cache_escritura`, `tokens_cache_lectura`. Único por
(`taller`, `fecha`).

**Límites:** campos nuevos en `cuentas.Taller`: `asistente_limite_mes` y
`asistente_limite_dia`, editables en `TallerAdmin`. **Por defecto 0 (apagado)**: David lo
activa por taller poniendo 600 y 40. 0 en cualquiera de los dos apaga el asistente.

```python
# asistente/uso.py
@dataclass(frozen=True)
class Cupo:
    usadas_hoy: int; limite_dia: int; usadas_mes: int; limite_mes: int
    # propiedades: quedan, porcentaje_mes, agotado ("" | "dia" | "mes"), pocas
def cupo(taller, hoy=None) -> Cupo
def reservar(taller, hoy=None) -> bool   # atómico: bloquea la fila del taller, revisa y suma 1
def devolver(taller, hoy=None) -> None
def anotar(taller, uso: Uso, hoy=None) -> None   # con F()
def costo_usd(uso) -> Decimal            # settings.ASISTENTE_PRECIOS_USD; no se guarda
```

Precios por millón (Opus 5.5): entrada 4.00, salida 20.00, escritura de caché 5.00, lectura de
caché 0.20. `pocas` es True si quedan 5 o menos hoy, o 10 % o menos del mes.

### 1.7 Cómo quedó la base (ajustes del coordinador en T25 y T26)

Lo que cambió respecto a lo de arriba al construir la base. Manda esto si algo choca.

- **`RespuestaClaude` vive en `asistente/contratos.py`** (congelado), no en `cliente.py`:
  la necesita también `falso.py`. `cliente.py` la importa de ahí.
- **Ya hechos por la base:** `cliente.obtener_cliente()` (None sin clave; si no, la clase de
  `settings.ASISTENTE_CLIENTE`), `disponibilidad.disponible(request)` y `uso.costo_usd(uso)`.
  Quien use el cliente lo llama siempre por el módulo: `cliente.obtener_cliente()`.
- **`conversacion.Respuesta` tiene un campo más:** `reiniciar: bool = False`, True cuando el
  historial ya no sirve (`BadRequestError`) y la vista debe borrar la conversación.
- **`herramientas.ejecutar()` ya revisa** tipos, opciones, fechas (las convierte a `date`) y
  los rangos de `RANGOS` (cantidad de 1 a 2000, mes de 1 a 12, texto del mensaje hasta 700
  caracteres, ganancia de 0 a 300, abono de 0 a 100, ids desde 1). Un error de código dentro
  de una herramienta llega a Claude como "No pude hacer esa consulta." y queda en el registro.
  Cada herramienta revisa lo que el esquema no dice (fechas al revés, rangos de días).
- **Cliente falso:** `falso.instalar(monkeypatch, settings, guion)` pone una clave de prueba y
  hace que `obtener_cliente()` devuelva el falso. Piezas del guion: `falso.texto(t)`,
  `falso.usa((nombre, entrada, id), ..., pensamiento_antes=True, texto_antes=None)`,
  `falso.rechazo()`, `falso.cortada()` y cualquier excepción (se lanza en esa vuelta).
- **Corte de internet en las pruebas:** `conftest.py` no parcha `ClienteAnthropic.enviar`;
  corta el envío dentro de la librería (`SyncAPIClient.request`). Así el carril B puede probar
  `enviar` reemplazando `anthropic.Anthropic` en `asistente.cliente`, y ninguna prueba llega
  a internet por ningún camino.
- **El botón es de la base:** `asistente/templates/asistente/_boton.html` lo incluye
  `base.html` (no es del carril D). Sin JavaScript lleva a `asistente:panel`.
- **El panel en `base.html`:** `<aside class="asistente" id="asistente" data-asistente>`,
  `hidden` si está cerrado, con `hx-get` a `asistente:panel` y `hx-trigger` `load` (abierto
  por la cookie) o `asistente-abrir once` (lo dispara `app.js` al abrirlo).
- **`GET asistente/` con HTMX devuelve el interior del panel** (`_panel.html`): la cabeza
  (título, "Solo consulta", "Nueva conversación" y la equis con `data-asistente-cerrar`),
  la conversación `<div class="asistente__mensajes" id="asistente-mensajes" aria-live="polite">`
  con `_conversacion.html` adentro, y el pie con el formulario. Sin HTMX, `pagina.html`.
- **Lo que espera `app.js` (sección 14) dentro del panel:**
  - el formulario lleva `data-asistente-form`, `hx-post`, `hx-target="#asistente-pendiente"`,
    `hx-swap="outerHTML"`, `hx-disabled-elt="find textarea, find button"`, un `<textarea
    name="pregunta" maxlength="500">` y un `<input type="hidden" name="pagina">` (el JS lo
    llena). No hace falta `hx-sync`: el JS no deja enviar si ya hay una pregunta en camino;
  - el saludo de la conversación vacía lleva `data-asistente-bienvenida` (el JS lo quita con
    la primera pregunta) y cada sugerencia es un botón `class="chip"` con
    `data-asistente-sugerencia`;
  - cada turno (pregunta y respuesta) va en `<div class="asistente__turno">`, y
    `POST asistente/preguntar/` devuelve ese bloque entero: reemplaza al
    `#asistente-pendiente` que puso el JS;
  - el aviso ámbar va en `<div id="asistente-uso">` dentro del pie, encima de la caja, y la
    vista lo manda aparte con `hx-swap-oob`.
- **Los tres puntos laten en `app.css`** (sección 8, con `--vuelta-latido`); en la maqueta
  están quietos. `.asistente__turno` está en la sección 9.
- **Mi taller:** `cuentas/mi_taller.py` pasa `uso_asistente` (el `Cupo`, o None si el
  asistente no está disponible) y la plantilla incluye `asistente/_uso_mi_taller.html` dentro
  de un bloque `ajuste`. Mientras `uso.cupo` sea un stub, Mi taller da error con el asistente
  prendido: el carril D lo prueba en `test_uso.py`.
- **La prueba corta** es `herramientas/humo_asistente.py` (fuera de pytest). Es el único
  lugar fuera de `asistente/cliente.py` donde aparece `Anthropic(`.
- **La maqueta del límite** está en su propia página: `diseno/asistente-limite.html`.
- **Lo que mostró la prueba corta con la clave (14 de noviembre de 2026)**, 3 llamadas con
  los parámetros de la sección 1.3, sin ningún 400:
  - la respuesta de Claude vuelve tal cual (`to_dict(mode="json")`, con los thinking) y se
    acepta; los esquemas `strict`, el mensaje `role: "system"`, `fallbacks` y la caché
    automática funcionan;
  - forma real de los bloques: la de `asistente/falso.py`. El thinking (vacío, con firma) a
    veces viene antes del `tool_use` y a veces no;
  - la caché funciona desde la segunda llamada (unos 3.200 tokens leídos de caché): cada
    llamada costó entre 0,1 y 1,6 centavos de dólar, menos de lo estimado;
  - **Claude escribe en Markdown** (`**negrita**`, tablas con `|`) y con emojis, y trata de
    "usted". Como el texto se muestra escapado, eso se vería tal cual: **las instrucciones
    (carril B) deben pedir texto plano, sin Markdown, sin tablas y sin emojis, tuteando a la
    dueña ("Te deben…"), y dejar las listas de cifras a las tarjetas**;
  - con una segunda pregunta que se podía contestar con lo que ya tenía, volvió a pedir una
    herramienta. Está bien (las cifras salen frescas), pero cuenta para el tiempo y el costo.
- **Ajustes de la integración (T35):** `ClienteClaude.enviar` recibe además `plazo` (segundos
  que le quedan a la pregunta; el ciclo lo pasa en cada vuelta). `ClienteAnthropic` espera
  como mucho `min(45, plazo)` y solo deja el reintento si cabe entero: una pregunta nunca pasa
  de `PLAZO_SEGUNDOS` (50). La vista anota en el registro vueltas, esfuerzo, `stop_reason` y
  modelos. Con el panel abierto al lado (de 1024 a 1439 px), las columnas de la hoja pasan a
  una (`app.css`, sección 9).
- **Ícono propio y caja de Hoy** (decisión de David después de T26): el ícono `asistente` es
  un botón de costura con carita, y `.avatar-asistente` (símbolo `asistente-cara`, en círculo
  negro) va arriba del panel en vez del ícono de línea (el 2026-11-15 los dos se cambiaron por
  la esfera de Lucy, T37; ver `docs/08-diseno.md`): `_panel.html` (carril D) copia la
  cabeza de `diseno/asistente.html`. La caja grande de Hoy, con el asistente prendido, es
  `asistente/_caja_hoy.html` (de la base): `app.js` abre el panel y manda la pregunta con el
  formulario del panel (`requestSubmit`), así que ese formulario no necesita nada especial.

## 2. Base del coordinador (T25 y T26, en orden, sin carriles)

**T25. Documentos, maqueta, librería y datos**

1. Documentos: `docs/08-diseno.md` (Shopify y sección Asistente), `docs/02-modelo-de-datos.md`,
   `docs/03-pantallas.md`, `docs/04-permisos.md` (fila Asistente), `docs/06-pruebas.md`,
   `docs/05-tareas.md` (T25 a T36), `docs/09-plan-de-construccion.md` (tanda 7), `CLAUDE.md`
   (lista de documentos), `docs/01-plan.md`, `docs/guia-publicacion.md` y
   `herramientas/servidor/` (120 s y `gthread`).
2. Maqueta: agregar a `diseno/asistente.html` la tarjeta de mensaje, la de cotización, el aviso
   ámbar y el estado de límite; agregar a `diseno/mi-taller.html` el bloque "Asistente" con el
   riel azul; pasar los estilos a `diseno/estilo.css`. **Mostrárselas a David y esperar su
   aprobación antes de lanzar los carriles.**
3. `uv add anthropic` (`pyproject.toml` y `uv.lock`).
4. Ajustes: en `config/settings/base.py`, `ANTHROPIC_API_KEY = entorno.texto("ANTHROPIC_API_KEY", "")`,
   los `ASISTENTE_*` y `"asistente"` en `INSTALLED_APPS`; en `config/settings/pruebas.py`, clave
   vacía y `ASISTENTE_CLIENTE = "asistente.falso.ClienteProhibido"`; en
   `config/settings/produccion.py`, el logger `asistente`; en `.env.example`, el comentario.
5. Modelos y migraciones: `asistente/models.py` con `asistente/migrations/0001`, y
   `cuentas/models.py` con su migración siguiente.
6. Admin: `asistente/admin.py` (solo lectura, con `costo_usd` y costo por pregunta,
   `date_hierarchy`) y `cuentas/admin.py` (límites y uso del mes).
7. `pedidos/calculos.py`: `gastos_entre` y `gastos_por_categoria`, con pruebas en
   `pedidos/tests/test_calculos.py`.
8. `tests/fabricas.py` (`crear_uso`) y `tests/test_aislamiento.py` (`UsoAsistente`).

**T26. Esqueleto y piezas**

9. `asistente/`: `contratos.py`, `esquemas.py`, `falso.py`, `disponibilidad.py`, `urls.py`,
   `herramientas/__init__.py` y los cinco módulos con stubs; stubs con firma de `cliente.py`,
   `conversacion.py`, `pagina.py`, `esfuerzo.py`, `instrucciones.py`, `uso.py`, `vistas.py`;
   plantillas vacías; `tests/test_contratos.py` (esquemas y registro coinciden, todos `strict`,
   orden fijo).
10. `config/urls.py` y `config/menu.py` (deja `asistente = {disponible, abierto}` en el
    contexto).
11. `templates/base.html`: bloque `acciones_antes`, botón y `<aside>`. Mover fecha, buscar y
    Excel a `acciones_antes` en `pedidos/templates/pedidos/hoy.html`, `lista.html` y
    `finanzas/templates/finanzas/resumen.html`.
12. `static/iconos/iconos.svg`: símbolos `asistente` y `enviar` (copiados de la maqueta).
13. `static/css/app.css` (copia idéntica) y `static/js/app.js` (sección 14).
14. `cuentas/templates/cuentas/mi_taller.html` (bloque Asistente) y `cuentas/mi_taller.py`
    (`uso_asistente` en `_pagina`).
15. `conftest.py`: fixture automático que hace fallar `ClienteAnthropic.enviar`.
16. `tests/test_base_visual.py`: el botón sale solo con clave, taller activado y dueña; Ctrl J.
17. **Prueba de humo con la clave real** (David pone la clave en `.env` al terminar T26): 3
    llamadas (pregunta, herramienta, segunda pregunta) para confirmar que `to_dict()` viaja de
    vuelta sin 400. De ahí sale el ejemplo de respuesta para `falso.py`. Si falla, se ajusta el
    contrato **antes** de lanzar los carriles.

## 3. Carriles (subagentes Opus 5.5, cada uno en su worktree)

Cada carril escribe una bitácora por tarea (`docs/bitacora/TNN.md`) y no toca archivos
congelados (ni `contratos.py`, `esquemas.py`, `falso.py`, `herramientas/__init__.py`,
`urls.py`).

| Carril | Tareas | Archivos propios |
|---|---|---|
| A. Consultas | T27, T28 | `herramientas/pedidos.py`, `plata.py`, `catalogo.py`; `tarjetas/{pedidos, pedido, entregas, quien_debe, cuentas, gastos, telas, clientes}.html`; `tests/test_herramientas_*.py` |
| B. Motor | T29, T30 | `cliente.py`, `conversacion.py`, `instrucciones.py`, `pagina.py`, `esfuerzo.py`; `tests/test_cliente.py`, `test_conversacion.py`, `test_pagina.py`, `test_esfuerzo.py` |
| C. Mensajes y cotizar | T31, T32 | `herramientas/mensajes.py`, `cotizar.py`; `tarjetas/mensaje.html`, `cotizacion.html`; `tests/test_mensajes.py`, `test_cotizar.py` |
| D. Panel y uso | T33, T34 | `vistas.py`, `uso.py`; `_boton`, `_panel`, `_conversacion`, `_turno`, `_uso_aviso`, `_uso_mi_taller`, `pagina.html`; `tests/test_panel.py`, `test_uso.py` |

**T27 (A). `buscar_pedidos`, `ver_pedido`, `entregas`, `telas`, `buscar_clientes`.** Pruebas:
con dos talleres ninguna devuelve lo del otro; `ver_pedido` con id ajeno o inexistente lanza
`ErrorDeHerramienta` con el mismo texto; `pedido_id=None` usa `ctx.pedido_actual`;
`filtro=atrasados` y `semana` dan lo mismo que `calculos.filtrar_pedidos`; las telas bajas
coinciden con `contadores_del_menu`; `json.dumps(datos)` no contiene WhatsApp, `token_tallas`,
notas ni nombres de tallas; sin float; con 25 pedidos, `mostrados=20` y `total=25`; las
tarjetas usan `pesos` y los enlaces `reverse`.

**T28 (A). `quien_debe`, `cuentas_del_mes`, `gastos`.** Pruebas: con `cargar_ejemplos`,
`quien_debe` da $ 5.790.000 y los cuatro deudores de `diseno/hoy.html`;
`sum(saldos) == calculos.por_cobrar` y coincide con `/`; `cuentas_del_mes` coincide con
`calculos.resumen_del_mes` y con `/resumen/?mes=`, con abonos y gastos de dos meses; `gastos`
de un mes coincide con `gastado_en`; los cotizados no cuentan; aislamiento en las tres.

**T29 (B). Cliente y ciclo.** Pruebas con `ClienteFalso`: una herramienta se ejecuta y la
segunda llamada lleva el `tool_result`; dos `tool_use` en paralelo dan un solo mensaje user con
dos resultados; error de herramienta con `is_error: true` y el ciclo sigue; los bloques
thinking vuelven idénticos y el prefijo de `mensajes` nunca cambia; `sistema` y `herramientas`
idénticos byte a byte entre llamadas y entre talleres; ni fecha ni taller en `sistema`; el
mismo esfuerzo en todas las vueltas de una pregunta; sexta llamada con `sin_herramientas`;
`refusal` y `max_tokens` no leen contenido y dejan `mensajes` igual; cada excepción del SDK da
el mensaje amable y `cobrada` correcto; `obtener_cliente()` es None sin clave;
`ClienteAnthropic` (con `anthropic.Anthropic` parcheado) manda `output_config`, `fallbacks`,
`betas` y `tool_choice` auto, y no manda `thinking`.

**T30 (B). Pantalla y esfuerzo.** Pruebas: `/pedidos/<id propio>/` da contexto con ese pedido;
id de otro taller, sin pedido y sin rastro en el texto; ruta inventada o externa, sección
genérica; el mensaje `role: "system"` va después del user y queda en el historial; tabla de
casos de `esfuerzo.elegir`; "¿Cuánto debe este pedido?" resuelve con `ver_pedido(None)`.

**T31 (C). `preparar_mensaje`.** Pruebas: el teléfono no aparece en `Resultado.datos` ni en
ningún `mensajes` enviado al cliente falso; la tarjeta lleva el mismo `wa.me` que
`mensajes.enlace_whatsapp`; sin número, enlace vacío y "Copiar"; cifra distinta al saldo real
da error; `[ENLACE]` se cambia por la URL pública, que no llega a Claude; enlace cerrado da
error; pedido o cliente ajeno, no encontrado; `<script>` en el texto sale escapado; no se crea
ni cambia ningún registro.

**T32 (C). `cotizar`.** Pruebas: el polo de `docs/06-pruebas.md` (costo 41.600, unidad 54.500,
20 unidades 1.090.000); mismo resultado que `FormularioCotizacion.cotizacion()`; el enlace al
cotizador abre la página con el mismo total; prenda de otro taller no existe; varias
coincidencias dan `opciones` sin tarjeta; cantidad 0 o mayor que 2000 da error.

**T33 (D). Panel.** Pruebas: costurera 403; sin sesión redirige; sin clave o con límite 0, 404
y sin botón; pregunta con guion falso trae texto y tarjeta; `<b>x</b><script>` escapado;
mensaje de límite sin llamar a Claude (`llamadas == []`); error del servicio con mensaje amable
y sesión intacta; "Nueva conversación" borra; huella cambiada reinicia; más de 25 turnos pide
nueva; la sesión de una usuaria no la ve otra; pregunta vacía o de más de 500 da 200 con
aviso; el panel recargado pinta los turnos guardados.

**T34 (D). Uso y límites.** Pruebas: `reservar` suma; al llegar a 40 del día o 600 del mes
devuelve False con su mensaje; mandan los límites del taller en `/admin`; el mes se cuenta en
Bogotá; `devolver` no baja de 0; `anotar` suma los cuatro tipos de token; `costo_usd` con un
caso a mano y sin float; el uso de un taller no afecta al otro; aviso ámbar solo con `pocas`;
la tarjeta de Mi taller muestra "N de 600" y el riel.

## 4. Lista del revisor

- `uv run pytest` pasa y ninguna prueba toca la red.
- `Anthropic(` aparece solo en `asistente/cliente.py`, con la clave explícita.
- Toda consulta de herramienta arranca de `.del_taller(ctx.taller)` o de
  `calculos.*(taller)`. Ningún `objects.get(pk=)` suelto.
- Las cifras salen de `pedidos/calculos.py`. Ningún `Sum` duplicado, ningún float.
- `Resultado.datos` no lleva WhatsApp, `token_tallas`, notas, nombres de tallas ni medidas.
- Ninguna plantilla del asistente usa `|safe`, `mark_safe` ni `autoescape off`. Las URL salen
  de `reverse`.
- Historial solo-agregar. `sistema` y `herramientas` constantes. Fecha, taller y pantalla solo
  en el mensaje `role: "system"`. Un esfuerzo por pregunta.
- No aparecen `thinking: disabled`, `budget_tokens`, `tool_choice` any/tool ni `temperature`.
- `stop_reason` se revisa antes del contenido.
- Las tres vistas llevan `@solo_duena` y revisan `disponible`.
- El límite se revisa en el servidor antes de llamar. El log no tiene el texto de las
  preguntas.
- Ninguna herramienta escribe en la base.
- El panel coincide con la maqueta en 1280, 900 y 390 px. Rojo solo en vencidos. Foco y
  teclado funcionan.
- Ningún carril tocó archivos congelados. Un commit y una bitácora por tarea.

## 5. Unión y prueba real

Orden de unión: A, C, B, D, con `uv run pytest` después de cada uno.

**T35 (coordinador). Integración.**

- `asistente/tests/test_punta_a_punta.py`: vista real, ciclo real, herramientas reales y
  `ClienteFalso`, sobre `cargar_ejemplos`. Casos: "¿quién me debe?" con la tarjeta igual a
  Hoy; "este pedido" desde `/pedidos/<id>/`; mensaje de cobro; cotización.
- `herramientas/capturas.py`: `PANTALLAS[7]` con la cookie `asistente=abierto` y una
  conversación sembrada en la sesión. Capturas en `docs/capturas/tanda-7/`.

**T36 (a mano, con la clave). 20 preguntas reales.**

- Script `herramientas/probar_asistente.py`, fuera de pytest.
- Reparto: 8 consultas, 4 de plata, 3 con "este pedido", 3 mensajes y 2 cotizaciones. Cada
  una en `medium` y en `high`.
- Por pregunta: correcta o no contra la pantalla, vueltas, segundos, tokens de los cuatro
  tipos, `cache_read > 0` desde la segunda, y costo.
- Tabla en `docs/bitacora/tanda-7.md` con costo medio y percentil 90 por esfuerzo, y la
  comparación de `UsoAsistente` contra la consola de Anthropic.
- Con eso se decide si la regla de esfuerzo se queda y se revisa el tiempo contra el límite
  del servidor.

## 6. Decisiones de David y riesgos

Decisiones (14 de noviembre de 2026):

1. Las piezas nuevas de la maqueta se le muestran a David antes de lanzar los carriles.
2. El asistente viene **apagado** por taller; David lo activa en `/admin`.
3. A Anthropic no van nombres ni medidas de tallas, ni notas de clientes. Hay que avisarle a la
   clienta y confirmar los términos comerciales de Anthropic.
4. El servidor sube a 120 s y `gthread`. Lo ejecuta David al publicar.
5. David crea en la consola de Anthropic la clave y el tope de gasto, y pone la clave en `.env`
   al terminar T26.

Riesgos técnicos:

- **Ida y vuelta de `response.content`.** Que `to_dict()` se acepte de vuelta sin 400 lo cubre
  la prueba de humo (paso 17), antes de los carriles. Las cuentas nuevas tienen activa la
  revisión del historial: por eso la huella y el no recortar.
- **Límites de `strict`.** Si da 400 por demasiados parámetros anulables, se quita `strict` de
  `buscar_pedidos` y se valida en código (que igual se hace).
- **Cifras en el texto.** Claude puede escribir un total en su prosa; solo las tarjetas están
  garantizadas. T36 lo mide antes de decidir si se agrega un chequeo.
- **Sesiones** en la base, guardadas en cada petición: por eso el tope de 200 KB.
- **Dos pestañas a la vez:** gana la última que guarda.

## 7. Bosquejo de la tanda 8

**Reemplazado** el 15 de noviembre de 2026 por `docs/12-agente.md` (qué hace el agente) y
`docs/13-plan-tanda-8.md` (cómo se construye). Lo de abajo queda solo como historia.

- **Herramientas `proponer_*`** (pedido, abono, gasto, etapa, "Usé" tela). No escriben:
  devuelven una tarjeta `borrador` con los datos y una carga firmada
  (`django.core.signing`: taller, usuaria, vencimiento, un solo uso).
- **`POST asistente/confirmar/`** valida la firma y guarda con los mismos formularios y
  funciones de las pantallas (`NuevoPedidoForm` y `crear_pedido`, el de abonos,
  `FormularioGasto`, `FormularioMovimiento`, `puede_mover_etapa`): mismas reglas y mismos
  avisos. Alternativa a evaluar: que "Revisar" abra la ventana existente ya llena.
- **Nunca borrar:** no existe herramienta para eso.
- **Lo guardado se le cuenta a Claude** agregando un mensaje al historial, nunca editándolo.
- **Costureras:** otro conjunto fijo de herramientas, sin plata, con `puede_mover_etapa` y
  "Usé". Va con su propio prefijo de caché y se elige al empezar la conversación, nunca a
  mitad.
- **Por decidir:** si la cronología (`pedidos/cronologia.py`) marca "con el asistente"; si
  confirmar cuenta como pregunta; el texto de la insignia que reemplaza "Solo consulta".
- **Pruebas:** sin confirmar no cambia nada; firma ajena, vencida o repetida se rechaza;
  permisos iguales a los de la vista; aislamiento.
