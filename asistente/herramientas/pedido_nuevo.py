"""Proponer un pedido nuevo: cliente, pedido, abono que dejó y tela (T39, carril A).

Reglas: docs/13-plan-tanda-8.md, secciones 1.1 y 1.2. No guarda nada: arma un borrador con
`asistente.borradores` y la dueña lo guarda con un toque (`asistente.guardar`).
"""

from asistente.contratos import Contexto, Resultado


def proponer_pedido(
    ctx: Contexto, *, cliente, cliente_id, tipo_cliente, detalle, cantidad, tallaje,
    fecha_entrega, prenda, total, abono, tela, metros,
) -> Resultado:
    raise NotImplementedError
