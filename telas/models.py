"""Inventario de telas, su historial de "Entró" y "Usé", y la tela de cada pedido
(docs/02-modelo-de-datos.md)."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
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
    pedido = models.ForeignKey(
        "pedidos.Pedido",
        verbose_name="pedido",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_de_tela",
        help_text="Opcional. El pedido que gastó esta tela (un \"Usé\").",
    )
    por_asistente = models.BooleanField(
        "lo anotó el asistente", default=False,
        help_text="Se guardó con el agente (la dueña tocó Guardar en su borrador).",
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


class TelaPedido(models.Model):
    """Qué tela del inventario usa un pedido y cuántos metros (tanda 8).

    Mientras el pedido está Confirmado, esos metros cuentan como apartados: con eso se sabe si
    la tela alcanza (pedidos/calculos.py). No mueve los metros de la tela: eso lo hace el "Usé".
    """

    ruta_taller = "pedido__taller"

    pedido = models.ForeignKey(
        "pedidos.Pedido", verbose_name="pedido", on_delete=models.CASCADE, related_name="telas"
    )
    tela = models.ForeignKey(
        Tela, verbose_name="tela", on_delete=models.CASCADE, related_name="pedidos"
    )
    metros = models.DecimalField(
        "metros", max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    creado = models.DateTimeField("creado", auto_now_add=True)

    objects = DelTallerQuerySet.as_manager()

    class Meta:
        verbose_name = "tela del pedido"
        verbose_name_plural = "telas del pedido"
        ordering = ["creado", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["pedido", "tela"],
                name="tela_pedido_una_vez_por_pedido",
                violation_error_message="Esa tela ya está en el pedido.",
            ),
            models.CheckConstraint(
                condition=Q(metros__gt=0),
                name="tela_pedido_metros_mayor_que_0",
                violation_error_message="Los metros deben ser más que 0.",
            ),
        ]

    def __str__(self):
        return f"{self.pedido_id}: {self.tela} ({self.metros} m)"

    def clean(self):
        super().clean()
        if self.pedido_id and self.tela_id and self.pedido.taller_id != self.tela.taller_id:
            raise ValidationError({"tela": "La tela no es de este taller."})
