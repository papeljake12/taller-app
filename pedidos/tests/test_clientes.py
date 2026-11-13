"""Clientes (T04): la lista con buscador, crear y editar.

Con el ajuste "pantalla fija y animaciones": la tabla se desplaza por dentro en computador,
cada fila lleva el id de su cliente y al guardar sale un aviso corto.
"""

import re
from datetime import date

import pytest
from django.urls import reverse

from pedidos import ejemplos
from pedidos.formularios.clientes import MENSAJE_NOMBRE_REPETIDO, ClienteForm
from pedidos.models import Cliente, Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}
URL = "/clientes/"


def filas(html):
    """Los nombres de la tabla, en orden."""
    return re.findall(r'<tr id="cliente-\d+"><td><strong>([^<]+)</strong>', html)


def ids_de_filas(html):
    return re.findall(r'<tr id="(cliente-\d+)">', html)


def avisos_pendientes(html):
    """Los avisos cortos que la página deja para static/js/app.js (base.html)."""
    return re.findall(r"<p data-aviso>([^<]*)</p>", html)


def nuevo(sesion, **datos):
    datos.setdefault("tipo", "particular")
    return sesion.post(reverse("pedidos:cliente_nuevo"), datos, headers=HTMX)


# --- La lista ----------------------------------------------------------------------------------


def test_la_lista_sale_como_el_diseno(client):
    taller = ejemplos.cargar(hoy=date(2026, 11, 11), con_fotos=False)
    client.force_login(taller.usuarias.filter(rol="duena").first())

    html = client.get(URL).text

    assert "6 clientes, 4 te deben" in html
    assert filas(html) == [
        "Colegio Nuevo Amanecer",
        "Restaurante El Fogón Costeño",
        "Comparsa Brisa Caribe",
        "Grupo de danza Tambores del Río",
        "Ferretería La Esquina",
        "Marcela P.",
    ]
    colegio = html[html.index("Colegio Nuevo Amanecer"):html.index("</tr>", html.index("Colegio"))]
    assert "<td>Colegio</td><td>1</td>" in colegio
    assert "$ 4.800.000" in colegio
    assert '<strong class="texto-rojo dinero">$ 3.300.000</strong>' in colegio
    comparsa = html[html.index("Comparsa Brisa Caribe"):]
    assert '<strong class="texto-verde">Al día</strong>' in comparsa[:comparsa.index("</tr>")]
    marcela = html[html.index("Marcela P."):]
    marcela = marcela[:marcela.index("</tr>")]
    assert "Sin compras" in marcela and "Cotización abierta" in marcela
    for titulo in ("Cliente", "Tipo", "Pedidos", "Ha comprado", "Debe", "Acción"):
        assert f">{titulo}</th>" in html


def test_cada_cliente_tiene_su_boton_editar(sesion_duena, taller):
    cliente = fabricas.crear_cliente(taller, nombre="Cliente con botón")
    url = reverse("pedidos:cliente_editar", args=[cliente.pk])

    html = sesion_duena.get(URL).text

    assert f'hx-get="{url}" hx-target="#ventana"' in html
    assert ">Editar</a>" in html


