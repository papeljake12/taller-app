"""Fotos de los pedidos (T13): revisar, reducir y guardar la foto de un pedido.

La foto del pedido es la que pasa en "Trabajos del taller", en la pantalla Hoy.

Al subirla:
1. Se revisa que pese máximo 10 MB y que de verdad sea una foto (no basta con que el
   archivo se llame .jpg: se abre y se lee).
2. Se endereza: los celulares guardan la foto "acostada" y anotan aparte cómo girarla
   (la orientación EXIF). Aquí se gira de verdad, para que se vea derecha en todas partes.
3. Se reduce: el lado largo queda en máximo 1600 px, y se guarda como JPEG de calidad 82.
   Una foto de celular de 4 MB queda en unos 200 a 400 KB, y Hoy carga rápido.
4. Se guarda con un nombre al azar en media/pedidos/fotos/, para que no se pueda adivinar
   la dirección de la foto de otro pedido.

Cambiar o quitar la foto borra el archivo anterior: no quedan fotos sueltas ocupando espacio.
Es lo mismo que hace reducir() en demo/index.html, pero en el servidor.
"""

import secrets
from io import BytesIO

from django import forms
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError


# Lo más que puede pesar el archivo que se sube.
PESO_MAXIMO = 10 * 1024 * 1024  # 10 MB
# Lo más que puede medir la foto antes de reducirla (50 megapíxeles, más que un celular
# normal). Un archivo pequeño puede esconder una imagen enorme que llena la memoria.
PIXELES_MAXIMOS = 50_000_000
# El lado largo de la foto guardada y su calidad JPEG (de 1 a 95).
LADO_MAXIMO = 1600
CALIDAD = 82
# Los formatos de foto que se aceptan. Pillow sabe abrir otros (algunos con programas
# externos); estos son los que llegan de un celular o un computador. JPEG también abre las
# fotos "MPO" de algunas cámaras.
FORMATOS = ("JPEG", "PNG", "WEBP", "AVIF", "GIF", "BMP", "TIFF")

NO_ES_FOTO = "Ese archivo no es una foto."
MUY_PESADA = "La foto pesa más de 10 MB. Elige una más liviana."
MUY_GRANDE = "La foto es demasiado grande. Elige una más pequeña."


class FotoInvalida(Exception):
    """El archivo no sirve como foto. El mensaje dice por qué, para la usuaria."""


def reducir(archivo):
    """La foto lista para guardar: derecha, en RGB, con el lado largo de máximo 1600 px y
    en JPEG. Devuelve un ContentFile con un nombre al azar.

    Si el archivo no es una foto (o pesa o mide demasiado) lanza FotoInvalida.
    """
    if archivo.size > PESO_MAXIMO:
        raise FotoInvalida(MUY_PESADA)
    Image.init()  # carga todos los formatos de Pillow (al empezar solo conoce los más comunes)
    try:
        # Primera lectura: verify() revisa que el archivo esté completo y sea de verdad una
        # imagen, sin dibujarla. Después de verify() hay que volver a abrirlo.
        archivo.seek(0)
        with Image.open(archivo, formats=FORMATOS) as imagen:
            if imagen.width * imagen.height > PIXELES_MAXIMOS:
                raise FotoInvalida(MUY_GRANDE)
            imagen.verify()
        archivo.seek(0)
        with Image.open(archivo, formats=FORMATOS) as imagen:
            # Con JPEG, leerla ya reducida (más rápido y con menos memoria).
            imagen.draft("RGB", (LADO_MAXIMO, LADO_MAXIMO))
            derecha = ImageOps.exif_transpose(imagen)
            derecha = _en_rgb(derecha)
            derecha.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)
            salida = BytesIO()
            derecha.save(salida, "JPEG", quality=CALIDAD, optimize=True)
    except FotoInvalida:
        raise
    except Image.DecompressionBombError as error:
        raise FotoInvalida(MUY_GRANDE) from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, TypeError) as error:
        # Pillow avisa con distintos errores según el daño del archivo: para la usuaria
        # todos son lo mismo.
        raise FotoInvalida(NO_ES_FOTO) from error
    return ContentFile(salida.getvalue(), name=f"{secrets.token_hex(16)}.jpg")


def _en_rgb(imagen):
    """La imagen en colores RGB, como la guarda un JPEG. Lo transparente queda blanco (si
    no, quedaría negro)."""
    if imagen.mode == "P" and "transparency" in imagen.info:
        imagen = imagen.convert("RGBA")
    if imagen.mode in ("RGBA", "LA"):
        fondo = Image.new("RGB", imagen.size, "white")
        fondo.paste(imagen, mask=imagen.getchannel("A"))
        return fondo
    return imagen.convert("RGB")


class FormularioFoto(forms.Form):
    """La foto que se sube para un pedido. Si es válida, `cleaned_data["foto"]` ya viene
    reducida (un ContentFile listo para guardar)."""

    foto = forms.FileField(
        label="Elige una foto",
        error_messages={
            "required": "Elige una foto.",
            "empty": "Ese archivo está vacío. Elige una foto.",
            "invalid": NO_ES_FOTO,
            "missing": "Elige una foto.",
        },
    )

    def clean_foto(self):
        try:
            return reducir(self.cleaned_data["foto"])
        except FotoInvalida as error:
            raise forms.ValidationError(str(error)) from error


def guardar(pedido, contenido):
    """Pone la foto ya reducida en el pedido y borra la que tenía antes."""
    anterior = pedido.foto.name
    pedido.foto.save(contenido.name, contenido, save=False)
    pedido.save(update_fields=["foto", "actualizado"])
    borrar_archivo(pedido.foto.storage, anterior)


def quitar(pedido):
    """Quita la foto del pedido y borra su archivo. Si no tenía, no hace nada."""
    if not pedido.foto:
        return
    anterior = pedido.foto.name
    pedido.foto = ""
    pedido.save(update_fields=["foto", "actualizado"])
    borrar_archivo(pedido.foto.storage, anterior)


def borrar_archivo(almacen, nombre):
    """Borra el archivo de una foto, si existe. Se llama después de guardar el pedido: si
    algo falla antes, la foto anterior sigue en su lugar."""
    if nombre and almacen.exists(nombre):
        almacen.delete(nombre)
