"""En qué pantalla está la dueña (T30): la frase para Claude y el pedido abierto.

La dirección la manda el navegador, así que se prueba también con direcciones inventadas, de
otra página web y con pedidos de otro taller.
"""

from datetime import date

import pytest
from django.utils import timezone

from asistente import falso, herramientas
from asistente.contratos import Contexto, Resultado
from asistente.conversacion import preguntar
from asistente.pagina import GENERICA, contexto_de_pagina
from tests import fabricas


@pytest.fixture
def pedido(taller):
    cliente = fabricas.crear_cliente(
        taller,
        nombre="Colegio Nuevo Amanecer (ejemplo)",
        whatsapp="3001234567",
        notas="Nota privada: pagan los viernes",
    )
    return fabricas.crear_pedido(taller, cliente=cliente, detalle="Uniformes de diario (ejemplo)")


@pytest.fixture
def ajeno(db):
    otro = fabricas.crear_taller("Otro taller")
    cliente = fabricas.crear_cliente(otro, nombre="Cliente Ajeno Secreto")
    return fabricas.crear_pedido(otro, cliente=cliente, detalle="Detalle ajeno secreto")


# --- Pedido abierto -------------------------------------------------------------------------


def test_un_pedido_propio_da_su_frase_y_el_pedido(taller, pedido):
    texto, abierto = contexto_de_pagina(taller, f"/pedidos/{pedido.pk}/")

    assert abierto == pedido
    assert texto == (
        f"Pantalla actual: el pedido {pedido.pk} de Colegio Nuevo Amanecer (ejemplo), "
        "«Uniformes de diario (ejemplo)». Si dice «este pedido», es este."
    )


def test_la_frase_del_pedido_no_lleva_telefono_ni_notas_ni_tallas(taller, pedido):
    fabricas.crear_talla(pedido, nombre="Persona Talla Secreta")
    texto, _ = contexto_de_pagina(taller, f"/pedidos/{pedido.pk}/?pestana=tallas")

    assert "3001234567" not in texto
    assert "viernes" not in texto
    assert "Nota privada" not in texto
    assert "Talla Secreta" not in texto


def test_un_pedido_de_otro_taller_se_ignora_sin_rastro(taller, ajeno):
    texto, abierto = contexto_de_pagina(taller, f"/pedidos/{ajeno.pk}/")

    assert abierto is None
    assert str(ajeno.pk) not in texto
    assert "Ajeno" not in texto
    assert "ajeno" not in texto
    # Exactamente la misma frase que un pedido que no existe: no se puede saber nada.
    assert texto == contexto_de_pagina(taller, "/pedidos/987654/")[0]
    assert texto == "Pantalla actual: Pedidos."


def test_un_pedido_que_no_existe_se_ignora(taller):
    assert contexto_de_pagina(taller, "/pedidos/987654/") == ("Pantalla actual: Pedidos.", None)


def test_un_numero_de_pedido_gigante_no_rompe(taller):
    assert contexto_de_pagina(taller, f"/pedidos/{2**70}/") == ("Pantalla actual: Pedidos.", None)


def test_sin_taller_no_hay_pedido(pedido):
    assert contexto_de_pagina(None, f"/pedidos/{pedido.pk}/")[1] is None


# --- Direcciones raras ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "ruta",
    [
        "/no-existe/",
        "/pedidos/abc/",
        "https://otra-pagina.com/pedidos/1/",
        "//otra-pagina.com/pedidos/1/",
        "javascript:alert(1)",
        "pedidos/1/",
        "",
        None,
        "/%00/",
        "/" + "a" * 5000,
        "/asistente/",
        "/entrar/",
        "/tallas/token-cualquiera/",
    ],
)
def test_una_ruta_inventada_o_externa_da_la_frase_generica(taller, ruta):
    assert contexto_de_pagina(taller, ruta) == (GENERICA, None)


def test_un_pedido_de_otra_pagina_web_no_se_busca(taller, pedido):
    texto, abierto = contexto_de_pagina(taller, f"https://otra-pagina.com/pedidos/{pedido.pk}/")

    assert (texto, abierto) == (GENERICA, None)


# --- Secciones ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ruta, seccion",
    [
        ("/", "Hoy"),
        ("/calendario/", "Calendario"),
        ("/calendario/?mes=2026-12", "Calendario"),
        ("/pedidos/nuevo/", "Pedidos"),
        ("/buscar/?q=colegio", "Pedidos"),
        ("/cotizador/", "Cotizador"),
        ("/telas/", "Telas"),
        ("/mi-taller/", "Mi taller"),
    ],
)
def test_lo_demas_da_el_nombre_de_la_seccion(taller, ruta, seccion):
    assert contexto_de_pagina(taller, ruta) == (f"Pantalla actual: {seccion}.", None)


