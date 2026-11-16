"""El asistente de punta a punta (T35): la vista, el ciclo, las herramientas y las tarjetas de
verdad, juntos, sobre los datos de ejemplo. Solo Claude es de mentira (asistente.falso): sigue
un guion, como lo haría el de verdad, y nunca se sale a internet.

Casos de docs/11-plan-tanda-7.md (T35): "¿quién me debe?" con la tarjeta igual a Hoy, "este
pedido" desde la pantalla del pedido, un mensaje de cobro y una cotización.
"""

import json
import re

import pytest
from django.utils import timezone

from asistente import falso
from asistente.models import UsoAsistente
from cuentas.models import Usuario
from pedidos import ejemplos
from pedidos.models import Pedido
from tests import fabricas

HTMX = {"HTTP_HX_REQUEST": "true"}
# Solo existe en la base temporal de esta prueba.
NUMERO_DE_PRUEBA = "3001234567"


@pytest.fixture
def taller(db, settings):
    taller = ejemplos.cargar(hoy=timezone.localdate(), con_fotos=False)
    taller.asistente_limite_mes, taller.asistente_limite_dia = 600, 40
    taller.save()
    return taller


@pytest.fixture
def navegador(client, taller):
    duena = Usuario.objects.filter(taller=taller, rol=Usuario.Rol.DUENA).order_by("pk").first()
    client.force_login(duena)
    return client


def preguntar(navegador, pregunta, pagina="/"):
    respuesta = navegador.post(
        "/asistente/preguntar/", {"pregunta": pregunta, "pagina": pagina}, **HTMX
    )
    assert respuesta.status_code == 200
    # La plata del borrador lleva un espacio que no se parte entre el $ y la cifra.
    return respuesta.content.decode().replace(" ", " ")


def resultados_de_herramientas(claude, llamada=1):
    """Los tool_result que recibió Claude en esa llamada, ya leídos como JSON."""
    ultimo = claude.llamadas[llamada]["mensajes"][-1]
    return [json.loads(b["content"]) for b in ultimo["content"] if b["type"] == "tool_result"]


def todo_lo_que_vio_claude(claude):
    return json.dumps([c["mensajes"] for c in claude.llamadas], ensure_ascii=False)


def sin_espacios(html):
    return re.sub(r"\s+", " ", html)


def test_quien_me_debe_trae_la_misma_tarjeta_que_hoy(navegador, taller, monkeypatch, settings):
    claude = falso.instalar(monkeypatch, settings, [
        falso.usa(("quien_debe", {}, "toolu_1")),
        falso.texto("Te deben $ 5.790.000 entre 4 clientes. La más urgente es Ferretería La "
                    "Esquina: su pedido va atrasado."),
    ])

    html = sin_espacios(preguntar(navegador, "¿Quién me debe plata?"))
    hoy = sin_espacios(navegador.get("/").content.decode())

    # Lo que leyó Claude salió de la herramienta de verdad.
    datos, = resultados_de_herramientas(claude)
    assert datos["por_cobrar"] == 5_790_000
    # La tarjeta del asistente y "Quién te debe" de Hoy dicen lo mismo.
    for cliente, saldo in [("Colegio Nuevo Amanecer", "$ 3.300.000"),
                           ("Restaurante El Fogón Costeño", "$ 1.260.000"),
                           ("Grupo de danza Tambores del Río", "$ 750.000"),
                           ("Ferretería La Esquina", "$ 480.000")]:
        assert cliente in html and saldo in html
        assert cliente in hoy and saldo in hoy
    assert "Vencida" in html
    assert "Revisé" in html and "Te deben $ 5.790.000" in html
    # Contó una pregunta y guardó la conversación.
    assert UsoAsistente.objects.get(taller=taller).preguntas == 1
    assert len(navegador.session["asistente"]["turnos"]) == 1
    # Cada llamada esperó como mucho lo que le quedaba a la pregunta.
    assert all(0 < c["plazo"] <= 50 for c in claude.llamadas)


