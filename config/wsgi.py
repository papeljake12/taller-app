"""Punto de entrada para el servidor (Gunicorn).

Gunicorn arranca la aplicación desde aquí: `gunicorn config.wsgi`. Por defecto usa los
ajustes de producción (config/settings/produccion.py), para que el servidor nunca arranque
por descuido con los del computador de desarrollo. DJANGO_SETTINGS_MODULE (en el sistema o
en el .env) puede escoger otros. `runserver` también pasa por aquí, pero para entonces
manage.py ya escogió los ajustes de desarrollo.
"""

from pathlib import Path

from django.core.wsgi import get_wsgi_application

from config import entorno

entorno.elegir_ajustes(Path(__file__).resolve().parent.parent, "config.settings.produccion")

application = get_wsgi_application()
