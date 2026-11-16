"""T31 (carril C): preparar_mensaje, el WhatsApp que deja listo el asistente.

Se llama como la llamaría Claude: por `herramientas.ejecutar(nombre, entrada, ctx)`. Lo que
le llegaría a Claude es el tool_result que arma el ciclo (docs/11-plan-tanda-7.md, 1.4):
`json.dumps(resultado.datos, ensure_ascii=False, sort_keys=True)`. Ahí nunca pueden estar el
número de WhatsApp ni la clave del enlace de tallas.
"""

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pytest
from django.db import connection
from django.template.loader import render_to_string
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from asistente import herramientas
from asistente.contratos import Contexto, ErrorDeHerramienta, Tarjeta
from asistente.herramientas.mensajes import cifras_en_pesos
from cotizador.models import PrendaGuardada
from pedidos import mensajes
from pedidos.models import Abono, Cliente, Material, Pedido, Talla
from tests import fabricas

# Un número inventado, solo para las pruebas.
NUMERO = "300 555 0123"
DIGITOS = "3005550123"

PLANTILLAS = Path(__file__).resolve().parent.parent / "templates" / "asistente" / "tarjetas"


def contexto(taller, pedido_actual=None):
    return Contexto(
        taller=taller,
        usuaria=fabricas._duena_de(taller),
        hoy=date(2026, 11, 14),
        pedido_actual=pedido_actual,
        url_base="http://testserver/",
    )


def entrada(**cambios):
    return {"pedido_id": None, "cliente_id": None, "motivo": "otro",
            "texto": "Hola, le escribimos del taller.", **cambios}


def preparar(ctx, **cambios):
    return herramientas.ejecutar("preparar_mensaje", entrada(**cambios), ctx)


def lo_que_lee_claude(resultado):
    """El contenido del tool_result que el ciclo le mandaría a Claude."""
    return json.dumps(resultado.datos, ensure_ascii=False, sort_keys=True)


def dibujar(tarjeta):
    return render_to_string(f"asistente/tarjetas/{tarjeta.tipo}.html", {"tarjeta": tarjeta})


@pytest.fixture
def pedido(taller):
    """Total 1.000.000, abonado 520.000 y saldo 480.000."""
    cliente = fabricas.crear_cliente(taller, nombre="Ferretería de prueba", whatsapp=NUMERO)
    pedido = fabricas.crear_pedido(
        taller, cliente=cliente, detalle="8 overoles", cantidad=8, total=1_000_000,
        estado=Pedido.Estado.CONFECCION,
    )
    fabricas.crear_abono(pedido, valor=500_000)
    fabricas.crear_abono(pedido, valor=20_000)
    return pedido


# --- El número va solo en la tarjeta --------------------------------------------------------


def test_el_numero_no_le_llega_a_claude_y_la_tarjeta_lleva_el_mismo_wa_me(taller, pedido):
    texto = "Hola, le recordamos el saldo de su pedido: $ 480.000. ¡Gracias!"
    resultado = preparar(contexto(taller), pedido_id=pedido.pk, motivo="cobro", texto=texto)

    assert resultado.datos == {"listo": True, "tiene_whatsapp": True}
    leido = lo_que_lee_claude(resultado)
    assert DIGITOS not in leido and NUMERO not in leido and "wa.me" not in leido
    assert resultado.tarjeta.tipo == "mensaje"
    assert resultado.tarjeta.titulo == "Para Ferretería de prueba"
    assert resultado.tarjeta.datos["enlace_whatsapp"] == mensajes.enlace_whatsapp(NUMERO, texto)
    assert resultado.tarjeta.datos["enlace_whatsapp"].startswith("https://wa.me/57" + DIGITOS)
    assert resultado.tarjeta.datos["texto"] == texto


