"""Formularios de Mi taller (T20): los datos del taller y las costureras.

- FormularioTaller: el nombre, el teléfono y el logo del taller. El logo se revisa y se
  reduce aquí (reducir_logo), con los mismos cuidados que la foto de un pedido
  (pedidos/fotos.py), pero guardando la transparencia de los logos en PNG.
- FormularioCostureraNueva: nombre, usuario y contraseña de una costurera nueva.
- FormularioNombre: cambiar el nombre con el que aparece una costurera.

El taller nunca llega del formulario: lo pone la vista con `request.taller`.
"""

import secrets
from io import BytesIO

from django import forms
from django.contrib.auth import password_validation
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from cuentas.models import Taller, Usuario
from pedidos import fotos

# El lado largo del logo guardado. Un logo se ve pequeño (en los recibos, arriba): 512 px
# alcanzan de sobra y el archivo queda liviano.
LADO_DEL_LOGO = 512
# Calidad JPEG de los logos sin transparencia (de 1 a 95). Un poco más alta que la de las
# fotos (82), porque los logos tienen letras y bordes que se notan si se borronean.
CALIDAD_DEL_LOGO = 90

NO_ES_IMAGEN = "Ese archivo no es una imagen. Elige el logo en JPG o PNG."
LOGO_PESADO = "El logo pesa más de 10 MB. Elige uno más liviano."
LOGO_GRANDE = "El logo es demasiado grande. Elige uno más pequeño."

# Los caracteres que puede tener un teléfono y cuántas cifras (un fijo de 7, un celular de
# 10, o con el 57 del país adelante).
CARACTERES_DEL_TELEFONO = set("0123456789 +-().")
CIFRAS_MINIMAS = 7
CIFRAS_MAXIMAS = 15

NOMBRE_REPETIDO = "Ya hay una persona con ese nombre en tu taller. Agrégale el apellido."
USUARIO_REPETIDO = "Ese usuario ya existe. Elige otro, por ejemplo con su apellido."
USUARIO_INVALIDO = "Escribe el usuario sin espacios: solo letras, números y . @ + - _"

# Los mensajes de las reglas de contraseña de Django, con el trato de tú de la aplicación.
MENSAJES_DE_CONTRASENA = {
    "password_too_short": (
        "La contraseña es muy corta: escribe por lo menos {min_length} caracteres."
    ),
    "password_too_common": "Esa contraseña es muy común. Elige una más difícil de adivinar.",
    "password_entirely_numeric": "La contraseña no puede tener solo números. Agrégale letras.",
    "password_too_similar": "La contraseña se parece mucho al usuario. Elige otra.",
}


def enfocar(form, campo_por_defecto=None):
    """Deja el cursor en el primer campo con error o, si no hay errores, en
    `campo_por_defecto`. HTMX pone el cursor en el campo con `autofocus` cuando cambia la
    tarjeta, así quien escribe desde el celular no tiene que volver a tocar el campo."""
    nombre = next((n for n in form.fields if n in form.errors), campo_por_defecto)
    if nombre:
        form.fields[nombre].widget.attrs["autofocus"] = True
    return form


def _un_espacio(texto):
    """'  Ana   María ' -> 'Ana María'."""
    return " ".join((texto or "").split())


# --- El logo -----------------------------------------------------------------------------------


def reducir_logo(archivo):
    """El logo listo para guardar: derecho, con el lado largo de máximo 512 px. Devuelve un
    ContentFile con un nombre al azar.

    Si el logo tiene partes transparentes se guarda en PNG, para que la transparencia no se
    pierda (en JPEG quedaría un fondo de color). Si no, en JPEG, que pesa menos.
    Si el archivo no es una imagen (o pesa o mide demasiado) lanza fotos.FotoInvalida.
    """
    if archivo.size > fotos.PESO_MAXIMO:
        raise fotos.FotoInvalida(LOGO_PESADO)
    Image.init()  # carga todos los formatos de Pillow (al empezar solo conoce los más comunes)
    try:
        # Primera lectura: verify() revisa que sea de verdad una imagen, sin dibujarla.
        archivo.seek(0)
        with Image.open(archivo, formats=fotos.FORMATOS) as imagen:
            if imagen.width * imagen.height > fotos.PIXELES_MAXIMOS:
                raise fotos.FotoInvalida(LOGO_GRANDE)
            imagen.verify()
        archivo.seek(0)
        with Image.open(archivo, formats=fotos.FORMATOS) as imagen:
            derecha = ImageOps.exif_transpose(imagen)
            transparente = _tiene_transparencia(derecha)
            derecha = derecha.convert("RGBA" if transparente else "RGB")
            derecha.thumbnail((LADO_DEL_LOGO, LADO_DEL_LOGO), Image.Resampling.LANCZOS)
            salida = BytesIO()
            if transparente:
                derecha.save(salida, "PNG", optimize=True)
                extension = "png"
            else:
                derecha.save(salida, "JPEG", quality=CALIDAD_DEL_LOGO, optimize=True)
                extension = "jpg"
    except fotos.FotoInvalida:
        raise
    except Image.DecompressionBombError as error:
        raise fotos.FotoInvalida(LOGO_GRANDE) from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, TypeError) as error:
        # Pillow avisa con distintos errores según el daño del archivo: para la usuaria
        # todos son lo mismo.
        raise fotos.FotoInvalida(NO_ES_IMAGEN) from error
    return ContentFile(salida.getvalue(), name=f"{secrets.token_hex(16)}.{extension}")


