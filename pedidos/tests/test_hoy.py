"""Hoy (T06): las cifras, "Qué hacer hoy" y sus acciones, la gráfica, "Quién te debe" y
"Pedidos por etapa"."""

import re
from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from pedidos import ejemplos, mensajes
from pedidos.calculos import MesDeGrafica
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


def filas(html):
    """Los clientes de "Qué hacer hoy", en el orden en que salen."""
    return re.findall(r'<div class="fila[^"]*" id="pendiente-\d+">\s*<div class="fila__texto">'
                      r'<div class="fila__titulo"><strong>([^<]+)</strong>', html)


# --- La página con los datos del diseño -------------------------------------------------------


def test_las_cifras_salen_como_en_el_diseno(sesion_duena, ejemplo):
    cifras = parte(sesion_duena.get(PAGINA).text, "hoy-cifras")

    lista = reverse("pedidos:lista")
    for filtro, nombre, valor, apoyo in (
        ("produccion", "En producción", "4", "1 por confirmar"),
        ("semana", "Entregas en 7 días", "1", "La más cercana: en 3 días"),
        ("atrasados", "Atrasados", "1", "Pasó la fecha de entrega"),
        ("saldo", "Por cobrar", "$ 5.790.000", "4 pedidos con saldo"),
    ):
        assert (
            f'href="{lista}?filtro={filtro}">\n<div class="cifra__nombre">{nombre}</div>\n'
            f'<div class="cifra__valor">{valor}</div>\n<div class="cifra__apoyo">{apoyo}</div>'
        ) in cifras
    # Solo Atrasados va en rojo.
    assert cifras.count("cifra--alerta") == 1
    alerta = f'class="tarjeta cifra cifra--alerta[^"]*" href="{lista}[?]filtro=atrasados"'
    assert re.search(alerta, cifras)


def test_en_celular_las_cifras_van_en_el_orden_del_diseno(taller):
    cifras = vista.cifras(taller, HOY)

    en_celular = sorted(cifras, key=lambda c: c.orden_celular)

    assert [c.nombre for c in en_celular] == [
        "En producción", "Atrasados", "Entregas en 7 días", "Por cobrar"
    ]
    assert cifras[2].clase == "orden-celular-2"


def test_que_hacer_hoy_sale_como_en_el_diseno(sesion_duena, ejemplo):
    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    assert '<span class="tarjeta__aparte">3 pendientes</span>' in tarjeta
    assert filas(tarjeta) == [
        "Ferretería La Esquina", "Grupo de danza Tambores del Río", "Marcela P."
    ]
    for texto in (
        '<span class="etiqueta etiqueta--rojo">Atrasado 2 días</span>',
        "8 overoles con logo estampado. En confección con Carmen. Debe "
        '<span class="dinero">$ 480.000</span>.',
        ">Marcar como listo</button>",
        ">Avisar al cliente</button>",
        '<span class="etiqueta etiqueta--ambar">Faltan 3 días</span>',
        '15 polleras con blusa. Ya está listo. Debe <span class="dinero">$ 750.000</span>.',
        ">Cobrar el saldo</a>",
        '<span class="texto-computador">Marcar como entregado</span>'
        '<span class="texto-celular">Entregado</span>',
        '<span class="etiqueta etiqueta--ambar">Por confirmar</span>',
        'Vestido de grado a la medida. Cotizado en <span class="dinero">$ 380.000</span>.',
        '<span class="texto-computador">Preguntar si confirma</span>'
        '<span class="texto-celular">Preguntar</span></button>',
    ):
        assert texto in tarjeta, texto


def test_la_grafica_dice_lo_cobrado_en_el_mes(sesion_duena, ejemplo):
    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-grafica")

    assert (
        '<div class="cifra-grande"><span class="dinero">$ 4.460.000</span> '
        '<span class="cifra-grande__apoyo">cobrado en noviembre</span></div>'
    ) in tarjeta
    assert "Barras de cobrado y gastado de junio a noviembre." in tarjeta
    assert "En noviembre: cobrado 4,46 millones y gastado 0,94 millones." in tarjeta
    assert '<p class="nota">M = millones de pesos.</p>' in tarjeta
    assert "Valores de ejemplo" not in tarjeta


