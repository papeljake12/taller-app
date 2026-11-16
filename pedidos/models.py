"""Clientes, pedidos, abonos, tallas y materiales (docs/02-modelo-de-datos.md).

La plata va en enteros de pesos. El saldo no se guarda: se calcula en pedidos/calculos.py.
"""

import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone

from cuentas.aislamiento import DelTallerQuerySet, ModeloDeTaller


def nuevo_token():
    """Clave larga y al azar para el enlace público de tallas (32 caracteres)."""
    return secrets.token_urlsafe(24)


class Cliente(ModeloDeTaller):
    class Tipo(models.TextChoices):
        COMPARSA = "comparsa", "Comparsa"
        EMPRESA = "empresa", "Empresa"
        COLEGIO = "colegio", "Colegio"
        PARTICULAR = "particular", "Particular"

    nombre = models.CharField("nombre", max_length=80)
    tipo = models.CharField("tipo", max_length=12, choices=Tipo.choices, default=Tipo.PARTICULAR)
    whatsapp = models.CharField("WhatsApp", max_length=40, blank=True)
    notas = models.TextField("notas", blank=True)
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre"]
        constraints = [
            # Único dentro del taller, sin distinguir mayúsculas.
            models.UniqueConstraint(
                Lower("nombre"),
                F("taller"),
                name="cliente_nombre_unico_en_el_taller",
                violation_error_message="Ya hay un cliente con ese nombre.",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def whatsapp_digitos(self):
        """Solo los dígitos del número, como los pide el enlace de WhatsApp."""
        return "".join(c for c in self.whatsapp if c.isdigit())


class Pedido(ModeloDeTaller):
    class Estado(models.TextChoices):
        COTIZADO = "cotizado", "Cotizado"
        CONFIRMADO = "confirmado", "Confirmado"
        CORTE = "corte", "En corte"
        CONFECCION = "confeccion", "En confección"
        LISTO = "listo", "Listo"
        ENTREGADO = "entregado", "Entregado"

    class Tallaje(models.TextChoices):
        ADULTO = "adulto", "Adulto (XS a XXL)"
        NINO = "nino", "Niño (4 a 16)"

    # Tallas de cada tallaje, en orden. Además de estas, siempre se puede elegir MEDIDA.
    TALLAS = {
        Tallaje.ADULTO: ("XS", "S", "M", "L", "XL", "XXL"),
        Tallaje.NINO: ("4", "6", "8", "10", "12", "14", "16"),
    }
    MEDIDA = "medida"

    cliente = models.ForeignKey(
        Cliente, verbose_name="cliente", on_delete=models.PROTECT, related_name="pedidos"
    )
    detalle = models.CharField("qué pidió", max_length=160)
    cantidad = models.PositiveIntegerField(
        "para cuántas personas", validators=[MinValueValidator(1), MaxValueValidator(2000)]
    )
    tallaje = models.CharField(
        "tallaje", max_length=10, choices=Tallaje.choices, default=Tallaje.ADULTO
    )
    fecha_entrega = models.DateField("fecha de entrega")
    total = models.PositiveIntegerField("valor total")
    estado = models.CharField(
        "etapa", max_length=12, choices=Estado.choices, default=Estado.COTIZADO
    )
    encargada = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="encargada",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_a_cargo",
    )
    foto = models.ImageField("foto", upload_to="pedidos/fotos/", blank=True)
    token_tallas = models.CharField(
        "clave del enlace de tallas", max_length=32, unique=True, default=nuevo_token,
        editable=False,
    )
    tallas_abiertas = models.BooleanField("el enlace de tallas acepta envíos", default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creado por",
        on_delete=models.PROTECT,
        related_name="pedidos_creados",
    )
    por_asistente = models.BooleanField(
        "lo anotó el asistente", default=False,
        help_text="Se guardó con el agente (la dueña tocó Guardar en su borrador).",
    )
    creado = models.DateTimeField("creado", default=timezone.now)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["fecha_entrega", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad__gte=1, cantidad__lte=2000),
                name="pedido_cantidad_de_1_a_2000",
                violation_error_message="La cantidad debe estar entre 1 y 2000.",
            ),
        ]

    def __str__(self):
        return f"{self.cliente} · {self.detalle}"

    @property
    def opciones_de_talla(self):
        """Las tallas que se pueden elegir en este pedido, con "medida" al final."""
        return (*self.TALLAS.get(self.tallaje, ()), self.MEDIDA)

    def clean(self):
        super().clean()
        errores = {}
        if self.cliente_id and self.taller_id and self.cliente.taller_id != self.taller_id:
            errores["cliente"] = "El cliente no es de este taller."
        if self.encargada_id and self.taller_id and self.encargada.taller_id != self.taller_id:
            errores["encargada"] = "La encargada no es de este taller."
        if errores:
            raise ValidationError(errores)


