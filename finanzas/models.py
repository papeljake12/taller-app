"""Gastos del taller (docs/02-modelo-de-datos.md)."""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from cuentas.aislamiento import ModeloDeTaller


class Gasto(ModeloDeTaller):
    class Categoria(models.TextChoices):
        TELAS = "telas", "Telas"
        INSUMOS = "insumos", "Insumos"
        SERVICIOS = "servicios", "Servicios"
        OTROS = "otros", "Otros"

    fecha = models.DateField("fecha", default=timezone.localdate)
    concepto = models.CharField("en qué se gastó", max_length=80)
    categoria = models.CharField(
        "tipo de gasto", max_length=10, choices=Categoria.choices, default=Categoria.OTROS
    )
    valor = models.PositiveIntegerField("valor", validators=[MinValueValidator(1)])
    pedido = models.ForeignKey(
        "pedidos.Pedido",
        verbose_name="pedido",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gastos",
        help_text="Opcional. Sirve para calcular la ganancia por pedido (etapa 3).",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "gasto"
        verbose_name_plural = "gastos"
        ordering = ["-fecha", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="gasto_valor_mayor_que_0",
                violation_error_message="El gasto debe ser mayor que 0.",
            ),
        ]

    def __str__(self):
        return f"{self.concepto} ({self.valor})"

    def clean(self):
        super().clean()
        if self.pedido_id and self.taller_id and self.pedido.taller_id != self.taller_id:
            raise ValidationError({"pedido": "El pedido no es de este taller."})