def test_un_cliente_sin_pedidos(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Recién llegado")

    html = sesion_duena.get(URL).text

    assert "1 cliente, ninguno te debe" in html
    fila = html[html.index("Recién llegado"):]
    fila = fila[:fila.index("</tr>")]
    assert "<td>0</td>" in fila and "Sin compras" in fila
    assert "texto-verde" not in fila  # verde solo para lo pagado


def test_sin_clientes_invita_a_crear_el_primero(sesion_duena):
    html = sesion_duena.get(URL).text

    assert "Todavía no tienes clientes" in html
    assert "<table" not in html


def test_no_muestra_los_clientes_de_otro_taller(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Cliente propio")
    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_cliente(otro, nombre="Cliente ajeno")
    fabricas.crear_pedido(otro, cliente=ajeno, estado=Pedido.Estado.CONFIRMADO)

    html = sesion_duena.get(URL).text

    assert "Cliente propio" in html
    assert "Cliente ajeno" not in html
    assert "1 cliente, ninguno te debe" in html


def test_cuenta_uno_que_debe_en_singular(sesion_duena, taller):
    fabricas.crear_pedido(taller, estado=Pedido.Estado.CONFIRMADO, total=200_000)

    assert "1 cliente, 1 te debe" in sesion_duena.get(URL).text


# --- El buscador -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("busqueda", "encontrados"),
    [
        ("ferreteria", ["Ferretería La Esquina"]),  # sin tilde
        ("EMPRESA", ["Ferretería La Esquina"]),  # por tipo
        ("4567", ["Marcela Ejemplo"]),  # por WhatsApp
        ("  ", ["Ferretería La Esquina", "Marcela Ejemplo"]),
    ],
)
def test_buscar_por_nombre_tipo_o_whatsapp(sesion_duena, taller, busqueda, encontrados):
    fabricas.crear_cliente(taller, nombre="Ferretería La Esquina", tipo="empresa")
    fabricas.crear_cliente(taller, nombre="Marcela Ejemplo", whatsapp="300 123 4567")

    html = sesion_duena.get(URL, {"q": busqueda}).text

    assert filas(html) == encontrados


def test_buscar_sin_resultados_lo_dice(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Marcela Ejemplo")

    html = sesion_duena.get(URL, {"q": "zapatos"}).text

    assert "Ningún cliente coincide con «zapatos»." in html
    # El encabezado sigue contando a todos.
    assert "1 cliente, ninguno te debe" in html


def test_el_buscador_trae_solo_la_tabla(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Marcela Ejemplo")

    respuesta = sesion_duena.get(URL, {"q": "marcela"}, headers={**HTMX, "HX-Target": "clientes-lista"})

    assert respuesta.text.startswith(
        '<div id="clientes-lista" class="tabla-contenedor desplazable">')
    assert "<html" not in respuesta.text
    assert filas(respuesta.text) == ["Marcela Ejemplo"]


# --- Pantalla fija y animaciones (docs/08-diseno.md) --------------------------------------------


def test_en_computador_solo_la_tabla_se_desplaza(sesion_duena, taller):
    """La tarjeta de la lista toma el alto que queda (.llenar) y la caja de la tabla se
    desplaza por dentro (.desplazable): el aviso de dotación y el buscador quedan quietos."""
    fabricas.crear_cliente(taller, nombre="Marcela Ejemplo")

    html = sesion_duena.get(URL).text

    tarjeta = re.search(r'<section class="([^"]*)" aria-labelledby="t-clientes">', html)
    assert "llenar" in tarjeta.group(1).split()
    lista = html[tarjeta.end():]
    assert lista.index('role="search"') < lista.index(
        '<div id="clientes-lista" class="tabla-contenedor desplazable">')
    assert html.index("tarjeta-oscura") < tarjeta.start()


def test_cada_fila_lleva_el_id_de_su_cliente_y_no_cambia_al_buscar(sesion_duena, taller):
    """Con el mismo id antes y después, al buscar solo entran y salen las filas que cambian
    (static/js/app.js, sección 11): las que siguen no parpadean."""
    marcela = fabricas.crear_cliente(taller, nombre="Marcela Ejemplo")
    ferreteria = fabricas.crear_cliente(taller, nombre="Ferretería La Esquina")

    pagina = sesion_duena.get(URL).text
    buscada = sesion_duena.get(URL, {"q": "marcela"},
                               headers={**HTMX, "HX-Target": "clientes-lista"}).text

    assert sorted(ids_de_filas(pagina)) == sorted(
        [f"cliente-{marcela.pk}", f"cliente-{ferreteria.pk}"])
    assert ids_de_filas(buscada) == [f"cliente-{marcela.pk}"]
    # La tabla tiene su id en la página y en la búsqueda: no se vuelve a dibujar entera.
    assert pagina.count('<table class="tabla" id="clientes-tabla">') == 1
    assert buscada.count('<table class="tabla" id="clientes-tabla">') == 1


def test_las_notas_de_la_lista_tienen_su_id(sesion_duena, taller):
    """Sin resultados, la nota entra con un id fijo: al seguir escribiendo no parpadea."""
    assert 'id="clientes-vacio"' in sesion_duena.get(URL).text

    fabricas.crear_cliente(taller, nombre="Marcela Ejemplo")
    for busqueda in ("zap", "zapatos"):
        html = sesion_duena.get(URL, {"q": busqueda},
                                headers={**HTMX, "HX-Target": "clientes-lista"}).text
        nota = f"Ningún cliente coincide con «{busqueda}»."
        assert f'<p class="tarjeta__nota" id="clientes-ninguno">{nota}</p>' in html
        assert "clientes-tabla" not in html


def test_buscar_no_lleva_aviso(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Marcela Ejemplo")

    respuesta = sesion_duena.get(URL, {"q": "marcela"},
                                 headers={**HTMX, "HX-Target": "clientes-lista"})

    assert "HX-Trigger" not in respuesta.headers


def test_el_buscador_funciona_sin_javascript(sesion_duena):
    html = sesion_duena.get(URL).text

    assert f'<form method="get" action="{URL}"' in html
    assert 'name="q"' in html


# --- Crear ---------------------------------------------------------------------------------------


def test_crear_un_cliente(sesion_duena, taller):
    respuesta = nuevo(sesion_duena, nombre="  Comparsa   Nueva ", tipo="comparsa",
                      whatsapp="300 123 4567", notas="Ensayan los sábados.")

    assert respuesta.status_code == 200
    assert respuesta.headers["HX-Redirect"] == URL
    cliente = Cliente.objects.get()
    assert cliente.taller == taller
    assert (cliente.nombre, cliente.tipo, cliente.whatsapp, cliente.notas) == (
        "Comparsa Nueva", "comparsa", "300 123 4567", "Ensayan los sábados.")


def test_crear_avisa_cliente_creado_en_la_lista(sesion_duena):
    """Al guardar se vuelve a la lista: el aviso corto sale allá (config/avisos.py)."""
    respuesta = nuevo(sesion_duena, nombre="Comparsa Nueva")

    assert respuesta.headers["HX-Redirect"] == URL
    assert "HX-Trigger" not in respuesta.headers
    assert avisos_pendientes(sesion_duena.get(URL).text) == ["Cliente creado."]
    # Se muestra una sola vez.
    assert avisos_pendientes(sesion_duena.get(URL).text) == []


def test_crear_sin_javascript_tambien_avisa(sesion_duena):
    respuesta = sesion_duena.post(reverse("pedidos:cliente_nuevo"),
                                  {"nombre": "Sin JS", "tipo": "empresa"}, follow=True)

    assert respuesta.redirect_chain == [(URL, 302)]
    assert avisos_pendientes(respuesta.text) == ["Cliente creado."]


def test_con_errores_no_hay_aviso(sesion_duena):
    respuesta = nuevo(sesion_duena, nombre="  ")

    assert respuesta.status_code == 422
    assert "HX-Trigger" not in respuesta.headers
    assert avisos_pendientes(sesion_duena.get(URL).text) == []


def test_la_ventana_de_nuevo_cliente_trae_sus_campos(sesion_duena):
    html = sesion_duena.get(reverse("pedidos:cliente_nuevo"), headers=HTMX).text

    assert "<html" not in html
    assert "Nuevo cliente" in html
    for nombre in ("nombre", "tipo", "whatsapp", "notas"):
        assert f'name="{nombre}"' in html
    assert "Crear cliente" in html


def test_crear_sin_javascript_vuelve_a_la_lista(sesion_duena):
    respuesta = sesion_duena.post(reverse("pedidos:cliente_nuevo"),
                                  {"nombre": "Sin JS", "tipo": "empresa"})

    assert respuesta.status_code == 302
    assert respuesta.url == URL
    assert Cliente.objects.filter(nombre="Sin JS").exists()


def test_sin_nombre_se_rechaza_con_un_mensaje_claro(sesion_duena):
    respuesta = nuevo(sesion_duena, nombre="  ")

    assert respuesta.status_code == 422
    assert "Escribe el nombre del cliente." in respuesta.text
    assert not Cliente.objects.exists()


def test_un_nombre_repetido_sin_importar_mayusculas_da_un_aviso(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Comparsa Brisa Caribe")

    respuesta = nuevo(sesion_duena, nombre="comparsa BRISA caribe")

    assert respuesta.status_code == 422
    assert "Ya tienes un cliente con ese nombre." in respuesta.text
    assert Cliente.objects.count() == 1


def test_dos_personas_creando_el_mismo_nombre_a_la_vez_reciben_el_aviso(
    sesion_duena, taller, monkeypatch
):
    """Si la otra persona guarda justo entre la revisión del nombre y el guardado, la base de
    datos lo frena y la ventana muestra el mismo aviso, sin romperse."""
    fabricas.crear_cliente(taller, nombre="Comparsa Brisa Caribe")
    # La revisión del formulario "no alcanza a ver" el cliente que se acaba de crear.
    monkeypatch.setattr(ClienteForm, "clean_nombre", lambda form: form.cleaned_data["nombre"])

    respuesta = nuevo(sesion_duena, nombre="comparsa brisa caribe")

    assert respuesta.status_code == 422
    assert MENSAJE_NOMBRE_REPETIDO in respuesta.text
    assert Cliente.objects.count() == 1


def test_el_mismo_nombre_en_otro_taller_si_se_puede(sesion_duena, taller):
    fabricas.crear_cliente(fabricas.crear_taller(), nombre="Comparsa Brisa Caribe")

    assert nuevo(sesion_duena, nombre="Comparsa Brisa Caribe").status_code == 200
    assert Cliente.objects.filter(taller=taller, nombre="Comparsa Brisa Caribe").exists()


@pytest.mark.parametrize("numero", ["123", "llámame", "300 123 4567 ext 2", "1" * 16])
def test_un_whatsapp_que_no_sirve_se_rechaza(sesion_duena, numero):
    respuesta = nuevo(sesion_duena, nombre="Cliente nuevo", whatsapp=numero)

    assert respuesta.status_code == 422
    assert "Revisa el número" in respuesta.text
    assert not Cliente.objects.exists()


def test_un_tipo_inventado_se_rechaza(sesion_duena):
    respuesta = nuevo(sesion_duena, nombre="Cliente nuevo", tipo="vip")

    assert respuesta.status_code == 422
    assert "Elige uno de los tipos de la lista." in respuesta.text


def test_el_taller_no_se_puede_elegir_desde_el_formulario(sesion_duena, taller):
    otro = fabricas.crear_taller()

    nuevo(sesion_duena, nombre="Cliente nuevo", taller=otro.pk)

    assert Cliente.objects.get().taller == taller


# --- Editar --------------------------------------------------------------------------------------


def test_editar_un_cliente(sesion_duena, taller):
    cliente = fabricas.crear_cliente(taller, nombre="Nombre viejo", tipo="particular")
    url = reverse("pedidos:cliente_editar", args=[cliente.pk])

    ventana = sesion_duena.get(url, headers=HTMX).text
    assert 'value="Nombre viejo"' in ventana and "Editar cliente" in ventana
    assert "Guardar cambios" in ventana

    respuesta = sesion_duena.post(url, {"nombre": "Nombre nuevo", "tipo": "empresa",
                                        "whatsapp": "3001234567"}, headers=HTMX)

    assert respuesta.headers["HX-Redirect"] == URL
    cliente.refresh_from_db()
    assert (cliente.nombre, cliente.tipo, cliente.whatsapp) == (
        "Nombre nuevo", "empresa", "3001234567")
    assert Cliente.objects.count() == 1


def test_editar_avisa_cliente_guardado_en_la_lista(sesion_duena, taller):
    cliente = fabricas.crear_cliente(taller, nombre="Nombre viejo")
    url = reverse("pedidos:cliente_editar", args=[cliente.pk])

    respuesta = sesion_duena.post(url, {"nombre": "Nombre nuevo", "tipo": "particular"},
                                  headers=HTMX)

    assert respuesta.headers["HX-Redirect"] == URL
    assert avisos_pendientes(sesion_duena.get(URL).text) == ["Cliente guardado."]


def test_editar_con_errores_no_avisa(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Ya existe")
    cliente = fabricas.crear_cliente(taller, nombre="Otro")
    url = reverse("pedidos:cliente_editar", args=[cliente.pk])

    respuesta = sesion_duena.post(url, {"nombre": "ya existe", "tipo": "particular"},
                                  headers=HTMX)

    assert respuesta.status_code == 422
    assert avisos_pendientes(sesion_duena.get(URL).text) == []


def test_editar_conservando_el_mismo_nombre_se_puede(sesion_duena, taller):
    cliente = fabricas.crear_cliente(taller, nombre="Marcela Ejemplo")
    url = reverse("pedidos:cliente_editar", args=[cliente.pk])

    respuesta = sesion_duena.post(url, {"nombre": "MARCELA ejemplo", "tipo": "particular"},
                                  headers=HTMX)

    assert respuesta.status_code == 200
    cliente.refresh_from_db()
    assert cliente.nombre == "MARCELA ejemplo"


def test_editar_al_nombre_de_otro_cliente_se_rechaza(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Ya existe")
    cliente = fabricas.crear_cliente(taller, nombre="Otro")
    url = reverse("pedidos:cliente_editar", args=[cliente.pk])

    respuesta = sesion_duena.post(url, {"nombre": "ya existe", "tipo": "particular"},
                                  headers=HTMX)

    assert respuesta.status_code == 422
    assert "Ya tienes un cliente con ese nombre." in respuesta.text
    cliente.refresh_from_db()
    assert cliente.nombre == "Otro"


def test_no_se_edita_un_cliente_de_otro_taller(sesion_duena):
    ajeno = fabricas.crear_cliente(fabricas.crear_taller(), nombre="Ajeno")
    url = reverse("pedidos:cliente_editar", args=[ajeno.pk])

    assert sesion_duena.get(url, headers=HTMX).status_code == 404
    respuesta = sesion_duena.post(url, {"nombre": "Cambiado", "tipo": "empresa"}, headers=HTMX)

    assert respuesta.status_code == 404
    ajeno.refresh_from_db()
    assert ajeno.nombre == "Ajeno"


def test_sin_sesion_no_se_crea_nada(client):
    respuesta = client.post(reverse("pedidos:cliente_nuevo"), {"nombre": "X", "tipo": "empresa"})

    assert respuesta.status_code == 302
    assert not Cliente.objects.exists()
