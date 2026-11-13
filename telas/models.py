"""Inventario de telas y su historial de "Entró" y "Usé" (docs/02-modelo-de-datos.md)."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from cuentas.aislamiento import DelTallerQuerySet, ModeloDeTaller


class Tela(ModeloDeTaller):
    nombre = models.CharField("nombre", max_length=60)
    metros = models.DecimalField(
        "metros que quedan", max_digits=8, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    minimo = models.DecimalField(
        "avisar cuando queden", max_digits=8, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="0 = sin aviso.",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "tela"
        verbose_name_plural = "telas"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=Q(metros__gte=0),
                name="tela_metros_no_negativos",
                violation_error_message="Los metros no pueden quedar por debajo de 0.",
            ),
            models.CheckConstraint(
                condition=Q(minimo__gte=0),
                name="tela_minimo_no_negativo",
                violation_error_message="El mínimo no puede ser negativo.",
            ),
        ]

    def __str__(self):
        return self.nombre


class MovimientoTela(models.Model):
    """Un "Entró" (metros positivos) o un "Usé" (metros negativos)."""

    ruta_taller = "tela__taller"

    tela = models.ForeignKey(
        Tela, verbose_name="tela", on_delete=models.CASCADE, related_name="movimientos"
    )
    metros = models.DecimalField("metros", max_digits=8, decimal_places=2)
    fecha = models.DateTimeField("fecha", default=timezone.now)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="quién lo registró",
        on_delete=models.PROTECT,
        related_name="movimientos_de_tela",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)

    objects = DelTallerQuerySet.as_manager()

    class Meta:
        verbose_name = "movimiento de tela"
        verbose_name_plural = "movimientos de tela"
        ordering = ["-fecha", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(metros=0),
                name="movimiento_de_tela_distinto_de_0",
                violation_error_message="El movimiento no puede ser de 0 metros.",
            ),
        ]

    def __str__(self):
        return f"{self.tela}: {self.metros} m"
