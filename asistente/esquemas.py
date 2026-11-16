"""Las herramientas que Claude puede pedir, tal como se le describen (el esquema JSON).

Archivo congelado (docs/11-plan-tanda-7.md, sección 1.2): solo lo cambia el coordinador.

Reglas:
- Todas con `strict: true`, `additionalProperties: false` y todas las propiedades en
  `required`. Lo opcional se acepta como `null`.
- La lista va ordenada por nombre y nunca cambia entre llamadas ni entre talleres: así Claude
  guarda las herramientas en caché y cada pregunta cuesta menos.
- Los rangos (meses de 1 a 12, cantidades hasta 2000...) no se pueden poner en el esquema con
  `strict`: los revisa `asistente.herramientas.ejecutar()`.
- Con `strict`, la API acepta como mucho 16 parámetros anulables (o con varios tipos) sumando
  todas las herramientas (lo mostró la prueba corta de la tanda 8). Por eso las herramientas
  `proponer_*` dicen "no hay" con 0 o "" en vez de null; `ejecutar()` los convierte en None
  (`VACIOS` en asistente/herramientas/__init__.py).
- Las descripciones dicen a Claude qué hace cada una. Ninguna lleva datos de un taller.
"""

FECHA = {"type": "string", "format": "date", "description": "Fecha AAAA-MM-DD."}
FECHA_O_NADA = {"anyOf": [FECHA, {"type": "null"}]}
TEXTO_O_NADA = {"type": ["string", "null"]}
ENTERO_O_NADA = {"type": ["integer", "null"]}
FECHA_O_HOY = {"type": "string", "description": 'Fecha AAAA-MM-DD, o "" para hoy.'}
ID_O_CERO = {"type": "integer"}
TEXTO_O_VACIO = {"type": "string"}


def _opciones_o_nada(opciones, descripcion):
    return {
        "anyOf": [{"type": "string", "enum": list(opciones)}, {"type": "null"}],
        "description": descripcion,
    }


def _con(descripcion, esquema):
    return {**esquema, "description": descripcion}


def _herramienta(nombre, descripcion, propiedades):
    return {
        "name": nombre,
        "description": descripcion,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": propiedades,
            "required": list(propiedades),
            "additionalProperties": False,
        },
    }


