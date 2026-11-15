"""El panel del asistente (T33): abrir, preguntar y empezar de nuevo.

Ninguna prueba llama a Claude. `conversacion.preguntar` (carril B) y
`pagina.contexto_de_pagina` se cambian por unos falsos que cumplen el contrato
(docs/11-plan-tanda-7.md, sección 1.4). La prueba de punta a punta, con el ciclo y las
herramientas de verdad, es la del coordinador (T35).
"""

import logging
from datetime import date

import pytest
from django.utils import timezone

from asistente import conversacion, falso, uso, vistas
from asistente.contratos import Enlace, Resultado, Tarjeta, Uso
from asistente.models import UsoAsistente
from cuentas.models import Usuario
from tests import fabricas
from tests.test_base_visual import Elementos

HTMX = {"HTTP_HX_REQUEST": "true"}
PREGUNTA = "¿Quién me debe plata?"
TEXTO = (
    "Te deben $ 5.790.000 entre 4 clientes:\n\n"
    "La de Ferretería La Esquina es la más urgente.\nNo ha abonado nada."
)


@pytest.fixture
def prendido(settings, taller):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    taller.asistente_limite_mes = 600
    taller.asistente_limite_dia = 40
    taller.save()
    return taller


def _resultado_quien_debe():
    return Resultado(
        datos={"por_cobrar": 5790000},
        revisado="Revisé los saldos de tus pedidos confirmados",
        tarjeta=Tarjeta("quien_debe", "Quién te debe", {"por_cobrar": 5790000, "deudores": []}),
        enlace=Enlace("Ver los pedidos con saldo", "/pedidos/?filtro=saldo"),
    )


class Falsos:
    """El ciclo y la pantalla de mentira. Guarda con qué se llamaron."""

    def __init__(self, monkeypatch, *, texto=TEXTO, estado="ok", cobrada=True, reiniciar=False,
                 resultados=None, uso_=Uso(entrada=1200, salida=80), error=None):
        self.llamadas = []
        self.rutas = []
        self.texto, self.estado, self.cobrada, self.reiniciar = texto, estado, cobrada, reiniciar
        self.resultados = [_resultado_quien_debe()] if resultados is None else resultados
        self.uso, self.error = uso_, error
        self.pedido = None
        monkeypatch.setattr("asistente.conversacion.preguntar", self.preguntar)
        monkeypatch.setattr("asistente.pagina.contexto_de_pagina", self.contexto_de_pagina)

    def contexto_de_pagina(self, taller, ruta):
        self.rutas.append((taller, ruta))
        return f"La dueña está en {ruta or 'Hoy'}.", self.pedido

    def preguntar(self, *, cliente, ctx, mensajes, pregunta, pagina, herramientas=None):
        self.llamadas.append(
            {"cliente": cliente, "ctx": ctx, "mensajes": list(mensajes), "pregunta": pregunta,
             "pagina": pagina}
        )
        if self.error:
            raise self.error
        if self.estado == "ok":
            nuevos = list(mensajes) + [
                {"role": "user", "content": pregunta},
                {"role": "assistant", "content": [{"type": "text", "text": self.texto}]},
            ]
        else:
            nuevos = list(mensajes)
        return conversacion.Respuesta(
            estado=self.estado, texto=self.texto, resultados=self.resultados, uso=self.uso,
            mensajes=nuevos, cobrada=self.cobrada, reiniciar=self.reiniciar,
        )


def _preguntar(cliente_web, pregunta=PREGUNTA, pagina="/", htmx=True):
    extra = HTMX if htmx else {}
    return cliente_web.post("/asistente/preguntar/", {"pregunta": pregunta, "pagina": pagina},
                            **extra)


def _sesion(cliente_web):
    return cliente_web.session.get("asistente")


def _sembrar(cliente_web, turnos, mensajes=None, huella=None):
    sesion = cliente_web.session
    sesion["asistente"] = {
        "huella": huella or vistas.huella(),
        "mensajes": mensajes if mensajes is not None else [{"role": "user", "content": "antes"}],
        "turnos": turnos,
    }
    sesion.save()


def _turno_guardado(pregunta="¿Qué entrego esta semana?", texto="Tienes 3 entregas."):
    return {"pregunta": pregunta, "estado": "ok", "texto": texto, "revisado": [],
            "tarjetas": [], "enlaces": []}


def _preguntas_de_hoy(taller):
    fila = UsoAsistente.objects.filter(taller=taller, fecha=timezone.localdate()).first()
    return fila.preguntas if fila else 0


# --- Quién entra ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "metodo, direccion",
    [("get", "/asistente/"), ("post", "/asistente/preguntar/"), ("post", "/asistente/nueva/")],
)
def test_la_costurera_no_entra(client, costurera, prendido, metodo, direccion):
    client.force_login(costurera)

    assert getattr(client, metodo)(direccion).status_code == 403


