"""Ajustes del servidor (VPS): NGINX recibe a los celulares por https y le pasa cada petición
a Gunicorn, que corre Django con estos ajustes.

Se escogen con DJANGO_SETTINGS_MODULE=config.settings.produccion (en el .env del servidor y
en el servicio de Gunicorn). Todo lo que cambia de un servidor a otro (la clave, el dominio,
la base de datos, las carpetas) se lee del .env. La guía completa, paso a paso, está en
docs/guia-publicacion.md; la explicación de cada ajuste, en docs/bitacora/T24.md.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import BASE_DIR, MIDDLEWARE, SECRET_KEY, entorno

# Nunca se muestran las páginas de error con detalles en el servidor, diga lo que diga el .env.
DEBUG = False

# La clave secreta ya es obligatoria en base.py. Aquí además se exige que sea larga: una clave
# corta o la de ejemplo de Django se puede adivinar.
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY es muy corta o es la de ejemplo. Genera una nueva como dice "
        "docs/guia-publicacion.md (paso 10)."
    )


# Dominio

# Los nombres con los que se entra a la aplicación, por ejemplo: taller.midominio.com
# Son obligatorios: Django rechaza cualquier petición que llegue con otro nombre.
ALLOWED_HOSTS = entorno.lista("DJANGO_ALLOWED_HOSTS", None)

# Las direcciones completas, con https://, desde las que se aceptan formularios. Por
# ejemplo: https://taller.midominio.com
CSRF_TRUSTED_ORIGINS = entorno.lista("DJANGO_CSRF_TRUSTED_ORIGINS", None)
for _origen in CSRF_TRUSTED_ORIGINS:
    if not _origen.startswith("https://"):
        raise ImproperlyConfigured(
            f"Cada dirección de DJANGO_CSRF_TRUSTED_ORIGINS debe empezar por https://, "
            f"no «{_origen}»."
        )


# https

# NGINX recibe la conexión segura (https) y le avisa a Django con el encabezado
# X-Forwarded-Proto. Así Django sabe que la conexión es segura y los enlaces que arma
# (por ejemplo, el enlace de tallas para compartir) empiezan por https://.
# Ojo: NGINX debe escribir siempre ese encabezado (ver herramientas/servidor/nginx-taller.conf).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Si alguien entra por http://, se le manda a https://. NGINX ya lo hace; esto es una segunda
# red por si algún día cambia la configuración de NGINX.
SECURE_SSL_REDIRECT = True

# Las galletas (cookies) de la sesión y del formulario solo viajan por https.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS: le dice al navegador "a este dominio entra siempre por https, durante tanto tiempo".
# Se empieza con una hora (3600 segundos): si algo sale mal con el certificado, el navegador
# lo olvida pronto. Cuando todo lleve una semana funcionando, se sube a un año (31536000)
# cambiando DJANGO_HSTS_SEGUNDOS en el .env. Ver la guía, paso 16.
SECURE_HSTS_SECONDS = int(entorno.texto("DJANGO_HSTS_SEGUNDOS", "3600"))
# Incluir los subdominios obliga también a www.TU_DOMINIO, correo.TU_DOMINIO, etc. a ir por
# https. Solo conviene si todos lo tienen. Si la aplicación va en el dominio principal (@) y
# hay otras cosas en subdominios que solo van por http, se romperían durante todo el tiempo
# de HSTS. Por eso viene apagado y se prende con DJANGO_HSTS_SUBDOMINIOS=True en el .env.
SECURE_HSTS_INCLUDE_SUBDOMAINS = entorno.booleano("DJANGO_HSTS_SUBDOMINIOS", False)
# "Preload" inscribe el dominio en una lista que viene dentro de los navegadores y es muy
# difícil de deshacer. No se usa; por eso se calla el aviso de Django que lo sugiere (W021).
# W005 es el aviso de que los subdominios no están incluidos: es a propósito (ver arriba).
SECURE_HSTS_PRELOAD = False
SILENCED_SYSTEM_CHECKS = ["security.W021", "security.W005"]

# Ninguna otra página puede mostrar la aplicación dentro de un recuadro (iframe): evita que
# una página falsa la ponga debajo de botones engañosos.
X_FRAME_OPTIONS = "DENY"
# El navegador no "adivina" el tipo de un archivo: una foto se trata como foto, nunca como
# programa.
SECURE_CONTENT_TYPE_NOSNIFF = True


# Archivos estáticos (estilos, fuentes, íconos, HTMX): los entrega Whitenoise desde Gunicorn

# Whitenoise va justo después de SecurityMiddleware, como pide su documentación.
MIDDLEWARE = [*MIDDLEWARE]
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

# collectstatic copia aquí todos los archivos estáticos, les pone una huella en el nombre
# (app.3f2a9c.css) y los comprime. Así el navegador los guarda mucho tiempo y, cuando cambian,
# pide la versión nueva sola.
STATIC_ROOT = entorno.texto("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# Archivos subidos (fotos de pedidos y logos): los entrega NGINX, no Django

# Conviene que estén fuera de la carpeta del código, por ejemplo /srv/taller/media: así una
# actualización con git nunca los toca y la copia de seguridad los encuentra en un solo lugar.
# Es obligatoria y sin valor por defecto: NGINX y la copia de seguridad leen las fotos de esa
# misma carpeta. Si por un olvido en el .env Django las guardara en otra, NGINX no las
# mostraría y la copia de cada noche saldría vacía sin que nadie lo notara.
MEDIA_ROOT = entorno.texto("DJANGO_MEDIA_ROOT")


# Caché compartida

# Gunicorn corre varios procesos a la vez. Con la caché por defecto (en la memoria de cada
# proceso), el límite de envíos por minuto del formulario público se contaría por separado
# en cada uno. Guardada en una tabla de la base de datos, todos cuentan juntos.
# La tabla se crea una vez con: uv run python manage.py createcachetable
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_django",
    }
}


# Registro de lo que pasa (logs)

# Todo se escribe en la consola. En el servidor, systemd lo guarda y se lee con
# journalctl -u taller (ver la guía). Los errores salen con todo el detalle.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "consola": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["consola"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["consola"], "level": "INFO", "propagate": False},
        # Intentos fallidos al entrar y bloqueos (los avisos de rutina no se escriben).
        "axes": {"handlers": ["consola"], "level": "WARNING", "propagate": False},
        # Cada pregunta al asistente: taller, vueltas, tokens y esfuerzo. Nunca el texto.
        "asistente": {"handlers": ["consola"], "level": "INFO", "propagate": False},
    },
}
