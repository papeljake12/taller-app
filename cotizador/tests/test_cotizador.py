"""T15. Cotizador: el resultado mientras se escribe, "Mis prendas" (elegir, guardar y quitar),
copiar o enviar la cotización y crear el pedido con ella."""

import re
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import unquote

import pytest
from django.urls import reverse
from django.utils import timezone

from cotizador.models import PrendaGuardada
from pedidos.models import Cliente, Material, Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db

# El cálculo mientras se escribe apunta al resultado; los botones, al formulario entero.
HTMX = {"HX-Request": "true", "HX-Target": "resultado"}
BOTON = {"HX-Request": "true", "HX-Target": "cotizador"}

URL_INICIO = reverse("cotizador:inicio")
URL_CALCULAR = reverse("cotizador:calcular")
URL_GUARDAR = reverse("cotizador:prenda_guardar")
URL_CREAR = reverse("cotizador:crear_pedido")

# La camisa polo del diseño y de docs/06-pruebas.md: 20 camisas, 30 % de ganancia y 50 % de
# abono dan $ 1.090.000 en total.
CAMISA_POLO = {
    "cliente": "Panadería El Trigal",
    "tipo": "empresa",
    "whatsapp": "",
    "prenda": "Camisa polo bordada",
    "cantidad": "20",
    "entrega": "2026-12-11",
    "metros": "1,2",
    "precio_metro": "18000",
    "insumos": "3000",
    "mano_obra": "12000",
    "extra": "5000",
    "ganancia": "30",
    "abono": "50",
}

CIFRAS_DEL_DISENO = {
    "Precio por unidad": "$ 54.500",
    "Costo de hacer una": "$ 41.600",
    "De eso, en tela": "$ 21.600",
    "Tu ganancia en el pedido": "$ 258.000",
    "Abono para empezar": "$ 545.000",
}


def url_quitar(prenda):
    return reverse("cotizador:prenda_quitar", args=[prenda.pk])


def con(**cambios):
    """Los datos de la camisa polo, con algunos cambios."""
    return {**CAMISA_POLO, **cambios}


def resultado(html):
    """La tarjeta del resultado (id="resultado"), hasta su </section>."""
    return re.search(r'<section[^>]*id="resultado".*?</section>', html, re.S).group(0)


def total(html):
    return re.search(r'cotizacion__total dinero">([^<]*)<', html).group(1)


def renglon(html, nombre):
    """El valor del renglón `nombre` del resultado."""
    return re.search(
        rf'<span>{nombre}</span><(?:strong|span)[^>]*>([^<]*)<', resultado(html)
    ).group(1)


def valor_de(html, nombre):
    """Lo que dice el campo `nombre` del formulario."""
    etiqueta = re.search(rf'<input[^>]*name="{nombre}"[^>]*>', html).group(0)
    coincide = re.search(r'value="([^"]*)"', etiqueta)
    return coincide.group(1) if coincide else ""


def boton(html, texto):
    """La etiqueta de apertura del botón (o enlace) que dice `texto`."""
    return re.search(rf'<(?:button|a)\b[^>]*>(?=[^<]*{texto})', html).group(0)


@pytest.fixture
def camisa(taller):
    return fabricas.crear_prenda(
        taller, nombre="Camisa polo bordada", metros=Decimal("1.2"), precio_metro=18_000,
        insumos=3_000, mano_obra=12_000, extra=5_000,
    )


# --- La pantalla ----------------------------------------------------------------------------


def test_la_pantalla_abre_con_las_tarjetas_y_los_textos_del_diseno(sesion_duena):
    html = sesion_duena.get(URL_INICIO).text

    assert "<h1>Cotizador</h1>" in html
    assert "El precio se actualiza mientras escribes" in html
    for titulo in ("Para quién", "Qué prenda", "Cuánto cuesta hacer una", "Tu ganancia"):
        assert f">{titulo}</h2>" in html
    for etiqueta in (
        "Cliente", "Tipo de cliente", "WhatsApp (opcional)", "Prenda", "Cantidad",
        "Entrega estimada", "Metros de tela", "Precio del metro", "Insumos", "Mano de obra",
        "Bordado o estampado", "Ganancia sobre el costo (%)", "Abono para empezar (%)",
    ):
        assert f">{etiqueta}</label>" in html
    tarjeta = resultado(html)
    assert "Total de la cotización" in tarjeta
    for nombre in CIFRAS_DEL_DISENO:
        assert f"<span>{nombre}</span>" in tarjeta
    assert "Crear pedido con esta cotización" in tarjeta
    assert "Enviar por WhatsApp" in tarjeta and "Copiar cotización" in tarjeta
    assert "El precio por unidad se redondea hacia arriba a los 500 pesos." in tarjeta
    assert "Valores de ejemplo" not in html


