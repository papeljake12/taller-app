"""Pedidos (T05): la lista con filtros y buscador, "Nuevo pedido" y el buscador del menú."""

import re
from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from pedidos import ejemplos
from pedidos.formularios.lista import leer_pesos
from pedidos.models import Cliente, Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db

LISTA = reverse("pedidos:lista")
NUEVO = reverse("pedidos:nuevo")
BUSCAR = reverse("pedidos:buscar")
HTMX = {"HX-Request": "true"}


MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def nota_de_entrega_de(taller, dias):
    """Lo que dice la entrega de un pedido en producción que se entrega dentro de `dias`."""
    from pedidos.vistas.lista import nota_de_entrega

    hoy = timezone.localdate()
    pedido = Pedido(taller=taller, estado="confeccion", fecha_entrega=hoy + timedelta(days=dias))
    return nota_de_entrega(pedido, hoy)


@pytest.fixture
def ejemplo_de_costurera(taller, costurera):
    return ejemplos.cargar(taller=taller, con_fotos=False)


@pytest.fixture
def ejemplo(taller, duena):
    """Los pedidos de diseno/pedidos.html, contados desde hoy y a nombre de la dueña."""
    return ejemplos.cargar(taller=taller, con_fotos=False)


def clientes_en_orden(html):
    """Los nombres de cliente de la tabla, en el orden en que salen."""
    return re.findall(r'<tr class="tabla__fila" id="pedido-\d+">.*?class="tabla__enlace" href="[^"]+">([^<]+)</a>',
                      html, re.S)


def filtro_elegido(html):
    elegido = re.search(r'class="filtro es-elegido"[^>]*>(.*?)</a>', html, re.S).group(1)
    return " ".join(re.sub(r"<[^>]+>", " ", elegido).split())


def texto_de(html):
    """El texto de la página sin etiquetas y con los espacios juntos."""
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


# --- La lista ---------------------------------------------------------------------------------


def test_la_lista_sale_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    assert '<div class="paginas">6 pedidos</div>' in html
    assert "hoja--completa" in html
    assert clientes_en_orden(html) == [
        "Ferretería La Esquina",
        "Grupo de danza Tambores del Río",
        "Marcela P.",
        "Restaurante El Fogón Costeño",
        "Colegio Nuevo Amanecer",
        "Comparsa Brisa Caribe",
    ]
    for texto in (
        'placeholder="Buscar por cliente, prenda o encargada"',
        "Descargar para Excel",
        '<table class="tabla tabla--pedidos">',
        '<td class="solo-tabla tabla__prenda">8 overoles con logo estampado</td>',
        '<span class="etiqueta etiqueta--azul etiqueta--medio">En confección</span>',
        '<span class="etiqueta etiqueta--rojo etiqueta--alerta">Vencido</span>',
        '<span class="etiqueta etiqueta--naranja etiqueta--medio">Abonado 67 %</span>',
        '<span class="etiqueta etiqueta--gris etiqueta--vacio">Sin abonos</span>',
        '<span class="etiqueta etiqueta--verde etiqueta--lleno">Listo</span>',
        '<span class="etiqueta etiqueta--gris etiqueta--lleno">Entregado</span>',
        '<span class="etiqueta etiqueta--gris etiqueta--lleno">Pagado</span>',
        '<td class="solo-tabla">Carmen</td>',
        '<span class="texto-2">Sin asignar</span>',
        '<td class="solo-tabla">8 de 8</td>',
        '<td class="solo-tabla">0 de 1</td>',
        '<td class="solo-tabla">14 de 18</td>',
        '<td class="solo-tabla">9 de 40</td>',
        '<td class="num dinero celda-total">$ 960.000</td>',
        '<td class="num dinero celda-total">$ 2.520.000</td>',
        '<th scope="col" class="num">Total</th>',
    ):
        assert texto in html, texto