@pytest.mark.parametrize(
    "metodo, direccion",
    [("get", "/asistente/"), ("post", "/asistente/preguntar/"), ("post", "/asistente/nueva/")],
)
def test_sin_sesion_lleva_a_entrar(client, prendido, metodo, direccion):
    respuesta = getattr(client, metodo)(direccion)

    assert respuesta.status_code == 302
    assert "/entrar/" in respuesta.url or "login" in respuesta.url


@pytest.mark.parametrize(
    "metodo, direccion",
    [("get", "/asistente/"), ("post", "/asistente/preguntar/"), ("post", "/asistente/nueva/")],
)
def test_sin_clave_no_existe_y_no_sale_el_boton(sesion_duena, prendido, settings, metodo,
                                                direccion):
    settings.ANTHROPIC_API_KEY = ""

    assert getattr(sesion_duena, metodo)(direccion).status_code == 404
    assert "data-asistente-abrir" not in sesion_duena.get("/").text


@pytest.mark.parametrize("campo", ["asistente_limite_mes", "asistente_limite_dia"])
def test_con_limite_0_no_existe_y_no_sale_el_boton(sesion_duena, prendido, campo):
    setattr(prendido, campo, 0)
    prendido.save()

    assert sesion_duena.get("/asistente/").status_code == 404
    assert sesion_duena.post("/asistente/preguntar/", {"pregunta": PREGUNTA}).status_code == 404
    assert "data-asistente-abrir" not in sesion_duena.get("/").text


def test_preguntar_y_nueva_solo_con_post(sesion_duena, prendido):
    assert sesion_duena.get("/asistente/preguntar/").status_code == 405
    assert sesion_duena.get("/asistente/nueva/").status_code == 405
    assert sesion_duena.post("/asistente/").status_code == 405


# --- El panel -------------------------------------------------------------------------------


def test_el_panel_con_htmx_trae_lo_que_espera_app_js(sesion_duena, prendido):
    respuesta = sesion_duena.get("/asistente/", **HTMX)
    html = respuesta.text
    elementos = Elementos(html).elementos

    assert respuesta.status_code == 200
    assert "<html" not in html  # solo lo de adentro del <aside>
    assert [t.name for t in respuesta.templates][0] == "asistente/_panel.html"

    def uno(**atributos):
        encontrados = [e for e in elementos
                       if all(e["atributos"].get(k, "\0") == v for k, v in atributos.items())]
        assert len(encontrados) == 1, atributos
        return encontrados[0]

    titulo = uno(id="asistente-titulo")
    assert titulo["etiqueta"] == "h2" and "Asistente" in titulo["texto"]
    assert "Solo consulta" in html
    mensajes = uno(id="asistente-mensajes")
    assert mensajes["clases"] == ["asistente__mensajes"]
    assert mensajes["atributos"]["aria-live"] == "polite"
    assert uno(**{"data-asistente-cerrar": None})["etiqueta"] == "button"
    formulario = uno(**{"data-asistente-form": None})
    assert formulario["etiqueta"] == "form"
    assert formulario["atributos"]["hx-post"] == "/asistente/preguntar/"
    assert formulario["atributos"]["action"] == "/asistente/preguntar/"
    assert formulario["atributos"]["method"] == "post"
    assert formulario["atributos"]["hx-target"] == "#asistente-pendiente"
    assert formulario["atributos"]["hx-swap"] == "outerHTML"
    assert formulario["atributos"]["hx-disabled-elt"] == "find textarea, find button"
    caja = uno(name="pregunta", id="asistente-pregunta")
    assert caja["etiqueta"] == "textarea" and caja["atributos"]["maxlength"] == "500"
    assert "disabled" not in caja["atributos"]
    assert caja["atributos"]["placeholder"] == "Pregunta algo de tu taller"
    assert uno(name="pagina")["atributos"]["type"] == "hidden"
    # Los dos formularios (la pregunta y "Nueva conversación") llevan su ficha CSRF.
    formularios = html.split("</form>")[:2]
    assert all('name="csrfmiddlewaretoken"' in f for f in formularios)
    assert uno(id="asistente-uso")
    assert uno(**{"data-asistente-bienvenida": None})
    sugerencias = [e for e in elementos if "data-asistente-sugerencia" in e["atributos"]]
    assert [s["texto"] for s in sugerencias] == vistas.SUGERENCIAS
    assert all(s["clases"] == ["chip"] and s["etiqueta"] == "button" for s in sugerencias)
    nueva = uno(id="asistente-nueva")
    assert nueva["atributos"]["hx-post"] == "/asistente/nueva/"
    assert nueva["atributos"]["hx-target"] == "#asistente-mensajes"
    assert uno(**{"aria-label": "Nueva conversación"})["atributos"]["form"] == "asistente-nueva"
    assert "Solo lee tus datos, no cambia nada." in html
    # El aviso del uso va en el pie, encima de la caja.
    assert html.index('id="asistente-uso"') < html.index('id="asistente-pregunta"')
    assert html.index('id="asistente-mensajes"') < html.index("data-asistente-form")


