"""Ajustes para las pruebas automáticas (`uv run pytest`).

Las pruebas crean su propia base de datos temporal (test_taller) y la borran al
terminar. Nunca tocan los datos de la base de trabajo.
"""

from .base import *  # noqa: F403

DEBUG = False

# Guardar contraseñas de forma rápida. Solo en pruebas: así corren en segundos.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