def test_este_pedido_es_el_que_esta_en_pantalla(navegador, taller, monkeypatch, settings):
    pedido = Pedido.objects.get(taller=taller, cliente__nombre="Ferretería La Esquina")
    claude = falso.instalar(monkeypatch, settings, [
        falso.usa(("ver_pedido", {"pedido_id": None}, "toolu_1")),
        falso.texto("Este pedido debe $ 480.000."),
    ])

    html = preguntar(navegador, "¿Cuánto debe este pedido?", pagina=f"/pedidos/{pedido.pk}/")

    # La pantalla le llegó a Claude en el mensaje de sistema, y la herramienta usó ese pedido.
    sistema = [m for m in claude.llamadas[0]["mensajes"] if m["role"] == "system"]
    assert "Ferretería La Esquina" in sistema[-1]["content"]
    datos, = resultados_de_herramientas(claude)
    assert datos["pedido"]["id"] == pedido.pk
    assert datos["pagos"]["saldo"] == 480_000
    assert "8 overoles con logo estampado" in html


def test_un_pedido_de_otro_taller_en_pantalla_no_le_llega_a_claude(
    navegador, taller, monkeypatch, settings
):
    otro = fabricas.crear_taller(nombre="Otro taller")
    ajeno = fabricas.crear_pedido(otro, cliente=fabricas.crear_cliente(otro, "Cliente del otro"))
    claude = falso.instalar(monkeypatch, settings, [
        falso.usa(("ver_pedido", {"pedido_id": ajeno.pk}, "toolu_1")),
        falso.texto("No encontré ese pedido."),
    ])

    preguntar(navegador, "¿Cuánto debe este pedido?", pagina=f"/pedidos/{ajeno.pk}/")

    ultimo = claude.llamadas[1]["mensajes"][-1]["content"][0]
    assert ultimo["is_error"] is True and "No encontré ese pedido." in ultimo["content"]
    vio = todo_lo_que_vio_claude(claude)
    assert "Otro taller" not in vio and "Cliente del otro" not in vio


def test_el_mensaje_de_cobro_trae_whatsapp_pero_el_numero_no_va_a_claude(
    navegador, taller, monkeypatch, settings
):
    pedido = Pedido.objects.get(taller=taller, cliente__nombre="Ferretería La Esquina")
    pedido.cliente.whatsapp = NUMERO_DE_PRUEBA
    pedido.cliente.save()
    claude = falso.instalar(monkeypatch, settings, [
        falso.usa(("preparar_mensaje", {
            "pedido_id": pedido.pk, "cliente_id": None, "motivo": "cobro",
            "texto": "Hola, te escribimos del taller. Tu pedido tiene un saldo de $ 480.000.",
        }, "toolu_1")),
        falso.texto("Te dejé el mensaje listo para que lo revises."),
    ])

    html = preguntar(navegador, "Escríbele a la Ferretería que me debe")

    assert "https://wa.me/57" + NUMERO_DE_PRUEBA in html
    assert "Abrir en WhatsApp" in html and "Copiar" in html
    assert NUMERO_DE_PRUEBA not in todo_lo_que_vio_claude(claude)
    assert pedido.token_tallas not in todo_lo_que_vio_claude(claude)


def test_la_cotizacion_da_lo_mismo_que_el_cotizador(navegador, taller, monkeypatch, settings):
    claude = falso.instalar(monkeypatch, settings, [
        falso.usa(("cotizar", {"prenda": "Vestido de comparsa", "cantidad": 15,
                               "ganancia_pct": None, "abono_pct": None}, "toolu_1")),
        falso.texto("Con 30 % de ganancia te queda así."),
    ])

    html = preguntar(navegador, "¿Cuánto cobro por 15 vestidos de comparsa?")

    datos, = resultados_de_herramientas(claude)
    assert datos["total"] == 2_730_000
    assert "$ 2.730.000" in html and "$ 182.000" in html
    enlace = re.search(r'href="(/cotizador/[^"]+)"', html).group(1).replace("&amp;", "&")
    assert "$ 2.730.000" in navegador.get(enlace).content.decode()


def test_si_claude_no_responde_no_se_gasta_la_pregunta(navegador, taller, monkeypatch, settings):
    import anthropic
    import httpx2

    falso.instalar(monkeypatch, settings, [
        anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com")),
    ])

    html = preguntar(navegador, "¿Quién me debe plata?")

    assert "No pude contestar ahora." in html
    assert not UsoAsistente.objects.filter(taller=taller, preguntas__gt=0).exists()


# --- Tanda 8: el agente propone y ella guarda con un toque ------------------------------------

from datetime import timedelta  # noqa: E402
from decimal import Decimal  # noqa: E402

from django.core.management import call_command  # noqa: E402

from pedidos.models import Abono, Cliente  # noqa: E402
from telas.models import TelaPedido  # noqa: E402


def firma_de(html):
    firmas = re.findall(r'name="firma" value="([^"]+)"', html)
    assert len(firmas) == 1
    return firmas[0]