def test_empieza_vacio_con_30_de_ganancia_50_de_abono_y_empresa(sesion_duena):
    html = sesion_duena.get(URL_INICIO).text

    assert valor_de(html, "ganancia") == "30"
    assert valor_de(html, "abono") == "50"
    assert valor_de(html, "prenda") == "" and valor_de(html, "metros") == ""
    assert re.search(r'<option value="empresa" selected>Empresa</option>', html)
    assert total(html) == "$ 0"
    tarjeta = resultado(html)
    assert "Escribe la prenda, la cantidad y los costos para ver el precio." in tarjeta
    assert "disabled" in boton(tarjeta, "Crear pedido con esta cotización")
    assert "disabled" in boton(tarjeta, "Copiar cotización")
    assert "disabled" in boton(tarjeta, "Enviar por WhatsApp")


def test_empezar_de_nuevo_abre_la_pantalla_vacia_tambien_en_celular(sesion_duena):
    html = sesion_duena.get(URL_INICIO).text

    # Uno en el encabezado (computador) y otro al comienzo del contenido (celular).
    assert html.count(f'<a class="boton" href="{URL_INICIO}">Empezar de nuevo</a>') == 2
    assert '<div class="navegacion-mes"><a class="boton"' in html


def test_el_formulario_se_calcula_mientras_se_escribe(sesion_duena):
    html = sesion_duena.get(URL_INICIO).text
    formulario = re.search(r'<form[^>]*id="cotizador"[^>]*>', html).group(0)

    assert f'hx-post="{URL_CALCULAR}"' in formulario
    assert 'hx-trigger="input changed delay:300ms, change, submit"' in formulario
    assert 'hx-target="#resultado"' in formulario and f'action="{URL_CALCULAR}"' in formulario
    # Sin JavaScript, el botón "Calcular".
    assert '<noscript><button type="submit" class="boton">Calcular</button></noscript>' in html


# --- El resultado ---------------------------------------------------------------------------


def test_la_camisa_polo_da_las_cifras_del_diseno(sesion_duena):
    respuesta = sesion_duena.post(URL_CALCULAR, CAMISA_POLO, headers=HTMX)

    assert respuesta.status_code == 200
    html = respuesta.text
    # Con HTMX vuelve solo el resultado.
    assert html.lstrip().startswith("<section") and "Para quién" not in html
    assert "HX-Retarget" not in respuesta.headers
    assert total(html) == "$ 1.090.000"
    for nombre, valor in CIFRAS_DEL_DISENO.items():
        assert renglon(html, nombre) == valor
    ganancia = re.search(r"Tu ganancia en el pedido</span><strong[^>]*>", html).group(0)
    assert "texto-verde" in ganancia
    assert "disabled" not in boton(html, "Crear pedido con esta cotización")
    assert "Escribe la prenda, la cantidad" not in html


def test_sin_javascript_calcular_devuelve_la_pagina_entera(sesion_duena):
    html = sesion_duena.post(URL_CALCULAR, CAMISA_POLO).text

    assert "<h1>Cotizador</h1>" in html
    assert total(html) == "$ 1.090.000"
    assert valor_de(html, "metros") == "1,2" and valor_de(html, "cliente") == "Panadería El Trigal"


def test_la_plata_se_escribe_con_puntos_o_signo_y_los_metros_con_coma_o_punto(sesion_duena):
    datos = con(precio_metro="$ 18.000", insumos="3.000", mano_obra="12000", extra=" 5.000 ",
                metros="1.2")

    html = sesion_duena.post(URL_CALCULAR, datos, headers=HTMX).text

    assert total(html) == "$ 1.090.000"


