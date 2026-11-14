"""El ciclo de una pregunta (T29): herramientas, historial, caché, esfuerzo, plazos y errores.

Claude es el cliente falso (asistente/falso.py) con un guion. Las herramientas de verdad
todavía son de otros carriles, así que cada prueba pone en `herramientas.REGISTRO` una
herramienta de mentira que devuelve un `Resultado` (y anota con qué la llamaron).
"""

import json
from datetime import date

import anthropic
import httpx2
import pytest

from asistente import conversacion, esfuerzo, falso, herramientas
from asistente.contratos import Contexto, ErrorDeHerramienta, Resultado, Tarjeta, Uso
from asistente.conversacion import (
    CONTESTA_YA,
    MENSAJE_CORTADO,
    MENSAJE_RECHAZO,
    MENSAJE_SIN_SERVICIO,
    preguntar,
)
from asistente.esquemas import ESQUEMAS
from asistente.instrucciones import INSTRUCCIONES
from config.piezas import fecha_larga
from tests import fabricas

HOY = date(2026, 11, 14)  # un sábado
PANTALLA = "Pantalla actual: Hoy."

# Un historial de una pregunta anterior, como lo guarda la vista en la sesión.
ANTERIOR = [
    {"role": "user", "content": "¿Qué entrego esta semana?"},
    {"role": "system", "content": "Hoy es viernes, 13 de noviembre de 2026. Taller: X."},
    {"role": "assistant", "content": [{"type": "text", "text": "Tienes dos entregas."}]},
]


def contexto_de(taller, pedido=None):
    return Contexto(
        taller=taller,
        usuaria=None,
        hoy=HOY,
        pedido_actual=pedido,
        url_base="http://testserver/",
    )


@pytest.fixture
def ctx(taller):
    return contexto_de(taller)


@pytest.fixture
def llamadas_a_herramientas():
    return []


@pytest.fixture
def herramienta(monkeypatch, llamadas_a_herramientas):
    """Pone herramientas de mentira en el registro. Devuelve con qué se llamó cada una."""

    def poner(nombre, datos=None, error=None):
        def de_mentira(ctx, **entrada):
            llamadas_a_herramientas.append((nombre, entrada, ctx))
            if error is not None:
                raise ErrorDeHerramienta(error)
            return Resultado(
                datos=datos if datos is not None else {"herramienta": nombre},
                revisado=f"Revisé {nombre}",
                tarjeta=Tarjeta(tipo=nombre, titulo=nombre, datos={}),
            )

        monkeypatch.setitem(herramientas.REGISTRO, nombre, de_mentira)
        return de_mentira

    return poner


def hacer(ctx, guion, monkeypatch, settings, pregunta="¿Quién me debe plata?", mensajes=None,
          pagina=PANTALLA, **otros):
    claude = falso.instalar(monkeypatch, settings, guion)
    respuesta = preguntar(
        cliente=claude,
        ctx=ctx,
        mensajes=list(ANTERIOR) if mensajes is None else mensajes,
        pregunta=pregunta,
        pagina=pagina,
        **otros,
    )
    return claude, respuesta


def peticion():
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def respuesta_http(codigo):
    return httpx2.Response(codigo, request=peticion())


def _de_estado(clase, codigo):
    return lambda: clase("falló", response=respuesta_http(codigo), body=None)


# Cada error de la librería: (cómo se fabrica, si la vista debe borrar la conversación).
ERRORES_DEL_SDK = {
    "400": (_de_estado(anthropic.BadRequestError, 400), True),
    "429": (_de_estado(anthropic.RateLimitError, 429), False),
    "500": (_de_estado(anthropic.InternalServerError, 500), False),
    "529": (_de_estado(anthropic.APIStatusError, 529), False),
    "conexion": (lambda: anthropic.APIConnectionError(request=peticion()), False),
    "tiempo": (lambda: anthropic.APITimeoutError(request=peticion()), False),
}


# --- Herramientas ---------------------------------------------------------------------------