def test_la_entrega_dice_cuanto_falta_o_cuanto_se_atraso(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text
    hoy = timezone.localdate()

    atraso = hoy - timedelta(days=2)
    proxima = hoy + timedelta(days=3)
    assert (f'<span class="texto-atraso">{atraso.day} {MESES[atraso.month - 1]} · 2 días tarde'
            '</span>') in html
    assert (f'{proxima.day} {MESES[proxima.month - 1]} · <span class="texto-2">en 3 días</span>'
            ) in html
    # Lo que se entrega hoy o mañana lo dice con esas palabras.
    assert nota_de_entrega_de(ejemplo, 0) == "hoy"
    assert nota_de_entrega_de(ejemplo, 1) == "mañana"
    assert nota_de_entrega_de(ejemplo, 7) == "en 7 días"
    assert nota_de_entrega_de(ejemplo, 8) == ""
    assert nota_de_entrega_de(ejemplo, -1) == "1 día tarde"


def test_la_barra_de_cifras_sale_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    assert '<section class="cifras cifras--barra"' in html
    assert 'class="chip"' in html and "Hoy</span>" in html
    cifras = dict(re.findall(
        r'<span class="cifra__nombre">([^<]+)</span><span class="cifra__valor">([^<]+)</span>',
        html))
    assert cifras == {"Activos": "5", "En producción": "4", "Se entregan esta semana": "1",
                      "Atrasados": "1", "Por cobrar": "$ 5.790.000"}
    assert f'<a class="cifra cifra--alerta" href="{LISTA}?filtro=atrasados" title=' in html
    assert f'<a class="cifra" href="{LISTA}?filtro=produccion" title=' in html
    assert f'<a class="cifra" href="{LISTA}?filtro=semana" title=' in html
    assert f'<a class="cifra" href="{LISTA}?filtro=saldo" title=' in html
    assert 'title="Pedidos que no se han entregado"' in html


def test_atrasados_va_en_rojo_solo_si_hay(sesion_duena, taller):
    fabricas.crear_pedido(taller, fecha_entrega=timezone.localdate() + timedelta(days=20))

    html = sesion_duena.get(LISTA).text

    assert "cifra--alerta" not in html


def test_el_buscador_esta_escondido_detras_de_la_lupa(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    assert '<div class="buscador-fila" id="buscador-pedidos" hidden>' in html
    # La lupa del encabezado (celular) y la de la tarjeta (computador).
    assert html.count('data-mostrar="buscador-pedidos"') == 2
    # Sin JavaScript, la lupa lleva a la misma lista con el buscador a la vista.
    assert f'href="{LISTA}?filtro=todos&amp;buscar=1"' in html
    abierto = sesion_duena.get(LISTA, {"filtro": "todos", "buscar": "1"}).text
    assert '<div class="buscador-fila" id="buscador-pedidos">' in abierto


def test_si_hay_algo_buscado_el_buscador_se_ve(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA, {"q": "esquina"}).text

    assert '<div class="buscador-fila" id="buscador-pedidos">' in html


def test_cada_fila_trae_la_lista_de_celular_de_la_referencia(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    for clase in ("celda-mini solo-celular", "celda-cliente", "celda-etapa",
                  "celda-apoyo solo-celular", "num dinero celda-total"):
        assert html.count(f'<td class="{clase}">') == 6, clase
    # La insignia del pago va dentro de un solo-celular, antes de la etapa.
    assert html.count('<td class="celda-etapa"><span class="solo-celular"><span class="etiqueta') == 6


def test_la_costurera_no_ve_total_pago_ni_por_cobrar(client, costurera, ejemplo_de_costurera):
    client.force_login(costurera)
    html = client.get(LISTA).text

    assert len(clientes_en_orden(html)) == 6
    texto = texto_de(html)
    for prohibido in ("Por cobrar", "Total", "Pago", "Con saldo", "Abonado", "Sin abonos",
                      "Vencido", "$ ", "Descargar para Excel", "Nuevo pedido"):
        assert prohibido not in texto, prohibido
    assert "celda-total" not in html
    for visible in ("Activos", "En producción", "Entrega", "Etapa", "Tallas", "Encargada",
                    "Atrasados"):
        assert visible in texto, visible


def test_la_costurera_no_puede_pedir_el_filtro_con_saldo(client, costurera, ejemplo_de_costurera):
    client.force_login(costurera)

    html = client.get(LISTA, {"filtro": "saldo"}).text

    assert filtro_elegido(html).startswith("Todos")
    assert len(clientes_en_orden(html)) == 6


def test_los_filtros_muestran_su_conteo_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    for texto in ("Todos 6", "En producción 4", "Esta semana 1", "Atrasados 1", "Con saldo 4",
                  "Entregados 1"):
        nombre, conteo = texto.rsplit(" ", 1)
        assert f'>{nombre} <span class="filtro__conteo">{conteo}</span></a>' in html, texto
    assert filtro_elegido(html) == "Todos 6"
    assert 'href="?filtro=atrasados"' not in html
    assert f'href="{LISTA}?filtro=atrasados"' in html


@pytest.mark.parametrize(
    ("filtro", "esperados"),
    [
        ("produccion", ["Ferretería La Esquina", "Grupo de danza Tambores del Río",
                        "Restaurante El Fogón Costeño", "Colegio Nuevo Amanecer"]),
        ("semana", ["Grupo de danza Tambores del Río"]),
        ("atrasados", ["Ferretería La Esquina"]),
        ("saldo", ["Ferretería La Esquina", "Grupo de danza Tambores del Río",
                   "Restaurante El Fogón Costeño", "Colegio Nuevo Amanecer"]),
        ("entregados", ["Comparsa Brisa Caribe"]),
    ],
)
def test_cada_filtro_muestra_sus_pedidos(sesion_duena, ejemplo, filtro, esperados):
    html = sesion_duena.get(LISTA, {"filtro": filtro}).text

    assert clientes_en_orden(html) == esperados
    assert 'aria-current="true"' in html


def test_un_filtro_desconocido_es_todos(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA, {"filtro": "inventado"}).text

    assert len(clientes_en_orden(html)) == 6
    assert filtro_elegido(html) == "Todos 6"


def test_los_entregados_van_al_final_del_mas_reciente_al_mas_viejo(sesion_duena, taller):
    hoy = timezone.localdate()
    entregado_viejo = fabricas.crear_pedido(
        taller, fabricas.crear_cliente(taller, "Entregado viejo"), estado="entregado",
        fecha_entrega=hoy - timedelta(days=20))
    entregado_nuevo = fabricas.crear_pedido(
        taller, fabricas.crear_cliente(taller, "Entregado nuevo"), estado="entregado",
        fecha_entrega=hoy - timedelta(days=2))
    lejano = fabricas.crear_pedido(
        taller, fabricas.crear_cliente(taller, "Lejano"), fecha_entrega=hoy + timedelta(days=40))
    cercano = fabricas.crear_pedido(
        taller, fabricas.crear_cliente(taller, "Cercano"), fecha_entrega=hoy + timedelta(days=4))

    html = sesion_duena.get(LISTA).text

    esperados = [cercano, lejano, entregado_nuevo, entregado_viejo]
    assert clientes_en_orden(html) == [p.cliente.nombre for p in esperados]


def test_cada_fila_abre_su_pedido(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    for pedido in Pedido.objects.filter(taller=ejemplo):
        assert f'href="{reverse("pedidos:detalle", args=[pedido.pk])}"' in html


def test_la_tabla_va_en_una_tarjeta_recortada_con_sus_pestanas(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    assert 'class="tarjeta tarjeta--recortada tarjeta--lista-celular"' in html
    assert '<div class="filtros">\n<div class="filtros__pestanas"' in html
    assert 'class="filtros__herramientas solo-computador"' in html
    assert '<div id="lista-pedidos">' in html
    assert '<div class="tabla-contenedor" id="lista-pedidos-tabla">' in html
    # Ya no hay pantalla fija: nada de lo que era para caber en 1366 x 768.
    for vieja in ("llenar", "desplazable", "zona-tabla", "tarjeta--lista "):
        assert vieja not in html, vieja


def test_cada_fila_tiene_un_id_que_no_cambia_al_buscar(sesion_duena, ejemplo):
    """Mientras se escribe, solo entran y salen las filas que cambian: se reconocen por su id."""
    ferreteria = Pedido.objects.get(taller=ejemplo, cliente__nombre="Ferretería La Esquina")
    pagina = sesion_duena.get(LISTA).text
    buscado = sesion_duena.get(LISTA, {"q": "esquina"}, headers=HTMX).text

    ids = re.findall(r'<tr class="tabla__fila" id="([^"]+)">', pagina)
    assert len(ids) == 6
    assert ids == [
        f"pedido-{Pedido.objects.get(taller=ejemplo, cliente__nombre=nombre).pk}"
        for nombre in clientes_en_orden(pagina)
    ]
    # La misma fila lleva el mismo id en la página y en la respuesta del buscador.
    assert re.findall(r'<tr class="tabla__fila" id="([^"]+)">', buscado) == [
        f"pedido-{ferreteria.pk}"]


def test_el_aviso_de_nada_coincide_tiene_su_id(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA, {"q": "zapatos"}, headers=HTMX).text

    assert '<div class="tarjeta__cuerpo" id="lista-pedidos-vacia">' in html
    assert "lista-pedidos-tabla" not in html


def test_sin_pedidos_invita_a_crear_el_primero(sesion_duena):
    html = sesion_duena.get(LISTA).text

    assert "Aquí vas a ver tus pedidos" in html
    assert "Cómo llevar los pedidos del taller" in html
    assert 'class="vacio"' in html
    assert "<table" not in html and "cifras--barra" not in html
    assert html.count(f'hx-get="{NUEVO}"') == 2  # el del encabezado y el de la pantalla vacía


def test_sin_pedidos_la_costurera_no_ve_el_boton_de_crear(client, costurera):
    client.force_login(costurera)

    html = client.get(LISTA).text

    assert "Aquí vas a ver tus pedidos" in html
    assert NUEVO not in html


def test_un_solo_pedido_dice_pedido_en_singular(sesion_duena, taller):
    fabricas.crear_pedido(taller)

    assert '<div class="paginas">1 pedido</div>' in sesion_duena.get(LISTA).text


def test_un_filtro_sin_pedidos_lo_dice_y_ofrece_ver_todos(sesion_duena, taller):
    fabricas.crear_pedido(taller)

    html = sesion_duena.get(LISTA, {"filtro": "atrasados"}).text

    assert "Ningún pedido en este filtro." in html
    assert f'href="{LISTA}?filtro=todos">Ver todos</a>' in html


# --- El buscador de la lista -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("busqueda", "esperado"),
    [
        ("ferreteria", "Ferretería La Esquina"),  # sin la tilde
        ("FOGÓN", "Restaurante El Fogón Costeño"),  # en mayúsculas
        ("overoles", "Ferretería La Esquina"),  # por la prenda
        ("polleras", "Grupo de danza Tambores del Río"),
        ("yolima", "Colegio Nuevo Amanecer"),  # por la encargada
    ],
)
def test_el_buscador_encuentra_por_cliente_prenda_o_encargada(sesion_duena, ejemplo, busqueda,
                                                              esperado):
    html = sesion_duena.get(LISTA, {"q": busqueda}).text

    assert clientes_en_orden(html) == [esperado]
    assert f'value="{busqueda}"' in html


def test_el_buscador_respeta_el_filtro_elegido(sesion_duena, ejemplo):
    # "Marta" lleva dos pedidos: Tambores (listo, en producción) y el Fogón (en corte).
    assert len(clientes_en_orden(sesion_duena.get(LISTA, {"q": "marta"}).text)) == 2

    html = sesion_duena.get(LISTA, {"filtro": "semana", "q": "marta"}).text

    assert clientes_en_orden(html) == ["Grupo de danza Tambores del Río"]
    assert '<input type="hidden" name="filtro" value="semana">' in html
    # Los demás filtros guardan lo buscado.
    assert f'href="{LISTA}?filtro=atrasados&amp;q=marta"' in html


def test_si_nada_coincide_lo_dice(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA, {"q": "zapatos"}).text

    assert clientes_en_orden(html) == []
    assert "Ningún pedido coincide con lo que buscas." in html
    assert "Ver todos</a>" in html


def test_mientras_se_escribe_htmx_recibe_solo_la_tabla_y_los_filtros(sesion_duena, ejemplo):
    respuesta = sesion_duena.get(LISTA, {"q": "esquina", "filtro": "todos"}, headers=HTMX)
    html = respuesta.text

    assert "<html" not in html
    assert html.lstrip().startswith('<div id="lista-pedidos">')
    assert '<div class="paginas">1 pedido</div>' in html
    assert clientes_en_orden(html) == ["Ferretería La Esquina"]
    assert 'id="filtros-pedidos" role="group" aria-label="Filtrar pedidos" hx-swap-oob="true"' in html
    assert "HX-Request" in respuesta["Vary"]


def test_al_volver_atras_htmx_recibe_la_pagina_entera(sesion_duena, ejemplo):
    cabeceras = {**HTMX, "HX-History-Restore-Request": "true"}

    html = sesion_duena.get(LISTA, {"q": "esquina"}, headers=cabeceras).text

    assert "<html" in html


def test_el_formulario_del_buscador_funciona_con_y_sin_javascript(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    assert f'<form role="search" action="{LISTA}" hx-get="{LISTA}"' in html
    assert 'hx-target="#lista-pedidos"' in html
    assert 'name="q"' in html


# --- Otro taller -------------------------------------------------------------------------------


def test_la_lista_no_muestra_pedidos_de_otro_taller(sesion_duena, taller):
    propio = fabricas.crear_pedido(taller, fabricas.crear_cliente(taller, "Cliente propio"))
    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_pedido(otro, fabricas.crear_cliente(otro, "Cliente ajeno"),
                                  detalle="Camisas ajenas", fecha_entrega=date(2020, 1, 1))

    html = sesion_duena.get(LISTA).text
    buscado = sesion_duena.get(LISTA, {"q": "ajen"}).text

    assert clientes_en_orden(html) == ["Cliente propio"]
    assert '>Todos <span class="filtro__conteo">1</span></a>' in html
    assert '>Atrasados <span class="filtro__conteo">0</span></a>' in html
    assert "Cliente ajeno" not in html and "Cliente ajeno" not in buscado
    assert reverse("pedidos:detalle", args=[ajeno.pk]) not in html
    assert propio.pk != ajeno.pk


# --- Nuevo pedido ------------------------------------------------------------------------------


def datos_validos(**cambios):
    datos = {
        "cliente": "Panadería de ejemplo",
        "tipo": "empresa",
        "detalle": "20 camisas polo con logo",
        "cantidad": "20",
        "tallaje": "adulto",
        "fecha_entrega": (timezone.localdate() + timedelta(days=30)).isoformat(),
        "total": "1.260.000",
        "whatsapp": "",
    }
    datos.update(cambios)
    return datos


def test_la_ventana_trae_todos_los_campos(sesion_duena):
    html = sesion_duena.get(NUEVO, headers=HTMX).text

    for etiqueta in ("Cliente", "Tipo de cliente", "¿Qué pidió?", "¿Para cuántas personas?",
                     "Tallas", "Fecha de entrega", "Valor total (pesos)", "WhatsApp (opcional)"):
        assert f">{etiqueta}</label>" in html, etiqueta
    assert "Adulto (XS a XXL)" in html and "Niño (4 a 16)" in html
    for ejemplo_en_campo in ("Ej.: Colegio San José", "Ej.: 20 camisas polo con logo bordado",
                             "Ej.: 1.200.000", "Ej.: 300 123 4567"):
        assert f'placeholder="{ejemplo_en_campo}"' in html, ejemplo_en_campo
    assert html.count('<div class="campos">') == 5
    assert ">Cancelar</button>" in html and ">Guardar pedido</button>" in html
    assert 'type="date"' in html
    assert f'hx-post="{NUEVO}" hx-target="#ventana"' in html
    assert "Guardar pedido" in html
    # El cuadro de la IA es de la etapa 3. Se buscan sus marcas, no las letras "IA" sueltas,
    # que pueden salir por azar en la clave del formulario (csrfmiddlewaretoken).
    for marca in ("ia-caja", "la IA", "con IA", "Dictar"):
        assert marca not in html, marca


def test_crear_un_pedido_con_htmx_lo_deja_cotizado_y_abre_su_detalle(sesion_duena, taller, duena):
    respuesta = sesion_duena.post(NUEVO, datos_validos(whatsapp="300 000 0000"), headers=HTMX)

    pedido = Pedido.objects.get()
    assert respuesta.status_code == 200
    assert respuesta["HX-Redirect"] == reverse("pedidos:detalle", args=[pedido.pk])
    assert pedido.taller == taller
    assert pedido.creado_por == duena
    assert pedido.estado == Pedido.Estado.COTIZADO
    assert pedido.encargada is None
    assert pedido.detalle == "20 camisas polo con logo"
    assert pedido.cantidad == 20
    assert pedido.tallaje == "adulto"
    assert pedido.fecha_entrega == timezone.localdate() + timedelta(days=30)
    assert pedido.total == 1_260_000
    assert pedido.cliente.nombre == "Panadería de ejemplo"
    assert pedido.cliente.tipo == "empresa"
    assert pedido.cliente.whatsapp == "300 000 0000"
    assert pedido.cliente.taller == taller


def test_crear_un_pedido_sin_javascript_lleva_al_detalle(sesion_duena):
    respuesta = sesion_duena.post(NUEVO, datos_validos())

    pedido = Pedido.objects.get()
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:detalle", args=[pedido.pk])


AVISO_PEDIDO = '<div id="avisos-pendientes" hidden><p data-aviso>Pedido guardado.</p></div>'


def test_al_crear_un_pedido_el_detalle_muestra_el_aviso_de_la_demo(sesion_duena):
    """La ventana lleva al pedido nuevo: el aviso ("Pedido guardado.", de la demo) sale allí."""
    respuesta = sesion_duena.post(NUEVO, datos_validos(), headers=HTMX)

    assert "HX-Trigger" not in respuesta  # se va a otra página: no va en la cabecera
    detalle = sesion_duena.get(respuesta["HX-Redirect"]).text
    assert AVISO_PEDIDO in detalle
    # Sale una sola vez: al volver a abrir el pedido ya no está.
    assert "avisos-pendientes" not in sesion_duena.get(respuesta["HX-Redirect"]).text


def test_al_crear_un_pedido_sin_javascript_tambien_avisa(sesion_duena):
    respuesta = sesion_duena.post(NUEVO, datos_validos(), follow=True)

    assert respuesta.redirect_chain[0][1] == 302
    assert AVISO_PEDIDO in respuesta.text


def test_un_formulario_con_errores_no_avisa(sesion_duena):
    respuesta = sesion_duena.post(NUEVO, datos_validos(cliente=""), headers=HTMX)

    assert respuesta.status_code == 422
    assert "HX-Trigger" not in respuesta
    assert "avisos-pendientes" not in sesion_duena.get(LISTA).text


def test_sin_javascript_la_ventana_abre_como_pagina(sesion_duena):
    html = sesion_duena.get(NUEVO).text

    assert "<html" in html and "ventana--pagina" in html and "Guardar pedido" in html


def test_si_el_cliente_ya_existe_lo_reutiliza_sin_mirar_mayusculas(sesion_duena, taller):
    existente = fabricas.crear_cliente(taller, "Colegio Nuevo Amanecer", tipo="colegio")

    sesion_duena.post(NUEVO, datos_validos(cliente="  colegio  NUEVO amanecer ", tipo="empresa",
                                           whatsapp="301 000 0000"))

    pedido = Pedido.objects.get()
    assert pedido.cliente == existente
    assert Cliente.objects.count() == 1
    existente.refresh_from_db()
    assert existente.nombre == "Colegio Nuevo Amanecer"
    assert existente.tipo == "colegio"  # su tipo no cambia
    assert existente.whatsapp == "301 000 0000"  # no tenía: se le pone


def test_si_el_cliente_ya_tenia_whatsapp_no_se_cambia(sesion_duena, taller):
    existente = fabricas.crear_cliente(taller, "Marcela P.", whatsapp="302 000 0000")

    sesion_duena.post(NUEVO, datos_validos(cliente="marcela p.", whatsapp="303 000 0000"))

    existente.refresh_from_db()
    assert existente.whatsapp == "302 000 0000"
    assert Pedido.objects.get().cliente == existente


def test_un_cliente_con_el_mismo_nombre_en_otro_taller_no_se_reutiliza(sesion_duena, taller):
    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_cliente(otro, "Marcela P.")

    sesion_duena.post(NUEVO, datos_validos(cliente="Marcela P."))

    pedido = Pedido.objects.get()
    assert pedido.cliente != ajeno
    assert pedido.cliente.taller == taller
    assert Cliente.objects.filter(taller=otro).count() == 1


def test_si_otra_persona_crea_el_mismo_cliente_a_la_vez_se_usa_ese(sesion_duena, taller,
                                                                     monkeypatch):
    """Dos personas guardan a la vez un pedido del mismo cliente nuevo.

    Justo después de buscarlo (y no encontrarlo), la otra persona lo guarda. Al crearlo,
    la base de datos no deja repetir el nombre en el taller: se usa el de la otra persona.
    """
    from django.db.models import QuerySet

    primero_de_verdad = QuerySet.first
    ya_paso = []

    def buscar_mientras_la_otra_guarda(queryset):
        if queryset.model is Cliente and not ya_paso:
            ya_paso.append(True)
            Cliente.objects.create(taller=taller, nombre="Marcela P.", tipo="particular",
                                   whatsapp="304 000 0000")
            return None
        return primero_de_verdad(queryset)

    monkeypatch.setattr(QuerySet, "first", buscar_mientras_la_otra_guarda)

    respuesta = sesion_duena.post(NUEVO, datos_validos(cliente="marcela p.", tipo="empresa"))

    assert ya_paso
    assert respuesta.status_code == 302
    assert Cliente.objects.count() == 1
    cliente = Cliente.objects.get()
    assert Pedido.objects.get().cliente == cliente
    assert cliente.nombre == "Marcela P." and cliente.tipo == "particular"


def test_el_taller_y_la_etapa_no_llegan_del_formulario(sesion_duena, taller):
    otro = fabricas.crear_taller()

    sesion_duena.post(NUEVO, datos_validos(taller=otro.pk, estado="entregado",
                                           creado_por=fabricas.crear_usuaria(otro).pk))

    pedido = Pedido.objects.get()
    assert pedido.taller == taller
    assert pedido.estado == Pedido.Estado.COTIZADO
    assert pedido.creado_por.taller == taller


@pytest.mark.parametrize(
    ("texto", "valor"),
    [("1260000", 1_260_000), ("1.260.000", 1_260_000), ("$ 380.000", 380_000),
     ("$380.000", 380_000), ("0", 0), ("1.000", 1_000)],
)
def test_el_valor_total_se_acepta_con_puntos_o_con_signo(sesion_duena, texto, valor):
    sesion_duena.post(NUEVO, datos_validos(total=texto))

    assert Pedido.objects.get().total == valor


@pytest.mark.parametrize(
    "texto",
    ["380,50", "-5000", "abc", "$", "1e6", "³", "380.5", "1.260.00", "1..000", ".500", "500."],
)
def test_leer_pesos_rechaza_lo_que_no_es_plata_entera(texto):
    assert leer_pesos(texto) is None


@pytest.mark.parametrize(
    ("cambios", "campo", "mensaje"),
    [
        ({"cliente": ""}, "cliente", "Escribe el nombre del cliente."),
        ({"cliente": "   "}, "cliente", "Escribe el nombre del cliente."),
        ({"cliente": "x" * 81}, "cliente", "El nombre es muy largo: usa máximo 80 letras."),
        ({"tipo": "otro"}, "tipo", "Elige uno de los tipos de la lista."),
        ({"detalle": ""}, "detalle", "Escribe qué pidió el cliente."),
        ({"cantidad": ""}, "cantidad", "Escribe para cuántas personas es el pedido."),
        ({"cantidad": "0"}, "cantidad", "Escribe un número entre 1 y 2000."),
        ({"cantidad": "2001"}, "cantidad", "Escribe un número entre 1 y 2000."),
        ({"cantidad": "veinte"}, "cantidad", "Escribe un número entero, por ejemplo 20."),
        ({"tallaje": "bebe"}, "tallaje", "Elige las tallas: adulto o niño."),
        ({"fecha_entrega": ""}, "fecha_entrega", "Elige la fecha de entrega."),
        ({"fecha_entrega": "2026-02-30"}, "fecha_entrega",
         "Elige una fecha de entrega que exista."),
        ({"total": ""}, "total", "Escribe el valor total en pesos."),
        ({"total": "380,50"}, "total",
         "Escribe el valor en pesos, solo con números. Por ejemplo: 380.000."),
        ({"total": "5000000000"}, "total", "Ese valor es demasiado alto. Revisa los ceros."),
        ({"whatsapp": "llamar"}, "whatsapp",
         "Escribe solo el número de WhatsApp, con o sin espacios."),
        ({"whatsapp": "123"}, "whatsapp",
         "Escribe solo el número de WhatsApp, con o sin espacios."),
    ],
)
def test_cada_campo_se_valida_con_un_mensaje_claro(sesion_duena, cambios, campo, mensaje):
    respuesta = sesion_duena.post(NUEVO, datos_validos(**cambios), headers=HTMX)

    html = respuesta.text
    assert respuesta.status_code == 422
    assert "<html" not in html and "ventana__cabeza" in html
    assert f'<span class="campo__error" id="id_{campo}_error">{mensaje}</span>' in html
    assert "Revisa los campos marcados." in html
    assert not Pedido.objects.exists()
    assert not Cliente.objects.exists()


def test_con_errores_se_conserva_lo_escrito(sesion_duena):
    html = sesion_duena.post(NUEVO, datos_validos(cantidad="0"), headers=HTMX).text

    assert 'value="Panadería de ejemplo"' in html
    assert 'value="1.260.000"' in html
    assert '<option value="empresa" selected>' in html


def test_con_errores_sin_javascript_responde_la_pagina_con_los_mensajes(sesion_duena):
    respuesta = sesion_duena.post(NUEVO, datos_validos(detalle=""))

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert "Escribe qué pidió el cliente." in respuesta.text


def test_sin_sesion_no_se_crea_nada(client, taller):
    respuesta = client.post(NUEVO, datos_validos())

    assert respuesta.status_code == 302
    assert not Pedido.objects.exists()


# --- El buscador del menú -----------------------------------------------------------------------


def test_el_buscador_del_menu_encuentra_pedidos_y_clientes(sesion_duena, ejemplo):
    html = sesion_duena.get(BUSCAR, {"q": "ESQUINA"}).text

    ferreteria = Pedido.objects.get(taller=ejemplo, cliente__nombre="Ferretería La Esquina")
    assert "«ESQUINA»" in html
    assert clientes_en_orden(html) == ["Ferretería La Esquina"]
    assert f'href="{reverse("pedidos:detalle", args=[ferreteria.pk])}"' in html
    assert '<h2 id="t-clientes">Clientes</h2>' in html
    assert f'href="{reverse("pedidos:clientes")}?q=Ferreter%C3%ADa%20La%20Esquina"' in html
    assert "Empresa" in html


def test_buscar_usa_el_lenguaje_de_pedidos(sesion_duena, ejemplo):
    html = sesion_duena.get(BUSCAR, {"q": "ESQUINA"}).text

    assert "hoja--completa" in html
    assert 'class="buscador-fila buscador-fila--sola"' in html
    assert html.count('class="tarjeta tarjeta--recortada') == 2
    assert '<div class="tabla-contenedor" id="resultados-pedidos-tabla">' in html
    assert "paginas" not in html
    assert re.search(r'<h2 id="t-clientes">Clientes</h2>.*?<table class="tabla">', html, re.S)
    assert "llenar" not in html and "desplazable" not in html and "tarjeta--resultados" not in html


def test_la_costurera_en_buscar_solo_ve_pedidos_sin_valores(client, costurera,
                                                           ejemplo_de_costurera):
    client.force_login(costurera)

    html = client.get(BUSCAR, {"q": "esquina"}).text

    assert clientes_en_orden(html) == ["Ferretería La Esquina"]
    assert '<h2 id="t-clientes">' not in html
    assert "celda-total" not in html and "Abonado" not in html and "Vencido" not in html


def test_el_buscador_del_menu_no_mira_tildes_ni_mayusculas(sesion_duena, ejemplo):
    html = sesion_duena.get(BUSCAR, {"q": "fogon costeno"}).text

    assert clientes_en_orden(html) == ["Restaurante El Fogón Costeño"]


def test_el_buscador_del_menu_encuentra_por_prenda_y_encargada(sesion_duena, ejemplo):
    assert clientes_en_orden(sesion_duena.get(BUSCAR, {"q": "vestidos"}).text) == [
        "Comparsa Brisa Caribe"]
    assert clientes_en_orden(sesion_duena.get(BUSCAR, {"q": "Carmen"}).text) == [
        "Ferretería La Esquina"]


def test_un_cliente_sin_pedidos_tambien_aparece(sesion_duena, taller):
    fabricas.crear_cliente(taller, "Academia de baile", tipo="comparsa")

    html = sesion_duena.get(BUSCAR, {"q": "academia"}).text

    assert "<strong>Academia de baile</strong>" in html
    assert '<h2 id="t-pedidos">' not in html


def test_el_buscador_del_menu_vacio_da_una_pista(sesion_duena, ejemplo):
    html = sesion_duena.get(BUSCAR).text

    assert "Escribe el nombre de un cliente, una prenda o una encargada." in html
    assert clientes_en_orden(html) == []
    assert '<h2 id="t-clientes">' not in html


def test_el_buscador_del_menu_dice_si_no_encuentra_nada(sesion_duena, ejemplo):
    html = sesion_duena.get(BUSCAR, {"q": "zapatos"}).text

    assert "No hay pedidos ni clientes que coincidan con «zapatos»." in html


def test_el_buscador_del_menu_no_muestra_nada_de_otro_taller(sesion_duena, taller):
    otro = fabricas.crear_taller()
    fabricas.crear_pedido(otro, fabricas.crear_cliente(otro, "Cliente ajeno"),
                          detalle="Camisas ajenas")
    fabricas.crear_cliente(otro, "Otro ajeno")

    html = sesion_duena.get(BUSCAR, {"q": "ajen"}).text

    assert "Cliente ajeno" not in html and "Otro ajeno" not in html
    assert "No hay pedidos ni clientes que coincidan" in html


# --- Celular y computador (en Chrome) -------------------------------------------------------------

# Que la página no se desborde de lado y que la tabla se vuelva lista en celular.
MEDIR_DESBORDE = """() => ({
  ancho: document.documentElement.scrollWidth, ventana: innerWidth,
  filas_visibles: [...document.querySelectorAll('.tabla--pedidos tbody tr')]
    .filter(f => f.offsetHeight > 0).length,
  prenda_visible: [...document.querySelectorAll('.tabla--pedidos .tabla__prenda')]
    .some(c => c.offsetHeight > 0),
  apoyo_visible: [...document.querySelectorAll('.tabla--pedidos .celda-apoyo')]
    .some(c => c.offsetHeight > 0),
})"""


def _abrir_chrome():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright no está instalado (uv sync con el grupo dev).")
    manejador = sync_playwright().start()
    try:
        return manejador, manejador.chromium.launch(channel="chrome")
    except Exception as error:  # noqa: BLE001 (sin Chrome no hay prueba)
        manejador.stop()
        pytest.skip(f"No se pudo abrir Chrome: {error}")


@pytest.mark.django_db(transaction=True)
def test_pedidos_y_buscar_no_se_desbordan_y_la_tabla_se_vuelve_lista_en_celular(live_server):
    from django.test import Client

    from cuentas.models import Usuario

    taller = ejemplos.cargar(con_fotos=False)
    navegador_django = Client()
    navegador_django.force_login(Usuario.objects.get(taller=taller, rol=Usuario.Rol.DUENA))
    sesion = navegador_django.cookies["sessionid"].value

    manejador, navegador = _abrir_chrome()
    medidas = {}
    try:
        for ancho, alto in [(1280, 800), (390, 844)]:
            contexto = navegador.new_context(viewport={"width": ancho, "height": alto})
            contexto.add_cookies([{"name": "sessionid", "value": sesion,
                                   "url": live_server.url}])
            pagina = contexto.new_page()
            for direccion in ["/pedidos/", "/buscar/?q=a"]:
                pagina.goto(live_server.url + direccion, wait_until="load")
                pagina.evaluate("document.fonts.ready")
                medidas[(direccion, ancho)] = pagina.evaluate(MEDIR_DESBORDE)
            contexto.close()
    finally:
        navegador.close()
        manejador.stop()

    for (direccion, ancho), medida in medidas.items():
        donde = f"{direccion} en {ancho} px"
        assert medida["ancho"] <= medida["ventana"], f"{donde}: se desborda de lado"
        assert medida["filas_visibles"] > 0, donde
        assert medida["prenda_visible"] == (ancho > 768), f"{donde}: columna Prenda"
        assert medida["apoyo_visible"] == (ancho < 768), f"{donde}: línea de apoyo del celular"
