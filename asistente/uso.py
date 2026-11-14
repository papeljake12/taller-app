"""El cupo de preguntas de cada taller y lo que cuesta cada pregunta.

Carril D (T34) completa `cupo`, `reservar`, `devolver` y `anotar`. `costo_usd` lo deja hecho
la base (T25) porque lo usa el panel de administración.

Reglas (docs/11-plan-tanda-7.md, sección 1.6):
- Los límites son los del taller (`Taller.asistente_limite_mes` y `_dia`); 0 lo apaga.
- El día y el mes se cuentan en la hora de Bogotá.
- `reservar` es atómico: bloquea la fila del taller, revisa el cupo y suma 1.
- `pocas` es True si quedan 5 o menos hoy, o el 10 % o menos del mes.

Lo que se cuenta son preguntas, no plata: la plata la ve solo David, en /admin.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from asistente.contratos import Uso
from config.piezas import dia_y_mes

UN_MILLON = Decimal(1_000_000)
POCAS_DEL_DIA = 5  # quedan 5 o menos hoy...
POCAS_DEL_MES_PCT = 10  # ...o el 10 % o menos del mes


def _primero_del_mes_siguiente(hoy: date) -> date:
    if hoy.month == 12:
        return date(hoy.year + 1, 1, 1)
    return date(hoy.year, hoy.month + 1, 1)


def _preguntas(numero: int) -> str:
    return "1 pregunta" if numero == 1 else f"{numero} preguntas"


def _te_quedan(numero: int) -> str:
    return f"Te {'queda' if numero == 1 else 'quedan'} {_preguntas(numero)}"


@dataclass(frozen=True)
class Cupo:
    usadas_hoy: int
    limite_dia: int
    usadas_mes: int
    limite_mes: int
    hoy: date | None = None  # el día (de Bogotá) con que se contó: para decir cuándo vuelve

    @property
    def quedan_hoy(self) -> int:
        return max(0, self.limite_dia - self.usadas_hoy)

    @property
    def quedan_mes(self) -> int:
        return max(0, self.limite_mes - self.usadas_mes)

    @property
    def quedan(self) -> int:
        """Las que todavía se pueden hacer hoy: manda el límite que se acabe primero."""
        return min(self.quedan_hoy, self.quedan_mes)

    @property
    def porcentaje_mes(self) -> int:
        """Cuánto del mes ya se usó, de 0 a 100 (entero: es el ancho del riel)."""
        if self.limite_mes <= 0:
            return 100
        return min(100, self.usadas_mes * 100 // self.limite_mes)

    @property
    def agotado(self) -> str:
        """'' si aún hay cupo, 'dia' o 'mes' si se acabó.

        Si se acabaron los dos, dice 'mes': esperar a mañana no serviría.
        """
        if self.quedan_mes <= 0:
            return "mes"
        if self.quedan_hoy <= 0:
            return "dia"
        return ""

    @property
    def pocas_de(self) -> str:
        """'dia' o 'mes' si quedan pocas de ese límite; '' si hay de sobra o si ya no hay.

        Si los dos andan bajos, manda el que deja menos preguntas.
        """
        if self.agotado:
            return ""
        del_dia = self.quedan_hoy <= POCAS_DEL_DIA
        del_mes = self.quedan_mes * 100 <= self.limite_mes * POCAS_DEL_MES_PCT
        if del_dia and (not del_mes or self.quedan_hoy <= self.quedan_mes):
            return "dia"
        if del_mes:
            return "mes"
        return ""

    @property
    def pocas(self) -> bool:
        """Quedan 5 o menos hoy, o el 10 % o menos del mes (y todavía queda alguna)."""
        return bool(self.pocas_de)

    @property
    def vuelve_el(self) -> date:
        """El día en que el conteo del mes vuelve a cero: el 1 del mes que sigue."""
        return _primero_del_mes_siguiente(self.hoy or timezone.localdate())

    @property
    def aviso(self) -> str:
        """La línea ámbar de "quedan pocas" (vacía si no hace falta)."""
        if self.pocas_de == "dia":
            return (
                f"{_te_quedan(self.quedan_hoy)} por hoy. "
                f"Mañana vuelves a tener {self.limite_dia}."
            )
        if self.pocas_de == "mes":
            return (
                f"{_te_quedan(self.quedan_mes)} este mes. "
                f"El {dia_y_mes(self.vuelve_el)} vuelves a tener {self.limite_mes}."
            )
        return ""

    @property
    def mensaje_limite(self) -> str:
        """Lo que dice el asistente cuando ya no hay preguntas (vacío si todavía hay)."""
        if self.agotado == "mes":
            return (
                f"Este mes ya usaste las {self.limite_mes} preguntas. "
                f"Vuelvo a contestar el {dia_y_mes(self.vuelve_el)}."
            )
        if self.agotado == "dia":
            return (
                f"Por hoy ya usaste las {self.limite_dia} preguntas. "
                "Mañana vuelvo a contestar."
            )
        return ""

    @property
    def vuelve(self) -> str:
        """Lo que dice la caja apagada: "Vuelvo a contestar mañana" (o "el 1 de diciembre")."""
        if self.agotado == "mes":
            return f"Vuelvo a contestar el {dia_y_mes(self.vuelve_el)}"
        if self.agotado == "dia":
            return "Vuelvo a contestar mañana"
        return ""


def _contar(taller, hoy, limite_dia, limite_mes) -> Cupo:
    from asistente.models import UsoAsistente

    del_mes = UsoAsistente.objects.del_taller(taller).filter(
        fecha__year=hoy.year, fecha__month=hoy.month
    )
    usadas_mes = del_mes.aggregate(total=Sum("preguntas"))["total"] or 0
    usadas_hoy = del_mes.filter(fecha=hoy).values_list("preguntas", flat=True).first() or 0
    return Cupo(
        usadas_hoy=usadas_hoy,
        limite_dia=limite_dia,
        usadas_mes=usadas_mes,
        limite_mes=limite_mes,
        hoy=hoy,
    )


def cupo(taller, hoy=None) -> Cupo:
    """Cuántas preguntas lleva el taller hoy y este mes, con sus límites."""
    hoy = hoy or timezone.localdate()
    return _contar(taller, hoy, taller.asistente_limite_dia, taller.asistente_limite_mes)


def reservar(taller, hoy=None) -> bool:
    """Aparta una pregunta antes de llamar a Claude. False si ya no hay cupo.

    Bloquea la fila del taller mientras revisa y suma, para que dos preguntas al mismo
    tiempo no se pasen del límite. Los límites se leen de la base en ese momento: los que
    David tenga puestos en /admin.
    """
    from asistente.models import UsoAsistente
    from cuentas.models import Taller

    hoy = hoy or timezone.localdate()
    with transaction.atomic():
        fila = Taller.objects.select_for_update().get(pk=taller.pk)
        actual = _contar(fila, hoy, fila.asistente_limite_dia, fila.asistente_limite_mes)
        if actual.agotado:
            return False
        dia, _ = UsoAsistente.objects.get_or_create(taller=fila, fecha=hoy)
        UsoAsistente.objects.filter(pk=dia.pk).update(preguntas=F("preguntas") + 1)
    return True


def devolver(taller, hoy=None) -> None:
    """Devuelve la pregunta apartada cuando Claude no llegó a contestar. Nunca baja de 0."""
    from asistente.models import UsoAsistente

    hoy = hoy or timezone.localdate()
    UsoAsistente.objects.del_taller(taller).filter(fecha=hoy, preguntas__gt=0).update(
        preguntas=F("preguntas") - 1
    )


def anotar(taller, uso: Uso, hoy=None) -> None:
    """Suma al día los tokens de una pregunta, de los cuatro tipos."""
    from asistente.models import UsoAsistente

    if not uso.total:
        return
    hoy = hoy or timezone.localdate()
    dia, _ = UsoAsistente.objects.get_or_create(taller=taller, fecha=hoy)
    UsoAsistente.objects.filter(pk=dia.pk).update(
        tokens_entrada=F("tokens_entrada") + uso.entrada,
        tokens_salida=F("tokens_salida") + uso.salida,
        tokens_cache_escritura=F("tokens_cache_escritura") + uso.cache_escritura,
        tokens_cache_lectura=F("tokens_cache_lectura") + uso.cache_lectura,
    )


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
