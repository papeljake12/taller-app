"""Lee la configuración del proyecto desde el archivo .env.

El archivo .env tiene una variable por línea, con la forma NOMBRE=valor. Las líneas
vacías y las que empiezan con # se ignoran. Si una variable ya existe en el sistema
(por ejemplo, en el servidor), gana la del sistema y la del archivo no se usa.

Se escribió aquí, en vez de instalar una librería, porque son pocas líneas.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

_VERDADERO = {"true", "1", "si", "sí", "yes"}
_FALSO = {"false", "0", "no"}


def cargar(ruta: Path) -> None:
    """Pasa las variables del archivo a os.environ, sin pisar las que ya existen."""
    if not ruta.exists():
        return
    # utf-8-sig quita la marca invisible que algunos editores de Windows ponen al inicio.
    contenido = ruta.read_text(encoding="utf-8-sig")
    for numero, linea in enumerate(contenido.splitlines(), start=1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        nombre, signo, valor = linea.partition("=")
        nombre = nombre.strip()
        if not signo or not nombre:
            raise ImproperlyConfigured(
                f"La línea {numero} de {ruta.name} debe tener la forma NOMBRE=valor."
            )
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        os.environ.setdefault(nombre, valor)


def texto(nombre: str, defecto: str | None = None) -> str:
    """Devuelve la variable. Sin valor por defecto, es obligatoria."""
    valor = os.environ.get(nombre, "").strip()
    if valor:
        return valor
    if defecto is None:
        raise ImproperlyConfigured(f"Falta la variable {nombre} en el archivo .env.")
    return defecto


def booleano(nombre: str, defecto: bool) -> bool:
    """Devuelve True o False. Acepta True/False, 1/0 y sí/no."""
    valor = os.environ.get(nombre, "").strip().lower()
    if not valor:
        return defecto
    if valor in _VERDADERO:
        return True
    if valor in _FALSO:
        return False
    raise ImproperlyConfigured(f"La variable {nombre} debe ser True o False, no «{valor}».")


def lista(nombre: str, defecto: str = "") -> list[str]:
    """Devuelve una lista a partir de valores separados por comas."""
    return [parte.strip() for parte in texto(nombre, defecto).split(",") if parte.strip()]