def test_la_tarjeta_se_puede_guardar_en_la_sesion(taller, pedido):
    resultado = preparar(contexto(taller), pedido_id=pedido.pk)
    datos = resultado.tarjeta.datos

    assert json.loads(json.dumps(datos)) == datos
    assert set(datos) == {"cliente", "motivo", "texto", "enlace_whatsapp"}


def test_la_tarjeta_trae_copiar_y_abrir_en_whatsapp(taller, pedido):
    resultado = preparar(contexto(taller), pedido_id=pedido.pk)
    html = dibujar(resultado.tarjeta)

    assert 'class="tarjeta mensaje__tarjeta"' in html
    assert 'class="mensaje__para"' in html and "Para Ferretería de prueba" in html
    assert 'class="mensaje__borrador">Hola, le escribimos del taller.</p>' in html
    assert 'data-copiar="Hola, le escribimos del taller."' in html
    assert "Abrir en WhatsApp" in html
    assert 'target="_blank" rel="noopener"' in html
    assert 'class="boton boton--principal" href="https://wa.me/57' + DIGITOS in html


@pytest.mark.parametrize("numero", ["", "123", "no tiene"])
def test_sin_numero_que_sirva_el_enlace_queda_vacio_y_solo_se_copia(taller, numero):
    cliente = fabricas.crear_cliente(taller, whatsapp=numero)
    pedido = fabricas.crear_pedido(taller, cliente=cliente)

    resultado = preparar(contexto(taller), pedido_id=pedido.pk)
    html = dibujar(resultado.tarjeta)

    assert resultado.datos == {"listo": True, "tiene_whatsapp": False}
    assert resultado.tarjeta.datos["enlace_whatsapp"] == ""
    assert "data-copiar=" in html and "Copiar" in html
    assert "Abrir en WhatsApp" not in html and "wa.me" not in html


# --- Las cifras -----------------------------------------------------------------------------


@pytest.mark.parametrize("cifra", [
    "$ 480.000", "$480000", "$480.000", "$ 1.000.000", "$1,000,000", "520.000 pesos",
    "$ 520000",
])
def test_las_cifras_del_pedido_se_aceptan_con_o_sin_puntos(taller, pedido, cifra):
    texto = f"Hola, le escribimos del taller. Su pedido va por {cifra}."
    resultado = preparar(contexto(taller), pedido_id=pedido.pk, motivo="cobro", texto=texto)

    assert resultado.datos["listo"] is True


@pytest.mark.parametrize("cifra", ["$ 450.000", "$480001", "$ 48.000", "750.000 pesos"])
def test_una_cifra_que_no_es_del_pedido_da_error_con_las_cifras_correctas(taller, pedido, cifra):
    with pytest.raises(ErrorDeHerramienta) as error:
        preparar(contexto(taller), pedido_id=pedido.pk, motivo="cobro",
                 texto=f"Hola. Su saldo es {cifra}. ¡Gracias!")

    texto = str(error.value)
    assert "el saldo es 480000" in texto
    assert "el total es 1000000" in texto.lower()
    assert "lo abonado es 520000" in texto
    assert "corrige la cifra" in texto


def test_cada_cifra_del_texto_se_revisa(taller, pedido):
    with pytest.raises(ErrorDeHerramienta, match="La cifra 5000 no es del pedido"):
        preparar(contexto(taller), pedido_id=pedido.pk, motivo="cobro",
                 texto="Debe $ 480.000 y el envío cuesta $ 5.000.")


def test_cifras_en_pesos_lee_las_formas_de_escribir_plata():
    assert cifras_en_pesos("$ 1.090.000, $480000. y 520.000 pesos; 3 polos") == [
        1_090_000, 480_000, 520_000,
    ]
    assert cifras_en_pesos("Sin plata: 15 polleras para el 20 de diciembre.") == []


def test_cobrar_un_pedido_ya_pagado_da_error(taller):
    pedido = fabricas.crear_pedido(taller, total=300_000)
    fabricas.crear_abono(pedido, valor=300_000)

    with pytest.raises(ErrorDeHerramienta, match="ya está pagado"):
        preparar(contexto(taller), pedido_id=pedido.pk, motivo="cobro")


