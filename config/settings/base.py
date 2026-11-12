"""Ajustes comunes a todos los entornos.

Cada entorno tiene su archivo, que parte de este:
- local.py: el computador de desarrollo.
- pruebas.py: cuando se corre `uv run pytest`.

Los valores secretos (claves y contraseñas) no se escriben aquí: se leen del archivo .env.
"""

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
    "pedidos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
            ],
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
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
