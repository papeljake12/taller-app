"""El resumen de la mañana (T43): los puntos del día, el párrafo de Claude, el comando de la
madrugada y la tarjeta "Tu resumen de hoy" arriba de Hoy.

Casos de docs/13-plan-tanda-8.md, "T43 (C)". Claude es siempre el de mentira (asistente.falso):
ninguna prueba sale a internet. Los datos de ejemplo se cargan el día del diseño, como en
pedidos/tests/test_calculos.py, o el día de hoy cuando se abre la pantalla Hoy.
"""

import io
import json
import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import anthropic
import httpx2
import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from asistente import falso, resumen
from asistente.models import ResumenDelDia, UsoAsistente
from cuentas.models import Usuario
from pedidos import calculos, ejemplos, mensajes
from pedidos.models import Cliente, Pedido
from telas.models import Tela
from tests import fabricas

DIA_DEL_DISENO = date(2026, 11, 11)
# Solo existe en la base temporal de estas pruebas.
NUMERO_DE_PRUEBA = "3001234567"
PARRAFO = (
    "Buenos días. Hoy no tienes entregas. Va atrasado el pedido de 8 overoles de Ferretería La "
    "Esquina, que era para el lunes, y todavía te debe $ 480.000. Faltan tallas en dos pedidos y "
    "se están acabando la popelina y el piqué."
)


def _prender(taller):
    taller.asistente_limite_mes, taller.asistente_limite_dia = 600, 40
    taller.save()
    return taller


def _pedido(taller, cliente):
    return Pedido.objects.get(taller=taller, cliente__nombre=cliente)


@pytest.fixture
def ejemplo(db):
    """Los ejemplos de diseno/, el día del diseño, con el asistente prendido."""
    return _prender(ejemplos.cargar(hoy=DIA_DEL_DISENO, con_fotos=False))


@pytest.fixture
def ejemplo_hoy(db, settings):
    """Los ejemplos contados desde hoy, con clave y el asistente prendido: para abrir Hoy."""
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    return _prender(ejemplos.cargar(hoy=timezone.localdate(), con_fotos=False))


def _duena(taller):
    return Usuario.objects.filter(taller=taller, rol=Usuario.Rol.DUENA).order_by("pk").first()


def _abrir_hoy(client, persona):
    client.force_login(persona)
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    return respuesta.content.decode()


def _filas(puntos):
    return [(p.tipo, p.titulo, p.detalle) for p in puntos]


# --- Los puntos del día -------------------------------------------------------------------------


def test_los_puntos_con_los_ejemplos_son_los_de_la_maqueta(ejemplo):
    puntos = resumen.puntos_del_dia(ejemplo, DIA_DEL_DISENO)

    assert _filas(puntos) == [
        ("atraso", "Ferretería La Esquina",
         "Era para el lunes 9 de noviembre. Va en confección. Debe $ 480.000."),
        ("cobro", "Ferretería La Esquina", "Debe $ 480.000. Su último abono fue hace 20 días."),
        ("tallas", "Colegio Nuevo Amanecer", "Faltan 31 de 40 tallas."),
        ("tallas", "Restaurante El Fogón Costeño", "Faltan 4 de 18 tallas, y ya está en corte."),
        ("tela", "Telas por acabarse",
         "Popelina blanca (quedan 4 m) y piqué blanco (quedan 6 m)."),
    ]
    cobro, tela = puntos[1], puntos[4]
    assert cobro.etiqueta == {"texto": "Vencida", "color": "rojo", "circulo": ""}
    assert cobro.cifras == (480_000,)
    assert tela.etiqueta == {"texto": "2 telas", "color": "ambar", "circulo": "vacio"}
    assert tela.boton.texto == "Ver telas" and tela.boton.url == "/telas/"
    assert cobro.texto == (
        "Ferretería La Esquina · Debe $ 480.000. Su último abono fue hace 20 días."
    )


