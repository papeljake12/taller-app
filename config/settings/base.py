"""Ajustes comunes a todos los entornos.

Cada entorno tiene su archivo, que parte de este:
- local.py: el computador de desarrollo.
- pruebas.py: cuando se corre `uv run pytest`.
- produccion.py: el servidor (VPS). Ver docs/guia-publicacion.md.

Los valores secretos (claves y contraseñas) no se escriben aquí: se leen del archivo .env.
"""

from datetime import timedelta
from pathlib import Path

from config import entorno

BASE_DIR = Path(__file__).resolve().parent.parent.parent

entorno.cargar(BASE_DIR / ".env")

SECRET_KEY = entorno.texto("DJANGO_SECRET_KEY")
DEBUG = entorno.booleano("DJANGO_DEBUG", False)
ALLOWED_HOSTS = entorno.lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")


# Aplicaciones

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "cuentas",
    "pedidos",
    "telas",
    "finanzas",
    "cotizador",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Sin sesión, toda pantalla lleva a "Entrar", salvo las marcadas como públicas.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    # Deja a mano el taller de la usuaria (request.taller). Ver cuentas/aislamiento.py.
    "cuentas.aislamiento.TallerMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # django-axes va de último: muestra el aviso de bloqueo cuando corresponde.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # El menú (secciones, sección actual, contadores) en todas las pantallas.
                "config.menu.menu",
            ],
            # {% load piezas %}: íconos, fecha larga y campos. Ver config/piezas.py.
            "libraries": {"piezas": "config.piezas"},
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Base de datos: PostgreSQL

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": entorno.texto("DB_NAME"),
        "USER": entorno.texto("DB_USER"),
        "PASSWORD": entorno.texto("DB_PASSWORD", ""),
        "HOST": entorno.texto("DB_HOST", "localhost"),
        "PORT": entorno.texto("DB_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Usuarias, inicio de sesión y bloqueo por intentos fallidos

AUTH_USER_MODEL = "cuentas.Usuario"

AUTHENTICATION_BACKENDS = [
    # Primero django-axes, que cuenta los intentos fallidos y bloquea.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "cuentas:entrar"
LOGIN_REDIRECT_URL = "pedidos:hoy"
LOGOUT_REDIRECT_URL = "cuentas:entrar"

# La sesión se cierra sola después de 7 días sin usar la aplicación. Cada visita
# vuelve a contar los 7 días desde cero.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
SESSION_SAVE_EVERY_REQUEST = True

# Después de 5 intentos fallidos seguidos, ese usuario queda bloqueado en ese equipo
# (misma dirección de internet) durante 15 minutos.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = "cuentas.vistas.bloqueado"

# Direcciones desde las que llega NGINX (el "portero" del servidor). Solo cuando la petición
# viene de una de ellas se cree en el encabezado X-Forwarded-For, que dice la dirección real
# del celular. Ver config/red.py.
PROXIES_DE_CONFIANZA = ["127.0.0.1", "::1"]
# django-axes cuenta los intentos por usuario y dirección real, no por la de NGINX.
AXES_CLIENT_IP_CALLABLE = "config.red.ip_del_cliente"


# Contraseñas

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Idioma y hora: español de Colombia, hora de Bogotá

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True


# Archivos estáticos (estilos, fuentes, íconos) y archivos subidos (fotos, logos)

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