# --- Solo un cliente, sin pedido ------------------------------------------------------------


def test_sin_pedido_la_unica_cifra_es_lo_que_debe_el_cliente(taller, pedido):
    # El mismo cliente tiene otro pedido confirmado con saldo 200.000: debe 680.000 en total.
    otro = fabricas.crear_pedido(taller, cliente=pedido.cliente, total=200_000,
                                 estado=Pedido.Estado.CONFIRMADO)
    # Un cotizado no se debe todavía (igual que en la pantalla Clientes).
    fabricas.crear_pedido(taller, cliente=pedido.cliente, total=900_000)
    ctx = contexto(taller)

    bien = preparar(ctx, cliente_id=pedido.cliente_id, motivo="cobro",
                    texto="Hola, en total nos debe $ 680.000. ¡Gracias!")
    assert bien.datos == {"listo": True, "tiene_whatsapp": True}
    assert bien.revisado == "Revisé los datos de Ferretería de prueba"
    assert bien.enlace.url == reverse("pedidos:clientes") + "?q=Ferreter%C3%ADa+de+prueba"

    with pytest.raises(ErrorDeHerramienta, match="lo que debe en total: 680000"):
        preparar(ctx, cliente_id=otro.cliente_id, motivo="cobro",
                 texto="Hola, nos debe $ 480.000.")


def test_sin_pedido_y_sin_deuda_no_van_cifras_ni_cobros(taller):
    cliente = fabricas.crear_cliente(taller, whatsapp=NUMERO)
    ctx = contexto(taller)

    assert preparar(ctx, cliente_id=cliente.pk, texto="Hola, ¿le cotizamos?").datos["listo"]
    with pytest.raises(ErrorDeHerramienta, match="no debe nada"):
        preparar(ctx, cliente_id=cliente.pk, texto="Le ofrecemos polos a $ 50.000.")
    with pytest.raises(ErrorDeHerramienta, match="no debe nada"):
        preparar(ctx, cliente_id=cliente.pk, motivo="cobro", texto="Hola, ¿nos paga?")


def test_avisar_que_esta_listo_pide_el_pedido(taller):
    cliente = fabricas.crear_cliente(taller)
    with pytest.raises(ErrorDeHerramienta, match="de qué pedido"):
        preparar(contexto(taller), cliente_id=cliente.pk, motivo="listo")


# --- El enlace de tallas --------------------------------------------------------------------


def test_el_marcador_se_cambia_por_la_direccion_publica_que_no_llega_a_claude(taller, pedido):
    texto = "Hola. Para las tallas, cada persona llena este formulario: [ENLACE] ¡Gracias!"
    resultado = preparar(contexto(taller), pedido_id=pedido.pk, motivo="tallas", texto=texto)

    direccion = "http://testserver" + reverse("pedidos:publico_tallas",
                                              args=[pedido.token_tallas])
    final = texto.replace("[ENLACE]", direccion)
    assert resultado.tarjeta.datos["texto"] == final
    assert "[ENLACE]" not in resultado.tarjeta.datos["texto"]
    assert resultado.tarjeta.datos["enlace_whatsapp"] == mensajes.enlace_whatsapp(NUMERO, final)
    leido = lo_que_lee_claude(resultado)
    assert pedido.token_tallas not in leido and "/tallas/" not in leido
    assert pedido.token_tallas in dibujar(resultado.tarjeta)


def test_pedir_tallas_sin_marcador_da_error(taller, pedido):
    with pytest.raises(ErrorDeHerramienta, match=r"\[ENLACE\]"):
        preparar(contexto(taller), pedido_id=pedido.pk, motivo="tallas",
                 texto="Hola, mándenos las tallas.")