def test_los_cobros_son_las_deudas_vencidas_de_quien_te_debe(ejemplo):
    vencidas = [
        (d.cliente.nombre, d.saldo)
        for d in calculos.quien_te_debe(ejemplo, DIA_DEL_DISENO)
        if d.atrasado
    ]
    cobros = [
        (p.titulo, p.cifras[0])
        for p in resumen.puntos_del_dia(ejemplo, DIA_DEL_DISENO)
        if p.tipo == "cobro"
    ]

    assert cobros == vencidas == [("Ferretería La Esquina", 480_000)]
    # Las que no están vencidas (Colegio, Restaurante, Tambores) no se cobran en el resumen.
    assert len(calculos.quien_te_debe(ejemplo, DIA_DEL_DISENO)) == 4


def test_la_tela_que_no_alcanza_coincide_con_el_calculo(ejemplo):
    colegio = _pedido(ejemplo, "Colegio Nuevo Amanecer")  # confirmado: aparta tela
    dril = Tela.objects.get(taller=ejemplo, nombre="Dril azul")
    fabricas.crear_tela_pedido(colegio, dril, metros=Decimal("66"))

    no_alcanzan = calculos.telas_que_no_alcanzan(ejemplo)
    tela = [p for p in resumen.puntos_del_dia(ejemplo, DIA_DEL_DISENO) if p.tipo == "tela"]

    assert [(f.tela.nombre, f.faltan) for f in no_alcanzan] == [("Dril azul", Decimal("48.00"))]
    assert len(tela) == 1
    assert tela[0].detalle == (
        "Dril azul (faltan 48 m), popelina blanca (quedan 4 m) y piqué blanco (quedan 6 m)."
    )
    assert tela[0].etiqueta["texto"] == "3 telas"


def test_una_sola_tela_va_en_singular_y_sin_insignia(taller):
    fabricas.crear_tela(taller, nombre="Lino blanco", metros=3, minimo=5)

    (tela,) = resumen.telas(taller)

    assert (tela.titulo, tela.detalle, tela.etiqueta) == (
        "Tela por acabarse", "Lino blanco (quedan 3 m).", None
    )


def test_una_tela_que_no_alcanza_y_esta_baja_sale_una_vez(taller):
    tela = fabricas.crear_tela(taller, nombre="Lino blanco", metros=3, minimo=5)
    pedido = fabricas.crear_pedido(taller, estado="confirmado")
    fabricas.crear_tela_pedido(pedido, tela, metros=10)

    (punto,) = resumen.telas(taller)

    assert punto.detalle == "Lino blanco (faltan 7 m)."


def test_las_entregas_de_hoy_y_de_manana(ejemplo):
    # Dos días después del diseño, las polleras de Tambores del Río se entregan mañana.
    puntos = resumen.puntos_del_dia(ejemplo, DIA_DEL_DISENO + timedelta(days=2))
    entregas = [p for p in puntos if p.tipo == "entrega"]

    assert _filas(entregas) == [
        ("entrega", "Grupo de danza Tambores del Río",
         "Se entrega mañana. Ya está listo. Debe $ 750.000."),
    ]
    assert entregas[0].pedido == "15 polleras con blusa"
    assert entregas[0].cifras == (750_000,)

    hoy = resumen.puntos_del_dia(ejemplo, DIA_DEL_DISENO + timedelta(days=3))
    assert [p.detalle for p in hoy if p.tipo == "entrega"] == [
        "Se entrega hoy. Ya está listo. Debe $ 750.000."
    ]


def test_tallas_solo_de_pedidos_sin_entregar_con_el_enlace_abierto(taller):
    abierto = fabricas.crear_pedido(taller, estado="confeccion", cantidad=3)
    fabricas.crear_talla(abierto)
    cerrado = fabricas.crear_pedido(taller, estado="confirmado", cantidad=3, tallas_abiertas=False)
    cotizado = fabricas.crear_pedido(taller, estado="cotizado", cantidad=3)
    listo = fabricas.crear_pedido(taller, estado="listo", cantidad=3)
    completo = fabricas.crear_pedido(taller, estado="confirmado", cantidad=1)
    fabricas.crear_talla(completo)

    puntos = resumen.tallas(taller)

    assert [(p.titulo, p.detalle) for p in puntos] == [
        (abierto.cliente.nombre, "Faltan 2 de 3 tallas, y ya está en confección.")
    ]
    nombres = {p.titulo for p in puntos}
    assert not nombres & {cerrado.cliente.nombre, cotizado.cliente.nombre, listo.cliente.nombre}


