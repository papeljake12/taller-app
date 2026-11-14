"""Lo que se guarda del asistente: cuántas preguntas y cuántos tokens gastó cada taller por día.

La conversación no se guarda aquí: vive en la sesión de la usuaria (docs/10-asistente.md).
El costo en dólares se calcula con los precios de los ajustes; no se guarda.
"""

from django.db import models

from asistente.contratos import Uso
from cuentas.aislamiento import ModeloDeTaller


class UsoAsistente(ModeloDeTaller):
    fecha = models.DateField("fecha")
    preguntas = models.PositiveIntegerField("preguntas", default=0)
    tokens_entrada = models.PositiveBigIntegerField("tokens que entran", default=0)
    tokens_salida = models.PositiveBigIntegerField("tokens que salen", default=0)
    tokens_cache_escritura = models.PositiveBigIntegerField(
        "tokens guardados en caché", default=0
    )
    tokens_cache_lectura = models.PositiveBigIntegerField("tokens leídos de caché", default=0)

    class Meta:
        verbose_name = "uso del asistente"
        verbose_name_plural = "uso del asistente"
        ordering = ["-fecha", "taller"]
        constraints = [
            models.UniqueConstraint(fields=["taller", "fecha"], name="uso_asistente_un_dia"),
        ]

    def __str__(self):
        return f"{self.taller} · {self.fecha}"

    @property
    def uso(self):
        """Los tokens del día como `Uso`, para calcular el costo."""
        return Uso(
            entrada=self.tokens_entrada,
            salida=self.tokens_salida,
            cache_escritura=self.tokens_cache_escritura,
            cache_lectura=self.tokens_cache_lectura,
        )