def test_el_panel_copia_la_cabeza_de_la_maqueta(sesion_duena, prendido):
    html = sesion_duena.get("/asistente/", **HTMX).text

    # El avatar es la esfera de Lucy, y es la única que se mueve.
    assert ('<span class="esfera avatar-asistente" data-esfera data-esfera-viva aria-hidden="true">'
            '<canvas class="esfera__lienzo"></canvas></span>Asistente</h2>') in html
    assert "#asistente-cara" not in html
    assert '<span class="etiqueta etiqueta--gris">Solo consulta</span>' in html
    assert "Pregúntame lo que quieras saber de tu taller." in html
    assert "Miro tus pedidos, abonos, telas y gastos, y te contesto con las cifras." in html


def test_sin_javascript_el_panel_es_una_pagina_entera(sesion_duena, prendido):
    respuesta = sesion_duena.get("/asistente/")
    html = respuesta.text

    assert respuesta.status_code == 200
    assert "<html" in html and "<title>Asistente" in html
    assert 'action="/asistente/preguntar/"' in html and 'method="post"' in html
    # Esta página ya es el asistente: sin el botón del encabezado ni el panel de al lado,
    # y la equis vuelve a Hoy.
    assert "data-asistente-abrir" not in html
    assert 'id="asistente"' not in html
    assert "data-asistente-cerrar" not in html
    assert 'aria-label="Cerrar el asistente"' in html


def test_la_caja_de_hoy_sin_javascript_trae_la_pregunta(sesion_duena, prendido):
    html = sesion_duena.get("/asistente/", {"pregunta": "¿Qué tela se está acabando?"}).text

    assert ">¿Qué tela se está acabando?</textarea>" in html


# --- Preguntar ------------------------------------------------------------------------------


def test_una_pregunta_trae_el_texto_la_tarjeta_y_el_enlace(sesion_duena, prendido, monkeypatch):
    falsos = Falsos(monkeypatch)

    respuesta = _preguntar(sesion_duena)
    html = respuesta.text

    assert respuesta.status_code == 200
    assert html.startswith('<div class="asistente__turno">')
    assert f'<div class="mensaje mensaje--usuaria"><p>{PREGUNTA}</p></div>' in html
    assert '<p class="mensaje__consulta"><svg' in html
    assert "Revisé los saldos de tus pedidos confirmados" in html
    assert "asistente/tarjetas/quien_debe.html" in [t.name for t in respuesta.templates]
    assert '<p class="mensaje__enlaces"><a href="/pedidos/?filtro=saldo">Ver los pedidos con saldo</a></p>' in html
    # Primer párrafo, tarjeta, resto (con su salto de línea) y enlaces, en ese orden.
    assert "<p>Te deben $ 5.790.000 entre 4 clientes:</p>" in html
    assert "<p>La de Ferretería La Esquina es la más urgente.<br>No ha abonado nada.</p>" in html
    assert (html.index("mensaje__consulta") < html.index("Te deben")
            < html.index("La de Ferretería") < html.index("mensaje__enlaces"))
    assert len(falsos.llamadas) == 1


def test_la_tarjeta_va_entre_el_primer_parrafo_y_el_resto(sesion_duena, prendido, monkeypatch,
                                                         settings, tmp_path):
    # Las tarjetas de verdad son de los carriles A y C: aquí una de prueba que deja una marca.
    carpeta = tmp_path / "asistente" / "tarjetas"
    carpeta.mkdir(parents=True)
    (carpeta / "marca.html").write_text(
        '<section class="tarjeta mensaje__tarjeta">MARCA {{ tarjeta.titulo }} '
        "{{ tarjeta.datos.total }}</section>", "utf-8"
    )
    plantillas = [{**settings.TEMPLATES[0], "DIRS": [tmp_path, *settings.TEMPLATES[0]["DIRS"]]}]
    settings.TEMPLATES = plantillas
    Falsos(monkeypatch, resultados=[
        Resultado(datos={}, revisado="Revisé", tarjeta=Tarjeta("marca", "<i>Hola</i>", {"total": 7}))
    ])

    html = _preguntar(sesion_duena).text
    recargado = sesion_duena.get("/asistente/", **HTMX).text

    for pagina in (html, recargado):
        assert "MARCA &lt;i&gt;Hola&lt;/i&gt; 7" in pagina
        assert pagina.index("Te deben") < pagina.index("MARCA") < pagina.index("La de Ferretería")


