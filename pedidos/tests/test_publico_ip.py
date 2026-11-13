"""La dirección real de quien envía la talla, también detrás de NGINX (T24).

En el servidor todas las peticiones llegan a Django desde NGINX (127.0.0.1), y NGINX anota la
dirección real en X-Forwarded-For y X-Real-IP. Solo se les cree a esos encabezados cuando la
petición viene de una dirección de confianza (settings.PROXIES_DE_CONFIANZA).
"""

import pytest
from axes.helpers import get_client_ip_address
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.urls import reverse

from pedidos.models import Talla
from pedidos.vistas import publico
from tests import fabricas
from tests.fabricas import CLAVE

NGINX = "127.0.0.1"
CELULAR = "198.51.100.7"
OTRO_CELULAR = "198.51.100.8"
INVENTADA = "203.0.113.99"


def peticion(remota=NGINX, **encabezados):
    return RequestFactory().get("/", REMOTE_ADDR=remota, **encabezados)


def ip(remota=NGINX, **encabezados):
    return publico._ip(peticion(remota, **encabezados))


# --- Sin NGINX: la dirección con la que llega -----------------------------------------------


def test_sin_encabezados_usa_la_direccion_con_la_que_llega():
    assert ip(remota=CELULAR) == CELULAR
    assert ip(remota=NGINX) == NGINX


def test_desde_una_direccion_que_no_es_de_confianza_no_cree_en_los_encabezados():
    # Un celular que habla directo con Django e inventa los encabezados para saltarse el límite.
    resultado = ip(remota=CELULAR, HTTP_X_FORWARDED_FOR=INVENTADA, HTTP_X_REAL_IP=INVENTADA)

    assert resultado == CELULAR


# --- Detrás de NGINX: la dirección real -------------------------------------------------------


def test_desde_nginx_lee_la_direccion_real_de_x_forwarded_for():
    assert ip(HTTP_X_FORWARDED_FOR=CELULAR) == CELULAR


def test_desde_nginx_por_ipv6_tambien_cree_en_el_encabezado():
    assert ip(remota="::1", HTTP_X_FORWARDED_FOR=CELULAR) == CELULAR


def test_toma_la_ultima_direccion_la_que_agrego_nginx_no_la_que_invento_el_celular():
    # El celular manda "X-Forwarded-For: INVENTADA" y NGINX le agrega al final la real.
    assert ip(HTTP_X_FORWARDED_FOR=f"{INVENTADA}, {CELULAR}") == CELULAR


def test_salta_las_direcciones_de_confianza_al_final_de_la_lista():
    assert ip(HTTP_X_FORWARDED_FOR=f"{INVENTADA}, {CELULAR}, 127.0.0.1") == CELULAR


def test_sin_x_forwarded_for_usa_x_real_ip():
    assert ip(HTTP_X_REAL_IP=CELULAR) == CELULAR


def test_un_encabezado_que_no_es_una_direccion_no_se_usa():
    assert ip(HTTP_X_FORWARDED_FOR="no-es-una-ip") == NGINX
    assert ip(HTTP_X_FORWARDED_FOR=f"{INVENTADA}, basura") == NGINX
    assert ip(HTTP_X_FORWARDED_FOR="basura", HTTP_X_REAL_IP=CELULAR) == CELULAR
    assert ip(HTTP_X_REAL_IP="<script>") == NGINX


def test_las_direcciones_de_confianza_se_pueden_cambiar_en_los_ajustes(settings):
    settings.PROXIES_DE_CONFIANZA = ["10.0.0.5"]

    assert ip(remota="10.0.0.5", HTTP_X_FORWARDED_FOR=CELULAR) == CELULAR
    # 127.0.0.1 ya no es de confianza: se usa tal cual.
    assert ip(remota=NGINX, HTTP_X_FORWARDED_FOR=CELULAR) == NGINX


def test_por_defecto_solo_confia_en_el_mismo_servidor(settings):
    assert settings.PROXIES_DE_CONFIANZA == ["127.0.0.1", "::1"]


# --- El límite por minuto cuenta por celular detrás de NGINX -----------------------------------


@pytest.fixture
def pedido(taller):
    cache.clear()
    yield fabricas.crear_pedido(taller)
    cache.clear()


def enviar(client, pedido, nombre):
    direccion = reverse("pedidos:publico_tallas", args=[pedido.token_tallas])
    return client.post(direccion, {"nombre": nombre, "talla": "M"})


def detras_de_nginx(direccion_real):
    """Un navegador de prueba cuyas peticiones llegan como las pasa NGINX."""
    return Client(REMOTE_ADDR=NGINX, HTTP_X_FORWARDED_FOR=direccion_real)


def test_detras_de_nginx_el_limite_es_por_celular_y_no_para_todos_juntos(pedido):
    celular = detras_de_nginx(CELULAR)
    for numero in range(publico.LIMITE):
        assert enviar(celular, pedido, f"Persona {numero}").status_code == 302
    assert enviar(celular, pedido, "Una de más").status_code == 429

    # Otro celular, que también llega por NGINX, todavía puede enviar.
    assert enviar(detras_de_nginx(OTRO_CELULAR), pedido, "Otra persona").status_code == 302
    assert Talla.objects.filter(pedido=pedido).count() == publico.LIMITE + 1


def test_inventar_el_encabezado_no_salta_el_limite(pedido):
    # NGINX siempre agrega la dirección real al final; lo que el celular invente queda antes.
    for numero in range(publico.LIMITE):
        falso = Client(REMOTE_ADDR=NGINX, HTTP_X_FORWARDED_FOR=f"10.9.9.{numero}, {CELULAR}")
        enviar(falso, pedido, f"Persona {numero}")

    otro_intento = Client(REMOTE_ADDR=NGINX, HTTP_X_FORWARDED_FOR=f"10.8.8.8, {CELULAR}")
    assert enviar(otro_intento, pedido, "Una de más").status_code == 429


# --- django-axes usa la misma dirección para bloquear -----------------------------------------


def test_axes_bloquea_por_la_direccion_real_y_no_por_la_de_nginx():
    assert get_client_ip_address(peticion(HTTP_X_FORWARDED_FOR=CELULAR)) == CELULAR
    assert get_client_ip_address(peticion(remota=CELULAR, HTTP_X_FORWARDED_FOR=INVENTADA)) == (
        CELULAR
    )


def test_detras_de_nginx_el_bloqueo_al_entrar_es_solo_en_ese_celular(duena):
    celular = detras_de_nginx(CELULAR)
    for _ in range(5):
        celular.post("/entrar/", {"username": duena.username, "password": "otra-clave"})

    datos = {"username": duena.username, "password": CLAVE}
    assert celular.post("/entrar/", datos).status_code == 429
    # La misma usuaria desde otro celular, que también llega por NGINX, sí entra.
    assert detras_de_nginx(OTRO_CELULAR).post("/entrar/", datos).status_code == 302
