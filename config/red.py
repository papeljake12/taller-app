"""La dirección de internet (IP) real de quien hace la petición.

En el servidor, los celulares no hablan directo con Django: hablan con NGINX, y NGINX le pasa
la petición a Gunicorn desde el mismo servidor (127.0.0.1). Para Django, entonces, todos
llegan desde 127.0.0.1. NGINX anota la dirección real en el encabezado X-Forwarded-For (y en
X-Real-IP).

Ese encabezado lo puede escribir cualquiera, así que solo se le cree cuando la petición viene
de una dirección de confianza (settings.PROXIES_DE_CONFIANZA: por defecto 127.0.0.1 y ::1,
es decir, NGINX en el mismo servidor). Si viene de otra parte, se usa la dirección con la
que llegó.

De X-Forwarded-For se toma la última dirección que no sea de confianza: NGINX agrega la real
al final, y lo que esté más a la izquierda lo pudo inventar el celular.

La usan el límite por minuto del formulario público de tallas (pedidos/vistas/publico.py) y
django-axes, que bloquea por usuario y dirección después de 5 intentos fallidos.
"""

import ipaddress

from django.conf import settings

CONFIANZA_POR_DEFECTO = ("127.0.0.1", "::1")


def _es_ip(valor):
    try:
        ipaddress.ip_address(valor)
    except ValueError:
        return False
    return True


def ip_del_cliente(request):
    remota = request.META.get("REMOTE_ADDR", "")
    confianza = set(getattr(settings, "PROXIES_DE_CONFIANZA", CONFIANZA_POR_DEFECTO))
    if remota not in confianza:
        return remota

    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "")
    for parte in reversed(reenviada.split(",")):
        parte = parte.strip()
        if not _es_ip(parte):
            break
        if parte not in confianza:
            return parte

    real = request.META.get("HTTP_X_REAL_IP", "").strip()
    if _es_ip(real):
        return real
    return remota