def test_quien_te_debe_sale_como_en_el_diseno(sesion_duena, ejemplo):
    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-quien-debe")

    filas_ = re.findall(
        r'<div class="fila-proporcion"><a class="fila-proporcion__nombre( texto-rojo)?" '
        r'href="[^"]+">([^<]+)</a><strong class="dinero( texto-rojo)?">([^<]+)</strong>'
        r'<span class="proporcion( proporcion--atrasado)?" style="width: (\d+)%">',
        tarjeta,
    )
    assert filas_ == [
        ("", "Colegio Nuevo Amanecer", "", "$ 3.300.000", "", "100"),
        ("", "Restaurante El Fogón Costeño", "", "$ 1.260.000", "", "38"),
        ("", "Grupo de danza Tambores del Río", "", "$ 750.000", "", "23"),
        # Tiene un pedido atrasado: nombre, valor y barra en rojo. El rojo va en el nombre
        # mismo, porque un enlace no toma el color de la fila.
        (
            " texto-rojo", "Ferretería La Esquina", " texto-rojo", "$ 480.000",
            " proporcion--atrasado", "15",
        ),
    ]


def test_cada_deudor_abre_sus_pedidos_con_saldo(sesion_duena, ejemplo):
    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-quien-debe")

    lista = reverse("pedidos:lista")
    assert f'href="{lista}?filtro=saldo&amp;q=Ferreter%C3%ADa+La+Esquina"' in tarjeta


def test_pedidos_por_etapa_sale_como_en_el_diseno(sesion_duena, ejemplo):
    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-etapas")

    etapas = re.findall(
        r'<span class="etapas__nombre">([^<]+)</span><strong class="etapas__cantidad">(\d+)'
        r'</strong>(?:<span class="etiqueta etiqueta--(\w+)">([^<]+)</span>)?\s*</div>',
        tarjeta,
    )
    assert etapas == [
        ("Cotizado", "1", "", ""),
        ("Confirmado", "1", "", ""),
        ("En corte", "1", "", ""),
        ("En confección", "1", "rojo", "1 atrasado"),
        ("Listo", "1", "", ""),
        ("Entregado", "1", "verde", "Pagado"),
    ]


def test_hoy_no_muestra_nada_de_otro_taller(sesion_duena, taller):
    otro = fabricas.crear_taller()
    pedido_de(otro, cliente="Cliente ajeno", fecha_entrega=HOY - timedelta(days=3), total=900_000)
    fabricas.crear_gasto(otro, valor=70_000, fecha=HOY)

    html = sesion_duena.get(PAGINA).text

    assert "Cliente ajeno" not in html
    assert '<div class="cifra__valor">0</div>' in parte(html, "hoy-cifras")
    assert "$ 900.000" not in html
    assert "No hay nada por hacer hoy." in html
    assert "Nadie te debe" in html
    assert "Todavía no hay cobros ni gastos en estos seis meses." in html


# --- Las cifras -----------------------------------------------------------------------------


def test_sin_pedidos_las_cifras_dicen_algo_sensato(sesion_duena, taller):
    cifras = parte(sesion_duena.get(PAGINA).text, "hoy-cifras")

    for texto in ("Sin cotizaciones pendientes", "Nada para esta semana", "Todo va a tiempo",
                  "0 pedidos con saldo", "$ 0"):
        assert texto in cifras, texto
    assert "cifra--alerta" not in cifras


@pytest.mark.parametrize(
    "dias, apoyo",
    [(0, "La más cercana: hoy"), (1, "La más cercana: mañana"), (5, "La más cercana: en 5 días")],
)
def test_la_entrega_mas_cercana(sesion_duena, taller, dias, apoyo):
    pedido_de(taller, fecha_entrega=HOY + timedelta(days=dias))
    pedido_de(taller, cliente="Otro cliente", fecha_entrega=HOY + timedelta(days=6))

    assert f'<div class="cifra__apoyo">{apoyo}</div>' in sesion_duena.get(PAGINA).text


def test_un_pedido_con_saldo_se_dice_en_singular(sesion_duena, taller):
    pedido_de(taller, total=300_000)

    assert "1 pedido con saldo" in parte(sesion_duena.get(PAGINA).text, "hoy-cifras")


# --- Qué hacer hoy --------------------------------------------------------------------------


def test_sin_pendientes_dice_que_no_hay_nada_por_hacer(sesion_duena, taller):
    pedido_de(taller, estado=Estado.ENTREGADO, fecha_entrega=HOY - timedelta(days=4))

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    assert '<span class="tarjeta__aparte">Sin pendientes</span>' in tarjeta
    assert "No hay nada por hacer hoy." in tarjeta


