"""Las herramientas que Claude puede pedir, tal como se le describen (el esquema JSON).

Archivo congelado (docs/11-plan-tanda-7.md, sección 1.2): solo lo cambia el coordinador.

Reglas:
- Todas con `strict: true`, `additionalProperties: false` y todas las propiedades en
  `required`. Lo opcional se acepta como `null`.
- La lista va ordenada por nombre y nunca cambia entre llamadas ni entre talleres: así Claude
  guarda las herramientas en caché y cada pregunta cuesta menos.
- Los rangos (meses de 1 a 12, cantidades hasta 2000...) no se pueden poner en el esquema con
  `strict`: los revisa `asistente.herramientas.ejecutar()`.
- Las descripciones dicen a Claude qué hace cada una. Ninguna lleva datos de un taller.
"""

FECHA = {"type": "string", "format": "date", "description": "Fecha AAAA-MM-DD."}
FECHA_O_NADA = {"anyOf": [FECHA, {"type": "null"}]}
TEXTO_O_NADA = {"type": ["string", "null"]}
ENTERO_O_NADA = {"type": ["integer", "null"]}


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
