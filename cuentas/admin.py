"""Panel de administración: aquí David crea los talleres y sus usuarias."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from cuentas.formularios import UsuarioCreacionForm
from cuentas.models import Taller, Usuario

admin.site.site_header = "Administración de los talleres"
admin.site.site_title = "Administración"
admin.site.index_title = "Talleres y usuarios"


class SinAgregar:
    """Para los datos de un taller: se ven y se corrigen aquí, pero nacen en la aplicación.

    El taller de cada registro no se puede elegir en el panel (lo pone siempre la
    aplicación), así que crear uno desde aquí no tendría taller.
    """

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Taller)
class TallerAdmin(admin.ModelAdmin):
    list_display = [
        "nombre",
        "telefono",
        "asistente_limite_mes",
        "asistente_limite_dia",
        "preguntas_del_mes",
        "creado",
    ]
    search_fields = ["nombre"]
    readonly_fields = ["preguntas_del_mes"]
    fieldsets = (
        (None, {"fields": ("nombre", "telefono", "logo")}),
        (
            "Asistente",
            {
                "fields": ("asistente_limite_mes", "asistente_limite_dia", "preguntas_del_mes"),
                "description": (
                    "El asistente viene apagado. Para prenderlo, pon 600 al mes y 40 al día. "
                    "0 en cualquiera de los dos lo vuelve a apagar."
                ),
            },
        ),
    )

    @admin.display(description="preguntas este mes")
    def preguntas_del_mes(self, obj):
        from django.db.models import Sum
        from django.utils import timezone

        from asistente.models import UsoAsistente

        if not obj.pk:
            return 0
        inicio = timezone.localdate().replace(day=1)
        usos = UsoAsistente.objects.del_taller(obj).filter(fecha__gte=inicio)
        return usos.aggregate(suma=Sum("preguntas"))["suma"] or 0


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCreacionForm
    list_display = ["username", "nombre_visible", "taller", "rol", "is_active", "is_superuser"]
    list_filter = ["taller", "rol", "is_active", "is_superuser"]
    search_fields = ["username", "nombre_visible", "first_name", "last_name", "email"]

    _datos_del_taller = ("Taller", {"fields": ("taller", "rol", "nombre_visible")})

    # Los datos del taller van justo después del usuario y la contraseña.
    fieldsets = (UserAdmin.fieldsets[0], _datos_del_taller, *UserAdmin.fieldsets[1:])
    add_fieldsets = (*UserAdmin.add_fieldsets, _datos_del_taller)