def test_lo_vacio_cuenta_como_0(sesion_duena):
    datos = con(metros="", precio_metro="", insumos="", extra="", mano_obra="10000",
                ganancia="", abono="")

    html = sesion_duena.post(URL_CALCULAR, datos, headers=HTMX).text

    assert renglon(html, "Costo de hacer una") == "$ 10.000"
    assert renglon(html, "Precio por unidad") == "$ 10.000"
    assert renglon(html, "Abono para empezar") == "$ 0"
    assert total(html) == "$ 200.000"


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("precio_metro", "abc",
         "Precio del metro: Escribe solo el valor en pesos, por ejemplo 18.000."),
        ("insumos", "3.0", "Insumos: Escribe solo el valor en pesos, por ejemplo 18.000."),
        ("metros", "uno", "Metros de tela: Escribe los metros con números, por ejemplo 1,2."),
        ("metros", "1,255", "Metros de tela: Usa máximo dos decimales, por ejemplo 1,25."),
        ("metros", "-2", "Metros de tela: Escribe los metros con números, por ejemplo 1,2."),
        ("cantidad", "2,5", "Cantidad: Escribe la cantidad con un número entero, por ejemplo 20."),
        ("cantidad", "3000", "Cantidad: Escribe una cantidad entre 1 y 2000."),
        ("ganancia", "30,5",
         "Ganancia sobre el costo (%): Escribe la ganancia con un número entero, por ejemplo 30."),
        ("abono", "120", "Abono para empezar (%): El abono va de 0 a 100 %."),
    ],
)
def test_un_valor_mal_escrito_se_avisa_y_cuenta_como_0(sesion_duena, campo, valor, mensaje):
    html = sesion_duena.post(URL_CALCULAR, con(**{campo: valor}), headers=HTMX).text

    assert '<div class="aviso" role="alert">' in html
    assert mensaje in html


def test_un_whatsapp_a_medio_escribir_no_se_avisa_mientras_se_escribe(sesion_duena):
    html = sesion_duena.post(URL_CALCULAR, con(whatsapp="30"), headers=HTMX).text

    assert "aviso" not in html
    assert total(html) == "$ 1.090.000"


# --- Copiar y enviar ------------------------------------------------------------------------


def test_copiar_cotizacion_trae_el_texto_de_la_cotizacion(sesion_duena, taller):
    html = sesion_duena.post(URL_CALCULAR, CAMISA_POLO, headers=HTMX).text

    copiar = boton(html, "Copiar cotización")
    assert "disabled" not in copiar
    texto = re.search(r'data-copiar="([^"]*)"', copiar).group(1)
    assert f"Cotización de {taller.nombre}" in texto
    assert "Cliente: Panadería El Trigal" in texto
    assert "20 × Camisa polo bordada" in texto
    assert "Precio por unidad: $ 54.500" in texto and "Total: $ 1.090.000" in texto
    assert "Abono para empezar: $ 545.000" in texto
    assert "Entrega estimada: 11 de dic" in texto


def test_con_un_whatsapp_que_sirve_se_envia_por_whatsapp(sesion_duena):
    html = sesion_duena.post(URL_CALCULAR, con(whatsapp="300 123 4567"), headers=HTMX).text

    enlace = boton(html, "Enviar por WhatsApp")
    assert enlace.startswith("<a ")
    href = re.search(r'href="([^"]*)"', enlace).group(1)
    assert href.startswith("https://wa.me/573001234567?text=")
    assert "Total: $ 1.090.000" in unquote(href)
    assert "Escribe el WhatsApp del cliente" not in html


def test_sin_whatsapp_el_boton_se_apaga_y_una_nota_lo_pide(sesion_duena):
    html = sesion_duena.post(URL_CALCULAR, CAMISA_POLO, headers=HTMX).text

    assert "disabled" in boton(html, "Enviar por WhatsApp")
    assert "wa.me" not in html
    assert "Escribe el WhatsApp del cliente para enviarle la cotización." in html


def test_sin_prenda_no_hay_cotizacion_para_mandar(sesion_duena):
    html = sesion_duena.post(URL_CALCULAR, con(prenda=""), headers=HTMX).text

    assert "Escribe la prenda, la cantidad y los costos para ver el precio." in html
    assert "disabled" in boton(html, "Copiar cotización")
    assert 'data-copiar=""' in html


# --- Mis prendas: elegir --------------------------------------------------------------------


