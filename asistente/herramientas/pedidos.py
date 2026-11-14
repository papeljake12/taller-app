"""Consultas de pedidos.

Carril A (T27). Firma de cada herramienta: `def nombre(ctx, **entrada) -> Resultado`.
Contratos y reglas de `Resultado.datos`: asistente/contratos.py y docs/11-plan-tanda-7.md
(secciones 1.1 y 1.2). La entrada llega ya revisada por `asistente.herramientas.ejecutar()`
(las fechas ya son `date`).
"""

from asistente.contratos import Contexto, Resultado


def buscar_pedidos(ctx: Contexto, *, texto, filtro, entrega_desde, entrega_hasta) -> Resultado:
    raise NotImplementedError("Carril A (T27)")


def ver_pedido(ctx: Contexto, *, pedido_id) -> Resultado:
    raise NotImplementedError("Carril A (T27)")


def entregas(ctx: Contexto, *, desde, hasta) -> Resultado:
    raise NotImplementedError("Carril A (T27)")
