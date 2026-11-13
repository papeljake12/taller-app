"""El esqueleto de la tanda 2: cada sección del menú abre su pantalla y ninguna dirección
deja ver o tocar lo de otro taller.

La prueba de aislamiento recorre sola todas las direcciones que reciben un número (pedido,
cliente, tela...). Si un carril agrega una dirección nueva con número, entra aquí sin
hacer nada; si es de un modelo nuevo, hay que decir cuál en MODELO_DE_LA_DIRECCION.
"""

import pytest
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from tests import fabricas

pytestmark = pytest.mark.django_db

PANTALLAS = [
    "pedidos:hoy",
    "pedidos:lista",
    "pedidos:buscar",
    "pedidos:calendario",
    "pedidos:clientes",
    "cotizador:inicio",
    "telas:inicio",
    "finanzas:resumen",
    "cuentas:mi_taller",
]

VENTANAS = ["pedidos:nuevo", "pedidos:cliente_nuevo", "telas:nueva"]


@pytest.mark.parametrize("nombre", PANTALLAS + VENTANAS)
def test_cada_pantalla_abre_para_la_duena(sesion_duena, nombre):
    assert sesion_duena.get(reverse(nombre)).status_code == 200


@pytest.mark.parametrize("nombre", PANTALLAS + VENTANAS)
def test_sin_sesion_cada_pantalla_lleva_a_entrar(client, nombre):
    respuesta = client.get(reverse(nombre))

    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/entrar/")


def test_el_pedido_por_dentro_abre_con_sus_partes(sesion_duena, taller):
    pedido = fabricas.crear_pedido(taller, detalle="12 vestidos de fantasía")

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert pedido.cliente.nombre in html
    for titulo in ("Etapa", "Tallas", "Materiales", "Pagos", "Entrega", "Cliente"):
        assert f">{titulo}</h2>" in html, titulo


def test_hoy_reune_sus_partes_en_el_orden_del_diseno(sesion_duena):
    html = sesion_duena.get("/").text
    titulos = ["Qué hacer hoy", "Trabajos del taller", "Cobrado y gastado por mes",
               "Quién te debe", "Pedidos por etapa"]

    posiciones = [html.index(f">{t}</h2>") for t in titulos]

    assert posiciones == sorted(posiciones)
    # En celular: qué hacer hoy, quién te debe, trabajos, gráfica y etapas.
    for orden in range(1, 6):
        assert f"orden-celular-{orden}" in html


def test_el_menu_lleva_a_cada_seccion(sesion_duena):
    html = sesion_duena.get("/").text

    for nombre in PANTALLAS:
        if nombre not in ("pedidos:buscar",):
            assert f'href="{reverse(nombre)}"' in html, nombre
    assert 'aria-disabled="true"' not in html


def test_el_buscador_del_menu_lleva_a_los_resultados(sesion_duena):
    html = sesion_duena.get("/").text

    assert f'action="{reverse("pedidos:buscar")}"' in html
    assert 'name="q"' in html
    assert "«overoles»" in sesion_duena.get(reverse("pedidos:buscar"), {"q": "overoles"}).text


def test_la_ventana_con_htmx_trae_solo_su_contenido(sesion_duena):
    url = reverse("pedidos:nuevo")

    ventana = sesion_duena.get(url, headers={"HX-Request": "true"}).text
    pagina = sesion_duena.get(url).text

    assert "<html" not in ventana and "ventana__cabeza" in ventana
    assert "data-cerrar-ventana" in ventana
    # Como página, el título va una sola vez (el de la hoja), sin la X que no cierra nada,
    # y "Cancelar" es un enlace de verdad (T23).
    assert "<html" in pagina and "<h1>Nuevo pedido</h1>" in pagina
    assert "ventana__cabeza" not in pagina and "data-cerrar-ventana" not in pagina
    assert f'<a class="boton" href="{reverse("pedidos:lista")}">Cancelar</a>' in pagina