def test_mis_prendas_muestra_solo_las_del_taller(sesion_duena, taller, camisa):
    fabricas.crear_prenda(fabricas.crear_taller(), nombre="Prenda de otro taller")

    html = sesion_duena.get(URL_INICIO).text

    assert '<label class="oculto" for="cot-guardada">Mis prendas guardadas</label>' in html
    assert f'<option value="{camisa.pk}">Camisa polo bordada</option>' in html
    assert "Prenda de otro taller" not in html


def test_sin_prendas_guardadas_no_sale_la_lista(sesion_duena):
    assert 'name="guardada"' not in sesion_duena.get(URL_INICIO).text


def test_elegir_una_prenda_pasa_sus_costos_a_los_campos(sesion_duena, camisa):
    datos = {"guardada": camisa.pk, "aplicada": "", "cantidad": "20", "ganancia": "30",
             "abono": "50", "tipo": "empresa", "cliente": "Panadería El Trigal"}

    respuesta = sesion_duena.post(URL_CALCULAR, datos, headers=HTMX)

    # Vuelve el formulario entero, para cambiar los campos.
    assert respuesta.headers["HX-Retarget"] == "#cotizador"
    assert respuesta.headers["HX-Reswap"] == "outerHTML"
    html = respuesta.text
    assert html.lstrip().startswith('<form class="dos-columnas" id="cotizador"')
    assert valor_de(html, "prenda") == "Camisa polo bordada"
    assert valor_de(html, "metros") == "1,2"
    assert valor_de(html, "precio_metro") == "18000"
    assert valor_de(html, "insumos") == "3000"
    assert valor_de(html, "mano_obra") == "12000"
    assert valor_de(html, "extra") == "5000"
    assert valor_de(html, "aplicada") == str(camisa.pk)
    # Lo que ya estaba escrito se queda.
    assert valor_de(html, "cliente") == "Panadería El Trigal"
    assert valor_de(html, "cantidad") == "20"
    assert f'<option value="{camisa.pk}" selected>' in html
    assert total(html) == "$ 1.090.000"
    for nombre, valor in CIFRAS_DEL_DISENO.items():
        assert renglon(html, nombre) == valor
    assert "Quitar de mi lista" in html


def test_sin_javascript_la_prenda_elegida_se_pasa_al_tocar_calcular(sesion_duena, camisa):
    html = sesion_duena.post(URL_CALCULAR, {"guardada": camisa.pk, "cantidad": "20"}).text

    assert "<h1>Cotizador</h1>" in html
    assert valor_de(html, "metros") == "1,2" and valor_de(html, "aplicada") == str(camisa.pk)


def test_una_prenda_ya_pasada_no_vuelve_a_pisar_lo_escrito(sesion_duena, camisa):
    datos = con(guardada=camisa.pk, aplicada=camisa.pk, precio_metro="20000")

    respuesta = sesion_duena.post(URL_CALCULAR, datos, headers=HTMX)

    assert "HX-Retarget" not in respuesta.headers
    assert renglon(respuesta.text, "De eso, en tela") == "$ 24.000"


def test_una_prenda_sin_un_costo_deja_ese_campo_vacio(sesion_duena, taller):
    uniforme = fabricas.crear_prenda(taller, nombre="Uniforme", metros=Decimal("2.2"),
                                     precio_metro=16_000, insumos=4_000, mano_obra=20_000)

    html = sesion_duena.post(URL_CALCULAR, {"guardada": uniforme.pk}, headers=HTMX).text

    assert valor_de(html, "metros") == "2,2" and valor_de(html, "extra") == ""


def test_la_prenda_de_otro_taller_no_se_puede_elegir(sesion_duena):
    ajena = fabricas.crear_prenda(
        fabricas.crear_taller(), nombre="Secreta", metros=Decimal("3"), precio_metro=99_000
    )

    html = sesion_duena.post(URL_CALCULAR, {"guardada": ajena.pk}, headers=HTMX).text

    assert "Secreta" not in html and "99000" not in html
    assert valor_de(html, "metros") == "" and valor_de(html, "aplicada") == ""