def test_los_botones_abren_whatsapp_con_los_textos_y_sin_numero_van_al_pedido(ejemplo):
    Cliente.objects.filter(taller=ejemplo, nombre="Ferretería La Esquina").update(
        whatsapp=NUMERO_DE_PRUEBA
    )
    colegio = _pedido(ejemplo, "Colegio Nuevo Amanecer")
    Cliente.objects.filter(pk=colegio.cliente_id).update(whatsapp=NUMERO_DE_PRUEBA)
    ferreteria = _pedido(ejemplo, "Ferretería La Esquina")

    puntos = resumen.puntos_del_dia(ejemplo, DIA_DEL_DISENO, url_base="https://taller.example/")
    por_titulo = {(p.tipo, p.titulo): p.boton for p in puntos}

    cobrar = por_titulo[("cobro", "Ferretería La Esquina")]
    assert cobrar.texto == "Cobrar"
    assert cobrar.url == mensajes.enlace_whatsapp(
        NUMERO_DE_PRUEBA, mensajes.texto_cobro(ferreteria)
    )
    pedir = por_titulo[("tallas", "Colegio Nuevo Amanecer")]
    assert pedir.texto == "Pedir tallas"
    assert pedir.url.startswith("https://wa.me/573001234567?text=")
    assert colegio.token_tallas in pedir.url  # el enlace del formulario va en el mensaje
    # El Fogón no tiene WhatsApp guardado: el botón abre su pedido.
    fogon = _pedido(ejemplo, "Restaurante El Fogón Costeño")
    sin_numero = por_titulo[("tallas", "Restaurante El Fogón Costeño")]
    assert (sin_numero.texto, sin_numero.url) == ("Ver pedido", f"/pedidos/{fogon.pk}/")


def test_el_mensaje_de_pedir_tallas(ejemplo):
    colegio = _pedido(ejemplo, "Colegio Nuevo Amanecer")

    texto = mensajes.texto_pedir_tallas(colegio, "https://taller.example/tallas/abc/")

    assert texto == (
        "Hola, le escribimos de Taller de ejemplo. Para su pedido (40 uniformes de diario) "
        "todavía nos faltan 31 de 40 tallas. Las pueden enviar en este enlace: "
        "https://taller.example/tallas/abc/ ¡Gracias!"
    )


def test_un_taller_nunca_ve_los_puntos_de_otro(ejemplo):
    otro = fabricas.crear_taller("Otro taller")
    cliente = fabricas.crear_cliente(otro, nombre="Cliente Ajeno Secreto")
    fabricas.crear_pedido(otro, cliente=cliente, estado="confeccion",
                          fecha_entrega=DIA_DEL_DISENO - timedelta(days=1), total=700_000)
    fabricas.crear_tela(otro, nombre="Tela ajena", metros=1, minimo=5)

    mios = json.dumps([p.para_claude() for p in resumen.puntos_del_dia(ejemplo, DIA_DEL_DISENO)],
                      ensure_ascii=False)
    ajenos = resumen.puntos_del_dia(otro, DIA_DEL_DISENO)

    assert "Ajeno" not in mios and "ajena" not in mios
    assert {p.titulo for p in ajenos} == {"Cliente Ajeno Secreto", "Tela por acabarse"}
    assert not any("Ferretería" in p.texto or "Popelina" in p.texto for p in ajenos)


# --- El párrafo (escribir) ---------------------------------------------------------------------


def test_escribir_guarda_el_parrafo_y_anota_los_tokens_sin_sumar_preguntas(
    ejemplo, monkeypatch, settings
):
    claude = falso.instalar(monkeypatch, settings, [falso.texto(PARRAFO, entrada=900, salida=120)])

    guardado = resumen.escribir(ejemplo, DIA_DEL_DISENO, claude)

    assert guardado == ResumenDelDia.objects.get(taller=ejemplo, fecha=DIA_DEL_DISENO)
    assert guardado.texto == PARRAFO
    dia = UsoAsistente.objects.get(taller=ejemplo, fecha=DIA_DEL_DISENO)
    assert (dia.tokens_entrada, dia.tokens_salida, dia.preguntas) == (900, 120, 0)


