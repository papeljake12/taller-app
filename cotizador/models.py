"""Precios base del cotizador: "Mis prendas" (docs/02-modelo-de-datos.md)."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from cuentas.aislamiento import ModeloDeTaller


class PrendaGuardada(ModeloDeTaller):
    nombre = models.CharField("prenda", max_length=80)
    metros = models.DecimalField(
        "metros de tela por prenda", max_digits=6, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    precio_metro = models.PositiveIntegerField("precio del metro", default=0)
    insumos = models.PositiveIntegerField("insumos", default=0)
    mano_obra = models.PositiveIntegerField("mano de obra", default=0)
    extra = models.PositiveIntegerField("bordado o estampado", default=0)
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "prenda guardada"
        verbose_name_plural = "prendas guardadas"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["taller", "nombre"],
                name="prenda_nombre_unico_en_el_taller",
                violation_error_message="Ya hay una prenda guardada con ese nombre.",
            ),
        ]

    def __str__(self):
        return self.nombre