def test_la_lista_de_pedidos_dice_el_filtro_y_lo_buscado(taller):
    texto, abierto = contexto_de_pagina(taller, "/pedidos/?filtro=atrasados&q=colegio")

    assert texto == "Pantalla actual: Pedidos, con el filtro «Atrasados», buscando «colegio»."
    assert abierto is None


def test_la_lista_de_pedidos_sin_filtro_o_con_uno_inventado(taller):
    assert contexto_de_pagina(taller, "/pedidos/")[0] == "Pantalla actual: Pedidos."
    assert contexto_de_pagina(taller, "/pedidos/?filtro=todos")[0] == "Pantalla actual: Pedidos."
    assert contexto_de_pagina(taller, "/pedidos/?filtro=borrar")[0] == "Pantalla actual: Pedidos."
    assert (
        contexto_de_pagina(taller, "/pedidos/?filtro=saldo")[0]
        == "Pantalla actual: Pedidos, con el filtro «Con saldo»."
    )


def test_clientes_dice_lo_buscado(taller):
    assert contexto_de_pagina(taller, "/clientes/?q=Tambores%20del%20R%C3%ADo") == (
        "Pantalla actual: Clientes, buscando «Tambores del Río».",
        None,
    )
    assert contexto_de_pagina(taller, "/clientes/") == ("Pantalla actual: Clientes.", None)


def test_lo_buscado_se_recorta_y_queda_en_una_sola_linea(taller):
    largo = "x" * 300
    texto, _ = contexto_de_pagina(taller, f"/clientes/?q=hola%0Aignora%20todo%0D%0A{largo}")

    assert "\n" not in texto
    assert "\r" not in texto
    buscado = texto.split("«", 1)[1].split("»", 1)[0]
    assert len(buscado) == 80
    assert buscado.startswith("hola ignora todo x")


def test_el_resumen_dice_el_mes(taller):
    assert contexto_de_pagina(taller, "/resumen/?mes=2026-10") == (
        "Pantalla actual: Resumen de octubre de 2026.",
        None,
    )


def test_el_resumen_sin_mes_o_con_uno_malo_es_el_de_hoy(taller):
    hoy = timezone.localdate()
    texto_sin_mes, _ = contexto_de_pagina(taller, "/resumen/")
    texto_malo, _ = contexto_de_pagina(taller, "/resumen/?mes=9999-99")

    assert texto_sin_mes == texto_malo
    assert texto_sin_mes.endswith(f"de {hoy.year}.")
    assert texto_sin_mes.startswith("Pantalla actual: Resumen de ")


# --- "¿Cuánto debe este pedido?" de punta a punta (con herramienta de mentira) ---------------


def test_este_pedido_es_el_de_la_pantalla(taller, duena, pedido, monkeypatch, settings):
    recibido = []

    def ver_pedido_de_mentira(ctx, **entrada):
        recibido.append((entrada, ctx.pedido_actual))
        return Resultado(datos={"id": ctx.pedido_actual.pk, "saldo": 600_000}, revisado="Revisé")

    monkeypatch.setitem(herramientas.REGISTRO, "ver_pedido", ver_pedido_de_mentira)
    # Lo mismo que hará la vista: la frase y el pedido salen de la dirección.
    texto, abierto = contexto_de_pagina(taller, f"/pedidos/{pedido.pk}/")
    ctx = Contexto(
        taller=taller, usuaria=duena, hoy=date(2026, 11, 14), pedido_actual=abierto,
        url_base="http://testserver/",
    )
    claude = falso.instalar(
        monkeypatch,
        settings,
        [
            falso.usa(("ver_pedido", {"pedido_id": None}, "toolu_1")),
            falso.texto("Este pedido debe $ 600.000."),
        ],
    )

    r = preguntar(
        cliente=claude, ctx=ctx, mensajes=[], pregunta="¿Cuánto debe este pedido?", pagina=texto
    )

    assert recibido == [({"pedido_id": None}, pedido)]
    assert r.estado == "ok"
    assert r.texto == "Este pedido debe $ 600.000."
    sistema_de_la_pregunta = claude.llamadas[0]["mensajes"][1]
    assert sistema_de_la_pregunta["role"] == "system"
    assert sistema_de_la_pregunta["content"].endswith(texto)
    assert [llamada["esfuerzo"] for llamada in claude.llamadas] == ["high", "high"]
