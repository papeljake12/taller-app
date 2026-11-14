"""El cupo de preguntas de cada taller y lo que cuesta cada pregunta.

Carril D (T34) completa `cupo`, `reservar`, `devolver` y `anotar`. `costo_usd` lo deja hecho
la base (T25) porque lo usa el panel de administración.

Reglas (docs/11-plan-tanda-7.md, sección 1.6):
- Los límites son los del taller (`Taller.asistente_limite_mes` y `_dia`); 0 lo apaga.
- El día y el mes se cuentan en la hora de Bogotá.
- `reservar` es atómico: bloquea la fila del taller, revisa el cupo y suma 1.
- `pocas` es True si quedan 5 o menos hoy, o el 10 % o menos del mes.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from asistente.contratos import Uso

UN_MILLON = Decimal(1_000_000)


@dataclass(frozen=True)
class Cupo:
    usadas_hoy: int
    limite_dia: int
    usadas_mes: int
    limite_mes: int

    @property
    def quedan(self) -> int:
        raise NotImplementedError("Carril D (T34)")

    @property
    def porcentaje_mes(self) -> int:
        raise NotImplementedError("Carril D (T34)")

    @property
    def agotado(self) -> str:
        """'' si aún hay cupo, 'dia' o 'mes' si se acabó."""
        raise NotImplementedError("Carril D (T34)")

    @property
    def pocas(self) -> bool:
        raise NotImplementedError("Carril D (T34)")


def cupo(taller, hoy=None) -> Cupo:
    raise NotImplementedError("Carril D (T34)")


def reservar(taller, hoy=None) -> bool:
    raise NotImplementedError("Carril D (T34)")


def devolver(taller, hoy=None) -> None:
    raise NotImplementedError("Carril D (T34)")


def anotar(taller, uso: Uso, hoy=None) -> None:
    raise NotImplementedError("Carril D (T34)")


def costo_usd(uso: Uso) -> Decimal:
    """Lo que cuestan esos tokens en dólares, con los precios de los ajustes. Sin float."""
    precios = settings.ASISTENTE_PRECIOS_USD
    centavos_por_millon = (
        uso.entrada * precios["entrada"]
        + uso.salida * precios["salida"]
        + uso.cache_escritura * precios["cache_escritura"]
        + uso.cache_lectura * precios["cache_lectura"]
    )
    return centavos_por_millon / UN_MILLON