def test_escribir_hace_una_llamada_sin_herramientas_con_sus_instrucciones(
    ejemplo, monkeypatch, settings
):
    claude = falso.instalar(monkeypatch, settings, [falso.texto(PARRAFO)])

    resumen.escribir(ejemplo, DIA_DEL_DISENO, claude)

    (llamada,) = claude.llamadas
    assert llamada["herramientas"] == []
    assert llamada["esfuerzo"] == "medium"
    assert llamada["plazo"] == 45
    assert llamada["sistema"] == [{"type": "text", "text": resumen.INSTRUCCIONES_RESUMEN}]
    assert "sin_herramientas" not in llamada
    (mensaje,) = llamada["mensajes"]
    assert mensaje["role"] == "user"
    texto = mensaje["content"][0]["text"]
    datos = json.loads(texto[texto.index("{"):])
    assert datos["hoy"] == "miércoles, 11 de noviembre de 2026"
    assert [p["tipo"] for p in datos["puntos"]] == ["atraso", "cobro", "tallas", "tallas", "tela"]
    assert datos["puntos"][1] == {
        "tipo": "cobro",
        "titulo": "Ferretería La Esquina",
        "pedido": "8 overoles con logo estampado",
        "detalle": "Debe $ 480.000. Su último abono fue hace 20 días.",
        "cifras": [480_000],
    }


def test_las_instrucciones_piden_un_parrafo_en_texto_plano_y_tuteando():
    instrucciones = resumen.INSTRUCCIONES_RESUMEN
    assert '"Buenos días."' in instrucciones
    assert "tuteando" in instrucciones
    assert "Sin Markdown" in instrucciones and "Sin emojis" in instrucciones
    assert "$ 480.000" in instrucciones


def test_a_claude_no_le_llegan_telefonos_notas_tallas_con_nombre_ni_el_token(
    ejemplo, monkeypatch, settings
):
    Cliente.objects.filter(taller=ejemplo).update(whatsapp=NUMERO_DE_PRUEBA,
                                                  notas="Nota privada: pagan los viernes")
    tokens = list(Pedido.objects.filter(taller=ejemplo).values_list("token_tallas", flat=True))
    claude = falso.instalar(monkeypatch, settings, [falso.texto(PARRAFO)])

    resumen.escribir(ejemplo, DIA_DEL_DISENO, claude)

    enviado = json.dumps(claude.llamadas, ensure_ascii=False)
    assert NUMERO_DE_PRUEBA not in enviado and "wa.me" not in enviado
    assert "Nota privada" not in enviado and "viernes" not in enviado
    assert "Dato de ejemplo" not in enviado
    for nombre in ejemplos.NOMBRES_TALLAS:
        assert nombre not in enviado
    for token in tokens:
        assert token not in enviado
    assert "/tallas/" not in enviado
    # Tampoco el nombre de la encargada.
    for _, costurera in ejemplos.COSTURERAS:
        assert costurera not in enviado


@pytest.mark.parametrize("parrafo", [
    "Buenos días. Ferretería La Esquina te debe $ 500.000.",
    "Buenos días. Entre todos te deben $ 5.790.000.",
    "Buenos días. Te deben 480.001 pesos.",
])
def test_un_parrafo_con_una_cifra_inventada_no_se_guarda(
    ejemplo, monkeypatch, settings, caplog, parrafo
):
    claude = falso.instalar(monkeypatch, settings, [falso.texto(parrafo)])

    with caplog.at_level(logging.WARNING, logger="asistente"):
        assert resumen.escribir(ejemplo, DIA_DEL_DISENO, claude) is None

    assert not ResumenDelDia.objects.filter(taller=ejemplo).exists()
    assert "no están en los puntos" in caplog.text
    assert parrafo not in caplog.text and "Ferretería" not in caplog.text
    # Los tokens se pagaron igual: quedan anotados.
    assert UsoAsistente.objects.get(taller=ejemplo, fecha=DIA_DEL_DISENO).tokens_entrada == 1200