def test_volver_a_mis_prendas_sin_elegir_deja_lo_escrito(sesion_duena, camisa):
    datos = con(guardada="", aplicada=camisa.pk, precio_metro="20000")

    html = sesion_duena.post(URL_CALCULAR, datos, headers=HTMX).text

    assert valor_de(html, "precio_metro") == "20000" and valor_de(html, "aplicada") == ""
    assert "Quitar de mi lista" not in html


# --- Mis prendas: guardar -------------------------------------------------------------------


def test_guardar_esta_prenda_la_agrega_a_mis_prendas(sesion_duena, taller):
    respuesta = sesion_duena.post(URL_GUARDAR, con(precio_metro="18.000"), headers=BOTON)

    assert respuesta.status_code == 200
    prenda = PrendaGuardada.objects.get(taller=taller)
    assert prenda.nombre == "Camisa polo bordada"
    assert prenda.metros == Decimal("1.2")
    assert (prenda.precio_metro, prenda.insumos, prenda.mano_obra, prenda.extra) == (
        18_000, 3_000, 12_000, 5_000,
    )
    html = respuesta.text
    # El botón ya apunta al formulario entero: no hace falta cambiarle el destino.
    assert "HX-Retarget" not in respuesta.headers
    assert "Prenda guardada en tu lista." in html
    assert f'<option value="{prenda.pk}" selected>' in html
    assert valor_de(html, "cliente") == "Panadería El Trigal"


def test_guardar_con_el_mismo_nombre_cambia_la_prenda_en_vez_de_repetirla(
    sesion_duena, taller, camisa
):
    sesion_duena.post(URL_GUARDAR, con(prenda="camisa  POLO bordada", mano_obra="15000"))

    assert PrendaGuardada.objects.filter(taller=taller).count() == 1
    camisa.refresh_from_db()
    assert camisa.mano_obra == 15_000
    assert camisa.nombre == "camisa POLO bordada"


def test_guardar_sin_nombre_pide_la_prenda(sesion_duena, taller):
    respuesta = sesion_duena.post(URL_GUARDAR, con(prenda="  "), headers=BOTON)

    assert respuesta.status_code == 422
    assert "Escribe el nombre de la prenda para guardarla." in respuesta.text
    assert "Revisa los campos marcados." in respuesta.text
    assert not PrendaGuardada.objects.filter(taller=taller).exists()


def test_guardar_con_un_costo_mal_escrito_no_guarda(sesion_duena, taller):
    respuesta = sesion_duena.post(URL_GUARDAR, con(insumos="tres mil"))

    assert respuesta.status_code == 422
    assert "Escribe solo el valor en pesos, por ejemplo 18.000." in respuesta.text
    assert not PrendaGuardada.objects.filter(taller=taller).exists()


def test_guardar_no_toca_la_prenda_de_otro_taller_con_el_mismo_nombre(sesion_duena, taller):
    otro = fabricas.crear_taller()
    ajena = fabricas.crear_prenda(otro, nombre="Camisa polo bordada", mano_obra=1)

    sesion_duena.post(URL_GUARDAR, CAMISA_POLO)

    ajena.refresh_from_db()
    assert ajena.mano_obra == 1
    assert PrendaGuardada.objects.get(taller=taller).mano_obra == 12_000


def test_guardar_sin_javascript_devuelve_la_pagina_entera(sesion_duena):
    html = sesion_duena.post(URL_GUARDAR, CAMISA_POLO).text

    assert "<h1>Cotizador</h1>" in html and "Prenda guardada en tu lista." in html


# --- Mis prendas: quitar --------------------------------------------------------------------


def test_quitar_de_mi_lista_primero_pregunta(sesion_duena, camisa):
    datos = con(guardada=camisa.pk, aplicada=camisa.pk)

    respuesta = sesion_duena.post(url_quitar(camisa), datos, headers=BOTON)

    assert respuesta.status_code == 200
    assert PrendaGuardada.objects.filter(pk=camisa.pk).exists()
    html = respuesta.text
    assert "¿Quitar «Camisa polo bordada» de tus prendas guardadas?" in html
    assert "Sí, quitar la prenda" in html and ">Cancelar</button>" in html
    assert valor_de(html, "cliente") == "Panadería El Trigal"


