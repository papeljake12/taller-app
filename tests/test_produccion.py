"""Los ajustes del servidor (config/settings/produccion.py, T24).

Nada de esto toca un servidor de verdad: se cargan los ajustes con valores falsos y se revisa
que Django los acepte, que falten datos se note con un mensaje claro, y que los archivos
estáticos salgan como los entregará Whitenoise.
"""

import importlib
import os
import re
import subprocess
import sys

import pytest
from django.conf import settings as ajustes_de_django
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import Client

import config.settings as paquete_de_ajustes
from config import entorno

RAIZ = ajustes_de_django.BASE_DIR

# Valores falsos, solo para las pruebas. El dominio .invalid no existe en internet.
CLAVE_FALSA = "clave-falsa-solo-para-pruebas-" + "x1y2z3" * 8
DOMINIO = "taller.ejemplo.invalid"
VALIDAS = {
    "DJANGO_SECRET_KEY": CLAVE_FALSA,
    "DJANGO_ALLOWED_HOSTS": DOMINIO,
    "DJANGO_CSRF_TRUSTED_ORIGINS": f"https://{DOMINIO}",
    "DB_NAME": "base_falsa",
    "DB_USER": "usuario_falso",
}
VARIABLES = [
    *VALIDAS,
    "DJANGO_DEBUG",
    "DJANGO_HSTS_SEGUNDOS",
    "DJANGO_STATIC_ROOT",
    "DJANGO_MEDIA_ROOT",
]


@pytest.fixture
def cargar_produccion(monkeypatch):
    """Importa produccion.py de nuevo con las variables que se le pasen, y sin leer el .env.

    Al terminar la prueba todo vuelve a como estaba (variables, módulos ya importados).
    """

    def cargar(**variables):
        monkeypatch.setattr(entorno, "cargar", lambda ruta: None)
        for nombre in VARIABLES:
            monkeypatch.delenv(nombre, raising=False)
        for nombre, valor in variables.items():
            monkeypatch.setenv(nombre, valor)
        for modulo in ("base", "produccion"):
            monkeypatch.delitem(sys.modules, f"config.settings.{modulo}", raising=False)
            monkeypatch.setattr(
                paquete_de_ajustes, modulo, getattr(paquete_de_ajustes, modulo, None),
                raising=False,
            )
        return importlib.import_module("config.settings.produccion")

    return cargar


# --- Faltan datos: falla con un mensaje claro -------------------------------------------------


def test_sin_clave_secreta_no_arranca_y_dice_cual_falta(cargar_produccion):
    sin_clave = {k: v for k, v in VALIDAS.items() if k != "DJANGO_SECRET_KEY"}

    with pytest.raises(ImproperlyConfigured, match="Falta la variable DJANGO_SECRET_KEY"):
        cargar_produccion(**sin_clave)


@pytest.mark.parametrize("clave", ["corta", "django-insecure-" + "a1b2c3" * 10, "x" * 60])
def test_una_clave_corta_o_de_ejemplo_no_sirve(cargar_produccion, clave):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY es muy corta"):
        cargar_produccion(**{**VALIDAS, "DJANGO_SECRET_KEY": clave})


@pytest.mark.parametrize("nombre", ["DJANGO_ALLOWED_HOSTS", "DJANGO_CSRF_TRUSTED_ORIGINS"])
def test_el_dominio_es_obligatorio(cargar_produccion, nombre):
    with pytest.raises(ImproperlyConfigured, match=f"Falta la variable {nombre}"):
        cargar_produccion(**{**VALIDAS, nombre: ""})


def test_las_direcciones_de_confianza_deben_ser_https(cargar_produccion):
    with pytest.raises(ImproperlyConfigured, match="debe empezar por https://"):
        cargar_produccion(**{**VALIDAS, "DJANGO_CSRF_TRUSTED_ORIGINS": f"http://{DOMINIO}"})


# --- Con datos válidos ------------------------------------------------------------------------


def test_debug_siempre_apagado_aunque_el_env_diga_lo_contrario(cargar_produccion):
    produccion = cargar_produccion(**VALIDAS, DJANGO_DEBUG="True")

    assert produccion.DEBUG is False


def test_lee_el_dominio_del_env(cargar_produccion):
    produccion = cargar_produccion(
        **{**VALIDAS, "DJANGO_ALLOWED_HOSTS": f"{DOMINIO}, www.{DOMINIO}"}
    )

    assert produccion.ALLOWED_HOSTS == [DOMINIO, f"www.{DOMINIO}"]
    assert produccion.CSRF_TRUSTED_ORIGINS == [f"https://{DOMINIO}"]


def test_https_detras_de_nginx(cargar_produccion):
    produccion = cargar_produccion(**VALIDAS)

    assert produccion.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert produccion.SECURE_SSL_REDIRECT is True
    assert produccion.SESSION_COOKIE_SECURE is True
    assert produccion.CSRF_COOKIE_SECURE is True
    assert produccion.SECURE_HSTS_SECONDS == 3600
    assert produccion.SECURE_HSTS_PRELOAD is False
    assert produccion.X_FRAME_OPTIONS == "DENY"
    assert produccion.SECURE_CONTENT_TYPE_NOSNIFF is True