def test_la_vista_le_pasa_a_claude_lo_que_dice_el_contrato(sesion_duena, prendido, duena,
                                                         monkeypatch):
    falsos = Falsos(monkeypatch)
    pedido = fabricas.crear_pedido(prendido)
    falsos.pedido = pedido

    _preguntar(sesion_duena, pagina=f"/pedidos/{pedido.pk}/?pestana=pagos")

    llamada, = falsos.llamadas
    assert falsos.rutas == [(prendido, f"/pedidos/{pedido.pk}/?pestana=pagos")]
    assert llamada["pregunta"] == PREGUNTA
    assert llamada["pagina"] == f"La dueña está en /pedidos/{pedido.pk}/?pestana=pagos."
    assert llamada["mensajes"] == []
    ctx = llamada["ctx"]
    assert ctx.taller == prendido and ctx.usuaria == duena
    assert ctx.hoy == timezone.localdate()
    assert ctx.pedido_actual == pedido
    assert ctx.url_base == "http://testserver/"
    assert isinstance(llamada["cliente"], falso.ClienteProhibido)  # el de los ajustes


def test_la_segunda_pregunta_lleva_el_historial_de_la_primera(sesion_duena, prendido,
                                                             monkeypatch):
    falsos = Falsos(monkeypatch)

    _preguntar(sesion_duena)
    _preguntar(sesion_duena, "¿Y la más urgente?")

    primera, segunda = falsos.llamadas
    assert segunda["mensajes"] == [
        {"role": "user", "content": PREGUNTA},
        {"role": "assistant", "content": [{"type": "text", "text": TEXTO}]},
    ]
    guardada = _sesion(sesion_duena)
    assert guardada["huella"] == vistas.huella()
    assert len(guardada["mensajes"]) == 4
    assert [t["pregunta"] for t in guardada["turnos"]] == [PREGUNTA, "¿Y la más urgente?"]
    assert guardada["turnos"][0]["tarjetas"] == [
        {"tipo": "quien_debe", "titulo": "Quién te debe",
         "datos": {"por_cobrar": 5790000, "deudores": []}}
    ]
    assert guardada["turnos"][0]["enlaces"] == [
        {"texto": "Ver los pedidos con saldo", "url": "/pedidos/?filtro=saldo"}
    ]


def test_las_tarjetas_quedan_en_la_sesion_solo_con_json(sesion_duena, prendido, monkeypatch):
    tarjeta = Tarjeta("entregas", "Entregas", {"desde": date(2026, 11, 16), "lista": [1, 2]})
    Falsos(monkeypatch, resultados=[Resultado(datos={}, revisado="Revisé", tarjeta=tarjeta)])

    assert _preguntar(sesion_duena).status_code == 200

    guardada = _sesion(sesion_duena)["turnos"][0]["tarjetas"][0]
    assert guardada["datos"] == {"desde": "2026-11-16", "lista": [1, 2]}


def test_consultas_y_enlaces_repetidos_salen_una_vez(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch, resultados=[_resultado_quien_debe(), _resultado_quien_debe()])

    html = _preguntar(sesion_duena).text

    assert html.count("Revisé los saldos de tus pedidos confirmados") == 1
    assert html.count("Ver los pedidos con saldo") == 1


def test_una_tarjeta_sin_plantilla_no_tumba_el_panel(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch, resultados=[
        Resultado(datos={}, revisado="Revisé", tarjeta=Tarjeta("no_existe", "Nada", {}))
    ])

    respuesta = _preguntar(sesion_duena)

    assert respuesta.status_code == 200
    assert "Te deben" in respuesta.text


def test_el_texto_de_claude_y_la_pregunta_salen_escapados(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch, texto="<b>x</b><script>alert(1)</script>\n\n<img src=x onerror=alert(2)>")

    html = _preguntar(sesion_duena, "<script>alert(3)</script>").text
    recargado = sesion_duena.get("/asistente/", **HTMX).text

    for pagina in (html, recargado):
        assert "<script>" not in pagina and "<b>x</b>" not in pagina and "<img" not in pagina
        assert "&lt;b&gt;x&lt;/b&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in pagina
        assert "&lt;img src=x onerror=alert(2)&gt;" in pagina
        assert "&lt;script&gt;alert(3)&lt;/script&gt;" in pagina