def test_quitar_con_la_confirmacion_la_borra_y_deja_lo_escrito(sesion_duena, camisa):
    datos = con(guardada=camisa.pk, aplicada=camisa.pk, confirmar="si")

    html = sesion_duena.post(url_quitar(camisa), datos, headers=BOTON).text

    assert not PrendaGuardada.objects.filter(pk=camisa.pk).exists()
    assert "Prenda quitada de tu lista." in html
    assert valor_de(html, "prenda") == "Camisa polo bordada"
    assert valor_de(html, "aplicada") == ""
    assert total(html) == "$ 1.090.000"


def test_cancelar_no_quita_la_prenda(sesion_duena, camisa):
    datos = con(guardada=camisa.pk, aplicada=camisa.pk, cancelar="si")

    html = sesion_duena.post(url_quitar(camisa), datos, headers=BOTON).text

    assert PrendaGuardada.objects.filter(pk=camisa.pk).exists()
    assert "¿Quitar" not in html and "Quitar de mi lista" in html


def test_quitar_la_prenda_de_otro_taller_responde_404_y_no_la_borra(sesion_duena):
    ajena = fabricas.crear_prenda(fabricas.crear_taller())

    respuesta = sesion_duena.post(url_quitar(ajena), {"confirmar": "si"})

    assert respuesta.status_code == 404
    assert PrendaGuardada.objects.filter(pk=ajena.pk).exists()


def test_quitar_solo_se_hace_con_un_envio(sesion_duena, camisa):
    assert sesion_duena.get(url_quitar(camisa)).status_code == 405
    assert PrendaGuardada.objects.filter(pk=camisa.pk).exists()


# --- Crear el pedido ------------------------------------------------------------------------


def test_crear_pedido_con_la_cotizacion(sesion_duena, taller, duena):
    respuesta = sesion_duena.post(URL_CREAR, CAMISA_POLO, headers=BOTON)

    pedido = Pedido.objects.get(taller=taller)
    assert respuesta.status_code == 200
    assert respuesta.headers["HX-Redirect"] == reverse("pedidos:detalle", args=[pedido.pk])
    assert pedido.estado == Pedido.Estado.COTIZADO
    assert pedido.total == 1_090_000
    assert pedido.detalle == "20 × Camisa polo bordada"
    assert pedido.cantidad == 20
    assert pedido.fecha_entrega == date(2026, 12, 11)
    assert pedido.tallaje == Pedido.Tallaje.ADULTO
    assert pedido.creado_por == duena
    assert pedido.cliente.nombre == "Panadería El Trigal"
    assert pedido.cliente.tipo == Cliente.Tipo.EMPRESA
    assert list(pedido.materiales.values_list("nombre", "cantidad", "comprado")) == [
        ("Tela", "24 m", False)
    ]


def test_crear_pedido_sin_javascript_lleva_al_pedido(sesion_duena, taller):
    respuesta = sesion_duena.post(URL_CREAR, CAMISA_POLO)

    pedido = Pedido.objects.get(taller=taller)
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:detalle", args=[pedido.pk])


def test_la_tela_lleva_los_metros_de_todo_el_pedido_con_coma(sesion_duena, taller):
    sesion_duena.post(URL_CREAR, con(metros="1,25", cantidad="3"))

    assert Material.objects.get(pedido__taller=taller).cantidad == "3,75 m"


def test_sin_metros_no_se_agrega_la_tela(sesion_duena, taller):
    sesion_duena.post(URL_CREAR, con(metros="", precio_metro=""))

    pedido = Pedido.objects.get(taller=taller)
    assert not pedido.materiales.exists()


def test_sin_entrega_estimada_el_pedido_queda_para_dentro_de_15_dias(sesion_duena, taller):
    hoy = timezone.localdate()

    sesion_duena.post(URL_CREAR, con(entrega=""))

    assert Pedido.objects.get(taller=taller).fecha_entrega == hoy + timedelta(days=15)


def test_crear_pedido_usa_el_cliente_que_ya_existe(sesion_duena, taller):
    cliente = fabricas.crear_cliente(taller, nombre="Panadería El Trigal",
                                     tipo=Cliente.Tipo.PARTICULAR)

    sesion_duena.post(URL_CREAR, con(cliente="panadería  el trigal", tipo="colegio",
                                     whatsapp="300 123 4567"))

    pedido = Pedido.objects.get(taller=taller)
    assert pedido.cliente == cliente
    cliente.refresh_from_db()
    # El tipo no cambia; el WhatsApp se pone porque no tenía.
    assert cliente.tipo == Cliente.Tipo.PARTICULAR
    assert cliente.whatsapp == "300 123 4567"