def test_sin_nada_pendiente_no_se_llama_a_claude(taller, monkeypatch, settings):
    claude = falso.instalar(monkeypatch, settings, [])

    assert resumen.escribir(taller, DIA_DEL_DISENO, claude) is None
    assert claude.llamadas == []
    assert not UsoAsistente.objects.filter(taller=taller).exists()


def test_si_la_api_falla_no_se_guarda_y_queda_en_el_registro(
    ejemplo, monkeypatch, settings, caplog
):
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.invalid/"))
    claude = falso.instalar(monkeypatch, settings, [error])

    with caplog.at_level(logging.WARNING, logger="asistente"):
        assert resumen.escribir(ejemplo, DIA_DEL_DISENO, claude) is None

    assert not ResumenDelDia.objects.filter(taller=ejemplo).exists()
    assert "APIConnectionError" in caplog.text


@pytest.mark.parametrize("respuesta", [falso.rechazo(), falso.cortada("Buenos días. Hoy")])
def test_un_rechazo_o_una_respuesta_cortada_no_se_guardan(ejemplo, monkeypatch, settings,
                                                         respuesta):
    claude = falso.instalar(monkeypatch, settings, [respuesta])

    assert resumen.escribir(ejemplo, DIA_DEL_DISENO, claude) is None
    assert not ResumenDelDia.objects.filter(taller=ejemplo).exists()


def test_escribir_reemplaza_el_del_mismo_dia_y_junta_los_renglones(ejemplo, monkeypatch, settings):
    fabricas.crear_resumen(ejemplo, fecha=DIA_DEL_DISENO, texto="Buenos días. El viejo.")
    claude = falso.instalar(
        monkeypatch, settings, [falso.texto("Buenos días.\n\nHoy no entregas.")]
    )

    resumen.escribir(ejemplo, DIA_DEL_DISENO, claude)

    assert list(ResumenDelDia.objects.filter(taller=ejemplo).values_list("texto", flat=True)) == [
        "Buenos días. Hoy no entregas."
    ]


# --- El comando de la madrugada ------------------------------------------------------------------


def _correr(*argumentos):
    salida = io.StringIO()
    call_command("preparar_resumen", *argumentos, stdout=salida)
    return salida.getvalue()


def test_el_comando_prepara_el_resumen_y_no_lo_repite(ejemplo_hoy, monkeypatch, settings):
    claude = falso.instalar(monkeypatch, settings, [falso.texto(PARRAFO)])

    salida = _correr()

    assert '"Taller de ejemplo"' in salida and "listo el resumen de hoy" in salida
    guardado = ResumenDelDia.objects.get(taller=ejemplo_hoy, fecha=timezone.localdate())
    assert guardado.texto == PARRAFO
    assert UsoAsistente.objects.get(taller=ejemplo_hoy).preguntas == 0

    otra_vez = _correr()

    assert "ya tenía el resumen de hoy" in otra_vez
    assert len(claude.llamadas) == 1  # no se pagó dos veces


def test_con_de_nuevo_lo_reemplaza(ejemplo_hoy, monkeypatch, settings):
    fabricas.crear_resumen(ejemplo_hoy, fecha=timezone.localdate(), texto="Buenos días. Viejo.")
    claude = falso.instalar(monkeypatch, settings, [falso.texto(PARRAFO)])

    salida = _correr("--de-nuevo")

    assert "listo el resumen de hoy" in salida
    assert len(claude.llamadas) == 1
    assert ResumenDelDia.objects.get(taller=ejemplo_hoy).texto == PARRAFO


def test_sin_clave_no_llama_y_lo_dice(ejemplo_hoy, settings, monkeypatch):
    settings.ANTHROPIC_API_KEY = ""
    llamadas = []
    monkeypatch.setattr("asistente.resumen.escribir", lambda *a, **k: llamadas.append(a))

    salida = _correr()

    assert "No hay clave de Anthropic" in salida
    assert llamadas == []
    assert not ResumenDelDia.objects.exists()


