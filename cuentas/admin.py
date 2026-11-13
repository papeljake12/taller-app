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
    list_display = ["nombre", "telefono", "creado"]
    search_fields = ["nombre"]


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
