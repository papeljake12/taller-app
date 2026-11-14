"""Uso y límites del asistente (T34): el cupo de preguntas de cada taller.

Ninguna de estas pruebas llama a Claude: el cupo se cuenta en la base de datos.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.template.loader import render_to_string

from asistente import uso
from asistente.contratos import Uso
from asistente.models import UsoAsistente
from tests import fabricas

HOY = date(2026, 11, 14)


@pytest.fixture
def prendido(db):
    return fabricas.crear_taller(asistente_limite_mes=600, asistente_limite_dia=40)


def _preguntas(taller, fecha=HOY):
    fila = UsoAsistente.objects.filter(taller=taller, fecha=fecha).first()
    return fila.preguntas if fila else 0


# --- Cupo: las cuentas ----------------------------------------------------------------------


def test_cupo_sin_uso_tiene_todo_por_delante(prendido):
    cupo = uso.cupo(prendido, HOY)

    assert (cupo.usadas_hoy, cupo.usadas_mes) == (0, 0)
    assert (cupo.limite_dia, cupo.limite_mes) == (40, 600)
    assert cupo.quedan == 40
    assert cupo.porcentaje_mes == 0
    assert cupo.agotado == ""
    assert not cupo.pocas


def test_cupo_suma_el_dia_y_el_mes(prendido):
    fabricas.crear_uso(prendido, fecha=HOY, preguntas=6)
    fabricas.crear_uso(prendido, fecha=date(2026, 11, 2), preguntas=122)
    fabricas.crear_uso(prendido, fecha=date(2026, 10, 31), preguntas=300)  # otro mes

    cupo = uso.cupo(prendido, HOY)

    assert (cupo.usadas_hoy, cupo.usadas_mes) == (6, 128)
    assert cupo.porcentaje_mes == 21  # 128 de 600, como en diseno/mi-taller.html
    assert cupo.quedan == 34


def test_quedan_manda_el_limite_que_se_acaba_primero():
    assert uso.Cupo(usadas_hoy=2, limite_dia=40, usadas_mes=590, limite_mes=600).quedan == 10
    assert uso.Cupo(usadas_hoy=38, limite_dia=40, usadas_mes=100, limite_mes=600).quedan == 2


@pytest.mark.parametrize(
    "usadas_hoy, usadas_mes, agotado",
    [(39, 100, ""), (40, 100, "dia"), (10, 600, "mes"), (40, 600, "mes"), (45, 700, "mes")],
)
def test_agotado_dice_cual_limite_se_acabo(usadas_hoy, usadas_mes, agotado):
    cupo = uso.Cupo(usadas_hoy=usadas_hoy, limite_dia=40, usadas_mes=usadas_mes, limite_mes=600)

    assert cupo.agotado == agotado
    assert cupo.quedan == (0 if agotado else 40 - usadas_hoy)


@pytest.mark.parametrize(
    "usadas_hoy, usadas_mes, pocas",
    [
        (34, 100, False),  # quedan 6 hoy
        (35, 100, True),  # quedan 5 hoy
        (39, 100, True),  # queda 1 hoy
        (1, 539, False),  # quedan 61 del mes
        (1, 540, True),  # quedan 60 del mes: el 10 %
        (40, 100, False),  # ya no hay: no es "pocas", es "sin preguntas"
        (1, 600, False),
    ],
)
def test_pocas_con_5_del_dia_o_el_10_por_ciento_del_mes(usadas_hoy, usadas_mes, pocas):
    cupo = uso.Cupo(usadas_hoy=usadas_hoy, limite_dia=40, usadas_mes=usadas_mes, limite_mes=600)

    assert cupo.pocas is pocas


def test_el_porcentaje_del_mes_no_pasa_de_100():
    assert uso.Cupo(0, 40, 650, 600).porcentaje_mes == 100
    assert uso.Cupo(0, 0, 0, 0).porcentaje_mes == 100


def test_los_textos_de_pocas_y_del_limite():
    del_dia = uso.Cupo(usadas_hoy=36, limite_dia=40, usadas_mes=100, limite_mes=600, hoy=HOY)
    una = uso.Cupo(usadas_hoy=39, limite_dia=40, usadas_mes=100, limite_mes=600, hoy=HOY)
    del_mes = uso.Cupo(usadas_hoy=1, limite_dia=40, usadas_mes=570, limite_mes=600, hoy=HOY)
    sin_dia = uso.Cupo(usadas_hoy=40, limite_dia=40, usadas_mes=100, limite_mes=600, hoy=HOY)
    sin_mes = uso.Cupo(usadas_hoy=4, limite_dia=40, usadas_mes=600, limite_mes=600, hoy=HOY)

    assert del_dia.aviso == "Te quedan 4 preguntas por hoy. Mañana vuelves a tener 40."
    assert una.aviso == "Te queda 1 pregunta por hoy. Mañana vuelves a tener 40."
    assert del_mes.aviso == (
        "Te quedan 30 preguntas este mes. El 1 de diciembre vuelves a tener 600."
    )
    assert sin_dia.aviso == "" and sin_dia.mensaje_limite == (
        "Por hoy ya usaste las 40 preguntas. Mañana vuelvo a contestar."
    )
    assert sin_dia.vuelve == "Vuelvo a contestar mañana"
    assert sin_mes.mensaje_limite == (
        "Este mes ya usaste las 600 preguntas. Vuelvo a contestar el 1 de diciembre."
    )
    assert sin_mes.vuelve == "Vuelvo a contestar el 1 de diciembre"
    assert del_dia.mensaje_limite == ""


def test_en_diciembre_vuelve_el_1_de_enero():
    cupo = uso.Cupo(0, 40, 600, 600, hoy=date(2026, 12, 20))

    assert cupo.vuelve_el == date(2027, 1, 1)
    assert cupo.vuelve == "Vuelvo a contestar el 1 de enero"


# --- reservar, devolver y anotar ------------------------------------------------------------


def test_reservar_suma_una_pregunta(prendido):
    assert uso.reservar(prendido, HOY) is True
    assert uso.reservar(prendido, HOY) is True

    assert _preguntas(prendido) == 2
    assert uso.cupo(prendido, HOY).usadas_hoy == 2


def test_al_llegar_a_40_del_dia_no_reserva_mas(prendido):
    fabricas.crear_uso(prendido, fecha=HOY, preguntas=39)

    assert uso.reservar(prendido, HOY) is True
    assert uso.reservar(prendido, HOY) is False

    assert _preguntas(prendido) == 40
    cupo = uso.cupo(prendido, HOY)
    assert cupo.agotado == "dia"
    assert cupo.mensaje_limite == "Por hoy ya usaste las 40 preguntas. Mañana vuelvo a contestar."
    # Al día siguiente vuelve a haber.
    assert uso.reservar(prendido, HOY + timedelta(days=1)) is True


def test_al_llegar_a_600_del_mes_no_reserva_mas(prendido):
    fabricas.crear_uso(prendido, fecha=date(2026, 11, 1), preguntas=599)

    assert uso.reservar(prendido, HOY) is True
    assert uso.reservar(prendido, HOY) is False
    # Mañana tampoco: el mes manda. El 1 de diciembre sí.
    assert uso.reservar(prendido, date(2026, 11, 30)) is False
    assert uso.reservar(prendido, date(2026, 12, 1)) is True

    cupo = uso.cupo(prendido, HOY)
    assert cupo.agotado == "mes"
    assert cupo.mensaje_limite == (
        "Este mes ya usaste las 600 preguntas. Vuelvo a contestar el 1 de diciembre."
    )


def test_mandan_los_limites_que_david_pone_en_admin(sesion_administrador, prendido):
    respuesta = sesion_administrador.post(
        f"/admin/cuentas/taller/{prendido.pk}/change/",
        {"nombre": prendido.nombre, "telefono": "", "asistente_limite_mes": 600,
         "asistente_limite_dia": 2},
    )
    assert respuesta.status_code == 302

    # Aunque el objeto en memoria tenga el límite viejo, reservar lee el de la base.
    assert prendido.asistente_limite_dia == 40
    assert [uso.reservar(prendido, HOY) for _ in range(3)] == [True, True, False]


def test_reservar_lee_el_taller_de_la_base_para_el_mes(prendido):
    from cuentas.models import Taller

    Taller.objects.filter(pk=prendido.pk).update(asistente_limite_mes=1)

    assert uso.reservar(prendido, HOY) is True
    assert uso.reservar(prendido, HOY) is False


def test_el_dia_y_el_mes_se_cuentan_en_hora_de_bogota(prendido, monkeypatch):
    # 1 de diciembre a las 3 de la mañana en Londres es todavía 30 de noviembre en Bogotá.
    utc = datetime(2026, 12, 1, 3, 0, tzinfo=ZoneInfo("UTC"))
    monkeypatch.setattr("django.utils.timezone.now", lambda: utc)
    fabricas.crear_uso(prendido, fecha=date(2026, 11, 3), preguntas=599)

    assert uso.reservar(prendido) is True  # la 600 de noviembre, anotada el 30
    assert uso.reservar(prendido) is False  # sigue siendo noviembre: ya van 600

    assert _preguntas(prendido, date(2026, 11, 30)) == 1
    assert not UsoAsistente.objects.filter(fecha=date(2026, 12, 1)).exists()
    assert uso.cupo(prendido).usadas_mes == 600
    assert uso.cupo(prendido).hoy == date(2026, 11, 30)


def test_devolver_resta_y_nunca_baja_de_0(prendido):
    uso.reservar(prendido, HOY)

    uso.devolver(prendido, HOY)
    uso.devolver(prendido, HOY)
    uso.devolver(prendido, HOY + timedelta(days=1))  # un día sin registro: no pasa nada

    assert _preguntas(prendido) == 0
    assert not UsoAsistente.objects.filter(fecha=HOY + timedelta(days=1)).exists()


def test_anotar_suma_los_cuatro_tipos_de_token(prendido):
    uso.reservar(prendido, HOY)

    uso.anotar(prendido, Uso(entrada=1200, salida=80, cache_escritura=3000, cache_lectura=0), HOY)
    uso.anotar(prendido, Uso(entrada=300, salida=20, cache_escritura=0, cache_lectura=3200), HOY)

    fila = UsoAsistente.objects.get(taller=prendido, fecha=HOY)
    assert (fila.tokens_entrada, fila.tokens_salida) == (1500, 100)
    assert (fila.tokens_cache_escritura, fila.tokens_cache_lectura) == (3000, 3200)
    assert fila.preguntas == 1  # anotar no cuenta preguntas


def test_anotar_sin_reserva_crea_el_dia(prendido):
    uso.anotar(prendido, Uso(entrada=10), HOY)

    fila = UsoAsistente.objects.get(taller=prendido, fecha=HOY)
    assert (fila.preguntas, fila.tokens_entrada) == (0, 10)


def test_anotar_sin_tokens_no_escribe(prendido):
    uso.anotar(prendido, Uso(), HOY)

    assert not UsoAsistente.objects.exists()


def test_costo_usd_con_un_caso_hecho_a_mano():
    # 1.000.000 × 4 + 100.000 × 20 + 200.000 × 5 + 1.000.000 × 0,20, todo por millón:
    # 4 + 2 + 1 + 0,20 = 7,20 dólares.
    costo = uso.costo_usd(
        Uso(entrada=1_000_000, salida=100_000, cache_escritura=200_000, cache_lectura=1_000_000)
    )

    assert costo == Decimal("7.20")
    assert isinstance(costo, Decimal)
    # Una pregunta corta: 1200 de entrada y 80 de salida = 0,0048 + 0,0016 = 0,0064.
    assert uso.costo_usd(Uso(entrada=1200, salida=80)) == Decimal("0.0064")


def test_el_uso_de_un_taller_no_afecta_al_otro(prendido):
    otro = fabricas.crear_taller(asistente_limite_mes=600, asistente_limite_dia=40)
    fabricas.crear_uso(otro, fecha=HOY, preguntas=40)
    fabricas.crear_uso(otro, fecha=date(2026, 11, 1), preguntas=500)

    assert uso.cupo(prendido, HOY).usadas_mes == 0
    assert uso.reservar(prendido, HOY) is True
    uso.anotar(prendido, Uso(entrada=5), HOY)
    uso.devolver(prendido, HOY)

    assert uso.reservar(otro, HOY) is False
    assert _preguntas(otro) == 40
    assert UsoAsistente.objects.get(taller=otro, fecha=HOY).tokens_entrada == 0


# --- Lo que se ve: el aviso del panel y la tarjeta de Mi taller -----------------------------


def test_el_aviso_ambar_sale_solo_con_pocas():
    pocas = uso.Cupo(usadas_hoy=36, limite_dia=40, usadas_mes=100, limite_mes=600, hoy=HOY)
    bien = uso.Cupo(usadas_hoy=6, limite_dia=40, usadas_mes=100, limite_mes=600, hoy=HOY)
    sin = uso.Cupo(usadas_hoy=40, limite_dia=40, usadas_mes=100, limite_mes=600, hoy=HOY)

    con_aviso = render_to_string("asistente/_uso_aviso.html", {"cupo": pocas})
    assert '<div id="asistente-uso">' in con_aviso
    assert '<p class="aviso asistente__uso">Te quedan 4 preguntas por hoy. Mañana vuelves a tener 40.</p>' in con_aviso
    for cupo in (bien, sin):
        html = render_to_string("asistente/_uso_aviso.html", {"cupo": cupo})
        assert '<div id="asistente-uso"></div>' in html
        assert "aviso" not in html.replace('id="asistente-uso"', "")


def test_el_aviso_se_puede_mandar_aparte_con_hx_swap_oob():
    cupo = uso.Cupo(usadas_hoy=6, limite_dia=40, usadas_mes=100, limite_mes=600, hoy=HOY)

    html = render_to_string("asistente/_uso_aviso.html", {"cupo": cupo, "oob": True})

    assert '<div id="asistente-uso" hx-swap-oob="true"></div>' in html


def test_la_tarjeta_de_mi_taller_muestra_n_de_600_y_el_riel():
    cupo = uso.Cupo(usadas_hoy=6, limite_dia=40, usadas_mes=128, limite_mes=600, hoy=HOY)

    html = render_to_string("asistente/_uso_mi_taller.html", {"uso_asistente": cupo})

    assert "Preguntas este mes" in html
    assert '<span class="tarjeta__aparte">128 de 600</span>' in html
    assert '<span class="progreso__relleno" style="width: 21%"></span>' in html
    assert 'aria-label="Llevas 128 de 600 preguntas este mes"' in html
    assert "Hoy llevas 6 de 40. El conteo del mes vuelve a cero el 1 de diciembre." in html


@pytest.fixture
def asistente_prendido(settings, taller):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    taller.asistente_limite_mes = 600
    taller.asistente_limite_dia = 40
    taller.save()
    return taller


def test_mi_taller_con_el_asistente_prendido_muestra_el_bloque(sesion_duena, asistente_prendido):
    fabricas.crear_uso(asistente_prendido, preguntas=6)

    respuesta = sesion_duena.get("/mi-taller/")

    html = respuesta.text
    assert respuesta.status_code == 200
    assert "<h2>Asistente</h2>" in html
    assert '<span class="tarjeta__aparte">6 de 600</span>' in html
    assert 'class="progreso"' in html and 'class="progreso__relleno" style="width: 1%"' in html
    assert "Hoy llevas 6 de 40." in html


def test_mi_taller_sin_el_asistente_no_muestra_el_bloque(sesion_duena, settings):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"  # con clave, pero el taller lo tiene en 0

    html = sesion_duena.get("/mi-taller/").text

    assert "Preguntas este mes" not in html
