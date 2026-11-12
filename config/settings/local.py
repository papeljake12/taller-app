"""Ajustes del computador de desarrollo."""

from .base import *  # noqa: F403
from .base import entorno

DEBUG = entorno.booleano("DJANGO_DEBUG", True)