def test_las_plantillas_del_asistente_no_marcan_nada_como_seguro():
    from pathlib import Path

    carpeta = Path(vistas.__file__).parent / "templates" / "asistente"
    for archivo in carpeta.glob("*.html"):
        texto = archivo.read_text("utf-8")
        assert "|safe" not in texto and "autoescape off" not in texto, archivo.name
    assert "mark_safe" not in Path(vistas.__file__).read_text("utf-8")


def test_preguntar_devuelve_el_turno_y_el_aviso_con_hx_swap_oob(sesion_duena, prendido,
                                                               monkeypatch):
    Falsos(monkeypatch)

    html = _preguntar(sesion_duena).text

    assert html.count('<div class="asistente__turno">') == 1
    assert '<div id="asistente-uso" hx-swap-oob="true"></div>' in html  # todo bien: vacío
    assert html.index("asistente__turno") < html.index("hx-swap-oob")


def test_con_pocas_preguntas_sale_la_linea_ambar(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch)
    fabricas.crear_uso(prendido, preguntas=35)

    html = _preguntar(sesion_duena).text  # con esta van 36: quedan 4

    assert ('<div id="asistente-uso" hx-swap-oob="true"><p class="aviso asistente__uso">'
            "Te quedan 4 preguntas por hoy. Mañana vuelves a tener 40.</p></div>") in html
    assert "Te quedan 4 preguntas por hoy." in sesion_duena.get("/asistente/", **HTMX).text


def test_cada_pregunta_cuenta_y_anota_sus_tokens(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch, uso_=Uso(entrada=1200, salida=80, cache_escritura=50, cache_lectura=3200))

    _preguntar(sesion_duena)

    fila = UsoAsistente.objects.get(taller=prendido)
    assert fila.preguntas == 1
    assert (fila.tokens_entrada, fila.tokens_salida) == (1200, 80)
    assert (fila.tokens_cache_escritura, fila.tokens_cache_lectura) == (50, 3200)


def test_el_panel_recargado_pinta_los_turnos_guardados(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch)
    _preguntar(sesion_duena)

    respuesta = sesion_duena.get("/asistente/", **HTMX)
    html = respuesta.text

    assert "data-asistente-bienvenida" not in html
    assert html.count('<div class="asistente__turno">') == 1
    assert PREGUNTA in html and "<p>Te deben $ 5.790.000 entre 4 clientes:</p>" in html
    assert "Revisé los saldos de tus pedidos confirmados" in html
    assert "Ver los pedidos con saldo" in html
    assert "asistente/tarjetas/quien_debe.html" in [t.name for t in respuesta.templates]


def test_sin_javascript_la_pregunta_vuelve_a_la_pagina(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch)

    respuesta = _preguntar(sesion_duena, htmx=False)

    assert respuesta.status_code == 302 and respuesta.url == "/asistente/"
    assert "Te deben $ 5.790.000" in sesion_duena.get("/asistente/").text


def test_sin_javascript_una_sugerencia_es_la_pregunta(sesion_duena, prendido, monkeypatch):
    falsos = Falsos(monkeypatch)

    # El botón de la sugerencia manda su texto; la caja va vacía después.
    sesion_duena.post("/asistente/preguntar/",
                      {"pregunta": ["¿Qué entrego esta semana?", ""], "pagina": ""})

    assert falsos.llamadas[0]["pregunta"] == "¿Qué entrego esta semana?"


# --- Lo que no llega a Claude ---------------------------------------------------------------


@pytest.mark.parametrize("pregunta, aviso", [
    ("", vistas.PREGUNTA_VACIA),
    ("   \n ", vistas.PREGUNTA_VACIA),
    ("a" * 501, vistas.PREGUNTA_LARGA),
])
def test_pregunta_vacia_o_muy_larga_da_un_aviso_sin_llamar_a_claude(
    sesion_duena, prendido, monkeypatch, settings, pregunta, aviso
):
    claude = falso.instalar(monkeypatch, settings, [])
    falsos = Falsos(monkeypatch)

    respuesta = _preguntar(sesion_duena, pregunta)

    assert respuesta.status_code == 200
    assert f'<p class="aviso">{aviso}</p>' in respuesta.text
    assert 'class="asistente__turno"' in respuesta.text
    assert claude.llamadas == [] and falsos.llamadas == []
    assert _preguntas_de_hoy(prendido) == 0
    assert _sesion(sesion_duena) is None


def test_una_pregunta_de_500_si_pasa(sesion_duena, prendido, monkeypatch):
    falsos = Falsos(monkeypatch)

    _preguntar(sesion_duena, "a" * 500)

    assert len(falsos.llamadas) == 1


