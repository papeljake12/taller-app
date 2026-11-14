"""Hoy (rediseño): el saludo, la caja grande, las tarjetas de lo que hay que hacer y sus
acciones, "Tu mes", la gráfica, "Quién te debe" y "Pedidos por etapa"."""

import re
from datetime import date, datetime, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from pedidos import ejemplos, mensajes
from pedidos.models import Pedido
from pedidos.vistas import hoy as vista
from tests import fabricas

pytestmark = pytest.mark.django_db

HOY = date(2026, 11, 11)  # el miércoles de diseno/hoy.html
PAGINA = reverse("pedidos:hoy")
HTMX = {"HX-Request": "true"}
Estado = Pedido.Estado


@pytest.fixture(autouse=True)
def dia_fijo(monkeypatch):
    """Hoy es siempre HOY, para que las pruebas no dependan del día en que se corren."""
    original = timezone.localdate

    def localdate(value=None, timezone=None):
        return HOY if value is None else original(value, timezone)

    monkeypatch.setattr("django.utils.timezone.localdate", localdate)


@pytest.fixture
def ejemplo(taller, duena):
    """Los pedidos, abonos y gastos de diseno/hoy.html, contados desde HOY."""
    return ejemplos.cargar(taller=taller, hoy=HOY, con_fotos=False)


@pytest.fixture
def sesion_costurera(client, costurera):
    client.force_login(costurera)
    return client


def accion(pedido, nombre):
    return reverse("pedidos:hoy_accion", args=[pedido.pk, nombre])


def pedido_de(taller, cliente="Cliente de prueba", whatsapp="", **campos):
    """Un pedido del taller con su cliente. Por defecto, en confección y para dentro de 30 días."""
    campos.setdefault("estado", Estado.CONFECCION)
    campos.setdefault("fecha_entrega", HOY + timedelta(days=30))
    cliente = fabricas.crear_cliente(taller, nombre=cliente, whatsapp=whatsapp)
    return fabricas.crear_pedido(taller, cliente=cliente, **campos)


def parte(html, id_):
    """El HTML de la parte con ese id, hasta el cierre de su <section>."""
    inicio = html.index(f'id="{id_}"')
    return html[inicio : html.index("</section>", inicio)]


def lista_de(respuesta):
    """Lo de adentro de las tarjetas en la respuesta de una acción: lo que va antes de las
    partes que llegan aparte (hx-swap-oob)."""
    return respuesta[: respuesta.index("hx-swap-oob")]


def tarjetas(html):
    """Los clientes de las tarjetas de lo que hay que hacer, en el orden en que salen."""
    return re.findall(r'<article class="carta" id="pendiente-\d+">.*?<h3><a href="[^"]+">'
                      r"([^<]+)</a></h3>", html, flags=re.S)


def caja_de(html):
    """La caja grande (el menú también tiene un formulario de búsqueda: va antes)."""
    inicio = html.index('<form class="caja-grande"')
    return html[inicio : html.index("</form>", inicio)]


def tarjeta_de(html, pedido):
    inicio = html.index(f'<article class="carta" id="pendiente-{pedido.pk}">')
    return html[inicio : html.index("</article>", inicio)]


# --- La página con los datos del diseño -------------------------------------------------------


