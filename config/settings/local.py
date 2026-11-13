"""Ajustes del computador de desarrollo."""

from .base import *  # noqa: F403
from .base import BASE_DIR, STATICFILES_DIRS, entorno

DEBUG = entorno.booleano("DJANGO_DEBUG", True)

# Las fotos de ejemplo de diseno/img/ se ven en la página interna "Piezas" como
# /static/ejemplo/... Solo en desarrollo: no se publican en el servidor.
STATICFILES_DIRS = [*STATICFILES_DIRS, ("ejemplo", BASE_DIR / "diseno" / "img")]