def test_crear_pedido_no_cambia_el_whatsapp_que_ya_tenia(sesion_duena, taller):
    cliente = fabricas.crear_cliente(taller, nombre="Panadería El Trigal", whatsapp="3110000000")

    sesion_duena.post(URL_CREAR, con(whatsapp="300 123 4567"))

    cliente.refresh_from_db()
    assert cliente.whatsapp == "3110000000"


def test_crear_pedido_con_un_cliente_nuevo_le_pone_tipo_y_whatsapp(sesion_duena, taller):
    sesion_duena.post(URL_CREAR, con(tipo="comparsa", whatsapp="300 123 4567"))

    cliente = Cliente.objects.get(taller=taller)
    assert cliente.tipo == Cliente.Tipo.COMPARSA and cliente.whatsapp == "300 123 4567"


def test_crear_pedido_no_usa_el_cliente_de_otro_taller(sesion_duena, taller):
    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_cliente(otro, nombre="Panadería El Trigal")

    sesion_duena.post(URL_CREAR, CAMISA_POLO)

    pedido = Pedido.objects.get(taller=taller)
    assert pedido.cliente != ajeno and pedido.cliente.taller == taller
    assert not Pedido.objects.filter(taller=otro).exists()


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"cliente": " "}, "Escribe el nombre del cliente para crear el pedido."),
        ({"prenda": ""}, "Escribe qué prenda es."),
        ({"cantidad": ""}, "Escribe cuántas prendas son."),
        ({"cantidad": "0"}, "Escribe una cantidad entre 1 y 2000."),
        ({"metros": "", "precio_metro": "", "insumos": "", "mano_obra": "", "extra": ""},
         "Escribe lo que cuesta hacer una para calcular el precio."),
        ({"whatsapp": "300"}, "Escribe solo el número de WhatsApp, con o sin espacios."),
        ({"entrega": "2026-02-31"}, "Elige una fecha de entrega que exista."),
    ],
)
def test_crear_pedido_sin_lo_necesario_lo_pide(sesion_duena, taller, cambios, mensaje):
    respuesta = sesion_duena.post(URL_CREAR, con(**cambios), headers=BOTON)

    assert respuesta.status_code == 422
    assert respuesta.text.lstrip().startswith('<form class="dos-columnas" id="cotizador"')
    assert mensaje in respuesta.text
    assert "Revisa los campos marcados." in respuesta.text
    assert not Pedido.objects.filter(taller=taller).exists()
    assert not Cliente.objects.filter(taller=taller).exists()


def test_crear_pedido_sin_lo_necesario_y_sin_javascript_muestra_la_pagina(sesion_duena, taller):
    respuesta = sesion_duena.post(URL_CREAR, con(cliente=""))

    assert respuesta.status_code == 422
    assert "<h1>Cotizador</h1>" in respuesta.text
    assert "Escribe el nombre del cliente para crear el pedido." in respuesta.text


def test_crear_pedido_solo_se_hace_con_un_envio(sesion_duena, taller):
    assert sesion_duena.get(URL_CREAR).status_code == 405
    assert sesion_duena.get(URL_GUARDAR).status_code == 405


def test_los_ejemplos_traen_la_camisa_polo_del_diseno(sesion_duena, duena):
    """Con las prendas de los datos de ejemplo, la camisa polo da las cifras del diseño."""
    from pedidos import ejemplos

    for nombre, metros, precio, insumos, mano, extra in ejemplos.PRENDAS:
        fabricas.crear_prenda(duena.taller, nombre=nombre, metros=Decimal(metros),
                              precio_metro=precio, insumos=insumos, mano_obra=mano, extra=extra)
    camisa = PrendaGuardada.objects.get(taller=duena.taller, nombre="Camisa polo bordada")

    html = sesion_duena.post(
        URL_CALCULAR, {"guardada": camisa.pk, "cantidad": "20", "ganancia": "30", "abono": "50"},
        headers=HTMX,
    ).text

    assert total(html) == "$ 1.090.000"
    for nombre, valor in CIFRAS_DEL_DISENO.items():
        assert renglon(html, nombre) == valor