class Abono(models.Model):
    ruta_taller = "pedido__taller"

    pedido = models.ForeignKey(
        Pedido, verbose_name="pedido", on_delete=models.CASCADE, related_name="abonos"
    )
    fecha = models.DateField("fecha", default=timezone.localdate)
    valor = models.PositiveIntegerField("valor", validators=[MinValueValidator(1)])
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        on_delete=models.PROTECT,
        related_name="abonos_registrados",
    )
    por_asistente = models.BooleanField(
        "lo anotó el asistente", default=False,
        help_text="Se guardó con el agente (la dueña tocó Guardar en su borrador).",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)

    objects = DelTallerQuerySet.as_manager()

    class Meta:
        verbose_name = "abono"
        verbose_name_plural = "abonos"
        ordering = ["fecha", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="abono_valor_mayor_que_0",
                violation_error_message="El abono debe ser mayor que 0.",
            ),
        ]

    def __str__(self):
        return f"Abono de {self.valor} al pedido {self.pedido_id}"


class Talla(models.Model):
    """Una fila por persona."""

    class Origen(models.TextChoices):
        ENLACE = "enlace", "La envió el cliente"
        MANUAL = "manual", "Agregada en el taller"

    ruta_taller = "pedido__taller"

    pedido = models.ForeignKey(
        Pedido, verbose_name="pedido", on_delete=models.CASCADE, related_name="tallas"
    )
    nombre = models.CharField("nombre", max_length=60)
    talla = models.CharField("talla", max_length=12)
    pecho = models.DecimalField("pecho (cm)", max_digits=5, decimal_places=1, null=True, blank=True)
    cintura = models.DecimalField(
        "cintura (cm)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    cadera = models.DecimalField("cadera (cm)", max_digits=5, decimal_places=1, null=True, blank=True)
    largo = models.DecimalField("largo (cm)", max_digits=5, decimal_places=1, null=True, blank=True)
    nota = models.CharField("nota", max_length=200, blank=True)
    origen = models.CharField("origen", max_length=8, choices=Origen.choices, default=Origen.MANUAL)
    creado = models.DateTimeField("creado", auto_now_add=True)

    objects = DelTallerQuerySet.as_manager()

    class Meta:
        verbose_name = "talla"
        verbose_name_plural = "tallas"
        ordering = ["creado", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(talla="medida")
                | Q(pecho__isnull=False, cintura__isnull=False, cadera__isnull=False),
                name="talla_a_la_medida_con_pecho_cintura_y_cadera",
                violation_error_message="A la medida hay que anotar pecho, cintura y cadera.",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} · {self.talla}"

    def clean(self):
        super().clean()
        if self.pedido_id and self.talla not in self.pedido.opciones_de_talla:
            raise ValidationError({"talla": "Esa talla no es de este pedido."})
        if self.talla == Pedido.MEDIDA:
            faltan = {
                campo: "Anota esta medida."
                for campo in ("pecho", "cintura", "cadera")
                if getattr(self, campo) is None
            }
            if faltan:
                raise ValidationError(faltan)


class Material(models.Model):
    """Lista de compras de un pedido."""

    ruta_taller = "pedido__taller"

    pedido = models.ForeignKey(
        Pedido, verbose_name="pedido", on_delete=models.CASCADE, related_name="materiales"
    )
    nombre = models.CharField("nombre", max_length=60)
    cantidad = models.CharField("cantidad", max_length=30, blank=True)
    comprado = models.BooleanField("comprado", default=False)
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    objects = DelTallerQuerySet.as_manager()

    class Meta:
        verbose_name = "material"
        verbose_name_plural = "materiales"
        ordering = ["creado", "pk"]

    def __str__(self):
        return self.nombre