def test_pedir_tallas_con_el_enlace_cerrado_da_error(taller, pedido):
    Pedido.objects.filter(pk=pedido.pk).update(tallas_abiertas=False)

    with pytest.raises(ErrorDeHerramienta, match="cerrado"):
        preparar(contexto(taller), pedido_id=pedido.pk, motivo="tallas",
                 texto="Hola, llenen este formulario: [ENLACE]")


def test_el_marcador_solo_sirve_para_pedir_tallas(taller, pedido):
    with pytest.raises(ErrorDeHerramienta, match="solo sirve para pedir tallas"):
        preparar(contexto(taller), pedido_id=pedido.pk, motivo="listo",
                 texto="Ya está listo. [ENLACE]")


def test_pedir_tallas_sin_pedido_da_error(taller):
    cliente = fabricas.crear_cliente(taller)
    with pytest.raises(ErrorDeHerramienta, match="de qué pedido"):
        preparar(contexto(taller), cliente_id=cliente.pk, motivo="tallas", texto="[ENLACE]")


# --- De quién es ----------------------------------------------------------------------------


def test_un_pedido_de_otro_taller_es_igual_que_uno_que_no_existe(taller):
    otro_taller = fabricas.crear_taller()
    ajeno = fabricas.crear_pedido(otro_taller)
    ctx = contexto(taller)

    with pytest.raises(ErrorDeHerramienta) as de_otro:
        preparar(ctx, pedido_id=ajeno.pk)
    with pytest.raises(ErrorDeHerramienta) as inexistente:
        preparar(ctx, pedido_id=ajeno.pk + 1000)

    assert str(de_otro.value) == str(inexistente.value) == "No encontré ese pedido."


def test_un_cliente_de_otro_taller_es_igual_que_uno_que_no_existe(taller):
    otro_taller = fabricas.crear_taller()
    ajeno = fabricas.crear_cliente(otro_taller, whatsapp=NUMERO)
    ctx = contexto(taller)

    with pytest.raises(ErrorDeHerramienta) as de_otro:
        preparar(ctx, cliente_id=ajeno.pk)
    with pytest.raises(ErrorDeHerramienta) as inexistente:
        preparar(ctx, cliente_id=ajeno.pk + 1000)

    assert str(de_otro.value) == str(inexistente.value) == "No encontré ese cliente."


def test_pedido_y_cliente_tienen_que_ir_juntos(taller, pedido):
    otro = fabricas.crear_cliente(taller)
    with pytest.raises(ErrorDeHerramienta, match="otro cliente"):
        preparar(contexto(taller), pedido_id=pedido.pk, cliente_id=otro.pk)

    resultado = preparar(contexto(taller), pedido_id=pedido.pk, cliente_id=pedido.cliente_id)
    assert resultado.tarjeta.datos["cliente"] == "Ferretería de prueba"


def test_sin_ids_usa_el_pedido_de_la_pantalla(taller, pedido):
    resultado = preparar(contexto(taller, pedido_actual=pedido), motivo="cobro",
                         texto="Hola, el saldo es $ 480.000.")

    assert resultado.revisado == "Revisé el pedido de 8 overoles"
    assert resultado.enlace.texto == "Ver el pedido"
    assert resultado.enlace.url == reverse("pedidos:detalle", args=[pedido.pk])
    assert resultado.tarjeta.titulo == "Para Ferretería de prueba"


def test_sin_ids_ni_pedido_en_pantalla_pregunta_cual(taller):
    with pytest.raises(ErrorDeHerramienta, match="para qué pedido o cliente"):
        preparar(contexto(taller))


def test_el_texto_largo_o_vacio_no_pasa(taller, pedido):
    with pytest.raises(ErrorDeHerramienta, match="entre 1 y 700"):
        preparar(contexto(taller), pedido_id=pedido.pk, texto="a" * 701)
    with pytest.raises(ErrorDeHerramienta, match="entre 1 y 700"):
        preparar(contexto(taller), pedido_id=pedido.pk, texto="")
    with pytest.raises(ErrorDeHerramienta, match="Escribe el texto"):
        preparar(contexto(taller), pedido_id=pedido.pk, texto="   ")