def test_hsts_se_sube_desde_el_env(cargar_produccion):
    produccion = cargar_produccion(**VALIDAS, DJANGO_HSTS_SEGUNDOS="31536000")

    assert produccion.SECURE_HSTS_SECONDS == 31536000


def test_whitenoise_va_justo_despues_de_security_middleware(cargar_produccion):
    produccion = cargar_produccion(**VALIDAS)
    seguridad = produccion.MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")

    assert produccion.MIDDLEWARE[seguridad + 1] == "whitenoise.middleware.WhiteNoiseMiddleware"
    assert produccion.STORAGES["staticfiles"]["BACKEND"] == (
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )
    # Los demás ajustes no cambian: base.py no gana Whitenoise.
    assert "whitenoise.middleware.WhiteNoiseMiddleware" not in ajustes_de_django.MIDDLEWARE


def test_las_carpetas_se_pueden_escoger_en_el_env(cargar_produccion):
    produccion = cargar_produccion(
        **VALIDAS, DJANGO_STATIC_ROOT="/srv/taller/static", DJANGO_MEDIA_ROOT="/srv/taller/media"
    )

    assert produccion.STATIC_ROOT == "/srv/taller/static"
    assert produccion.MEDIA_ROOT == "/srv/taller/media"


def test_la_cache_es_compartida_entre_los_procesos_de_gunicorn(cargar_produccion):
    produccion = cargar_produccion(**VALIDAS)

    assert produccion.CACHES["default"]["BACKEND"] == (
        "django.core.cache.backends.db.DatabaseCache"
    )


def test_los_registros_van_a_la_consola(cargar_produccion):
    produccion = cargar_produccion(**VALIDAS)

    assert produccion.LOGGING["handlers"]["consola"]["class"] == "logging.StreamHandler"


# --- Cómo se escoge el archivo de ajustes -----------------------------------------------------


def test_sin_escoger_ajustes_usa_el_valor_por_defecto(monkeypatch, tmp_path):
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "")

    entorno.elegir_ajustes(tmp_path, "config.settings.produccion")

    assert os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings.produccion"


def test_el_env_del_servidor_escoge_los_ajustes(monkeypatch, tmp_path):
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE")
    (tmp_path / ".env").write_text(
        "DJANGO_SETTINGS_MODULE=config.settings.produccion\n", encoding="utf-8"
    )

    entorno.elegir_ajustes(tmp_path, "config.settings.local")

    assert os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings.produccion"


def test_gunicorn_usa_produccion_y_manage_py_desarrollo_por_defecto():
    assert '"config.settings.produccion"' in (RAIZ / "config" / "wsgi.py").read_text("utf-8")
    assert '"config.settings.local"' in (RAIZ / "manage.py").read_text("utf-8")


# --- La revisión de Django para publicar ------------------------------------------------------


def correr_manage(*argumentos, **variables):
    """Corre manage.py en otro proceso con los ajustes de producción y valores falsos."""
    variables_del_proceso = {
        **os.environ,
        **VALIDAS,
        "DJANGO_SETTINGS_MODULE": "config.settings.produccion",
        "PYTHONIOENCODING": "utf-8",
        **variables,
    }
    return subprocess.run(
        [sys.executable, "manage.py", *argumentos],
        cwd=RAIZ,
        env=variables_del_proceso,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def test_check_deploy_pasa_sin_avisos():
    resultado = correr_manage("check", "--deploy", "--fail-level", "WARNING")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "no issues" in resultado.stdout


def test_manage_py_sin_clave_secreta_falla_con_un_mensaje_claro():
    # Vacía en el sistema: el .env no la puede rellenar (gana la del sistema).
    resultado = correr_manage("check", DJANGO_SECRET_KEY="")

    assert resultado.returncode != 0
    assert "Falta la variable DJANGO_SECRET_KEY" in resultado.stderr


# --- Archivos estáticos con Whitenoise --------------------------------------------------------


@pytest.mark.django_db
def test_collectstatic_y_whitenoise_entregan_los_estaticos_con_huella(
    cargar_produccion, settings, tmp_path, duena
):
    produccion = cargar_produccion(**VALIDAS)
    settings.STATIC_ROOT = tmp_path
    settings.STORAGES = produccion.STORAGES
    settings.MIDDLEWARE = produccion.MIDDLEWARE

    # Falla si algún estilo apunta a una fuente o imagen que no existe.
    call_command("collectstatic", interactive=False, verbosity=0)

    navegador = Client()
    navegador.force_login(duena)
    pagina = navegador.get("/")
    assert pagina.status_code == 200
    estilos = re.search(r'/static/css/app\.[0-9a-f]{12}\.css', pagina.text)
    assert estilos, "La página no enlaza los estilos con huella"
    assert navegador.get("/entrar/").status_code in (200, 302)

    archivo = navegador.get(estilos.group(0))
    assert archivo.status_code == 200
    # Con huella en el nombre, el navegador lo guarda por mucho tiempo.
    assert "max-age=315360000" in archivo["Cache-Control"]
    comprimido = navegador.get(estilos.group(0), HTTP_ACCEPT_ENCODING="gzip")
    assert comprimido["Content-Encoding"] == "gzip"
