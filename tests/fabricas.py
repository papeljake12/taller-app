"""Fábricas de datos para las pruebas.

Crean talleres y usuarias de prueba con valores que no se repiten. Son datos inventados
que solo existen dentro de la base temporal de las pruebas.
"""

import itertools

from cuentas.models import Taller, Usuario

CLAVE = "clave-de-prueba-123"

_numero = itertools.count(1)


def crear_taller(nombre=None, **campos):
    numero = next(_numero)
    return Taller.objects.create(nombre=nombre or f"Taller de prueba {numero}", **campos)


def crear_usuaria(taller, rol=Usuario.Rol.DUENA, username=None, password=CLAVE, **campos):
    numero = next(_numero)
    campos.setdefault("nombre_visible", f"Usuaria {numero}")
    return Usuario.objects.create_user(
        username=username or f"usuaria{numero}",
        password=password,
        taller=taller,
        rol=rol,
        **campos,
    )


def crear_administrador(username="admin", password=CLAVE):
    return Usuario.objects.create_superuser(username=username, email="", password=password)
