"""Cronología del pedido por dentro: lo que ha pasado, por día, con lo que ya se guarda."""

from datetime import date, datetime, timedelta, timezone as zona_utc

import pytest
from django.urls import reverse
from django.utils import timezone

from pedidos import cronologia
from pedidos.models import Talla
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


def a_las(dia, hora=12):
    """Un momento de ese día en Bogotá (UTC-5)."""
    return datetime(dia.year, dia.month, dia.day, hora + 5, 0, tzinfo=zona_utc.utc)


def fechar(objeto, momento):
    """Cambia la fecha de creación (auto_now_add no deja ponerla al crear)."""
    type(objeto).objects.filter(pk=objeto.pk).update(creado=momento)


@pytest.fixture
def hoy():
    return timezone.localdate()


@pytest.fixture
def pedido(taller, duena, hoy):
    pedido = fabricas.crear_pedido(taller, total=2_520_000, creado_por=duena)
    pedido.creado = a_las(hoy - timedelta(days=9))
    pedido.save()
    return pedido


def textos(dias):
    return [(d.nombre, [(e.antes, e.valor, e.despues, e.quien) for e in d.eventos]) for d in dias]


def test_el_pedido_creado_dice_el_valor_y_quien_lo_creo(pedido, duena, hoy):
    dias = cronologia.cronologia(pedido, hoy=hoy)

    assert len(dias) == 1
    evento = dias[0].eventos[0]
    assert evento.antes == "Se creó el pedido por "
    assert evento.valor == 2_520_000
    assert evento.quien == duena.nombre


def test_los_dias_van_del_mas_reciente_al_mas_antiguo_con_hoy_y_ayer(pedido, duena, hoy):
    abono = fabricas.crear_abono(pedido, valor=1_260_000, fecha=hoy - timedelta(days=1))
    fechar(abono, a_las(hoy - timedelta(days=1)))
    otro = fabricas.crear_abono(pedido, valor=100_000, fecha=hoy)

    dias = cronologia.cronologia(pedido, hoy=hoy)

    assert [d.nombre for d in dias[:2]] == ["Hoy", "Ayer"]
    assert dias[0].eventos[0].valor == 100_000
    assert dias[1].eventos[0].valor == 1_260_000
    assert dias[2].nombre == cronologia.dia_y_mes(hoy - timedelta(days=9))
    assert otro.registrado_por == duena


def test_los_dias_viejos_dicen_el_dia_y_el_mes_y_el_anio_si_cambia(pedido, hoy):
    pedido.creado = a_las(date(hoy.year - 1, 11, 5))
    pedido.save()

    assert cronologia.cronologia(pedido, hoy=hoy)[0].nombre == f"5 de noviembre de {hoy.year - 1}"
    assert cronologia.nombre_del_dia(date(2026, 11, 7), date(2026, 11, 13)) == "7 de noviembre"


def test_las_tallas_del_enlace_se_juntan_por_dia(pedido, hoy):
    ayer = hoy - timedelta(days=1)
    for _ in range(3):
        fechar(fabricas.crear_talla(pedido, origen=Talla.Origen.ENLACE), a_las(ayer, 9))
    fechar(fabricas.crear_talla(pedido, origen=Talla.Origen.ENLACE), a_las(hoy, 9))

    dias = textos(cronologia.cronologia(pedido, hoy=hoy))

    assert ("3 personas enviaron su talla por el enlace.", None, "", "Enlace") in [
        e for d in dias for e in d[1]
    ]
    assert dias[0][0] == "Hoy"
    assert dias[0][1] == [("1 persona envió su talla por el enlace.", None, "", "Enlace")]
    assert dias[1][0] == "Ayer"


def test_las_tallas_a_mano_van_una_por_una_con_el_nombre_de_la_persona(pedido, hoy):
    fabricas.crear_talla(pedido, nombre="Ana Ejemplo", origen=Talla.Origen.MANUAL)
    fabricas.crear_talla(pedido, nombre="Luis Ejemplo", origen=Talla.Origen.MANUAL)

    hoy_ = cronologia.cronologia(pedido, hoy=hoy)[0]

    assert hoy_.nombre == "Hoy"
    assert {e.antes for e in hoy_.eventos} == {
        "Se agregó a mano la talla de Ana Ejemplo.",
        "Se agregó a mano la talla de Luis Ejemplo.",
    }


def test_la_costurera_no_ve_plata_ni_abonos(pedido, hoy):
    fabricas.crear_abono(pedido, valor=777_000)

    dias = cronologia.cronologia(pedido, con_plata=False, hoy=hoy)

    todo = [e for d in dias for e in d.eventos]
    assert all(e.valor is None for e in todo)
    assert [e.antes for e in todo] == ["Se creó el pedido."]


def test_otro_taller_no_aparece(pedido, hoy):
    ajeno = fabricas.crear_pedido(fabricas.crear_taller(), total=9_999_000)
    fabricas.crear_abono(ajeno, valor=555_000)
    fabricas.crear_talla(ajeno, nombre="Persona ajena", origen=Talla.Origen.MANUAL)

    dias = cronologia.cronologia(pedido, hoy=hoy)

    assert all("ajena" not in e.antes and e.valor != 555_000 for d in dias for e in d.eventos)


# --- En la página ------------------------------------------------------------------------------


def test_la_pagina_muestra_la_cronologia_de_la_duena(sesion_duena, pedido, hoy):
    fabricas.crear_abono(pedido, valor=1_260_000)
    fabricas.crear_talla(pedido, origen=Talla.Origen.ENLACE)

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert '<h2 id="t-cronologia">Cronología</h2>' in html
    assert '<ol class="cronologia">' in html
    assert '<li class="cronologia__dia">Hoy</li>' in html
    assert "1 persona envió su talla por el enlace." in html
    assert 'Se registró un abono de <span class="dinero">$ 1.260.000</span>.' in html
    assert 'Se creó el pedido por <span class="dinero">$ 2.520.000</span>.' in html
    assert '<span class="cronologia__quien">Enlace</span>' in html


def test_la_pagina_de_la_costurera_no_trae_plata_en_la_cronologia(client, costurera, pedido):
    fabricas.crear_abono(pedido, valor=1_260_000)
    client.force_login(costurera)

    html = client.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    cuerpo = html.split('id="pedido-cronologia"')[1].split("</section>")[0]
    assert "Se creó el pedido." in cuerpo
    assert "abono" not in cuerpo and "dinero" not in cuerpo
    assert "1.260.000" not in html and "2.520.000" not in html


def test_registrar_un_abono_trae_la_cronologia_nueva(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        reverse("pedidos:abono_nuevo", args=[pedido.pk]), {"valor": "300.000"}, headers=HTMX
    )

    assert 'id="pedido-cronologia"' in respuesta.text
    assert 'hx-swap-oob="true"' in respuesta.text.split('id="pedido-cronologia"')[1][:80]
    assert "$ 300.000" in respuesta.text.split('id="pedido-cronologia"')[1]


def test_un_pedido_de_otro_taller_no_se_ve_en_la_cronologia(sesion_duena, pedido):
    ajeno = fabricas.crear_pedido(fabricas.crear_taller(), total=9_999_000)

    assert sesion_duena.get(reverse("pedidos:detalle", args=[ajeno.pk])).status_code == 404
