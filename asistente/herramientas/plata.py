"""Consultas de plata.

Carril A (T28). Firma de cada herramienta: `def nombre(ctx, **entrada) -> Resultado`.
Contratos y reglas de `Resultado.datos`: asistente/contratos.py y docs/11-plan-tanda-7.md
(secciones 1.1 y 1.2). La entrada llega ya revisada por `asistente.herramientas.ejecutar()`
(las fechas ya son `date`).
"""

from asistente.contratos import Contexto, Resultado


def quien_debe(ctx: Contexto) -> Resultado:
    raise NotImplementedError("Carril A (T28)")


def cuentas_del_mes(ctx: Contexto, *, anio, mes) -> Resultado:
    raise NotImplementedError("Carril A (T28)")


def gastos(ctx: Contexto, *, desde, hasta, categoria) -> Resultado:
    raise NotImplementedError("Carril A (T28)")