def test_el_orden_es_atrasados_listos_prontos_y_cotizados(sesion_duena, taller):
    pedido_de(taller, cliente="D cotizado", estado=Estado.COTIZADO)
    pedido_de(taller, cliente="C pronto", estado=Estado.CORTE,
              fecha_entrega=HOY + timedelta(days=2))
    pedido_de(taller, cliente="B listo", estado=Estado.LISTO,
              fecha_entrega=HOY + timedelta(days=20))
    pedido_de(taller, cliente="A atrasado", fecha_entrega=HOY - timedelta(days=1))
    pedido_de(taller, cliente="Sin afán")  # en confección, para dentro de 30 días: no sale

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    assert filas(tarjeta) == ["A atrasado", "B listo", "C pronto", "D cotizado"]
    assert '<span class="tarjeta__aparte">4 pendientes</span>' in tarjeta
    assert '<span class="etiqueta etiqueta--rojo">Atrasado 1 día</span>' in tarjeta
    assert '<span class="etiqueta etiqueta--ambar">Faltan 2 días</span>' in tarjeta


def test_un_pendiente_se_dice_en_singular(sesion_duena, taller):
    pedido_de(taller, estado=Estado.COTIZADO)

    assert '<span class="tarjeta__aparte">1 pendiente</span>' in sesion_duena.get(PAGINA).text


def test_el_que_se_entrega_pronto_lleva_a_su_pedido(sesion_duena, taller, duena):
    pedido = pedido_de(taller, estado=Estado.CORTE, fecha_entrega=HOY + timedelta(days=4),
                       total=500_000, encargada=duena)
    fabricas.crear_abono(pedido, valor=500_000, fecha=HOY)

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    detalle = reverse("pedidos:detalle", args=[pedido.pk])
    assert f'<a class="boton" href="{detalle}">Ver el pedido</a>' in tarjeta
    assert f"En corte con {duena.nombre}. Pagado." in tarjeta
    assert "<form" not in tarjeta


def test_sin_encargada_la_frase_dice_solo_la_etapa(sesion_duena, taller):
    pedido_de(taller, detalle="10 camisas.", fecha_entrega=HOY - timedelta(days=1), total=100_000)

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    # El punto del detalle no se repite.
    assert '10 camisas. En confección. Debe <span class="dinero">$ 100.000</span>.' in tarjeta


def test_avisar_al_cliente_con_whatsapp_abre_el_chat_con_el_aviso_de_atraso(sesion_duena, taller):
    pedido = pedido_de(taller, whatsapp="300 123 4567", fecha_entrega=HOY - timedelta(days=2))

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    enlace = mensajes.enlace_whatsapp("300 123 4567", mensajes.texto_atraso(pedido))
    assert enlace.startswith("https://wa.me/573001234567?text=")
    assert (
        f'<a class="boton" href="{enlace}" target="_blank" rel="noopener">Avisar al cliente</a>'
    ) in tarjeta


def test_avisar_al_cliente_sin_whatsapp_copia_el_aviso(sesion_duena, taller):
    pedido = pedido_de(taller, fecha_entrega=HOY - timedelta(days=2))

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    texto = mensajes.texto_atraso(pedido)
    assert "se nos demoró un poco" in texto
    assert f'data-copiar="{texto}"' in tarjeta
    assert ">Avisar al cliente</button>" in tarjeta


def test_preguntar_si_confirma_abre_el_chat_o_copia_el_mensaje(sesion_duena, taller):
    con = pedido_de(taller, cliente="Con número", whatsapp="3001234567", estado=Estado.COTIZADO)
    sin = pedido_de(taller, cliente="Sin número", estado=Estado.COTIZADO)

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    enlace = mensajes.enlace_whatsapp("3001234567", mensajes.texto_confirmar(con))
    # En celular el botón se acorta a "Preguntar", como en diseno/hoy-celular.html.
    nombre = (
        '<span class="texto-computador">Preguntar si confirma</span>'
        '<span class="texto-celular">Preguntar</span>'
    )
    assert f'href="{enlace}" target="_blank" rel="noopener">{nombre}</a>' in tarjeta
    assert f'data-copiar="{mensajes.texto_confirmar(sin)}"' in tarjeta
    assert f'title="Copia el mensaje para pegarlo en WhatsApp">{nombre}</button>' in tarjeta
    # Y en celular queda al lado de la frase, no debajo.
    assert tarjeta.count('<div class="fila fila--accion-al-lado" id="pendiente-') == 2


