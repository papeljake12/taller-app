"""Los contratos del asistente: las piezas que comparten todos los carriles.

Archivo congelado (docs/11-plan-tanda-7.md, sección 1.1): solo lo cambia el coordinador.

- `Contexto`: quién pregunta y desde dónde. Toda herramienta lo recibe y consulta solo el
  taller que trae.
- `Resultado`: lo que devuelve una herramienta. `datos` es lo ÚNICO que lee Claude; la
  tarjeta y el enlace los arma la aplicación y nunca salen del servidor.
- `Uso`: los tokens de una o varias llamadas a Claude.
- `RespuestaClaude`: una respuesta de Claude ya traducida a diccionarios. La arma el cliente
  de verdad (asistente/cliente.py) y también el falso de las pruebas (asistente/falso.py).
- `Fila`: una cosa de un borrador (tanda 8), como se ve en su tarjeta.
- `ErrorDeHerramienta`: algo que Claude pidió mal (un pedido que no existe, una cifra que no
  cuadra). Su texto le llega a Claude para que corrija.

Firma de toda herramienta: `def nombre(ctx: Contexto, **entrada) -> Resultado`.

Reglas de `Resultado.datos`:
- Plata en enteros (pesos). Metros como texto decimal ("6.50"), nunca float. Fechas ISO.
- Listas con tope (20 pedidos, 30 gastos), con `total` y `mostrados`.
- Los ids de pedido y cliente sí van, para encadenar herramientas.
- Nunca van: WhatsApp, `token_tallas`, `Cliente.notas`, ni nombres ni medidas de las tallas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cuentas.models import Taller, Usuario
    from pedidos.models import Pedido


@dataclass(frozen=True)
class Contexto:
    taller: Taller
    usuaria: Usuario
    hoy: date  # timezone.localdate()
    pedido_actual: Pedido | None  # el pedido abierto en pantalla, ya validado por taller
    url_base: str  # request.build_absolute_uri("/"), para el enlace público de tallas


@dataclass(frozen=True)
class Enlace:
    texto: str
    url: str  # siempre armada con reverse()


@dataclass(frozen=True)
class Tarjeta:
    tipo: str  # plantilla asistente/tarjetas/{tipo}.html
    titulo: str
    datos: dict = field(default_factory=dict)  # serializable a JSON (vive en la sesión)


@dataclass(frozen=True)
class Resultado:
    datos: dict  # lo único que lee Claude
    revisado: str  # "Revisé los saldos de tus pedidos confirmados"
    tarjeta: Tarjeta | None = None
    enlace: Enlace | None = None


@dataclass(frozen=True)
class Uso:
    entrada: int = 0
    salida: int = 0
    cache_escritura: int = 0
    cache_lectura: int = 0

    def __add__(self, otro: Uso) -> Uso:
        return Uso(
            entrada=self.entrada + otro.entrada,
            salida=self.salida + otro.salida,
            cache_escritura=self.cache_escritura + otro.cache_escritura,
            cache_lectura=self.cache_lectura + otro.cache_lectura,
        )

    @property
    def total(self) -> int:
        return self.entrada + self.salida + self.cache_escritura + self.cache_lectura


@dataclass(frozen=True)
class RespuestaClaude:
    # [b.to_dict(mode="json") for b in response.content], con los bloques thinking incluidos y
    # sin tocar: vuelven tal cual en el historial.
    contenido: list[dict]
    stop_reason: str  # end_turn | tool_use | max_tokens | refusal | ...
    uso: Uso
    modelo: str  # response.model (puede ser el de respaldo)
    id_peticion: str


@dataclass(frozen=True)
class Fila:
    """Una cosa de un borrador, como se ve en la tarjeta (tanda 8, docs/13-plan-tanda-8.md).

    La arma la aplicación con las cifras de pedidos/calculos.py: Claude nunca la escribe.
    """

    titulo: str  # "Pedido nuevo", "Abono de hoy", "Tela", "Tallas", "Gasto de hoy"
    detalle: str  # "Colegio Nuevo Amanecer · 30 uniformes de diario · ..."
    valor: int | None = None  # pesos, a la derecha
    aviso: str = ""  # en ámbar debajo: lo que falta o no alcanza ("Te faltan 48 m de dril azul.")


class ErrorDeHerramienta(Exception):
    """Su texto va a Claude en el tool_result, con is_error=True."""
