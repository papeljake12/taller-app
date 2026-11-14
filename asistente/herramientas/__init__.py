"""Las herramientas del asistente: el registro y la única puerta para ejecutarlas.

Archivo congelado (docs/11-plan-tanda-7.md, sección 1.1): solo lo cambia el coordinador.

Cada herramienta vive en un módulo de esta carpeta y tiene la firma
`def nombre(ctx: Contexto, **entrada) -> Resultado`. Claude nunca la llama directo: pide su
nombre y su entrada, y `ejecutar()` revisa la entrada, la convierte (las fechas pasan a `date`)
y la corre con el contexto de quien preguntó, que trae su taller.

Lo que sale mal se convierte en `ErrorDeHerramienta`, cuyo texto le llega a Claude para que
corrija: un nombre que no existe, una entrada que no cumple el esquema o se sale de su rango,
una herramienta sin terminar (`NotImplementedError`) y cualquier otro error (este último
además queda en el registro del servidor).
"""

import logging
from datetime import date

from asistente.contratos import Contexto, ErrorDeHerramienta, Resultado
from asistente.esquemas import POR_NOMBRE
from asistente.herramientas import catalogo, cotizar, mensajes, pedidos, plata

registro_del_servidor = logging.getLogger("asistente")

REGISTRO = {
    "buscar_clientes": catalogo.buscar_clientes,
    "buscar_pedidos": pedidos.buscar_pedidos,
    "cotizar": cotizar.cotizar,
    "cuentas_del_mes": plata.cuentas_del_mes,
    "entregas": pedidos.entregas,
    "gastos": plata.gastos,
    "preparar_mensaje": mensajes.preparar_mensaje,
    "quien_debe": plata.quien_debe,
    "telas": catalogo.telas,
    "ver_pedido": pedidos.ver_pedido,
}

# Las herramientas que tocan plata. Las preguntas típicas de estas deben caer en esfuerzo
# "high" (asistente/esfuerzo.py); las pruebas lo comprueban.
DE_PLATA = frozenset({"quien_debe", "cuentas_del_mes", "gastos", "cotizar"})

# Rangos que el esquema no puede expresar con `strict`: (mínimo, máximo), ambos incluidos.
RANGOS = {
    ("cotizar", "cantidad"): (1, 2000),
    ("cotizar", "ganancia_pct"): (0, 300),
    ("cotizar", "abono_pct"): (0, 100),
    ("cuentas_del_mes", "anio"): (2000, 2100),
    ("cuentas_del_mes", "mes"): (1, 12),
    ("buscar_pedidos", "texto"): (0, 100),
    ("buscar_clientes", "texto"): (0, 100),
    ("cotizar", "prenda"): (1, 80),
    ("preparar_mensaje", "texto"): (1, 700),
    ("preparar_mensaje", "pedido_id"): (1, 2**63 - 1),
    ("preparar_mensaje", "cliente_id"): (1, 2**63 - 1),
    ("ver_pedido", "pedido_id"): (1, 2**63 - 1),
}

_TIPOS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _cumple(valor, esquema):
    """True si el valor cumple ese pedazo de esquema (tipo, opciones y formato de fecha)."""
    if "anyOf" in esquema:
        return any(_cumple(valor, parte) for parte in esquema["anyOf"])
    tipos = esquema["type"]
    tipos = tipos if isinstance(tipos, list) else [tipos]
    if not any(_TIPOS[t](valor) for t in tipos):
        return False
    if "enum" in esquema and valor not in esquema["enum"]:
        return False
    if esquema.get("format") == "date" and isinstance(valor, str):
        try:
            date.fromisoformat(valor)
        except ValueError:
            return False
    return True


def _convertir(valor, esquema):
    """Las fechas pasan de texto a `date`. Lo demás queda igual."""
    partes = esquema.get("anyOf", [esquema])
    if isinstance(valor, str) and any(p.get("format") == "date" for p in partes):
        return date.fromisoformat(valor)
    return valor


def validar(nombre, entrada):
    """La entrada revisada y convertida, lista para `herramienta(ctx, **entrada)`."""
    esquema = POR_NOMBRE[nombre]["input_schema"]
    if not isinstance(entrada, dict):
        raise ErrorDeHerramienta("La entrada debe ser un objeto.")
    sobran = set(entrada) - set(esquema["properties"])
    faltan = set(esquema["required"]) - set(entrada)
    if sobran or faltan:
        raise ErrorDeHerramienta(
            f"Entrada inválida para {nombre}: sobran {sorted(sobran)}, faltan {sorted(faltan)}."
        )
    convertida = {}
    for campo, propiedad in esquema["properties"].items():
        valor = entrada[campo]
        if not _cumple(valor, propiedad):
            raise ErrorDeHerramienta(f"El campo {campo} de {nombre} no es válido.")
        rango = RANGOS.get((nombre, campo))
        if rango is not None and valor is not None:
            medida = len(valor) if isinstance(valor, str) else valor
            if not rango[0] <= medida <= rango[1]:
                raise ErrorDeHerramienta(
                    f"El campo {campo} de {nombre} debe estar entre {rango[0]} y {rango[1]}"
                    + (" caracteres." if isinstance(valor, str) else ".")
                )
        convertida[campo] = _convertir(valor, propiedad)
    return convertida


def ejecutar(nombre: str, entrada: dict, ctx: Contexto) -> Resultado:
    """Corre la herramienta `nombre` con la entrada que mandó Claude, para el taller de ctx."""
    herramienta = REGISTRO.get(nombre)
    if herramienta is None:
        raise ErrorDeHerramienta(f"No existe la herramienta {nombre}.")
    argumentos = validar(nombre, entrada)
    try:
        return herramienta(ctx, **argumentos)
    except ErrorDeHerramienta:
        raise
    except NotImplementedError:
        raise ErrorDeHerramienta("Esa consulta todavía no está lista.") from None
    except Exception:
        registro_del_servidor.exception(
            "La herramienta %s falló (taller %s)", nombre, ctx.taller.pk
        )
        raise ErrorDeHerramienta("No pude hacer esa consulta.") from None