def test_sin_preguntas_del_dia_contesta_el_limite_sin_llamar_a_claude(
    sesion_duena, prendido, monkeypatch, settings
):
    claude = falso.instalar(monkeypatch, settings, [])
    falsos = Falsos(monkeypatch)
    fabricas.crear_uso(prendido, preguntas=40)

    respuesta = _preguntar(sesion_duena)
    html = respuesta.text

    assert respuesta.status_code == 200
    assert claude.llamadas == [] and falsos.llamadas == []
    assert '<p class="mensaje__limite"><svg' in html and "#reloj" in html
    assert "Por hoy ya usaste las 40 preguntas. Mañana vuelvo a contestar." in html
    assert f"<p>{PREGUNTA}</p>" in html
    assert _preguntas_de_hoy(prendido) == 40
    # La caja se apaga sin recargar (y al recargar sigue apagada).
    caja = html[html.index('id="asistente-caja"'):]
    assert 'hx-swap-oob="true"' in caja[:80]
    assert 'placeholder="Vuelvo a contestar mañana" disabled' in caja
    assert _sesion(sesion_duena) is None


def test_sin_preguntas_el_panel_tiene_la_caja_apagada(sesion_duena, prendido):
    fabricas.crear_uso(prendido, preguntas=40)

    html = sesion_duena.get("/asistente/", **HTMX).text

    assert 'placeholder="Vuelvo a contestar mañana" disabled' in html
    assert 'class="boton boton--principal boton--icono asistente__enviar" disabled' in html
    assert "aviso asistente__uso" not in html  # sin preguntas no es "quedan pocas"


def test_sin_preguntas_del_mes_dice_cuando_vuelve(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch)
    hoy = timezone.localdate()
    fabricas.crear_uso(prendido, fecha=hoy.replace(day=1), preguntas=600 if hoy.day > 1 else 0)
    if hoy.day == 1:
        UsoAsistente.objects.filter(taller=prendido).update(preguntas=600)
    vuelve = uso.cupo(prendido).vuelve_el

    html = _preguntar(sesion_duena).text
    panel = sesion_duena.get("/asistente/", **HTMX).text

    from config.piezas import dia_y_mes

    assert (f"Este mes ya usaste las 600 preguntas. Vuelvo a contestar el {dia_y_mes(vuelve)}."
            in html)
    assert f'placeholder="Vuelvo a contestar el {dia_y_mes(vuelve)}" disabled' in panel


def test_la_ultima_pregunta_del_dia_apaga_la_caja(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch)
    fabricas.crear_uso(prendido, preguntas=39)

    html = _preguntar(sesion_duena).text

    assert "Te deben $ 5.790.000" in html  # esta sí se contesta
    assert 'id="asistente-caja" hx-swap-oob="true"' in html
    assert 'placeholder="Vuelvo a contestar mañana" disabled' in html


# --- Cuando algo sale mal -------------------------------------------------------------------


def test_si_el_servicio_falla_sale_el_mensaje_amable_y_la_sesion_no_cambia(
    sesion_duena, prendido, monkeypatch
):
    _sembrar(sesion_duena, [_turno_guardado()])
    antes = _sesion(sesion_duena)
    Falsos(monkeypatch, texto=conversacion.MENSAJE_SIN_SERVICIO, estado="error", cobrada=False,
           resultados=[], uso_=Uso())

    respuesta = _preguntar(sesion_duena)

    assert respuesta.status_code == 200
    assert "<p>No pude contestar ahora. Intenta de nuevo en un rato.</p>" in respuesta.text
    assert _sesion(sesion_duena) == antes
    assert _preguntas_de_hoy(prendido) == 0  # no se cobró: la pregunta se devolvió
    # Al recargar no queda: Claude tampoco la recuerda.
    assert "No pude contestar ahora" not in sesion_duena.get("/asistente/", **HTMX).text


def test_un_error_que_si_se_cobro_cuenta_la_pregunta(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch, texto=conversacion.MENSAJE_SIN_SERVICIO, estado="error", cobrada=True,
           resultados=[], uso_=Uso(entrada=900))

    _preguntar(sesion_duena)

    assert _preguntas_de_hoy(prendido) == 1
    assert UsoAsistente.objects.get(taller=prendido).tokens_entrada == 900
    assert _sesion(sesion_duena) is None


@pytest.mark.parametrize("estado", ["rechazo", "cortado"])
def test_rechazo_y_cortada_se_muestran_pero_no_se_guardan(sesion_duena, prendido, monkeypatch,
                                                          estado):
    _sembrar(sesion_duena, [_turno_guardado()])
    antes = _sesion(sesion_duena)
    Falsos(monkeypatch, texto="Solo sé de tu taller.", estado=estado, resultados=[])

    html = _preguntar(sesion_duena).text

    assert "<p>Solo sé de tu taller.</p>" in html
    assert _sesion(sesion_duena) == antes