_HERRAMIENTAS = [
    _herramienta(
        "buscar_clientes",
        "Busca clientes del taller por nombre o por tipo. Devuelve cuántos pedidos tiene cada "
        "uno, cuánto ha comprado, cuánto debe, si tiene una cotización abierta y si tiene "
        "WhatsApp guardado (nunca el número). Sin texto ni tipo, devuelve todos.",
        {
            "texto": _con("Parte del nombre del cliente, o null.", TEXTO_O_NADA),
            "tipo": _opciones_o_nada(
                ["comparsa", "empresa", "colegio", "particular"], "Tipo de cliente, o null."
            ),
        },
    ),
    _herramienta(
        "buscar_pedidos",
        "Busca pedidos del taller por texto (cliente, detalle o encargada), por filtro o por "
        "fecha de entrega. Devuelve hasta 20 pedidos con su estado, entrega, total, abonado y "
        "saldo, y cuántos hay en total. Filtros: todos, produccion (confirmados sin entregar), "
        "semana (entrega en los próximos 7 días), atrasados, saldo (con plata por cobrar), "
        "entregados, cotizados (sin confirmar).",
        {
            "texto": _con("Texto a buscar, o null.", TEXTO_O_NADA),
            "filtro": _opciones_o_nada(
                ["todos", "produccion", "semana", "atrasados", "saldo", "entregados", "cotizados"],
                "Filtro de la pantalla Pedidos, o null (todos).",
            ),
            "entrega_desde": _con("Entrega desde esta fecha, o null.", FECHA_O_NADA),
            "entrega_hasta": _con("Entrega hasta esta fecha, o null.", FECHA_O_NADA),
        },
    ),
    _herramienta(
        "cotizar",
        "Calcula cuánto cobrar por una cantidad de prendas con los precios de una prenda "
        "guardada en el Cotizador del taller (la misma fórmula del Cotizador). Si el nombre "
        "coincide con varias prendas guardadas, devuelve las opciones para preguntar cuál.",
        {
            "prenda": {"type": "string", "description": "Nombre de la prenda guardada."},
            "cantidad": {"type": "integer", "description": "Cuántas prendas (1 a 2000)."},
            "ganancia_pct": _con(
                "Porcentaje de ganancia (0 a 300), o null para el de siempre (30).",
                ENTERO_O_NADA,
            ),
            "abono_pct": _con(
                "Porcentaje de abono para empezar (0 a 100), o null para el de siempre (50).",
                ENTERO_O_NADA,
            ),
        },
    ),
    _herramienta(
        "cuentas_del_mes",
        "Las cuentas de un mes: vendido (pedidos confirmados creados ese mes), cobrado "
        "(abonos), gastado y lo que le quedó (cobrado menos gastado), y las ventas por tipo de "
        "cliente. Sin año ni mes, el mes actual.",
        {
            "anio": _con("Año, o null para el actual.", ENTERO_O_NADA),
            "mes": _con("Mes de 1 a 12, o null para el actual.", ENTERO_O_NADA),
        },
    ),
    _herramienta(
        "entregas",
        "Los pedidos en producción con entrega entre dos fechas (ambas incluidas) y, aparte, "
        "los que ya están atrasados.",
        {
            "desde": _con("Primer día.", FECHA),
            "hasta": _con("Último día (máximo 62 días después de desde).", FECHA),
        },
    ),
    _herramienta(
        "gastos",
        "Los gastos del taller entre dos fechas (ambas incluidas): el total, el total por "
        "tipo y hasta 30 gastos, del más nuevo al más viejo.",
        {
            "desde": _con("Primer día.", FECHA),
            "hasta": _con("Último día.", FECHA),
            "categoria": _opciones_o_nada(
                ["telas", "insumos", "servicios", "otros"], "Tipo de gasto, o null (todos)."
            ),
        },
    ),
    _herramienta(
        "preparar_mensaje",
        "Deja listo un mensaje de WhatsApp para que la dueña lo revise y lo envíe ella misma. "
        "No envía nada. Tú escribes el texto; la aplicación pone el número. Toda cifra en "
        "pesos del texto debe ser el total, lo abonado o el saldo del pedido. Para pedir "
        "tallas, escribe el marcador [ENLACE] donde va el enlace del formulario.",
        {
            "pedido_id": _con("Id del pedido, o null.", ENTERO_O_NADA),
            "cliente_id": _con("Id del cliente si no es sobre un pedido, o null.", ENTERO_O_NADA),
            "motivo": {
                "type": "string",
                "enum": ["cobro", "listo", "tallas", "otro"],
                "description": "Para qué es el mensaje.",
            },
            "texto": {"type": "string", "description": "El mensaje, hasta 700 caracteres."},
        },
    ),
    _herramienta(
        "proponer_abono",
        "Prepara un borrador para anotar un abono a un pedido que ya existe. No guarda nada: la "
        "aplicación le muestra el borrador a la dueña y ella toca Guardar. Con pedido_id 0 "
        "usa el pedido de la pantalla; si no hay, busca por el nombre del cliente. Si hay dos "
        "pedidos posibles, devuelve las opciones para preguntar cuál.",
        {
            "pedido_id": _con("Id del pedido, o 0 para el de la pantalla.", ID_O_CERO),
            "cliente": _con('Nombre del cliente si no hay pedido_id, o "".', TEXTO_O_VACIO),
            "valor": {"type": "integer", "description": "Valor del abono en pesos."},
            "fecha": FECHA_O_HOY,
        },
    ),
    _herramienta(
        "proponer_gasto",
        "Prepara un borrador para anotar un gasto del taller. No guarda nada: la aplicación le "
        "muestra el borrador a la dueña y ella toca Guardar.",
        {
            "concepto": {"type": "string", "description": "En qué se gastó, corto."},
            "categoria": {
                "type": "string",
                "enum": ["telas", "insumos", "servicios", "otros"],
                "description": "Tipo de gasto.",
            },
            "valor": {"type": "integer", "description": "Valor en pesos."},
            "fecha": FECHA_O_HOY,
            "pedido_id": _con("Id del pedido al que corresponde, o 0.", ID_O_CERO),
        },
    ),
    _herramienta(
        "proponer_pedido",
        "Prepara un borrador de pedido nuevo: el cliente (el que ya existe o uno nuevo), el "
        "pedido, el abono que dejó y la tela que usa. No guarda nada: la aplicación le muestra "
        "el borrador a la dueña y ella toca Guardar. Sin total, lo calcula con la prenda "
        "guardada del Cotizador. Sin metros, los saca de la prenda por la cantidad. Si el "
        "cliente, la prenda o la tela coinciden con varias, devuelve las opciones para preguntar.",
        {
            "cliente": {
                "type": "string", "description": "Nombre del cliente como lo dijo la dueña.",
            },
            "cliente_id": _con("Id del cliente si ya lo encontraste, o 0.", ID_O_CERO),
            "tipo_cliente": {
                "type": "string",
                "enum": ["comparsa", "empresa", "colegio", "particular", ""],
                "description": 'Tipo de cliente si es nuevo, o "" si no lo sabes.',
            },
            "detalle": {
                "type": "string", "description": "Qué pidió, corto: 30 uniformes de diario.",
            },
            "cantidad": {"type": "integer", "description": "Para cuántas personas (1 a 2000)."},
            "tallaje": {
                "type": "string",
                "enum": ["adulto", "nino"],
                "description": "Tallas de adulto (XS a XXL) o de niño (4 a 16).",
            },
            "fecha_entrega": _con("Fecha de entrega.", FECHA),
            "prenda": _con('Nombre de la prenda guardada en el Cotizador, o "".', TEXTO_O_VACIO),
            "total": _con("Total en pesos si la dueña lo dijo, o 0.", ID_O_CERO),
            "abono": _con("Abono que dejó, en pesos, o 0.", ID_O_CERO),
            "tela": _con('Nombre de la tela del inventario que usa, o "".', TEXTO_O_VACIO),
            "metros": _con(
                'Metros de esa tela para todo el pedido (66 o 12.5), o "".', TEXTO_O_VACIO
            ),
        },
    ),
    _herramienta(
        "quien_debe",
        "Quién le debe plata al taller: por cliente, la suma de los saldos de sus pedidos "
        "confirmados, de mayor a menor, y si alguno tiene un pedido atrasado (deuda vencida). "
        "También el total por cobrar.",
        {},
    ),
    _herramienta(
        "telas",
        "Las telas del taller con los metros que quedan y el mínimo para avisar, y cuáles se "
        "están acabando.",
        {"solo_bajas": {"type": "boolean", "description": "true: solo las que se acaban."}},
    ),
    _herramienta(
        "ver_pedido",
        "Un pedido por dentro: cliente, detalle, estado, entrega, pagos con sus abonos, "
        "cuántas tallas han llegado por talla, materiales comprados y faltantes. Con null, el "
        "pedido que la dueña tiene abierto en pantalla.",
        {"pedido_id": _con("Id del pedido, o null para el de la pantalla.", ENTERO_O_NADA)},
    ),
]

# Ordenadas por nombre, siempre en el mismo orden.
ESQUEMAS = sorted(_HERRAMIENTAS, key=lambda h: h["name"])
NOMBRES = tuple(h["name"] for h in ESQUEMAS)
POR_NOMBRE = {h["name"]: h for h in ESQUEMAS}