def test_un_taller_con_el_asistente_apagado_no_recibe_resumen(ejemplo_hoy, monkeypatch, settings):
    apagado = fabricas.crear_taller("Taller apagado", asistente_limite_mes=600,
                                    asistente_limite_dia=0)
    fabricas.crear_pedido(apagado, estado="confeccion",
                          fecha_entrega=timezone.localdate() - timedelta(days=1))
    claude = falso.instalar(monkeypatch, settings, [falso.texto(PARRAFO)])

    salida = _correr()

    assert "Taller apagado" not in salida
    assert len(claude.llamadas) == 1
    assert not ResumenDelDia.objects.filter(taller=apagado).exists()
    assert "no existe o tiene el asistente apagado" in _correr("--taller", str(apagado.pk))


def test_con_taller_solo_prepara_ese(ejemplo_hoy, monkeypatch, settings):
    otro = _prender(fabricas.crear_taller("Otro taller"))
    fabricas.crear_tela(otro, nombre="Lino", metros=1, minimo=5)
    claude = falso.instalar(monkeypatch, settings, [falso.texto("Buenos días. Se acaba el lino.")])

    salida = _correr("--taller", str(otro.pk))

    assert '"Otro taller"' in salida and "Taller de ejemplo" not in salida
    assert len(claude.llamadas) == 1
    assert "Lino" in claude.llamadas[0]["mensajes"][0]["content"][0]["text"]
    assert not ResumenDelDia.objects.filter(taller=ejemplo_hoy).exists()


def test_un_taller_sin_nada_pendiente_no_gasta(db, monkeypatch, settings):
    vacio = _prender(fabricas.crear_taller("Taller tranquilo"))
    claude = falso.instalar(monkeypatch, settings, [])

    salida = _correr()

    assert '"Taller tranquilo"' in salida and "no hay nada pendiente" in salida
    assert claude.llamadas == []
    assert not ResumenDelDia.objects.filter(taller=vacio).exists()


def test_un_parrafo_malo_lo_dice_el_comando(ejemplo_hoy, monkeypatch, settings):
    falso.instalar(monkeypatch, settings, [falso.texto("Buenos días. Te deben $ 1.000.")])

    salida = _correr()

    assert "no se pudo preparar el resumen" in salida
    assert not ResumenDelDia.objects.exists()


# --- La tarjeta en Hoy -------------------------------------------------------------------------


def test_hoy_muestra_la_tarjeta_con_la_esfera_el_parrafo_y_las_filas(client, ejemplo_hoy):
    guardado = fabricas.crear_resumen(ejemplo_hoy, fecha=timezone.localdate(), texto=PARRAFO)
    cinco = timezone.make_aware(datetime.combine(timezone.localdate(), time(5, 0)))
    ResumenDelDia.objects.filter(pk=guardado.pk).update(creado=cinco)

    html = _abrir_hoy(client, _duena(ejemplo_hoy))

    assert '<section class="tarjeta resumen-dia" aria-labelledby="t-resumen">' in html
    assert '<span class="esfera esfera--chica" data-esfera aria-hidden="true">' in html
    assert '<h2 id="t-resumen">Tu resumen de hoy</h2>' in html
    assert ('<span class="tarjeta__aparte"><span><span class="solo-computador">Lo preparé a las '
            '</span>5:00 a. m.</span></span>') in html
    assert 'y todavía te debe <span class="dinero">$ 480.000</span>. Faltan tallas' in html
    tarjeta = html[html.index("resumen-dia"):html.index("</section>", html.index("resumen-dia"))]
    assert tarjeta.count('<div class="fila fila--compacta">') == 4
    assert ('<strong>Ferretería La Esquina</strong><span class="etiqueta etiqueta--rojo">'
            "Vencida</span>") in tarjeta
    assert ('Debe <span class="dinero">$ 480.000</span>. Su último abono fue hace 20 días.'
            in tarjeta)
    assert "Faltan 31 de 40 tallas." in tarjeta
    assert "Faltan 4 de 18 tallas, y ya está en corte." in tarjeta
    assert ('<strong>Telas por acabarse</strong><span class="etiqueta etiqueta--ambar '
            'etiqueta--vacio">2 telas</span>') in tarjeta
    assert "Popelina blanca (quedan 4 m) y piqué blanco (quedan 6 m)." in tarjeta
    assert '<a class="boton" href="/telas/">' in tarjeta and "Ver telas</a>" in tarjeta
    # Las entregas y los atrasos no se repiten como filas: ya tienen sus cartas.
    assert "Era para" not in tarjeta
    # Arriba de la caja grande.
    assert html.index("resumen-dia") < html.index("caja-grande")


