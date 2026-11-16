"""Lo que se guarda del asistente: cuántas preguntas y cuántos tokens gastó cada taller por día,
el resumen de la mañana y los borradores que ya se guardaron (tanda 8).

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


class ResumenDelDia(ModeloDeTaller):
    """El párrafo de la mañana que escribe el agente (T43). Se guarda para no pagarlo cada vez
    que ella abre Hoy. Las cifras no se guardan aquí: las filas de Hoy se calculan al abrir."""

    fecha = models.DateField("fecha")
    texto = models.TextField("texto")
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "resumen del día"
        verbose_name_plural = "resúmenes del día"
        ordering = ["-fecha", "taller"]
        constraints = [
            models.UniqueConstraint(fields=["taller", "fecha"], name="resumen_un_dia"),
        ]

    def __str__(self):
        return f"{self.taller} · {self.fecha}"


class BorradorUsado(ModeloDeTaller):
    """La clave de un borrador que ya se guardó. Única: así un borrador sirve una sola vez,
    aunque lleguen dos toques de Guardar casi al mismo tiempo (decisión de David, 2026-11-15)."""

    clave = models.CharField("clave", max_length=32, unique=True)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "borrador guardado"
        verbose_name_plural = "borradores guardados"
        ordering = ["-creado"]

    def __str__(self):
        return self.clave
