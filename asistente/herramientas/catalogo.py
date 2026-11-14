"""Consultas de telas y clientes.

Carril A (T27). Firma de cada herramienta: `def nombre(ctx, **entrada) -> Resultado`.
Contratos y reglas de `Resultado.datos`: asistente/contratos.py y docs/11-plan-tanda-7.md
(secciones 1.1 y 1.2). La entrada llega ya revisada por `asistente.herramientas.ejecutar()`
(las fechas ya son `date`).
"""

from asistente.contratos import Contexto, Resultado


def telas(ctx: Contexto, *, solo_bajas) -> Resultado:
    raise NotImplementedError("Carril A (T27)")


def buscar_clientes(ctx: Contexto, *, texto, tipo) -> Resultado:
    raise NotImplementedError("Carril A (T27)")
