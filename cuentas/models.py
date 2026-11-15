"""Talleres y usuarias.

Todo en la aplicación cuelga de un Taller. Cada usuaria (dueña o costurera) pertenece a
uno. El administrador (David) no pertenece a ninguno: entra al panel de administración.
"""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q

from cuentas.aislamiento import DelTallerQuerySet


class Taller(models.Model):
    nombre = models.CharField("nombre", max_length=50)
    telefono = models.CharField("teléfono", max_length=40, blank=True)
    logo = models.ImageField("logo", upload_to="talleres/logos/", blank=True)
    # Asistente (docs/10-asistente.md). 0 en cualquiera de los dos lo apaga: así viene cada
    # taller nuevo, y David lo activa en /admin (600 al mes y 40 al día).
    asistente_limite_mes = models.PositiveIntegerField(
        "preguntas al asistente por mes",
        default=0,
        help_text="0 apaga el asistente. Lo normal: 600.",
    )
    asistente_limite_dia = models.PositiveIntegerField(
        "preguntas al asistente por día",
        default=0,
        help_text="0 apaga el asistente. Lo normal: 40.",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "taller"
        verbose_name_plural = "talleres"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class UsuarioManager(UserManager.from_queryset(DelTallerQuerySet)):
    """Crea usuarios (create_user, create_superuser) y filtra por taller (del_taller)."""


class Usuario(AbstractUser):
    """Usuario propio del proyecto, basado en el de Django.

    Se define desde la primera migración porque cambiarlo después es muy difícil.
    La fecha de creación es `date_joined`, que ya trae el usuario de Django.
    """

    class Rol(models.TextChoices):
        DUENA = "duena", "Dueña"
        COSTURERA = "costurera", "Costurera"

    taller = models.ForeignKey(
        Taller,
        verbose_name="taller",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarias",
        help_text="Obligatorio para dueñas y costureras. El administrador no tiene taller.",
    )
    rol = models.CharField("rol", max_length=10, choices=Rol.choices, default=Rol.COSTURERA)
    nombre_visible = models.CharField(
        "nombre visible",
        max_length=40,
        blank=True,
        help_text="Como aparece en «¿Quién lo está haciendo?».",
    )

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.CheckConstraint(
                condition=Q(is_superuser=True) | Q(taller__isnull=False),
                name="usuario_con_taller",
                violation_error_message=(
                    "Las dueñas y las costureras deben pertenecer a un taller."
                ),
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def nombre(self):
        """El nombre para mostrar: el visible, o el completo, o el de usuario."""
        return self.nombre_visible or self.get_full_name() or self.username

    @property
    def es_duena(self):
        return self.rol == self.Rol.DUENA