def _tiene_transparencia(imagen):
    """True si la imagen tiene partes transparentes (un PNG con fondo vacío, por ejemplo)."""
    if imagen.mode in ("RGBA", "LA", "PA"):
        return True
    return "transparency" in imagen.info


def guardar_logo(taller, contenido):
    """Pone el logo ya reducido en el taller y borra el que tenía antes."""
    anterior = taller.logo.name
    taller.logo.save(contenido.name, contenido, save=False)
    taller.save(update_fields=["logo", "actualizado"])
    fotos.borrar_archivo(taller.logo.storage, anterior)


def quitar_logo(taller):
    """Quita el logo del taller y borra su archivo. Si no tenía, no hace nada."""
    if not taller.logo:
        return
    anterior = taller.logo.name
    taller.logo = ""
    taller.save(update_fields=["logo", "actualizado"])
    fotos.borrar_archivo(taller.logo.storage, anterior)


# --- Tu taller ---------------------------------------------------------------------------------


class FormularioTaller(forms.ModelForm):
    """Nombre, teléfono y logo del taller. `guardar()` guarda todo y cambia o quita el logo.

    Si el logo es válido, `cleaned_data["logo"]` ya viene reducido (un ContentFile).
    """

    logo = forms.FileField(
        label="Logo (opcional)",
        required=False,
        help_text="Una imagen JPG o PNG de hasta 10 MB. Se guarda más pequeña.",
        # Un simple "elegir archivo": quitar el logo va en su propia casilla.
        widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/*"}),
        error_messages={
            "empty": "Ese archivo está vacío. Elige el logo en JPG o PNG.",
            "invalid": NO_ES_IMAGEN,
        },
    )
    quitar_logo = forms.BooleanField(label="Quitar el logo", required=False)

    class Meta:
        model = Taller
        fields = ("nombre", "telefono")
        labels = {"nombre": "Nombre del taller", "telefono": "Teléfono (opcional)"}
        help_texts = {
            "nombre": "Aparece en el menú, en los mensajes de WhatsApp y en los recibos.",
            "telefono": "Por ejemplo: 300 123 4567.",
        }
        error_messages = {
            "nombre": {
                "required": "Escribe el nombre del taller.",
                "max_length": "Escribe máximo 50 letras en el nombre.",
            },
            "telefono": {"max_length": "Escribe solo el número, sin más texto."},
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"autocomplete": "organization"}),
            "telefono": forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.logo:
            self.fields["logo"].label = "Cambiar el logo (opcional)"
        else:
            del self.fields["quitar_logo"]

    def clean_nombre(self):
        nombre = _un_espacio(self.cleaned_data["nombre"])
        if not nombre:
            raise forms.ValidationError(
                self.fields["nombre"].error_messages["required"], code="required"
            )
        return nombre

    def clean_telefono(self):
        numero = self.cleaned_data["telefono"].strip()
        if not numero:
            return ""
        cifras = sum(c.isdigit() for c in numero)
        if not set(numero) <= CARACTERES_DEL_TELEFONO or not (
            CIFRAS_MINIMAS <= cifras <= CIFRAS_MAXIMAS
        ):
            raise forms.ValidationError(
                "Revisa el teléfono: escribe solo el número, por ejemplo 300 123 4567.",
                code="invalido",
            )
        return numero

    def clean_logo(self):
        archivo = self.cleaned_data.get("logo")
        if not archivo:
            return None
        try:
            return reducir_logo(archivo)
        except fotos.FotoInvalida as error:
            raise forms.ValidationError(str(error)) from error

    def guardar(self):
        """Guarda el nombre y el teléfono; cambia el logo (si llegó uno) o lo quita (si se
        marcó la casilla). Un logo nuevo gana sobre la casilla de quitar."""
        taller = self.save()
        if self.cleaned_data.get("logo"):
            guardar_logo(taller, self.cleaned_data["logo"])
        elif self.cleaned_data.get("quitar_logo"):
            quitar_logo(taller)
        return taller


# --- Costureras --------------------------------------------------------------------------------


class _NombreDeLaPersona(forms.ModelForm):
    """El nombre visible, que no se repite dentro del taller (sin importar mayúsculas)."""

    def __init__(self, *args, taller, **kwargs):
        super().__init__(*args, **kwargs)
        self.taller = taller
        campo = self.fields["nombre_visible"]
        campo.required = True
        campo.help_text = "Así aparece en «¿Quién lo está haciendo?» de cada pedido."
        campo.error_messages.update({
            "required": "Escribe el nombre de la costurera.",
            "max_length": "Escribe máximo 40 letras en el nombre.",
        })

    def clean_nombre_visible(self):
        nombre = _un_espacio(self.cleaned_data["nombre_visible"])
        if not nombre:
            raise forms.ValidationError(
                self.fields["nombre_visible"].error_messages["required"], code="required"
            )
        repetido = (
            Usuario.objects.del_taller(self.taller)
            .filter(nombre_visible__iexact=nombre)
            .exclude(pk=self.instance.pk)
        )
        if repetido.exists():
            raise forms.ValidationError(NOMBRE_REPETIDO, code="repetido")
        return nombre


class FormularioNombre(_NombreDeLaPersona):
    """Cambiar el nombre con el que aparece una costurera."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", "costurera-nombre-%s")
        super().__init__(*args, **kwargs)

    class Meta:
        model = Usuario
        fields = ("nombre_visible",)
        labels = {"nombre_visible": "Nombre"}
        widgets = {"nombre_visible": forms.TextInput(attrs={"autocomplete": "off"})}


class FormularioCostureraNueva(_NombreDeLaPersona):
    """Una costurera nueva: su nombre, el usuario con el que entra y su contraseña.

    La contraseña pasa por las reglas de contraseña de Django (AUTH_PASSWORD_VALIDATORS) y
    nunca se vuelve a mostrar: si el formulario tiene un error, el campo vuelve vacío.
    """

    contrasena = forms.CharField(
        label="Contraseña",
        strip=False,
        help_text=(
            "Mínimo 8 caracteres, que no sean solo números. Dásela a ella: después no se "
            "vuelve a mostrar."
        ),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        error_messages={"required": "Escribe una contraseña para ella."},
    )

    class Meta:
        model = Usuario
        fields = ("nombre_visible", "username")
        labels = {"nombre_visible": "Nombre", "username": "Usuario"}
        help_texts = {"username": "Con este entra a la aplicación. Sin espacios."}
        error_messages = {
            "username": {
                "required": "Escribe el usuario con el que va a entrar.",
                "max_length": "Escribe máximo 150 letras en el usuario.",
                "unique": USUARIO_REPETIDO,
                "invalid": USUARIO_INVALIDO,
            },
        }
        widgets = {
            "nombre_visible": forms.TextInput(attrs={"autocomplete": "off"}),
            "username": forms.TextInput(
                attrs={"autocomplete": "off", "autocapitalize": "none", "spellcheck": "false"}
            ),
        }

    def __init__(self, *args, taller, **kwargs):
        # La costurera nueva ya es de este taller y con el rol de costurera: no llegan del
        # formulario.
        kwargs.setdefault("instance", Usuario(taller=taller, rol=Usuario.Rol.COSTURERA))
        # "costurera-nueva-nombre_visible"...: el botón "Agregar costurera" de arriba lleva a
        # ese campo, y no se confunde con el del formulario para cambiar el nombre.
        kwargs.setdefault("auto_id", "costurera-nueva-%s")
        super().__init__(*args, taller=taller, **kwargs)

    def clean_username(self):
        usuario = self.cleaned_data["username"].strip()
        # El usuario es de toda la aplicación, no solo del taller: no puede haber dos
        # iguales, ni siquiera con otras mayúsculas ("Marta" y "marta").
        if Usuario.objects.filter(username__iexact=usuario).exists():
            raise forms.ValidationError(USUARIO_REPETIDO, code="repetido")
        return usuario

    def clean(self):
        datos = super().clean()
        contrasena = datos.get("contrasena")
        if contrasena:
            # Las reglas comparan la contraseña con el usuario: se arma uno sin guardar.
            persona = Usuario(
                username=datos.get("username", ""),
                nombre_visible=datos.get("nombre_visible", ""),
            )
            try:
                password_validation.validate_password(contrasena, persona)
            except forms.ValidationError as error:
                self.add_error("contrasena", [_en_tu(e) for e in error.error_list])
        return datos

    def guardar(self):
        """Crea la costurera en el taller. La contraseña se guarda cifrada, nunca tal cual."""
        persona = self.save(commit=False)
        persona.set_password(self.cleaned_data["contrasena"])
        persona.save()
        return persona


def _en_tu(error):
    """El mensaje de una regla de contraseña con el trato de tú. Si es una regla que no
    está en la lista, queda el mensaje de Django (también en español)."""
    mensaje = MENSAJES_DE_CONTRASENA.get(error.code)
    if mensaje is None:
        return error
    return forms.ValidationError(mensaje.format(**(error.params or {})), code=error.code)