def test_si_el_ciclo_se_rompe_tambien_sale_el_mensaje_amable(sesion_duena, prendido,
                                                            monkeypatch, caplog):
    Falsos(monkeypatch, error=RuntimeError(f"algo con {PREGUNTA}"))

    with caplog.at_level(logging.INFO, logger="asistente"):
        respuesta = _preguntar(sesion_duena)

    assert respuesta.status_code == 200
    assert "No pude contestar ahora. Intenta de nuevo en un rato." in respuesta.text
    assert _preguntas_de_hoy(prendido) == 0
    assert "RuntimeError" in caplog.text and PREGUNTA not in caplog.text


def test_si_el_historial_ya_no_sirve_se_borra_la_conversacion(sesion_duena, prendido,
                                                             monkeypatch):
    _sembrar(sesion_duena, [_turno_guardado()])
    Falsos(monkeypatch, texto="Empecemos de nuevo.", estado="error", reiniciar=True,
           resultados=[])

    html = _preguntar(sesion_duena).text

    assert "Empecemos de nuevo." in html
    assert _sesion(sesion_duena) is None


# --- Nueva conversación, huella y conversación larga ----------------------------------------


def test_nueva_conversacion_borra(sesion_duena, prendido, monkeypatch):
    Falsos(monkeypatch)
    _preguntar(sesion_duena)

    respuesta = sesion_duena.post("/asistente/nueva/", **HTMX)

    assert respuesta.status_code == 200
    assert "data-asistente-bienvenida" in respuesta.text
    assert "asistente__turno" not in respuesta.text
    assert "<html" not in respuesta.text and "asistente__cabeza" not in respuesta.text
    assert _sesion(sesion_duena) is None
    assert "data-asistente-bienvenida" in sesion_duena.get("/asistente/", **HTMX).text


def test_nueva_conversacion_sin_javascript_vuelve_a_la_pagina(sesion_duena, prendido):
    _sembrar(sesion_duena, [_turno_guardado()])

    respuesta = sesion_duena.post("/asistente/nueva/")

    assert respuesta.status_code == 302 and respuesta.url == "/asistente/"
    assert _sesion(sesion_duena) is None


def test_si_cambio_la_huella_empieza_una_conversacion_nueva(sesion_duena, prendido,
                                                           monkeypatch):
    _sembrar(sesion_duena, [_turno_guardado()], huella="de-un-despliegue-anterior")
    falsos = Falsos(monkeypatch)

    assert "data-asistente-bienvenida" in sesion_duena.get("/asistente/", **HTMX).text
    _preguntar(sesion_duena)

    assert falsos.llamadas[0]["mensajes"] == []
    assert _sesion(sesion_duena)["huella"] == vistas.huella()
    assert len(_sesion(sesion_duena)["turnos"]) == 1


def test_la_huella_cambia_con_el_modelo_las_instrucciones_y_las_herramientas(settings,
                                                                           monkeypatch):
    original = vistas.huella()

    settings.ASISTENTE_MODELO = "otro-modelo"
    assert vistas.huella() != original
    settings.ASISTENTE_MODELO = "claude-opus-5-5"
    assert vistas.huella() == original

    monkeypatch.setattr("asistente.instrucciones.INSTRUCCIONES", "otras instrucciones")
    assert vistas.huella() != original
    monkeypatch.undo()

    from asistente import esquemas

    monkeypatch.setattr(esquemas, "ESQUEMAS", esquemas.ESQUEMAS[:-1])
    assert vistas.huella() != original


def test_con_mas_de_25_turnos_pide_una_conversacion_nueva(sesion_duena, prendido, monkeypatch,
                                                         settings):
    _sembrar(sesion_duena, [_turno_guardado() for _ in range(26)])
    claude = falso.instalar(monkeypatch, settings, [])
    falsos = Falsos(monkeypatch)

    panel = sesion_duena.get("/asistente/", **HTMX).text
    html = _preguntar(sesion_duena).text

    for pagina in (panel, html):
        assert vistas.MUY_LARGA in pagina
        assert '<button type="submit" form="asistente-nueva" class="chip">' in pagina
    assert claude.llamadas == [] and falsos.llamadas == []
    assert _preguntas_de_hoy(prendido) == 0


def test_con_25_turnos_todavia_se_puede_y_la_26_pide_nueva(sesion_duena, prendido,
                                                          monkeypatch):
    _sembrar(sesion_duena, [_turno_guardado() for _ in range(25)])
    falsos = Falsos(monkeypatch)

    assert vistas.MUY_LARGA not in sesion_duena.get("/asistente/", **HTMX).text
    html = _preguntar(sesion_duena).text

    assert len(falsos.llamadas) == 1
    assert "Te deben" in html and vistas.MUY_LARGA in html
    assert html.index("Te deben") < html.index(vistas.MUY_LARGA)