def test_los_botones_de_hoy_abren_whatsapp_en_otra_pestana(client, ejemplo_hoy):
    Cliente.objects.filter(taller=ejemplo_hoy, nombre="Ferretería La Esquina").update(
        whatsapp=NUMERO_DE_PRUEBA
    )

    html = _abrir_hoy(client, _duena(ejemplo_hoy))

    assert '<a class="boton" href="https://wa.me/573001234567?text=' in html
    inicio = html.index("https://wa.me/573001234567")
    boton = html[inicio:html.index("</a>", inicio)]
    assert 'target="_blank" rel="noopener"' in boton
    assert "#whatsapp" in boton and boton.endswith("Cobrar")
    # Sin número, "Ver pedido".
    colegio = _pedido(ejemplo_hoy, "Colegio Nuevo Amanecer")
    assert f'<a class="boton" href="/pedidos/{colegio.pk}/">Ver pedido</a>' in html


def test_sin_resumen_guardado_hoy_muestra_solo_las_filas(client, ejemplo_hoy):
    html = _abrir_hoy(client, _duena(ejemplo_hoy))

    assert "Tu resumen de hoy" in html
    assert "resumen-dia__parrafo" not in html
    assert "Lo preparé" not in html
    assert "Faltan 31 de 40 tallas." in html


def test_un_resumen_de_ayer_no_sale(client, ejemplo_hoy):
    ayer = timezone.localdate() - timedelta(days=1)
    fabricas.crear_resumen(ejemplo_hoy, fecha=ayer, texto="Buenos días. El de ayer.")

    html = _abrir_hoy(client, _duena(ejemplo_hoy))

    assert "El de ayer" not in html


def test_sin_nada_pendiente_ni_resumen_la_tarjeta_no_sale(client, settings, db):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    taller = _prender(fabricas.crear_taller())

    html = _abrir_hoy(client, fabricas.crear_usuaria(taller))

    assert "resumen-dia" not in html
    assert "caja-grande--asistente" in html  # el asistente sí está prendido


def test_la_costurera_no_ve_el_resumen(client, ejemplo_hoy):
    fabricas.crear_resumen(ejemplo_hoy, fecha=timezone.localdate(), texto=PARRAFO)
    costurera = _pedido(ejemplo_hoy, "Restaurante El Fogón Costeño").encargada

    html = _abrir_hoy(client, costurera)

    assert "Tu resumen de hoy" not in html
    assert "resumen-dia" not in html


def test_con_el_asistente_apagado_hoy_queda_igual(client, ejemplo_hoy, settings):
    fabricas.crear_resumen(ejemplo_hoy, fecha=timezone.localdate(), texto=PARRAFO)
    duena = _duena(ejemplo_hoy)
    prendido = _abrir_hoy(client, duena)
    assert "Tu resumen de hoy" in prendido

    ejemplo_hoy.asistente_limite_dia = 0
    ejemplo_hoy.save()
    apagado = _abrir_hoy(client, duena)
    settings.ANTHROPIC_API_KEY = ""
    sin_clave = _abrir_hoy(Client(), duena)

    for html in (apagado, sin_clave):
        assert "resumen-dia" not in html
        assert "Buenos días. Hoy no tienes entregas" not in html
        assert 'role="search"' in html  # la caja grande vuelve a ser el buscador