def test_una_herramienta_se_corre_y_la_segunda_llamada_lleva_su_resultado(
    ctx, herramienta, monkeypatch, settings, llamadas_a_herramientas
):
    herramienta("quien_debe", datos={"por_cobrar": 5_790_000, "deudores": []})
    claude, r = hacer(
        ctx,
        [falso.usa(("quien_debe", {}, "toolu_1")), falso.texto("Te deben $ 5.790.000.")],
        monkeypatch,
        settings,
    )

    assert len(claude.llamadas) == 2
    assert claude.llamadas[1]["mensajes"][-1] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_1",
                "content": json.dumps(
                    {"por_cobrar": 5_790_000, "deudores": []}, ensure_ascii=False, sort_keys=True
                ),
            }
        ],
    }
    assert llamadas_a_herramientas[0][:2] == ("quien_debe", {})
    assert llamadas_a_herramientas[0][2] is ctx
    assert r.estado == "ok"
    assert r.texto == "Te deben $ 5.790.000."
    assert [x.revisado for x in r.resultados] == ["Revisé quien_debe"]
    assert r.cobrada is True
    assert r.reiniciar is False


def test_el_resultado_va_en_json_con_tildes_y_claves_ordenadas(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("telas", datos={"telas": [{"nombre": "Algodón"}], "cantidad": 1})
    claude, _ = hacer(
        ctx,
        [falso.usa(("telas", {"solo_bajas": True}, "toolu_1")), falso.texto("Listo.")],
        monkeypatch,
        settings,
    )

    contenido = claude.llamadas[1]["mensajes"][-1]["content"][0]["content"]
    assert contenido == '{"cantidad": 1, "telas": [{"nombre": "Algodón"}]}'


def test_dos_herramientas_a_la_vez_vuelven_en_un_solo_mensaje(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    herramienta("telas")
    claude, r = hacer(
        ctx,
        [
            falso.usa(("quien_debe", {}, "toolu_a"), ("telas", {"solo_bajas": False}, "toolu_b")),
            falso.texto("Te deben y hay telas."),
        ],
        monkeypatch,
        settings,
    )

    mensajes = claude.llamadas[1]["mensajes"]
    # Después del assistant que pidió las dos, un único mensaje user con los dos resultados.
    assert mensajes[-2]["role"] == "assistant"
    assert mensajes[-1]["role"] == "user"
    assert [b["tool_use_id"] for b in mensajes[-1]["content"]] == ["toolu_a", "toolu_b"]
    assert all(b["type"] == "tool_result" for b in mensajes[-1]["content"])
    assert [x.revisado for x in r.resultados] == ["Revisé quien_debe", "Revisé telas"]


def test_un_error_de_herramienta_va_con_is_error_y_el_ciclo_sigue(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("ver_pedido", error="No encontré ese pedido.")
    herramienta("quien_debe")
    claude, r = hacer(
        ctx,
        [
            falso.usa(("ver_pedido", {"pedido_id": 999}, "toolu_1"), ("quien_debe", {}, "toolu_2")),
            falso.texto("No encontré ese pedido, pero te cuento quién debe."),
        ],
        monkeypatch,
        settings,
    )

    resultados = claude.llamadas[1]["mensajes"][-1]["content"]
    assert resultados[0] == {
        "type": "tool_result",
        "tool_use_id": "toolu_1",
        "content": "No encontré ese pedido.",
        "is_error": True,
    }
    assert "is_error" not in resultados[1]
    assert r.estado == "ok"
    # Solo cuentan las que funcionaron.
    assert [x.revisado for x in r.resultados] == ["Revisé quien_debe"]


def test_una_herramienta_que_no_existe_o_una_entrada_mala_tambien_vuelven_como_error(
    ctx, monkeypatch, settings
):
    claude, r = hacer(
        ctx,
        [
            falso.usa(("borrar_todo", {}, "toolu_1"), ("telas", {"solo_bajas": "si"}, "toolu_2")),
            falso.texto("No puedo."),
        ],
        monkeypatch,
        settings,
    )

    resultados = claude.llamadas[1]["mensajes"][-1]["content"]
    assert [b["is_error"] for b in resultados] == [True, True]
    assert "borrar_todo" in resultados[0]["content"]
    assert r.estado == "ok"
    assert r.resultados == []


# --- Historial solo-agregar y caché ---------------------------------------------------------


def test_los_thinking_vuelven_identicos_y_el_prefijo_nunca_cambia(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    herramienta("buscar_pedidos")
    primera = falso.usa(("quien_debe", {}, "toolu_1"))
    segunda = falso.usa(
        (
            "buscar_pedidos",
            {"texto": None, "filtro": "saldo", "entrega_desde": None, "entrega_hasta": None},
            "toolu_2",
        ),
        pensamiento_antes=False,
        texto_antes="Miro también los pedidos.",
    )
    tercera = falso.texto("Te deben en tres pedidos.")
    claude, r = hacer(ctx, [primera, segunda, tercera], monkeypatch, settings)

    enviados = [llamada["mensajes"] for llamada in claude.llamadas]
    # Cada llamada empieza exactamente con todo lo que se mandó en la anterior.
    for antes, despues in zip(enviados, enviados[1:]):
        assert despues[: len(antes)] == antes
    # La conversación anterior quedó intacta y en su lugar.
    assert enviados[0][: len(ANTERIOR)] == ANTERIOR
    # Lo que contestó Claude vuelve tal cual, con su bloque thinking y su firma.
    assert enviados[1][len(ANTERIOR) + 2] == {"role": "assistant", "content": primera.contenido}
    assert enviados[1][len(ANTERIOR) + 2]["content"][0]["type"] == "thinking"
    assert enviados[2][len(ANTERIOR) + 4] == {"role": "assistant", "content": segunda.contenido}
    # El historial nuevo es lo último que se mandó más la respuesta final.
    assert r.mensajes == [*enviados[-1], {"role": "assistant", "content": tercera.contenido}]


def test_la_segunda_pregunta_arranca_con_el_historial_de_la_primera(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    claude, primera = hacer(
        ctx,
        [falso.usa(("quien_debe", {}, "toolu_1")), falso.texto("Te deben.")],
        monkeypatch,
        settings,
        mensajes=[],
    )
    claude2, segunda = hacer(
        ctx,
        [falso.texto("La de la ferretería.")],
        monkeypatch,
        settings,
        pregunta="¿Y cuál está vencida?",
        mensajes=primera.mensajes,
    )

    enviados = claude2.llamadas[0]["mensajes"]
    assert enviados[: len(primera.mensajes)] == primera.mensajes
    assert enviados[len(primera.mensajes)] == {"role": "user", "content": "¿Y cuál está vencida?"}
    assert segunda.mensajes[: len(primera.mensajes)] == primera.mensajes


def test_no_toca_la_lista_de_mensajes_que_entra(ctx, herramienta, monkeypatch, settings):
    herramienta("quien_debe")
    entrada = list(ANTERIOR)
    copia = json.loads(json.dumps(entrada))
    hacer(
        ctx,
        [falso.usa(("quien_debe", {}, "toolu_1")), falso.texto("Te deben.")],
        monkeypatch,
        settings,
        mensajes=entrada,
    )

    assert entrada == copia


def test_el_mensaje_de_sistema_va_despues_de_la_pregunta_y_queda_en_el_historial(
    ctx, monkeypatch, settings
):
    claude, r = hacer(
        ctx, [falso.texto("Hola.")], monkeypatch, settings, pagina="Pantalla actual: Telas."
    )

    enviados = claude.llamadas[0]["mensajes"]
    assert enviados[len(ANTERIOR)] == {"role": "user", "content": "¿Quién me debe plata?"}
    sistema_de_la_pregunta = enviados[len(ANTERIOR) + 1]
    assert sistema_de_la_pregunta["role"] == "system"
    assert sistema_de_la_pregunta["content"] == (
        f"Hoy es sábado, 14 de noviembre de 2026. Taller: {ctx.taller.nombre}. "
        "Pantalla actual: Telas."
    )
    assert r.mensajes[len(ANTERIOR) + 1] == sistema_de_la_pregunta


def test_sistema_y_herramientas_son_iguales_byte_a_byte_entre_llamadas_y_entre_talleres(
    db, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    uno = contexto_de(fabricas.crear_taller("Taller Uno"))
    otro = contexto_de(fabricas.crear_taller("Taller Otro"))
    claude1, _ = hacer(
        uno,
        [falso.usa(("quien_debe", {}, "toolu_1")), falso.texto("Te deben.")],
        monkeypatch,
        settings,
    )
    claude2, _ = hacer(
        otro,
        [falso.usa(("quien_debe", {}, "toolu_1")), falso.texto("Te deben.")],
        monkeypatch,
        settings,
        pregunta="¿Qué entrego esta semana?",
    )

    todas = claude1.llamadas + claude2.llamadas
    assert len({json.dumps(llamada["sistema"]) for llamada in todas}) == 1
    assert len({json.dumps(llamada["herramientas"]) for llamada in todas}) == 1
    assert todas[0]["herramientas"] == ESQUEMAS
    assert todas[0]["sistema"] == [
        {"type": "text", "text": INSTRUCCIONES, "cache_control": {"type": "ephemeral"}}
    ]


def test_ni_la_fecha_ni_el_taller_ni_la_pantalla_van_en_sistema(db, monkeypatch, settings):
    taller = fabricas.crear_taller("Confecciones La Aguja")
    claude, _ = hacer(contexto_de(taller), [falso.texto("Hola.")], monkeypatch, settings)

    sistema = json.dumps(claude.llamadas[0]["sistema"], ensure_ascii=False)
    assert "La Aguja" not in sistema
    assert HOY.isoformat() not in sistema
    assert fecha_larga(HOY).lower() not in sistema.lower()
    assert "14 de noviembre" not in sistema
    assert PANTALLA not in sistema
    # Las instrucciones son fijas: no nombran ningún año.
    assert "2026" not in INSTRUCCIONES


def test_herramientas_none_son_todas_y_se_pueden_cambiar(ctx, monkeypatch, settings):
    solo_una = [ESQUEMAS[0]]
    claude, _ = hacer(ctx, [falso.texto("Hola.")], monkeypatch, settings, herramientas=solo_una)

    assert claude.llamadas[0]["herramientas"] == solo_una


# --- Esfuerzo -------------------------------------------------------------------------------


def test_el_esfuerzo_se_elige_una_vez_y_vale_para_todas_las_vueltas(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    elegidas = []

    def contar(pregunta):
        elegidas.append(pregunta)
        return "high"

    monkeypatch.setattr(esfuerzo, "elegir", contar)
    claude, r = hacer(
        ctx,
        [
            falso.usa(("quien_debe", {}, "toolu_1")),
            falso.usa(("quien_debe", {}, "toolu_2")),
            falso.texto("Te deben."),
        ],
        monkeypatch,
        settings,
    )

    assert elegidas == ["¿Quién me debe plata?"]
    assert [llamada["esfuerzo"] for llamada in claude.llamadas] == ["high", "high", "high"]
    assert r.esfuerzo == "high"


@pytest.mark.parametrize(
    "pregunta, nivel",
    [("¿Cuánto vendí este mes?", "high"), ("¿Qué telas se están acabando?", "medium")],
)
def test_el_esfuerzo_sale_de_la_pregunta(
    ctx, herramienta, monkeypatch, settings, pregunta, nivel
):
    herramienta("telas")
    claude, _ = hacer(
        ctx,
        [falso.usa(("telas", {"solo_bajas": True}, "toolu_1")), falso.texto("Listo.")],
        monkeypatch,
        settings,
        pregunta=pregunta,
    )

    assert [llamada["esfuerzo"] for llamada in claude.llamadas] == [nivel, nivel]


# --- Vueltas --------------------------------------------------------------------------------


def test_despues_de_cinco_vueltas_la_sexta_va_sin_herramientas(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    guion = [falso.usa(("quien_debe", {}, f"toolu_{n}")) for n in range(1, 6)]
    guion.append(falso.texto("Con lo que tengo: te deben."))
    claude, r = hacer(ctx, guion, monkeypatch, settings)

    assert len(claude.llamadas) == 6
    assert [llamada["sin_herramientas"] for llamada in claude.llamadas] == [False] * 5 + [True]
    # Las herramientas se siguen mandando iguales en la sexta.
    assert claude.llamadas[5]["herramientas"] == ESQUEMAS
    ultimo = claude.llamadas[5]["mensajes"][-1]
    assert ultimo["role"] == "user"
    assert [b["type"] for b in ultimo["content"]] == ["tool_result", "text"]
    assert ultimo["content"][0]["tool_use_id"] == "toolu_5"
    assert ultimo["content"][-1] == {"type": "text", "text": CONTESTA_YA}
    assert r.estado == "ok"
    assert r.texto == "Con lo que tengo: te deben."
    assert len(r.resultados) == 5
    assert r.vueltas == 6


def test_si_en_la_sexta_igual_pide_herramientas_no_se_guarda_nada(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    guion = [falso.usa(("quien_debe", {}, f"toolu_{n}")) for n in range(1, 7)]
    claude, r = hacer(ctx, guion, monkeypatch, settings)

    assert len(claude.llamadas) == 6
    assert r.estado == "error"
    assert r.texto == MENSAJE_SIN_SERVICIO
    assert r.mensajes == ANTERIOR
    assert r.cobrada is True


def test_el_texto_final_es_la_union_de_los_bloques_de_texto_de_la_ultima_respuesta(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    final = falso.texto("Te deben $ 5.790.000.")
    final.contenido.append({"type": "text", "text": "La de la ferretería está vencida."})
    _, r = hacer(
        ctx,
        [falso.usa(("quien_debe", {}, "toolu_1"), texto_antes="Voy a revisar."), final],
        monkeypatch,
        settings,
    )

    assert r.texto == "Te deben $ 5.790.000.\n\nLa de la ferretería está vencida."


def test_el_uso_se_suma_de_todas_las_llamadas(ctx, herramienta, monkeypatch, settings):
    herramienta("quien_debe")
    _, r = hacer(
        ctx,
        [
            falso.usa(("quien_debe", {}, "toolu_1"), entrada=1000, salida=50, cache_escritura=3000),
            falso.texto("Te deben.", entrada=200, salida=40, cache_lectura=3000),
        ],
        monkeypatch,
        settings,
    )

    assert r.uso == Uso(entrada=1200, salida=90, cache_escritura=3000, cache_lectura=3000)


# --- Rechazo y respuesta cortada ------------------------------------------------------------


def test_un_rechazo_no_lee_el_contenido_y_deja_la_conversacion_igual(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    rechazo = falso.rechazo()
    rechazo.contenido.append({"type": "text", "text": "texto que no se debe mostrar"})
    claude, r = hacer(
        ctx, [falso.usa(("quien_debe", {}, "toolu_1")), rechazo], monkeypatch, settings
    )

    assert r.estado == "rechazo"
    assert r.texto == MENSAJE_RECHAZO
    assert r.mensajes == ANTERIOR
    assert r.resultados == []
    assert r.cobrada is True
    assert r.reiniciar is False
    assert len(claude.llamadas) == 2


def test_una_respuesta_cortada_no_lee_el_contenido_y_deja_la_conversacion_igual(
    ctx, monkeypatch, settings
):
    _, r = hacer(ctx, [falso.cortada("Te deben $ 1.2")], monkeypatch, settings)

    assert r.estado == "cortado"
    assert r.texto == MENSAJE_CORTADO
    assert "1.2" not in r.texto
    assert r.mensajes == ANTERIOR
    assert r.cobrada is True
    assert r.stop_reason == "max_tokens"


# --- Errores del servicio -------------------------------------------------------------------


@pytest.mark.parametrize("clave", ERRORES_DEL_SDK)
def test_cada_error_del_sdk_en_la_primera_llamada_da_el_mensaje_amable_y_no_se_cobra(
    ctx, monkeypatch, settings, clave
):
    fabricar, reiniciar = ERRORES_DEL_SDK[clave]
    claude, r = hacer(ctx, [fabricar()], monkeypatch, settings)

    assert len(claude.llamadas) == 1
    assert r.estado == "error"
    assert r.texto == MENSAJE_SIN_SERVICIO
    assert r.mensajes == ANTERIOR
    assert r.resultados == []
    assert r.cobrada is False
    assert r.uso == Uso()
    assert r.reiniciar is reiniciar


@pytest.mark.parametrize("clave", ERRORES_DEL_SDK)
def test_un_error_del_sdk_despues_de_una_vuelta_cuenta_lo_que_si_respondio(
    ctx, herramienta, monkeypatch, settings, clave
):
    herramienta("quien_debe")
    fabricar, reiniciar = ERRORES_DEL_SDK[clave]
    claude, r = hacer(
        ctx,
        [falso.usa(("quien_debe", {}, "toolu_1"), entrada=700, salida=30), fabricar()],
        monkeypatch,
        settings,
    )

    assert len(claude.llamadas) == 2
    assert r.estado == "error"
    assert r.texto == MENSAJE_SIN_SERVICIO
    assert r.mensajes == ANTERIOR
    assert r.cobrada is True
    assert r.uso == Uso(entrada=700, salida=30)
    assert r.reiniciar is reiniciar


def test_un_error_que_no_es_del_sdk_no_se_esconde(ctx, monkeypatch, settings):
    with pytest.raises(AssertionError):
        preguntar(
            cliente=falso.ClienteProhibido(),
            ctx=ctx,
            mensajes=[],
            pregunta="Hola",
            pagina=PANTALLA,
        )


# --- Plazo ----------------------------------------------------------------------------------


class RelojFalso:
    """Hace las veces del módulo `time` dentro de asistente/conversacion.py."""

    def __init__(self, *marcas):
        self.marcas = list(marcas)

    def monotonic(self):
        return self.marcas.pop(0) if len(self.marcas) > 1 else self.marcas[0]


def test_si_se_acaba_el_plazo_no_hace_la_siguiente_llamada(
    ctx, herramienta, monkeypatch, settings
):
    herramienta("quien_debe")
    # Empieza en 0; antes de la 1.ª llamada van 1 s; antes de la 2.ª, 50 s.
    monkeypatch.setattr(conversacion, "time", RelojFalso(0.0, 1.0, 50.0))
    claude, r = hacer(
        ctx,
        [falso.usa(("quien_debe", {}, "toolu_1"), entrada=500), falso.texto("Te deben.")],
        monkeypatch,
        settings,
    )

    assert len(claude.llamadas) == 1
    assert r.estado == "error"
    assert r.texto == MENSAJE_SIN_SERVICIO
    assert r.mensajes == ANTERIOR
    assert r.cobrada is True
    assert r.uso.entrada == 500


def test_si_el_plazo_ya_se_acabo_no_llama_y_no_se_cobra(ctx, monkeypatch, settings):
    monkeypatch.setattr(conversacion, "time", RelojFalso(0.0, 60.0))
    claude, r = hacer(ctx, [falso.texto("Hola.")], monkeypatch, settings)

    assert claude.llamadas == []
    assert r.estado == "error"
    assert r.cobrada is False


def test_justo_antes_del_plazo_si_llama(ctx, monkeypatch, settings):
    monkeypatch.setattr(conversacion, "time", RelojFalso(0.0, 49.9))
    claude, r = hacer(ctx, [falso.texto("Hola.")], monkeypatch, settings)

    assert len(claude.llamadas) == 1
    assert r.estado == "ok"
