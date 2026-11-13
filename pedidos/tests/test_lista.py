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


@pytest.fixture
def ejemplo(taller, duena):
    """Los pedidos de diseno/pedidos.html, contados desde hoy y a nombre de la dueña."""
    return ejemplos.cargar(taller=taller, con_fotos=False)


def clientes_en_orden(html):
    """Los nombres de cliente de la tabla, en el orden en que salen."""
    return re.findall(r'class="tabla__enlace" href="[^"]+"><strong>([^<]+)</strong>', html)


def filtro_elegido(html):
    return re.search(r'class="filtro es-elegido"[^>]*>([^<]+)</a>', html).group(1)


# --- La lista ---------------------------------------------------------------------------------


def test_la_lista_sale_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    assert '<span class="encabezado__apoyo">6 pedidos</span>' in html
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
        "8 overoles con logo estampado",
        '<span class="etiqueta etiqueta--azul">En confección</span>',
        '<span class="etiqueta etiqueta--rojo">Atrasado 2 días</span>',
        '<span class="etiqueta etiqueta--ambar">Faltan 3 días</span>',
        '<span class="etiqueta etiqueta--verde">Entregado</span>',
        '<span class="etiqueta etiqueta--gris">Cotizado</span>',
        "<td>Carmen</td>",
        '<span class="texto-2">Sin asignar</span>',
        "<td>8 de 8</td>",
        "<td>0 de 1</td>",
        "<td>14 de 18</td>",
        "<td>9 de 40</td>",
        '<strong class="texto-rojo dinero">$ 480.000</strong>',
        '<strong class="texto-rojo dinero">$ 3.300.000</strong>',
        'Cotizado en <span class="dinero">$ 380.000</span>',
        '<strong class="texto-verde">Pagado</strong>',
    ):
        assert texto in html, texto


def test_los_filtros_muestran_su_conteo_como_en_el_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    for texto in ("Todos 6", "En producción 4", "Esta semana 1", "Atrasados 1", "Con saldo 4",
                  "Entregados 1"):
        assert f">{texto}</a>" in html, texto
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


def test_la_tabla_se_desplaza_dentro_de_su_tarjeta(sesion_duena, ejemplo):
    html = sesion_duena.get(LISTA).text

    assert '<div class="tabla-contenedor">' in html
    assert '<table class="tabla tabla--pedidos">' in html


def test_sin_pedidos_invita_a_crear_el_primero(sesion_duena):
    html = sesion_duena.get(LISTA).text

    assert '<span class="encabezado__apoyo">0 pedidos</span>' in html
    assert "Todavía no hay pedidos" in html
    assert "<table" not in html
    assert html.count(f'hx-get="{NUEVO}"') == 2


def test_un_solo_pedido_dice_pedido_en_singular(sesion_duena, taller):
    fabricas.crear_pedido(taller)

    assert '<span class="encabezado__apoyo">1 pedido</span>' in sesion_duena.get(LISTA).text


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
    assert clientes_en_orden(html) == ["Ferretería La Esquina"]
    assert 'aria-label="Filtrar pedidos" hx-swap-oob="true"' in html
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
    assert ">Todos 1</a>" in html and ">Atrasados 0</a>" in html
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
    assert 'type="date"' in html
    assert f'hx-post="{NUEVO}" hx-target="#ventana"' in html
    assert "Guardar pedido" in html
    assert "IA" not in html  # el cuadro de la IA es de la etapa 3


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