def test_el_pedido_de_las_10_30_de_punta_a_punta(navegador, taller, monkeypatch, settings):
    colegio = Cliente.objects.get(taller=taller, nombre="Colegio Nuevo Amanecer")
    entrega = (timezone.localdate() + timedelta(days=30)).isoformat()
    claude = falso.instalar(monkeypatch, settings, [
        falso.usa(("buscar_clientes", {"texto": "Colegio Nuevo Amanecer", "tipo": None}, "t1"),
                  ("telas", {"solo_bajas": False}, "t2")),
        falso.usa(("proponer_pedido", {
            "cliente": "Colegio Nuevo Amanecer", "cliente_id": colegio.pk, "tipo_cliente": "",
            "detalle": "30 uniformes de diario", "cantidad": 30, "tallaje": "nino",
            "fecha_entrega": entrega, "prenda": "Uniforme de diario", "total": 0,
            "abono": 500_000, "tela": "Dril azul", "metros": "",
        }, "t3")),
        falso.texto("Te dejé el pedido listo. Revísalo y toca Guardar."),
        falso.texto("Ya quedó guardado."),
    ])
    pedidos_antes = Pedido.objects.count()

    html = preguntar(navegador, "Vino la profe del Colegio Nuevo Amanecer, quiere 30 uniformes "
                                "de diario y dejó 500 mil")

    # La tarjeta trae las cifras de la aplicación, y nada se guardó todavía.
    assert "Para guardar" in html and "Sin guardar" in html
    assert "$ 2.310.000" in html and "$ 1.810.000" in html
    assert "Te faltan 48 m de dril azul." in html
    assert Pedido.objects.count() == pedidos_antes
    # La firma nunca le llegó a Claude.
    firma = firma_de(html)
    assert firma not in todo_lo_que_vio_claude(claude)

    guardado = navegador.post("/asistente/confirmar/", {"firma": firma}, **HTMX).content.decode()

    assert "Listo" in guardado
    pedido = Pedido.objects.get(taller=taller, detalle="30 uniformes de diario")
    assert (pedido.cliente, pedido.total, pedido.estado, pedido.por_asistente) == (
        colegio, 2_310_000, "confirmado", True)
    assert Abono.objects.get(pedido=pedido).valor == 500_000
    assert TelaPedido.objects.get(pedido=pedido).metros == Decimal("66.00")
    ficha = navegador.get(f"/pedidos/{pedido.pk}/").content.decode()
    assert "Lo anotó el asistente" in ficha
    assert "Falta tela" in ficha and "Te faltan 48 m de dril azul: tienes 18 m." in ficha

    # En la siguiente pregunta, Claude sabe lo que se guardó.
    preguntar(navegador, "¿Qué quedó?")
    assert f"pedido {pedido.pk}" in claude.llamadas[-1]["mensajes"][-1]["content"]


def test_un_abono_desde_la_pantalla_del_pedido(navegador, taller, monkeypatch, settings):
    tambores = Pedido.objects.get(taller=taller, cliente__nombre="Grupo de danza Tambores del Río")
    falso.instalar(monkeypatch, settings, [
        falso.usa(("proponer_abono", {"pedido_id": 0, "cliente": "", "valor": 300_000,
                                      "fecha": ""}, "t1")),
        falso.texto("Este es el abono. Revísalo y toca Guardar."),
    ])

    html = preguntar(navegador, "Me abonaron 300 mil", pagina=f"/pedidos/{tambores.pk}/")
    assert "Falta $ 450.000" in html

    navegador.post("/asistente/confirmar/", {"firma": firma_de(html)}, **HTMX)

    abono = Abono.objects.get(pedido=tambores, valor=300_000)
    assert abono.por_asistente
    pagos = navegador.get(f"/pedidos/{tambores.pk}/").content.decode()
    assert "$ 450.000" in pagos


def test_el_resumen_de_la_manana_sale_en_hoy(navegador, taller, monkeypatch, settings):
    falso.instalar(monkeypatch, settings, [
        falso.texto("Buenos días. Va atrasado el pedido de 8 overoles de Ferretería La Esquina "
                    "y todavía te debe $ 480.000."),
    ])

    call_command("preparar_resumen")
    html = sin_espacios(navegador.get("/").content.decode())

    assert "Tu resumen de hoy" in html
    assert "todavía te debe" in html
    assert "Ferretería La Esquina" in html and "Vencida" in html
    assert "Telas por acabarse" in html