def test_cada_pantalla_trae_la_ventana_y_el_boton_nuevo_pedido_la_abre(sesion_duena):
    html = sesion_duena.get("/").text

    assert '<dialog class="ventana" id="ventana"' in html
    assert f'hx-get="{reverse("pedidos:nuevo")}" hx-target="#ventana"' in html


def test_el_formulario_publico_abre_sin_sesion_y_sin_menu(client, taller):
    pedido = fabricas.crear_pedido(taller)

    respuesta = client.get(reverse("pedidos:publico_tallas", args=[pedido.token_tallas]))

    assert respuesta.status_code == 200
    assert 'class="menu"' not in respuesta.text
    assert str(pedido.total) not in respuesta.text


def test_un_enlace_publico_inventado_responde_404(client):
    assert client.get(reverse("pedidos:publico_tallas", args=["inventado"])).status_code == 404


# --- Ninguna dirección con número deja ver o tocar lo de otro taller -------------------------

# Qué se busca con el número `pk` de cada dirección. Las que no están aquí son de un pedido.
MODELO_DE_LA_DIRECCION = {
    "pedidos:cliente_editar": "cliente",
    "cotizador:prenda_quitar": "prenda",
    "telas:movimiento": "tela",
    "telas:quitar": "tela",
    "finanzas:gasto_quitar": "gasto",
    "cuentas:costurera_editar": "usuaria",
}
# Direcciones con número que no son de un taller (el enlace público usa un token).
SIN_TALLER = {"pedidos:publico_tallas"}


def direcciones_con_numero(resolver=None, prefijo=""):
    resolver = resolver or get_resolver()
    nombres = []
    for patron in resolver.url_patterns:
        if isinstance(patron, URLResolver):
            if patron.namespace == "admin":
                continue
            espacio = f"{prefijo}{patron.namespace}:" if patron.namespace else prefijo
            nombres += direcciones_con_numero(patron, espacio)
        elif isinstance(patron, URLPattern) and "pk" in patron.pattern.converters:
            nombres.append(f"{prefijo}{patron.name}")
    return nombres


def test_hay_direcciones_con_numero_para_revisar():
    nombres = direcciones_con_numero()

    assert {"pedidos:detalle", "pedidos:abono_quitar", "telas:quitar"} <= set(nombres)


def registro_de_otro_taller(tipo, otro):
    if tipo == "cliente":
        return fabricas.crear_cliente(otro)
    if tipo == "prenda":
        return fabricas.crear_prenda(otro)
    if tipo == "tela":
        return fabricas.crear_tela(otro)
    if tipo == "gasto":
        return fabricas.crear_gasto(otro)
    if tipo == "usuaria":
        return fabricas.crear_usuaria(otro, rol="costurera")
    return fabricas.crear_pedido(otro)


@pytest.mark.parametrize("nombre", [n for n in direcciones_con_numero() if n not in SIN_TALLER])
def test_con_el_numero_de_otro_taller_responde_404(sesion_duena, nombre):
    otro = fabricas.crear_taller()
    ajeno = registro_de_otro_taller(MODELO_DE_LA_DIRECCION.get(nombre, "pedido"), otro)
    patron = str(_patron(nombre))
    argumentos = {"pk": ajeno.pk}
    for parametro in ("abono", "talla", "material"):
        if f"<int:{parametro}>" in patron:
            argumentos[parametro] = 1
    if "<str:accion>" in patron:
        argumentos["accion"] = "listo"
    url = reverse(nombre, kwargs=argumentos)

    respuestas = {sesion_duena.get(url).status_code, sesion_duena.post(url).status_code}

    # 404 por la forma que acepta; 405 ("método no permitido") por la otra, si la hay.
    assert 404 in respuestas
    assert respuestas <= {404, 405}


def _patron(nombre):
    espacio, corto = nombre.split(":")
    for patron in get_resolver().url_patterns:
        if isinstance(patron, URLResolver) and patron.namespace == espacio:
            for hijo in patron.url_patterns:
                if getattr(hijo, "name", None) == corto:
                    return hijo.pattern
    raise LookupError(nombre)
