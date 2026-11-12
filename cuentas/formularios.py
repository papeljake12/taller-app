"""Formularios de cuentas: entrar a la aplicación y crear usuarios en el panel."""

from django import forms
from django.contrib.auth.forms import AdminUserCreationForm, AuthenticationForm

from cuentas.models import Usuario

MENSAJE_DATOS_INCORRECTOS = (
    "El usuario o la contraseña no son correctos. Revisa e intenta de nuevo."
)


class EntrarForm(AuthenticationForm):
    """Usuario y contraseña.

    Con datos incorrectos el mensaje es el mismo, falle el usuario o la contraseña, para no
    darle pistas a quien esté adivinando. Una usuaria desactivada recibe el mismo mensaje.
    """

    error_messages = {
        "invalid_login": MENSAJE_DATOS_INCORRECTOS,
        "inactive": MENSAJE_DATOS_INCORRECTOS,
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget = forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        )


class UsuarioCreacionForm(AdminUserCreationForm):
    """Formulario del panel de administración para crear dueñas y costureras."""

    class Meta(AdminUserCreationForm.Meta):
        model = Usuario
        fields = ("username", "taller", "rol", "nombre_visible")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Desde este formulario solo se crean dueñas y costureras, y ellas siempre
        # pertenecen a un taller. El administrador se crea con `createsuperuser`.
        self.fields["taller"].required = True