def test_el_encabezado_lleva_logo_estado_fecha_lupa_y_nuevo_pedido(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert f'<a class="encabezado__logo" href="{PAGINA}" aria-label="Ir a Hoy">' in html
    lista = reverse("pedidos:lista")
    assert (
        f'<a class="estado" href="{lista}?filtro=atrasados"><span class="estado__punto"></span>'
        "1 pedido atrasado</a>"
    ) in html
    assert 'class="encabezado__apoyo solo-computador">Miércoles, 11 de noviembre' in html
    assert f'href="{reverse("pedidos:buscar")}" aria-label="Buscar"' in html
    assert "boton--redondo-celular solo-celular" in html
    assert ">Nuevo pedido</span>" in html


def test_sin_atrasados_no_hay_estado(sesion_duena, taller):
    pedido_de(taller)

    html = sesion_duena.get(PAGINA).text

    assert 'class="estado"' not in html
    assert 'id="hoy-estado"' in html


def test_varios_atrasados_se_dicen_en_plural(sesion_duena, taller):
    pedido_de(taller, fecha_entrega=HOY - timedelta(days=1))
    pedido_de(taller, cliente="Otro", fecha_entrega=HOY - timedelta(days=3))

    assert "2 pedidos atrasados</a>" in sesion_duena.get(PAGINA).text


@pytest.mark.parametrize(
    "hora, saludo",
    [(0, "¡Buenos días!"), (11, "¡Buenos días!"), (12, "¡Buenas tardes!"),
     (17, "¡Buenas tardes!"), (18, "¡Buenas noches!"), (23, "¡Buenas noches!")],
)
def test_el_saludo_cambia_con_la_hora(hora, saludo):
    assert vista.saludo(datetime(2026, 11, 11, hora, 30)) == saludo


def test_el_saludo_usa_la_hora_de_bogota(sesion_duena, taller, monkeypatch):
    monkeypatch.setattr("django.utils.timezone.localtime", lambda: datetime(2026, 11, 11, 15, 0))

    html = sesion_duena.get(PAGINA).text

    assert (
        "<h1>¡Buenas tardes!<span class=\"bienvenida__resto\"><br>Esto es lo de hoy en "
        f'<span class="bienvenida__taller">{taller.nombre}</span></span></h1>'
    ) in html


@pytest.mark.parametrize(
    "cantidad, frase",
    [(0, "No tienes nada pendiente hoy"), (1, "Tienes 1 cosa pendiente hoy"),
     (3, "Tienes 3 cosas pendientes hoy")],
)
def test_la_frase_de_cosas_pendientes(cantidad, frase):
    assert vista.frase_de_pendientes(cantidad) == frase


def test_la_frase_de_pendientes_sale_en_la_pagina(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert '<p class="bienvenida__apoyo" id="hoy-pendientes">Tienes 3 cosas pendientes hoy</p>' in html


def test_la_caja_grande_busca_y_ofrece_atajos_a_la_duena(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert f'<form class="caja-grande" role="search" action="{reverse("pedidos:buscar")}" method="get">' in html
    assert 'name="q" placeholder="Busca un pedido o un cliente"' in html
    caja = caja_de(html)
    assert f'hx-get="{reverse("pedidos:nuevo")}" hx-target="#ventana"' in caja
    assert ">Nuevo pedido</a>" in caja
    assert f'href="{reverse("pedidos:lista")}?filtro=saldo">' in caja and "Registrar abono" in caja
    assert f'href="{reverse("cotizador:inicio")}">' in caja and "Cotizar" in caja


def test_la_costurera_busca_pedidos_y_no_tiene_atajos(sesion_costurera, ejemplo):
    html = sesion_costurera.get(PAGINA).text

    caja = caja_de(html)
    assert 'placeholder="Busca un pedido"' in caja
    assert "caja-grande__atajos" not in caja
    assert "Nuevo pedido" not in html and "Registrar abono" not in html and "Cotizar" not in html


def test_tu_mes_sale_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text
    cifras = parte(html, "hoy-cifras")

    assert '<h2>Tu mes</h2><a class="chip" href="' in html
    assert "Noviembre</a>" in html
    resumen, lista = reverse("finanzas:resumen"), reverse("pedidos:lista")
    for url, nombre, valor, explica in (
        (resumen, "Cobrado", "$ 4.460.000", "Los abonos que recibiste este mes"),
        (resumen, "Gastado", "$ 939.000", "Los gastos que anotaste este mes"),
        (f"{lista}?filtro=saldo", "Por cobrar", "$ 5.790.000",
         "Lo que te deben los pedidos confirmados: 4 pedidos con saldo"),
        (f"{lista}?filtro=produccion", "En producción", "4",
         "Pedidos confirmados que no se han entregado: 1 por confirmar"),
    ):
        assert (
            f'<a class="cifra" href="{url}" title="{explica}"><span class="cifra__nombre">'
            f'{nombre}</span><span class="cifra__valor">{valor}</span></a>'
        ) in cifras, nombre
    assert "cifra--alerta" not in cifras


def test_las_cifras_de_la_costurera_no_tienen_plata(sesion_costurera, taller, costurera):
    pedido_de(taller, fecha_entrega=HOY - timedelta(days=2), total=900_000, encargada=costurera)
    pedido_de(taller, cliente="Otro", fecha_entrega=HOY + timedelta(days=3))

    html = sesion_costurera.get(PAGINA).text
    cifras = parte(html, "hoy-cifras")

    assert "<h2>El taller hoy</h2>" in html and "Tu mes" not in html
    nombres = re.findall(r'cifra__nombre">([^<]+)<', cifras)
    assert nombres == ["En producción", "Se entregan esta semana", "Atrasados"]
    assert cifras.count("cifra--alerta") == 1
    for plata in ("$", "Cobrado", "Gastado", "Por cobrar", "Quién te debe"):
        assert plata not in html, plata


def test_sin_pedidos_las_cifras_dicen_algo_sensato(sesion_duena, taller):
    cifras = parte(sesion_duena.get(PAGINA).text, "hoy-cifras")

    assert cifras.count('<span class="cifra__valor">$ 0</span>') == 3
    assert '<span class="cifra__valor">0</span>' in cifras
    assert "0 pedidos con saldo" in cifras
    assert "cifra--alerta" not in cifras


def test_atrasados_va_en_rojo_para_la_costurera_solo_si_hay(sesion_costurera, taller):
    pedido_de(taller)

    assert "cifra--alerta" not in parte(sesion_costurera.get(PAGINA).text, "hoy-cifras")


def test_cobrado_y_gastado_son_los_del_mes(sesion_duena, taller):
    pedido = pedido_de(taller, total=900_000)
    fabricas.crear_abono(pedido, valor=300_000, fecha=HOY)
    fabricas.crear_abono(pedido, valor=200_000, fecha=HOY.replace(day=1))
    fabricas.crear_abono(pedido, valor=100_000, fecha=date(2026, 10, 31))
    fabricas.crear_gasto(taller, valor=70_000, fecha=HOY)
    fabricas.crear_gasto(taller, valor=900_000, fecha=date(2026, 10, 30))

    cifras = parte(sesion_duena.get(PAGINA).text, "hoy-cifras")

    assert '<span class="cifra__nombre">Cobrado</span><span class="cifra__valor">$ 500.000</span>' in cifras
    assert '<span class="cifra__nombre">Gastado</span><span class="cifra__valor">$ 70.000</span>' in cifras


# --- Las tarjetas de lo que hay que hacer ------------------------------------------------------


def test_las_tarjetas_salen_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text
    cartas = parte(html, "hoy-que-hacer")

    assert '<section class="cartas" id="hoy-que-hacer" aria-label="Lo que hay que hacer hoy">' in html
    assert tarjetas(cartas) == [
        "Ferretería La Esquina", "Grupo de danza Tambores del Río", "Marcela P."
    ]
    for texto in (
        '<span class="etiqueta etiqueta--rojo etiqueta--alerta">Atrasado 2 días</span>',
        '<span class="texto-2">8 overoles con logo estampado. En confección con Carmen. Debe '
        '<span class="dinero">$ 480.000</span>.</span>',
        ">Marcar como listo</button>",
        '<span class="etiqueta etiqueta--ambar etiqueta--vacio">Faltan 3 días</span>',
        '15 polleras con blusa. Ya está listo. Debe <span class="dinero">$ 750.000</span>.',
        ">Marcar como entregado</button>",
        '<span class="etiqueta etiqueta--gris etiqueta--vacio">Por confirmar</span>',
        '<span class="texto-2">Vestido de grado a la medida. Cotizado en '
        '<span class="dinero">$ 380.000</span>.</span>',
        ">Confirmar pedido</button>",
    ):
        assert texto in cartas, texto
    assert cartas.count("Avisar</") == 3
    assert "Cobrar el saldo" not in cartas
    assert cartas.count('class="carta__sin-foto"') == 3  # sin fotos en estas pruebas


def test_cada_tarjeta_lleva_su_foto_o_el_cuadrito_con_la_prenda(sesion_duena, taller):
    con_foto = pedido_de(taller, cliente="Con foto", fecha_entrega=HOY - timedelta(days=1))
    con_foto.foto = "pedidos/fotos/ejemplo.jpg"
    con_foto.save()
    sin_foto = pedido_de(taller, cliente="Sin foto", fecha_entrega=HOY - timedelta(days=2))

    html = sesion_duena.get(PAGINA).text

    assert 'src="/media/pedidos/fotos/ejemplo.jpg"' in tarjeta_de(html, con_foto)
    assert "carta__sin-foto" not in tarjeta_de(html, con_foto)
    assert "carta__sin-foto" in tarjeta_de(html, sin_foto)
    assert "<img" not in tarjeta_de(html, sin_foto)


def test_el_nombre_del_cliente_abre_el_pedido(sesion_duena, taller):
    pedido = pedido_de(taller, fecha_entrega=HOY - timedelta(days=1))

    html = tarjeta_de(sesion_duena.get(PAGINA).text, pedido)

    assert f'<h3><a href="{reverse("pedidos:detalle", args=[pedido.pk])}">Cliente de prueba</a></h3>' in html


def test_sin_pendientes_dice_que_no_hay_nada_por_hacer(sesion_duena, taller):
    pedido_de(taller, estado=Estado.ENTREGADO, fecha_entrega=HOY - timedelta(days=4))

    html = sesion_duena.get(PAGINA).text

    assert "No hay nada por hacer hoy." in parte(html, "hoy-que-hacer")
    assert "No tienes nada pendiente hoy" in html


def test_el_orden_es_atrasados_listos_prontos_y_cotizados(sesion_duena, taller):
    pedido_de(taller, cliente="D cotizado", estado=Estado.COTIZADO)
    pedido_de(taller, cliente="C pronto", estado=Estado.CORTE,
              fecha_entrega=HOY + timedelta(days=2))
    pedido_de(taller, cliente="B listo", estado=Estado.LISTO,
              fecha_entrega=HOY + timedelta(days=20))
    pedido_de(taller, cliente="A atrasado", fecha_entrega=HOY - timedelta(days=1))
    pedido_de(taller, cliente="Sin afán")  # en confección, para dentro de 30 días: no sale

    html = sesion_duena.get(PAGINA).text
    cartas = parte(html, "hoy-que-hacer")

    assert tarjetas(cartas) == ["A atrasado", "B listo", "C pronto", "D cotizado"]
    assert "Tienes 4 cosas pendientes hoy" in html
    assert '<span class="etiqueta etiqueta--rojo etiqueta--alerta">Atrasado 1 día</span>' in cartas
    assert '<span class="etiqueta etiqueta--ambar etiqueta--vacio">Faltan 2 días</span>' in cartas


def test_se_muestran_todas_las_tarjetas_sin_limite(sesion_duena, taller):
    for numero in range(9):
        pedido_de(taller, cliente=f"Cliente {numero}", estado=Estado.COTIZADO)

    assert len(tarjetas(sesion_duena.get(PAGINA).text)) == 9


def test_un_pendiente_se_dice_en_singular(sesion_duena, taller):
    pedido_de(taller, estado=Estado.COTIZADO)

    assert "Tienes 1 cosa pendiente hoy" in sesion_duena.get(PAGINA).text


def test_el_que_se_entrega_pronto_lleva_a_su_pedido(sesion_duena, taller, duena):
    pedido = pedido_de(taller, estado=Estado.CORTE, fecha_entrega=HOY + timedelta(days=4),
                       total=500_000, encargada=duena)
    fabricas.crear_abono(pedido, valor=500_000, fecha=HOY)

    tarjeta = tarjeta_de(sesion_duena.get(PAGINA).text, pedido)

    detalle = reverse("pedidos:detalle", args=[pedido.pk])
    assert f'<a class="boton" href="{detalle}">Ver el pedido</a>' in tarjeta
    assert f"En corte con {duena.nombre}. Pagado." in tarjeta
    assert "<form" not in tarjeta and "Avisar" not in tarjeta


def test_sin_encargada_la_frase_dice_solo_la_etapa(sesion_duena, taller):
    pedido = pedido_de(taller, detalle="10 camisas.", fecha_entrega=HOY - timedelta(days=1),
                       total=100_000)

    tarjeta = tarjeta_de(sesion_duena.get(PAGINA).text, pedido)

    # El punto del detalle no se repite.
    assert '10 camisas. En confección. Debe <span class="dinero">$ 100.000</span>.' in tarjeta


def test_avisar_con_whatsapp_abre_el_chat_con_el_aviso_de_atraso(sesion_duena, taller):
    pedido = pedido_de(taller, whatsapp="300 123 4567", fecha_entrega=HOY - timedelta(days=2))

    tarjeta = tarjeta_de(sesion_duena.get(PAGINA).text, pedido)

    enlace = mensajes.enlace_whatsapp("300 123 4567", mensajes.texto_atraso(pedido))
    assert enlace.startswith("https://wa.me/573001234567?text=")
    assert (
        f'<a class="boton boton--plano" href="{enlace}" target="_blank" rel="noopener">Avisar</a>'
    ) in tarjeta


def test_avisar_sin_whatsapp_copia_el_aviso(sesion_duena, taller):
    pedido = pedido_de(taller, fecha_entrega=HOY - timedelta(days=2))

    tarjeta = tarjeta_de(sesion_duena.get(PAGINA).text, pedido)

    texto = mensajes.texto_atraso(pedido)
    assert "se nos demoró un poco" in texto
    assert f'data-copiar="{texto}"' in tarjeta
    assert ">Avisar</button>" in tarjeta


def test_avisar_a_un_pedido_listo_manda_el_aviso_de_listo(sesion_duena, taller):
    pedido = pedido_de(taller, whatsapp="3001234567", estado=Estado.LISTO, total=200_000)

    tarjeta = tarjeta_de(sesion_duena.get(PAGINA).text, pedido)

    enlace = mensajes.enlace_whatsapp("3001234567", mensajes.texto_listo(pedido))
    assert f'href="{enlace}"' in tarjeta


def test_avisar_a_un_cotizado_pregunta_si_confirma(sesion_duena, taller):
    con = pedido_de(taller, cliente="Con número", whatsapp="3001234567", estado=Estado.COTIZADO)
    sin = pedido_de(taller, cliente="Sin número", estado=Estado.COTIZADO)

    html = sesion_duena.get(PAGINA).text

    enlace = mensajes.enlace_whatsapp("3001234567", mensajes.texto_confirmar(con))
    assert f'href="{enlace}" target="_blank" rel="noopener">Avisar</a>' in tarjeta_de(html, con)
    assert f'data-copiar="{mensajes.texto_confirmar(sin)}"' in tarjeta_de(html, sin)


def test_listo_y_pagado_solo_ofrece_entregar(sesion_duena, taller):
    pedido = pedido_de(taller, estado=Estado.LISTO, total=200_000)
    fabricas.crear_abono(pedido, valor=200_000, fecha=HOY)

    tarjeta = tarjeta_de(sesion_duena.get(PAGINA).text, pedido)

    assert "Ya está listo. Pagado." in tarjeta
    assert "Cobrar el saldo" not in tarjeta
    assert '<button type="submit" class="boton">Marcar como entregado</button>' in tarjeta


def test_las_acciones_funcionan_sin_javascript_y_con_htmx(sesion_duena, taller):
    pedido = pedido_de(taller, fecha_entrega=HOY - timedelta(days=1))

    tarjeta = tarjeta_de(sesion_duena.get(PAGINA).text, pedido)

    url = accion(pedido, "listo")
    assert (
        f'<form class="carta__acciones" method="post" action="{url}" hx-post="{url}" '
        'hx-target="#hoy-que-hacer" hx-swap="innerHTML"><input type="hidden" '
        'name="csrfmiddlewaretoken"'
    ) in tarjeta


# --- Las acciones -----------------------------------------------------------------------------


def test_marcar_como_listo_cambia_la_tarjeta_y_lo_que_depende(sesion_duena, taller):
    pedido = pedido_de(taller, cliente="Ferretería de prueba",
                       fecha_entrega=HOY - timedelta(days=2), total=960_000)
    fabricas.crear_abono(pedido, valor=480_000, fecha=HOY)

    respuesta = sesion_duena.post(accion(pedido, "listo"), headers=HTMX)

    assert respuesta.status_code == 200
    pedido.refresh_from_db()
    assert pedido.estado == Estado.LISTO
    html = respuesta.text
    lista = lista_de(html)
    # Llega lo de adentro de las tarjetas: la tarjeta, con el mismo id que tenía en la página.
    assert html.startswith(f'<article class="carta" id="pendiente-{pedido.pk}">')
    # Sigue atrasado, pero lo que sigue ahora es entregarlo.
    assert '<span class="etiqueta etiqueta--rojo etiqueta--alerta">Atrasado 2 días</span>' in lista
    assert "Ya está listo. Debe" in lista
    assert "Marcar como entregado" in lista and "Marcar como listo" not in lista
    # Las otras partes llegan marcadas para que HTMX las cambie donde están.
    for id_ in ("hoy-pendientes", "hoy-estado", "hoy-cifras", "hoy-quien-debe", "hoy-etapas"):
        assert re.search(f'id="{id_}"[^>]*hx-swap-oob="true"', html), id_
    assert html.count('hx-swap-oob="true"') == 5
    assert (
        '<p class="bienvenida__apoyo" id="hoy-pendientes" hx-swap-oob="true">'
        "Tienes 1 cosa pendiente hoy</p>"
    ) in html
    assert '<div hx-swap-oob="innerHTML:.menu__lista">' in html
    assert "1 pedido atrasado</a>" in html
    etapas = parte(html, "hoy-etapas")
    assert '<span class="etapas__nombre">Listo</span><span class="etapas__cantidad">1' in etapas


def test_marcar_como_entregado_quita_la_tarjeta_y_cambia_las_cuentas(sesion_duena, taller):
    pedido = pedido_de(taller, cliente="Atrasado listo", estado=Estado.LISTO,
                       fecha_entrega=HOY - timedelta(days=1), total=750_000)
    pedido_de(taller, cliente="Cotizado", estado=Estado.COTIZADO)
    antes = sesion_duena.get(PAGINA).text
    assert '<span class="menu__contador">1</span>' in antes
    assert "1 pedido atrasado</a>" in antes

    html = sesion_duena.post(accion(pedido, "entregado"), headers=HTMX).text

    pedido.refresh_from_db()
    assert pedido.estado == Estado.ENTREGADO
    assert tarjetas(lista_de(html)) == ["Cotizado"]
    assert "Tienes 1 cosa pendiente hoy" in html
    cifras = parte(html, "hoy-cifras")
    assert "cifra--alerta" not in cifras
    # Ya no hay atrasados: el estado de arriba queda vacío.
    assert '<div id="hoy-estado" class="solo-computador" hx-swap-oob="true"></div>' in html
    # Ya no va atrasado: en "Quién te debe" deja de llevar "Vencida", pero sigue debiendo.
    quien = parte(html, "hoy-quien-debe")
    assert "Vencida" not in quien and "$ 750.000" in quien
    # Entregado con saldo: en naranja.
    assert '<span class="etiqueta etiqueta--naranja">1 con saldo</span>' in parte(html, "hoy-etapas")
    # El menú se dibuja de nuevo: Hoy sigue resaltado y Pedidos ya no tiene contador.
    menu = html[html.index('<div hx-swap-oob="innerHTML:.menu__lista">'):]
    assert re.search(r'class="menu__enlace es-actual" href="/" data-nombre="Hoy"', menu)
    assert "menu__contador" not in menu.split('data-nombre="Calendario"')[0]


def test_confirmar_pedido_pasa_de_cotizado_a_confirmado(sesion_duena, taller):
    pedido = pedido_de(taller, estado=Estado.COTIZADO)

    html = sesion_duena.post(accion(pedido, "confirmado"), headers=HTMX).text

    pedido.refresh_from_db()
    assert pedido.estado == Estado.CONFIRMADO
    # Ya no está cotizado: sale de la lista.
    assert tarjetas(lista_de(html)) == []
    assert "No hay nada por hacer hoy." in lista_de(html)
    assert "No tienes nada pendiente hoy" in html


def test_confirmar_pedido_sin_javascript_vuelve_a_hoy(sesion_duena, taller):
    pedido = pedido_de(taller, estado=Estado.COTIZADO)

    respuesta = sesion_duena.post(accion(pedido, "confirmado"))

    assert respuesta.status_code == 302 and respuesta.url == f"{PAGINA}#hoy-que-hacer"
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CONFIRMADO


def test_sin_javascript_la_accion_vuelve_a_hoy(sesion_duena, taller):
    pedido = pedido_de(taller, estado=Estado.LISTO)

    respuesta = sesion_duena.post(accion(pedido, "entregado"))

    assert respuesta.status_code == 302
    assert respuesta.url == f"{PAGINA}#hoy-que-hacer"
    pedido.refresh_from_db()
    assert pedido.estado == Estado.ENTREGADO


@pytest.mark.parametrize(
    "estado, nombre",
    [
        (Estado.COTIZADO, "listo"),
        (Estado.ENTREGADO, "listo"),
        (Estado.COTIZADO, "entregado"),
        (Estado.CONFECCION, "entregado"),
        (Estado.CONFECCION, "confirmado"),
        (Estado.LISTO, "confirmado"),
    ],
)
def test_una_accion_que_no_corresponde_a_la_etapa_no_cambia_nada(sesion_duena, taller, estado,
                                                                 nombre):
    pedido = pedido_de(taller, estado=estado)

    respuesta = sesion_duena.post(accion(pedido, nombre), headers=HTMX)

    assert respuesta.status_code == 200
    pedido.refresh_from_db()
    assert pedido.estado == estado


def test_una_accion_inventada_responde_404_y_no_cambia_nada(sesion_duena, taller):
    pedido = pedido_de(taller)

    for nombre in ("cotizado", "borrar", "LISTO"):
        assert sesion_duena.post(accion(pedido, nombre), headers=HTMX).status_code == 404
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CONFECCION


def test_las_acciones_solo_se_hacen_con_post(sesion_duena, taller):
    pedido = pedido_de(taller)

    assert sesion_duena.get(accion(pedido, "listo")).status_code == 405
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CONFECCION


def test_las_acciones_sobre_un_pedido_de_otro_taller_responden_404(sesion_duena):
    ajeno = pedido_de(fabricas.crear_taller(), estado=Estado.LISTO)
    cotizado = pedido_de(fabricas.crear_taller(), estado=Estado.COTIZADO)

    for pedido, nombres in ((ajeno, ("listo", "entregado")), (cotizado, ("confirmado",))):
        for nombre in nombres:
            assert sesion_duena.post(accion(pedido, nombre), headers=HTMX).status_code == 404
            assert sesion_duena.post(accion(pedido, nombre)).status_code == 404
    ajeno.refresh_from_db()
    cotizado.refresh_from_db()
    assert ajeno.estado == Estado.LISTO and cotizado.estado == Estado.COTIZADO


def test_sin_sesion_la_accion_lleva_a_entrar(client, taller):
    pedido = pedido_de(taller, estado=Estado.LISTO)

    respuesta = client.post(accion(pedido, "entregado"))

    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/entrar/")
    pedido.refresh_from_db()
    assert pedido.estado == Estado.LISTO


def test_las_tarjetas_conservan_su_id_despues_de_una_accion(sesion_duena, taller):
    """Lo que sigue en la lista tiene el mismo id antes y después: no parpadea. Lo que se va
    (el entregado) ya no está: su tarjeta se cierra (static/js/app.js, sección 11)."""
    entregar = pedido_de(taller, cliente="Para entregar", estado=Estado.LISTO, total=500_000)
    sigue = pedido_de(taller, cliente="Sigue", fecha_entrega=HOY - timedelta(days=1),
                      total=300_000)
    pagina = sesion_duena.get(PAGINA).text
    ids_pagina = re.findall(r'id="(pendiente-\d+)"', parte(pagina, "hoy-que-hacer"))
    deudores_pagina = re.findall(r'id="(deudor-\d+)"', parte(pagina, "hoy-quien-debe"))

    html = sesion_duena.post(accion(entregar, "entregado"), headers=HTMX).text

    assert ids_pagina == [f"pendiente-{sigue.pk}", f"pendiente-{entregar.pk}"]
    assert re.findall(r'id="(pendiente-\d+)"', lista_de(html)) == [f"pendiente-{sigue.pk}"]
    # Quién te debe: cada fila lleva el id de su cliente, el mismo en la página y en la respuesta.
    assert deudores_pagina == [f"deudor-{entregar.cliente.pk}", f"deudor-{sigue.cliente.pk}"]
    assert re.findall(r'id="(deudor-\d+)"', parte(html, "hoy-quien-debe")) == deudores_pagina


def test_la_ultima_accion_deja_la_nota_dentro_de_las_tarjetas(sesion_duena, taller):
    pedido = pedido_de(taller, estado=Estado.LISTO)

    html = sesion_duena.post(accion(pedido, "entregado"), headers=HTMX).text

    assert html.startswith('<p class="tarjeta__nota cartas__vacio">No hay nada por hacer hoy.</p>')
    # En la página, la nota también va dentro de las tarjetas (que es lo que cambia la acción).
    assert (
        '<section class="cartas" id="hoy-que-hacer" aria-label="Lo que hay que hacer hoy">'
        '<p class="tarjeta__nota cartas__vacio">No hay nada por hacer hoy.</p>'
    ) in sesion_duena.get(PAGINA).text


def test_las_acciones_de_hoy_no_llevan_aviso_corto(sesion_duena, taller):
    """Cambiar de etapa no lleva aviso: el cambio se ve justo donde se tocó (la tarjeta cambia
    o se cierra)."""
    listo = pedido_de(taller, fecha_entrega=HOY - timedelta(days=1))
    entregar = pedido_de(taller, cliente="Otro", estado=Estado.LISTO)
    confirmar = pedido_de(taller, cliente="Cotizado", estado=Estado.COTIZADO)

    for pedido, nombre in ((listo, "listo"), (entregar, "entregado"), (confirmar, "confirmado")):
        respuesta = sesion_duena.post(accion(pedido, nombre), headers=HTMX)
        assert respuesta.status_code == 200
        assert "aviso" not in respuesta.get("HX-Trigger", "")


# --- La costurera ---------------------------------------------------------------------------


def test_la_costurera_solo_ve_las_acciones_que_puede_hacer(sesion_costurera, taller, costurera):
    suyo = pedido_de(taller, cliente="Suyo", fecha_entrega=HOY - timedelta(days=1),
                     encargada=costurera, total=800_000)
    ajeno = pedido_de(taller, cliente="Ajeno", fecha_entrega=HOY - timedelta(days=1),
                      total=800_000)
    listo = pedido_de(taller, cliente="Listo", estado=Estado.LISTO, encargada=costurera,
                      total=300_000)
    cotizado = pedido_de(taller, cliente="Cotizado", estado=Estado.COTIZADO, total=400_000)

    html = sesion_costurera.get(PAGINA).text

    assert ">Marcar como listo</button>" in tarjeta_de(html, suyo)
    assert "Avisar" in tarjeta_de(html, suyo)
    assert "Marcar como" not in tarjeta_de(html, ajeno)
    assert ">Ver el pedido</a>" in tarjeta_de(html, ajeno)
    # Un listo: puede entregarlo, pero el aviso de listo dice el saldo y ella no ve plata.
    assert ">Marcar como entregado</button>" in tarjeta_de(html, listo)
    assert "Avisar" not in tarjeta_de(html, listo)
    # Un cotizado: el mensaje dice el precio y "Confirmar pedido" no le toca.
    assert ">Ver el pedido</a>" in tarjeta_de(html, cotizado)
    assert "Confirmar pedido" not in html and "Avisar" not in tarjeta_de(html, cotizado)
    for plata in ("$", "Debe", "Cotizado en", "Pagado", "800.000"):
        assert plata not in html, plata


def test_la_costurera_no_confirma_pedidos(sesion_costurera, taller, costurera):
    pedido = pedido_de(taller, estado=Estado.COTIZADO, encargada=costurera)
    otro = pedido_de(taller, cliente="Otro", estado=Estado.COTIZADO)

    assert sesion_costurera.post(accion(otro, "confirmado"), headers=HTMX).status_code == 403
    otro.refresh_from_db()
    assert otro.estado == Estado.COTIZADO
    # Aunque sea la encargada, la tarjeta no le ofrece confirmar (el precio es de la dueña), y
    # tampoco puede confirmarlo pidiéndolo directo (lo notó el revisor).
    assert "Confirmar pedido" not in sesion_costurera.get(PAGINA).text
    assert sesion_costurera.post(accion(pedido, "confirmado"), headers=HTMX).status_code == 403
    pedido.refresh_from_db()
    assert pedido.estado == Estado.COTIZADO


def test_la_respuesta_de_una_accion_a_la_costurera_no_trae_plata(sesion_costurera, taller,
                                                                 costurera):
    pedido = pedido_de(taller, fecha_entrega=HOY - timedelta(days=1), encargada=costurera,
                       total=800_000)
    entregado = pedido_de(taller, cliente="Zulema Ajena", estado=Estado.ENTREGADO, total=500_000)

    html = sesion_costurera.post(accion(pedido, "listo"), headers=HTMX).text

    assert "hoy-quien-debe" not in html and "$" not in html
    assert "con saldo" not in html and entregado.cliente.nombre not in html


def test_la_costurera_no_ve_la_grafica_ni_quien_te_debe(sesion_costurera, ejemplo):
    html = sesion_costurera.get(PAGINA).text

    for texto in ("Cobrado y gastado", "Quién te debe", "hoy-grafica", "dos-columnas"):
        assert texto not in html, texto
    assert "Pedidos por etapa" in html
    assert "con saldo" not in html


# --- La gráfica, quién te debe y las etapas -------------------------------------------------


def test_hoy_no_muestra_nada_de_otro_taller(sesion_duena, taller):
    otro = fabricas.crear_taller()
    pedido_de(otro, cliente="Cliente ajeno", fecha_entrega=HOY - timedelta(days=3), total=900_000)
    fabricas.crear_gasto(otro, valor=70_000, fecha=HOY)

    html = sesion_duena.get(PAGINA).text

    assert "Cliente ajeno" not in html
    assert "$ 900.000" not in html and "$ 70.000" not in html
    assert "No hay nada por hacer hoy." in html
    assert "Nadie te debe" in html
    assert 'class="estado"' not in html


def test_la_grafica_sale_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text
    tarjeta = parte(html, "hoy-grafica")

    assert "Cobrado y gastado por mes</h2>" in tarjeta
    assert "leyenda__color--cobrado" in tarjeta and "leyenda__color--gastado" in tarjeta
    assert "Barras de cobrado y gastado de junio a noviembre." in tarjeta
    assert "En noviembre: cobrado 4,46 millones y gastado 0,94 millones." in tarjeta
    # Ya no lleva la cifra grande ni la nota de abajo.
    assert "cifra-grande" not in tarjeta and 'class="nota"' not in tarjeta
    assert "grafica--computador" not in tarjeta


def test_quien_te_debe_sale_como_en_el_diseno(sesion_duena, ejemplo):
    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-quien-debe")

    assert '<span class="tarjeta__aparte dinero">$ 5.790.000</span>' in tarjeta
    filas_ = re.findall(
        r'<div class="fila-proporcion" id="deudor-\d+"><a class="fila-proporcion__nombre" '
        r'href="[^"]+">([^<]+?)( <span class="etiqueta etiqueta--rojo">Vencida</span>)?</a>'
        r'<strong class="dinero">([^<]+)</strong>'
        r'<span class="proporcion( proporcion--atrasado)?" style="width: (\d+)%">',
        tarjeta,
    )
    assert filas_ == [
        ("Colegio Nuevo Amanecer", "", "$ 3.300.000", "", "100"),
        ("Restaurante El Fogón Costeño", "", "$ 1.260.000", "", "38"),
        ("Grupo de danza Tambores del Río", "", "$ 750.000", "", "23"),
        # Tiene un pedido atrasado: insignia roja "Vencida" (sin circulito) y barra en rojo.
        (
            "Ferretería La Esquina", ' <span class="etiqueta etiqueta--rojo">Vencida</span>',
            "$ 480.000", " proporcion--atrasado", "15",
        ),
    ]
    assert "texto-rojo" not in tarjeta


def test_cada_deudor_abre_sus_pedidos_con_saldo(sesion_duena, ejemplo):
    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-quien-debe")

    lista = reverse("pedidos:lista")
    assert f'href="{lista}?filtro=saldo&amp;q=Ferreter%C3%ADa+La+Esquina"' in tarjeta


def test_quien_te_debe_no_cuenta_cotizados_ni_pagados(sesion_duena, taller):
    pedido_de(taller, cliente="Cotizado", estado=Estado.COTIZADO)
    pagado = pedido_de(taller, cliente="Pagado", total=100_000)
    fabricas.crear_abono(pagado, valor=100_000, fecha=HOY)

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-quien-debe")

    assert "Cotizado" not in tarjeta and "Pagado" not in tarjeta
    assert "Nadie te debe: todos los pedidos están pagados." in tarjeta


def test_pedidos_por_etapa_sale_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text
    tarjeta = parte(html, "hoy-etapas")

    assert '<section class="etapas" id="hoy-etapas" aria-label="Pedidos por etapa">' in html
    assert "<h2" not in tarjeta
    etapas = re.findall(
        r'<span class="etapas__nombre">([^<]+)</span><span class="etapas__cantidad">(\d+)'
        r'(?: <span class="etiqueta etiqueta--(\w+)">([^<]+)</span>\s*)?</span></a>',
        tarjeta,
    )
    assert etapas == [
        ("Cotizado", "1", "", ""),
        ("Confirmado", "1", "", ""),
        ("En corte", "1", "", ""),
        ("En confección", "1", "rojo", "1 atrasado"),
        ("Listo", "1", "", ""),
        ("Entregado", "1", "", ""),
    ]
    # Nada en verde: ni "Pagado" en Entregado.
    assert "etiqueta--verde" not in tarjeta and "Pagado" not in tarjeta


def test_entregados_que_deben_se_dicen_en_naranja(sesion_duena, taller):
    pedido_de(taller, estado=Estado.ENTREGADO, total=100_000)
    pedido_de(taller, cliente="Otro", estado=Estado.ENTREGADO, total=100_000)

    etapas = parte(sesion_duena.get(PAGINA).text, "hoy-etapas")

    assert '<span class="etiqueta etiqueta--naranja">2 con saldo</span>' in etapas


def test_varios_atrasados_en_una_etapa(sesion_duena, taller):
    pedido_de(taller, fecha_entrega=HOY - timedelta(days=1))
    pedido_de(taller, cliente="Otro", fecha_entrega=HOY - timedelta(days=3))

    etapas = parte(sesion_duena.get(PAGINA).text, "hoy-etapas")

    assert '<span class="etiqueta etiqueta--rojo">2 atrasados</span>' in etapas


def test_hoy_ya_no_muestra_trabajos_del_taller(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert "Trabajos del taller" not in html and "hoy-trabajos" not in html


@pytest.mark.parametrize(
    "estado, con_encargada, frase",
    [
        (Estado.COTIZADO, False, ""),
        (Estado.CONFIRMADO, False, "Confirmado"),
        (Estado.CORTE, True, "En corte con Marta"),
        (Estado.CONFECCION, True, "En confección con Marta"),
        (Estado.LISTO, True, "Ya está listo"),
        (Estado.ENTREGADO, False, "Ya se entregó"),
    ],
)
def test_frase_de_etapa(taller, estado, con_encargada, frase):
    marta = fabricas.crear_usuaria(taller, rol="costurera", nombre_visible="Marta")
    pedido = pedido_de(taller, estado=estado, encargada=marta if con_encargada else None)

    assert vista.frase_de_etapa(pedido) == frase