def test_listo_y_pagado_solo_ofrece_entregar(sesion_duena, taller):
    pedido = pedido_de(taller, estado=Estado.LISTO, total=200_000)
    fabricas.crear_abono(pedido, valor=200_000, fecha=HOY)

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    assert "Ya está listo. Pagado." in tarjeta
    assert "Cobrar el saldo" not in tarjeta
    assert (
        '<button type="submit" class="boton boton--principal">Marcar como entregado</button>'
    ) in tarjeta


def test_cobrar_el_saldo_lleva_al_abono_del_pedido(sesion_duena, taller):
    pedido = pedido_de(taller, estado=Estado.LISTO)

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    detalle = reverse("pedidos:detalle", args=[pedido.pk])
    assert f'href="{detalle}#registrar-abono">Cobrar el saldo</a>' in tarjeta


def test_las_acciones_funcionan_sin_javascript_y_con_htmx(sesion_duena, taller):
    pedido = pedido_de(taller, fecha_entrega=HOY - timedelta(days=1))

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-que-hacer")

    url = accion(pedido, "listo")
    assert (
        f'<form class="fila__acciones" method="post" action="{url}" hx-post="{url}" '
        'hx-target="#hoy-que-hacer" hx-swap="outerHTML"><input type="hidden" '
        'name="csrfmiddlewaretoken"'
    ) in tarjeta


# --- Las acciones -----------------------------------------------------------------------------


def test_marcar_como_listo_cambia_la_fila_y_lo_que_depende(sesion_duena, taller):
    pedido = pedido_de(taller, cliente="Ferretería de prueba",
                       fecha_entrega=HOY - timedelta(days=2), total=960_000)
    fabricas.crear_abono(pedido, valor=480_000, fecha=HOY)

    respuesta = sesion_duena.post(accion(pedido, "listo"), headers=HTMX)

    assert respuesta.status_code == 200
    pedido.refresh_from_db()
    assert pedido.estado == Estado.LISTO
    html = respuesta.text
    tarjeta = parte(html, "hoy-que-hacer")
    assert html.startswith('<section class="tarjeta tarjeta--lista" id="hoy-que-hacer"')
    # Sigue atrasado, pero lo que sigue ahora es cobrar y entregar.
    assert '<span class="etiqueta etiqueta--rojo">Atrasado 2 días</span>' in tarjeta
    assert "Ya está listo. Debe" in tarjeta
    assert "Cobrar el saldo" in tarjeta
    assert "Marcar como listo" not in tarjeta
    # Las otras partes llegan marcadas para que HTMX las cambie donde están.
    for id_ in ("hoy-cifras", "hoy-quien-debe", "hoy-etapas"):
        assert re.search(f'id="{id_}"[^>]*hx-swap-oob="true"', html), id_
    assert html.count('hx-swap-oob="true"') == 3
    assert '<div hx-swap-oob="innerHTML:.menu__lista">' in html
    etapas = parte(html, "hoy-etapas")
    assert (
        '<span class="etapas__nombre">Listo</span><strong class="etapas__cantidad">1</strong>'
    ) in etapas


def test_marcar_como_entregado_quita_la_fila_y_cambia_las_cuentas(sesion_duena, taller):
    pedido = pedido_de(taller, cliente="Atrasado listo", estado=Estado.LISTO,
                       fecha_entrega=HOY - timedelta(days=1), total=750_000)
    pedido_de(taller, cliente="Cotizado", estado=Estado.COTIZADO)
    antes = sesion_duena.get(PAGINA).text
    assert '<span class="menu__contador">1</span>' in antes

    html = sesion_duena.post(accion(pedido, "entregado"), headers=HTMX).text

    pedido.refresh_from_db()
    assert pedido.estado == Estado.ENTREGADO
    tarjeta = parte(html, "hoy-que-hacer")
    assert filas(tarjeta) == ["Cotizado"]
    assert '<span class="tarjeta__aparte">1 pendiente</span>' in tarjeta
    cifras = parte(html, "hoy-cifras")
    assert "cifra--alerta" not in cifras
    assert "Todo va a tiempo" in cifras
    # Ya no va atrasado: en "Quién te debe" deja de estar en rojo, pero sigue debiendo.
    quien = parte(html, "hoy-quien-debe")
    assert '<div class="fila-proporcion"><a class="fila-proporcion__nombre"' in quien
    assert "$ 750.000" in quien
    assert '1 con saldo' in parte(html, "hoy-etapas")
    # El menú se dibuja de nuevo: Hoy sigue resaltado y Pedidos ya no tiene contador.
    menu = html[html.index('<div hx-swap-oob="innerHTML:.menu__lista">'):]
    assert 'aria-current="page"' in menu and 'data-nombre="Hoy"' in menu
    assert re.search(r'class="menu__enlace es-actual" href="/" data-nombre="Hoy"', menu)
    assert "menu__contador" not in menu.split('data-nombre="Calendario"')[0]


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

    for nombre in ("listo", "entregado"):
        assert sesion_duena.post(accion(ajeno, nombre), headers=HTMX).status_code == 404
        assert sesion_duena.post(accion(ajeno, nombre)).status_code == 404
    ajeno.refresh_from_db()
    assert ajeno.estado == Estado.LISTO


