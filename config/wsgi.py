"""Punto de entrada para el servidor (Gunicorn). La configuración de producción llega en T24."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_wsgi_application()