# --- Escapado -------------------------------------------------------------------------------


def test_el_texto_de_claude_sale_escapado_en_la_tarjeta(taller, pedido):
    texto = 'Hola <b>x</b><script>alert("hola")</script>\nSegunda línea'
    resultado = preparar(contexto(taller), pedido_id=pedido.pk, texto=texto)

    # Igual con la tarjeta recién hecha y con la que vuelve de la sesión (un diccionario).
    de_la_sesion = json.loads(json.dumps(asdict(resultado.tarjeta)))
    for tarjeta in (resultado.tarjeta, de_la_sesion):
        html = render_to_string("asistente/tarjetas/mensaje.html", {"tarjeta": tarjeta})
        assert "<script>" not in html and "<b>" not in html
        assert "&lt;script&gt;alert(&quot;hola&quot;)&lt;/script&gt;" in html
        assert "&lt;b&gt;x&lt;/b&gt;" in html
        # El salto de línea queda tal cual: lo respeta el CSS (white-space: pre-line).
        assert "\nSegunda línea</p>" in html


def test_el_nombre_del_cliente_tambien_sale_escapado(taller):
    cliente = fabricas.crear_cliente(taller, nombre='<img src=x onerror="1">')
    pedido = fabricas.crear_pedido(taller, cliente=cliente)

    html = dibujar(preparar(contexto(taller), pedido_id=pedido.pk).tarjeta)

    assert "<img" not in html
    assert "Para &lt;img src=x onerror=&quot;1&quot;&gt;" in html


def test_la_tarjeta_no_usa_safe():
    plantilla = (PLANTILLAS / "mensaje.html").read_text(encoding="utf-8")
    assert "|safe" not in plantilla and "autoescape" not in plantilla


# --- No cambia nada -------------------------------------------------------------------------


def _cuentas():
    return [m.objects.count() for m in (Pedido, Cliente, Abono, Talla, Material, PrendaGuardada)]


def test_no_crea_ni_cambia_ningun_registro(taller, pedido):
    ctx = contexto(taller, pedido_actual=pedido)
    antes = _cuentas()
    actualizado = Pedido.objects.get(pk=pedido.pk).actualizado

    with CaptureQueriesContext(connection) as consultas:
        preparar(ctx, pedido_id=pedido.pk, motivo="cobro", texto="Saldo: $ 480.000.")
        preparar(ctx, pedido_id=pedido.pk, motivo="tallas", texto="Formulario: [ENLACE]")
        preparar(ctx, cliente_id=pedido.cliente_id, motivo="cobro", texto="Debe $ 480.000.")
        with pytest.raises(ErrorDeHerramienta):
            preparar(ctx, pedido_id=pedido.pk, motivo="cobro", texto="Saldo: $ 1.")

    assert _cuentas() == antes
    assert Pedido.objects.get(pk=pedido.pk).actualizado == actualizado
    escrituras = [
        c["sql"] for c in consultas.captured_queries
        if c["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert escrituras == []


def test_devuelve_una_tarjeta_de_verdad(taller, pedido):
    resultado = preparar(contexto(taller), pedido_id=pedido.pk)
    assert isinstance(resultado.tarjeta, Tarjeta)
    assert resultado.revisado == "Revisé el pedido de 8 overoles"


def test_tambien_ve_las_cifras_escritas_con_mil_o_millones():
    # Ajuste del revisor (tanda 8): "480 mil" no se podía colar sin revisar.
    assert cifras_en_pesos("Te debe 480 mil y el total es 1,8 millones") == [480_000, 1_800_000]
    assert cifras_en_pesos("Faltan $ 450.000 (450 mil)") == [450_000]