def test_sin_sesion_la_accion_lleva_a_entrar(client, taller):
    pedido = pedido_de(taller, estado=Estado.LISTO)

    respuesta = client.post(accion(pedido, "entregado"))

    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/entrar/")
    pedido.refresh_from_db()
    assert pedido.estado == Estado.LISTO


# --- La gráfica, quién te debe y las etapas -------------------------------------------------


def test_la_grafica_suma_lo_cobrado_este_mes(sesion_duena, taller):
    pedido = pedido_de(taller, total=900_000)
    fabricas.crear_abono(pedido, valor=300_000, fecha=HOY)
    fabricas.crear_abono(pedido, valor=200_000, fecha=HOY.replace(day=1))
    fabricas.crear_abono(pedido, valor=100_000, fecha=date(2026, 10, 31))

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-grafica")

    assert (
        '<span class="dinero">$ 500.000</span> '
        '<span class="cifra-grande__apoyo">cobrado en noviembre</span>'
    ) in tarjeta
    assert "Valores en miles de pesos." in tarjeta


@pytest.mark.parametrize(
    "cobrado, gastado, nota",
    [
        (4_460_000, 940_000, "M = millones de pesos."),
        (0, 1_000_000, "M = millones de pesos."),
        # Con 1,5 M el eje dice "500 mil" y "1 M": la nota no puede decir que todo va en M.
        (1_500_000, 0, "M = millones de pesos."),
        (500_000, 20_000, "Valores en miles de pesos."),
        (0, 0, "Todavía no hay cobros ni gastos en estos seis meses."),
    ],
)
def test_nota_de_la_grafica(cobrado, gastado, nota):
    meses = [
        MesDeGrafica(date(2026, 10, 1), 0, 0),
        MesDeGrafica(date(2026, 11, 1), cobrado, gastado),
    ]

    assert vista.nota_de_la_grafica(meses) == nota


def test_quien_te_debe_no_cuenta_cotizados_ni_pagados(sesion_duena, taller):
    pedido_de(taller, cliente="Cotizado", estado=Estado.COTIZADO)
    pagado = pedido_de(taller, cliente="Pagado", total=100_000)
    fabricas.crear_abono(pagado, valor=100_000, fecha=HOY)

    tarjeta = parte(sesion_duena.get(PAGINA).text, "hoy-quien-debe")

    assert "Cotizado" not in tarjeta and "Pagado" not in tarjeta
    assert "Nadie te debe: todos los pedidos están pagados." in tarjeta


def test_sin_entregados_no_dice_pagado(sesion_duena, taller):
    pedido_de(taller)

    etapas = parte(sesion_duena.get(PAGINA).text, "hoy-etapas")

    assert "Pagado" not in etapas
    assert (
        '<span class="etapas__nombre">Entregado</span>'
        '<strong class="etapas__cantidad">0</strong></div>'
    ) in etapas


def test_entregados_que_deben_se_dicen_en_rojo(sesion_duena, taller):
    pedido_de(taller, estado=Estado.ENTREGADO, total=100_000)
    pedido_de(taller, cliente="Otro", estado=Estado.ENTREGADO, total=100_000)

    etapas = parte(sesion_duena.get(PAGINA).text, "hoy-etapas")

    assert '<span class="etiqueta etiqueta--rojo">2 con saldo</span>' in etapas


def test_varios_atrasados_en_una_etapa(sesion_duena, taller):
    pedido_de(taller, fecha_entrega=HOY - timedelta(days=1))
    pedido_de(taller, cliente="Otro", fecha_entrega=HOY - timedelta(days=3))

    etapas = parte(sesion_duena.get(PAGINA).text, "hoy-etapas")

    assert '<span class="etiqueta etiqueta--rojo">2 atrasados</span>' in etapas


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