def test_con_mas_de_200_kb_pide_una_conversacion_nueva(sesion_duena, prendido, monkeypatch):
    _sembrar(sesion_duena, [_turno_guardado()],
             mensajes=[{"role": "user", "content": "x" * (200 * 1024)}])
    falsos = Falsos(monkeypatch)

    assert vistas.MUY_LARGA in sesion_duena.get("/asistente/", **HTMX).text
    assert vistas.MUY_LARGA in _preguntar(sesion_duena).text
    assert falsos.llamadas == []


# --- Cada una con lo suyo -------------------------------------------------------------------


def test_la_conversacion_de_una_duena_no_la_ve_otra(client, prendido, monkeypatch, settings):
    from django.test import Client

    Falsos(monkeypatch)
    otro_taller = fabricas.crear_taller(asistente_limite_mes=600, asistente_limite_dia=40)
    una = fabricas.crear_usuaria(prendido, rol=Usuario.Rol.DUENA)
    otra = fabricas.crear_usuaria(otro_taller, rol=Usuario.Rol.DUENA)
    misma = fabricas.crear_usuaria(prendido, rol=Usuario.Rol.DUENA)
    client.force_login(una)
    _preguntar(client)

    for usuaria in (otra, misma):
        navegador = Client()
        navegador.force_login(usuaria)
        html = navegador.get("/asistente/", **HTMX).text
        assert "data-asistente-bienvenida" in html and PREGUNTA not in html
    # Y la pregunta cuenta para el taller de quien preguntó.
    assert _preguntas_de_hoy(prendido) == 1 and _preguntas_de_hoy(otro_taller) == 0


def test_el_registro_no_guarda_el_texto_de_la_pregunta(sesion_duena, prendido, monkeypatch,
                                                       caplog):
    Falsos(monkeypatch, uso_=Uso(entrada=1234, salida=56))

    with caplog.at_level(logging.INFO, logger="asistente"):
        _preguntar(sesion_duena, "¿Cuánto le debe Colegio Nuevo Amanecer?")

    assert caplog.records
    assert "Colegio Nuevo Amanecer" not in caplog.text and "Cuánto" not in caplog.text
    assert "Te deben" not in caplog.text
    registro = caplog.records[-1].getMessage()
    assert f"taller={prendido.pk}" in registro
    assert "estado=ok" in registro and "cobrada=True" in registro
    assert "entrada=1234" in registro and "salida=56" in registro


def test_el_registro_del_limite_tampoco_tiene_el_texto(sesion_duena, prendido, monkeypatch,
                                                       caplog):
    Falsos(monkeypatch)
    fabricas.crear_uso(prendido, preguntas=40)

    with caplog.at_level(logging.INFO, logger="asistente"):
        _preguntar(sesion_duena, "¿Cuánto le debe Colegio Nuevo Amanecer?")

    assert "sin cupo" in caplog.text and "Colegio" not in caplog.text


# --- Sin preguntas: el aviso va en la conversación, como diseno/asistente-limite.html ---------


def test_sin_preguntas_el_panel_muestra_el_aviso_en_vez_de_las_sugerencias(sesion_duena, prendido):
    fabricas.crear_uso(prendido, preguntas=40)

    html = sesion_duena.get("/asistente/", **HTMX).content.decode()

    assert '<p class="mensaje__limite">' in html
    assert "Por hoy ya usaste las 40 preguntas. Mañana vuelvo a contestar." in html
    assert "data-asistente-bienvenida" not in html
    assert "data-asistente-sugerencia" not in html


def test_sin_preguntas_el_aviso_va_al_final_de_la_conversacion(sesion_duena, prendido):
    _sembrar(sesion_duena, [_turno_guardado()])
    fabricas.crear_uso(prendido, preguntas=40)

    html = sesion_duena.get("/asistente/", **HTMX).content.decode()

    assert html.index("Tienes 3 entregas.") < html.index('<p class="mensaje__limite">')


def test_nueva_conversacion_sin_preguntas_muestra_el_aviso(sesion_duena, prendido):
    fabricas.crear_uso(prendido, preguntas=40)

    html = sesion_duena.post("/asistente/nueva/", **HTMX).content.decode()

    assert '<p class="mensaje__limite">' in html
    assert "data-asistente-sugerencia" not in html


def test_el_navegador_nunca_guarda_el_panel(sesion_duena, prendido):
    # El panel cambia con cada pregunta y trae datos del taller: siempre se pide de nuevo.
    respuesta = sesion_duena.get("/asistente/", **HTMX)

    assert "no-store" in respuesta["Cache-Control"]