def test_un_taller_nunca_ve_el_resumen_de_otro(client, ejemplo_hoy):
    otro = _prender(fabricas.crear_taller("Otro taller"))
    fabricas.crear_resumen(otro, fecha=timezone.localdate(), texto="Buenos días. Secreto ajeno.")
    cliente = fabricas.crear_cliente(otro, nombre="Cliente Ajeno Secreto")
    fabricas.crear_pedido(otro, cliente=cliente, estado="confeccion", total=900_000,
                          fecha_entrega=timezone.localdate() - timedelta(days=3))
    fabricas.crear_tela(otro, nombre="Tela ajena", metros=1, minimo=5)

    mio = _abrir_hoy(client, _duena(ejemplo_hoy))
    suyo = _abrir_hoy(Client(), fabricas.crear_usuaria(otro))

    assert "Secreto ajeno" not in mio and "Ajeno" not in mio and "Tela ajena" not in mio
    assert "Secreto ajeno" in suyo and "Cliente Ajeno Secreto" in suyo
    assert "Ferretería" not in suyo and "Popelina" not in suyo


def test_el_parrafo_de_claude_sale_escapado(client, ejemplo_hoy):
    fabricas.crear_resumen(ejemplo_hoy, fecha=timezone.localdate(),
                           texto='Buenos días. <script>alert("x")</script> Debes $ 480.000.')

    html = _abrir_hoy(client, _duena(ejemplo_hoy))

    assert '<script>alert("x")</script>' not in html
    assert "&lt;script&gt;" in html


def test_la_hora_en_bogota():
    import zoneinfo

    utc = zoneinfo.ZoneInfo("UTC")
    assert resumen.hora(datetime(2026, 11, 15, 10, 0, tzinfo=utc)) == "5:00 a. m."
    assert resumen.hora(datetime(2026, 11, 15, 17, 30, tzinfo=utc)) == "12:30 p. m."
    assert resumen.hora(datetime(2026, 11, 16, 5, 5, tzinfo=utc)) == "12:05 a. m."


def test_la_plata_se_marca_para_que_no_se_parta():
    assert resumen.partes("Debe $ 480.000. Ya.") == [
        {"texto": "Debe ", "dinero": False},
        {"texto": "$ 480.000", "dinero": True},
        {"texto": ". Ya.", "dinero": False},
    ]


# --- En celular ------------------------------------------------------------------------------

MEDIR = """() => {
  const pagina = document.scrollingElement || document.documentElement;
  const tarjeta = document.querySelector('.resumen-dia');
  return {
    ancho: pagina.scrollWidth,
    ventana: window.innerWidth,
    tarjeta: tarjeta ? tarjeta.getBoundingClientRect().right : null,
  };
}"""


def test_hoy_con_el_resumen_no_se_desborda_en_390(live_server, settings):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright no está instalado (uv sync con el grupo dev).")
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    taller = _prender(ejemplos.cargar(hoy=timezone.localdate(), con_fotos=False))
    fabricas.crear_resumen(taller, fecha=timezone.localdate(), texto=PARRAFO)
    navegador_django = Client()
    navegador_django.force_login(_duena(taller))
    sesion = navegador_django.cookies["sessionid"].value

    manejador = sync_playwright().start()
    try:
        try:
            navegador = manejador.chromium.launch(channel="chrome")
        except Exception as error:  # noqa: BLE001 (sin Chrome no hay prueba)
            pytest.skip(f"No se pudo abrir Chrome: {error}")
        contexto = navegador.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        contexto.add_cookies([{"name": "sessionid", "value": sesion, "url": live_server.url}])
        pagina = contexto.new_page()
        pagina.goto(live_server.url + "/", wait_until="load")
        pagina.evaluate("document.fonts.ready")
        medida = pagina.evaluate(MEDIR)
        contexto.close()
        navegador.close()
    finally:
        manejador.stop()

    assert medida["tarjeta"] is not None, "La tarjeta del resumen no salió en Hoy"
    assert medida["ancho"] <= medida["ventana"], f"Hoy mide {medida['ancho']} px de ancho"
    assert medida["tarjeta"] <= medida["ventana"]
