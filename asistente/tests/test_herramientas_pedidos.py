"""Las herramientas de pedidos del asistente (T27): buscar_pedidos, ver_pedido y entregas.

Se llaman como las llamaría Claude, por `herramientas.ejecutar(nombre, entrada, ctx)` con las
fechas en texto, sobre los datos de ejemplo cargados el día de las páginas de diseno/
(miércoles 11 de noviembre de 2026). Se comprueba que:

- las cifras y los filtros son los de pedidos/calculos.py (los mismos de las pantallas);
- nunca sale nada de otro taller, y un id ajeno responde igual que uno que no existe;
- lo que va a Claude (`datos`) no lleva teléfonos, notas, token ni nombres o medidas de
  tallas, ni números con decimales sueltos (float);
- las tarjetas usan `pesos` y enlaces armados con `reverse`.

Las piezas de ayuda de este archivo (contexto, sin_float...) las usan también
test_herramientas_catalogo.py y test_herramientas_plata.py.
"""

import json
from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from asistente import herramientas
from asistente.contratos import Contexto, ErrorDeHerramienta, Resultado
from pedidos import calculos, ejemplos
from pedidos.models import Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db

DIA_DEL_DISENO = date(2026, 11, 11)


# --- Ayudas ------------------------------------------------------------------------------------


def contexto(taller, hoy=DIA_DEL_DISENO, pedido=None):
    """El contexto de una pregunta de la dueña de ese taller, armado a mano."""
    return Contexto(
        taller=taller,
        usuaria=fabricas.crear_usuaria(taller),
        hoy=hoy,
        pedido_actual=pedido,
        url_base="http://testserver/",
    )


def hojas(valor):
    """Todos los valores sueltos de unos datos (recorre diccionarios y listas)."""
    if isinstance(valor, dict):
        for parte in valor.values():
            yield from hojas(parte)
    elif isinstance(valor, (list, tuple)):
        for parte in valor:
            yield from hojas(parte)
    else:
        yield valor


def sin_float(datos):
    """Los datos se pueden mandar como JSON y no tienen float ni Decimal (la plata va en
    enteros y los metros en texto)."""
    json.dumps(datos)
    raros = [v for v in hojas(datos) if isinstance(v, (float, Decimal))]
    assert raros == []


def tarjeta_como_en_la_sesion(tarjeta):
    """La tarjeta tal como vuelve de la sesión: un diccionario salido de JSON."""
    return json.loads(json.dumps(asdict(tarjeta)))


def pintar(tarjeta):
    """La tarjeta dibujada con su plantilla, como la incluye la respuesta."""
    return render_to_string(f"asistente/tarjetas/{tarjeta.tipo}.html", {"tarjeta": tarjeta})


def pintar_las_dos(tarjeta):
    """La misma tarjeta pintada desde el objeto y desde la sesión: debe verse igual."""
    html = pintar(tarjeta)
    assert render_to_string(
        f"asistente/tarjetas/{tarjeta.tipo}.html", {"tarjeta": tarjeta_como_en_la_sesion(tarjeta)}
    ) == html
    return html


def pedido_de(taller, cliente):
    return Pedido.objects.get(taller=taller, cliente__nombre=cliente)


def buscar(ctx, texto=None, filtro=None, desde=None, hasta=None):
    return herramientas.ejecutar(
        "buscar_pedidos",
        {"texto": texto, "filtro": filtro, "entrega_desde": desde, "entrega_hasta": hasta},
        ctx,
    )


def clientes_de(datos):
    return [p["cliente"] for p in datos["pedidos"]]


@pytest.fixture
def ejemplo(db):
    return ejemplos.cargar(hoy=DIA_DEL_DISENO, con_fotos=False)


# --- buscar_pedidos ----------------------------------------------------------------------------


def test_buscar_pedidos_sin_filtro_trae_todos_en_el_orden_de_la_lista(ejemplo):
    resultado = buscar(contexto(ejemplo))

    assert isinstance(resultado, Resultado)
    esperado = calculos.ordenar_pedidos(Pedido.objects.del_taller(ejemplo))
    assert [p["id"] for p in resultado.datos["pedidos"]] == [p.pk for p in esperado]
    assert resultado.datos["total"] == resultado.datos["mostrados"] == 6
    assert resultado.revisado == "Revisé tus pedidos"


@pytest.mark.parametrize("filtro", ["todos", "produccion", "semana", "atrasados", "saldo",
                                    "entregados"])
def test_cada_filtro_da_lo_mismo_que_calculos(ejemplo, filtro):
    resultado = buscar(contexto(ejemplo), filtro=filtro)

    esperado = calculos.filtrar_pedidos(Pedido.objects.del_taller(ejemplo), filtro, DIA_DEL_DISENO)
    assert sorted(p["id"] for p in resultado.datos["pedidos"]) == sorted(p.pk for p in esperado)


def test_atrasados_y_semana_como_en_el_diseno(ejemplo):
    ctx = contexto(ejemplo)

    assert clientes_de(buscar(ctx, filtro="atrasados").datos) == ["Ferretería La Esquina"]
    assert clientes_de(buscar(ctx, filtro="semana").datos) == ["Grupo de danza Tambores del Río"]


def test_cotizados_son_los_que_no_se_han_confirmado(ejemplo):
    resultado = buscar(contexto(ejemplo), filtro="cotizados")

    assert clientes_de(resultado.datos) == ["Marcela P."]
    assert resultado.datos["pedidos"][0]["estado"] == "Cotizado"
    # La pantalla Pedidos no tiene ese filtro: el enlace lleva a todos.
    assert resultado.enlace.url == reverse("pedidos:lista") + "?filtro=todos"


def test_el_texto_busca_sin_tildes_en_cliente_detalle_y_encargada(ejemplo):
    ctx = contexto(ejemplo)

    assert clientes_de(buscar(ctx, texto="ferreteria").datos) == ["Ferretería La Esquina"]
    assert clientes_de(buscar(ctx, texto="POLLERAS").datos) == ["Grupo de danza Tambores del Río"]
    # Marta tiene a cargo el Fogón y Tambores del Río.
    assert sorted(clientes_de(buscar(ctx, texto="marta").datos)) == [
        "Grupo de danza Tambores del Río",
        "Restaurante El Fogón Costeño",
    ]
    assert buscar(ctx, texto="no existe nada así").datos["total"] == 0


def test_por_fechas_de_entrega(ejemplo):
    ctx = contexto(ejemplo)

    resultado = buscar(ctx, desde="2026-11-01", hasta="2026-11-30")

    # Brisa Caribe (entregado el 6), Ferretería (el 9) y Tambores del Río (el 14). Marcela P.
    # se entrega el 1 de diciembre.
    assert sorted(clientes_de(resultado.datos)) == [
        "Comparsa Brisa Caribe",
        "Ferretería La Esquina",
        "Grupo de danza Tambores del Río",
    ]
    assert clientes_de(buscar(ctx, filtro="produccion", desde="2026-12-01").datos) == [
        "Restaurante El Fogón Costeño",
        "Colegio Nuevo Amanecer",
    ]


def test_fechas_al_reves_dan_un_error_que_claude_entiende(ejemplo):
    with pytest.raises(ErrorDeHerramienta, match="entrega_desde .* es después de entrega_hasta"):
        buscar(contexto(ejemplo), desde="2026-11-30", hasta="2026-11-01")


def test_cada_pedido_trae_sus_cuentas_de_calculos(ejemplo):
    datos = buscar(contexto(ejemplo), texto="ferreteria").datos["pedidos"][0]
    pedido = pedido_de(ejemplo, "Ferretería La Esquina")

    assert datos == {
        "id": pedido.pk,
        "cliente_id": pedido.cliente_id,
        "cliente": "Ferretería La Esquina",
        "detalle": "8 overoles con logo estampado",
        "cantidad": 8,
        "fecha_entrega": "2026-11-09",
        "estado": "En confección",
        "encargada": "Carmen",
        "dias_para_entrega": -2,
        "atrasado": True,
        "total": 960_000,
        "abonado": 480_000,
        "saldo": 480_000,
    }


def test_con_25_pedidos_van_20_y_dice_cuantos_hay(taller):
    cliente = fabricas.crear_cliente(taller)
    for _ in range(25):
        fabricas.crear_pedido(taller, cliente)

    resultado = buscar(contexto(taller))

    assert resultado.datos["total"] == 25
    assert resultado.datos["mostrados"] == 20
    assert len(resultado.datos["pedidos"]) == 20
    # La tarjeta muestra 6 y "y 19 más".
    assert len(resultado.tarjeta.datos["filas"]) == 6
    assert resultado.tarjeta.datos["mas"] == 19
    assert "y 19 más" in pintar(resultado.tarjeta)


def test_buscar_pedidos_no_ve_los_de_otro_taller(ejemplo):
    otro = fabricas.crear_taller()
    propio = fabricas.crear_pedido(otro, detalle="Camisetas del otro taller")

    del_otro = buscar(contexto(otro))
    del_ejemplo = buscar(contexto(ejemplo), texto="camisetas del otro")

    assert [p["id"] for p in del_otro.datos["pedidos"]] == [propio.pk]
    assert del_ejemplo.datos["total"] == 0


def test_el_enlace_lleva_a_la_lista_con_su_filtro_y_lo_buscado(ejemplo):
    ctx = contexto(ejemplo)

    con_saldo = buscar(ctx, filtro="saldo")
    con_texto = buscar(ctx, texto="colegio", filtro="produccion")

    assert con_saldo.enlace.texto == "Ver los pedidos con saldo"
    assert con_saldo.enlace.url == reverse("pedidos:lista") + "?filtro=saldo"
    assert con_texto.enlace.url == reverse("pedidos:lista") + "?filtro=produccion&q=colegio"
    assert con_texto.revisado == "Busqué «colegio» en tus pedidos"


def test_sin_pedidos_no_hay_tarjeta(taller):
    resultado = buscar(contexto(taller))

    assert resultado.datos == {"total": 0, "mostrados": 0, "pedidos": []}
    assert resultado.tarjeta is None


# --- ver_pedido --------------------------------------------------------------------------------


def ver(ctx, pedido_id):
    return herramientas.ejecutar("ver_pedido", {"pedido_id": pedido_id}, ctx)


def test_ver_pedido_trae_pagos_tallas_por_talla_y_materiales(ejemplo):
    pedido = pedido_de(ejemplo, "Restaurante El Fogón Costeño")

    resultado = ver(contexto(ejemplo), pedido.pk)

    datos = resultado.datos
    assert datos["pedido"]["id"] == pedido.pk
    assert datos["pagos"] == {
        "total": 2_520_000,
        "abonado": 1_260_000,
        "saldo": 1_260_000,
        "abonos": [{"fecha": "2026-11-05", "valor": 1_260_000}],
    }
    assert datos["tallas"] == {
        "recibidas": 14,
        "esperadas": 18,
        "por_talla": [
            {"talla": talla, "cantidad": n} for talla, n in calculos.tallas_por_talla(pedido)
        ],
    }
    assert sum(t["cantidad"] for t in datos["tallas"]["por_talla"]) == 14
    assert datos["materiales"] == {
        "comprados": 2,
        "total": 4,
        "faltan": [
            {"nombre": "Hilo para bordar", "cantidad": "6 conos"},
            {"nombre": "Botones", "cantidad": "60"},
        ],
    }
    assert datos["cliente"] == {
        "id": pedido.cliente_id,
        "nombre": "Restaurante El Fogón Costeño",
        "tipo": "empresa",
        "tiene_whatsapp": False,
    }
    assert datos["enlace_tallas_abierto"] is True
    assert resultado.revisado == "Revisé el pedido de 18 camisas polo bordadas y 18 delantales"
    assert resultado.enlace.texto == "Ver el pedido"
    assert resultado.enlace.url == reverse("pedidos:detalle", args=[pedido.pk])


def test_ver_pedido_de_otro_taller_o_que_no_existe_dan_el_mismo_error(ejemplo):
    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_pedido(otro)
    ctx = contexto(ejemplo)

    with pytest.raises(ErrorDeHerramienta) as de_otro:
        ver(ctx, ajeno.pk)
    with pytest.raises(ErrorDeHerramienta) as inexistente:
        ver(ctx, ajeno.pk + 1000)

    assert str(de_otro.value) == str(inexistente.value) == "No encontré ese pedido."


def test_sin_id_usa_el_pedido_abierto_en_pantalla(ejemplo):
    pedido = pedido_de(ejemplo, "Ferretería La Esquina")

    resultado = ver(contexto(ejemplo, pedido=pedido), None)

    assert resultado.datos["pedido"]["id"] == pedido.pk
    assert resultado.datos["pagos"]["saldo"] == 480_000


def test_sin_id_y_sin_pedido_en_pantalla_pide_cual(ejemplo):
    with pytest.raises(ErrorDeHerramienta, match="No hay un pedido abierto en pantalla"):
        ver(contexto(ejemplo), None)


def test_el_pedido_de_la_pantalla_tambien_se_revisa_por_taller(ejemplo):
    # Aunque la pantalla ya lo valida, la herramienta lo vuelve a buscar dentro del taller.
    ajeno = fabricas.crear_pedido(fabricas.crear_taller())

    with pytest.raises(ErrorDeHerramienta, match="No encontré ese pedido."):
        ver(contexto(ejemplo, pedido=ajeno), None)


def test_la_tarjeta_del_pedido(ejemplo):
    pedido = pedido_de(ejemplo, "Ferretería La Esquina")

    html = pintar_las_dos(ver(contexto(ejemplo), pedido.pk).tarjeta)

    assert f'href="{reverse("pedidos:detalle", args=[pedido.pk])}"' in html
    assert "Ferretería La Esquina" in html
    assert html.count("$ 480.000") == 2  # abonado y saldo
    assert "$ 960.000" in html
    assert "Atrasado 2 días" in html and "etiqueta--rojo" in html
    assert "Vencido" in html
    assert "8 de 8" in html
    assert "2 de 2 comprados" in html


# --- entregas ----------------------------------------------------------------------------------


def entregas(ctx, desde, hasta):
    return herramientas.ejecutar("entregas", {"desde": desde, "hasta": hasta}, ctx)


def test_entregas_de_la_semana_y_los_atrasados(ejemplo):
    resultado = entregas(contexto(ejemplo), "2026-11-11", "2026-11-18")

    datos = resultado.datos
    assert datos["desde"] == "2026-11-11" and datos["hasta"] == "2026-11-18"
    assert clientes_de(datos["entregas"]) == ["Grupo de danza Tambores del Río"]
    assert datos["entregas"]["total"] == datos["entregas"]["mostrados"] == 1
    assert clientes_de(datos["atrasados"]) == ["Ferretería La Esquina"]
    atrasados = calculos.pedidos_atrasados(Pedido.objects.del_taller(ejemplo), DIA_DEL_DISENO)
    assert [p["id"] for p in datos["atrasados"]["pedidos"]] == [p.pk for p in atrasados]
    assert resultado.revisado == "Revisé tus entregas del 11 de nov al 18 de nov"
    assert resultado.enlace.url == reverse("pedidos:calendario") + "?mes=2026-11"


def test_entregas_solo_cuenta_los_que_estan_en_produccion(ejemplo):
    # Del 1 al 30 de noviembre: Brisa Caribe ya se entregó y Marcela P. está cotizada.
    datos = entregas(contexto(ejemplo), "2026-11-01", "2026-11-30").datos

    assert clientes_de(datos["entregas"]) == [
        "Ferretería La Esquina",
        "Grupo de danza Tambores del Río",
    ]


def test_entregas_con_fechas_al_reves_o_un_rango_muy_largo_da_error(ejemplo):
    ctx = contexto(ejemplo)

    with pytest.raises(ErrorDeHerramienta, match="desde .* es después de hasta"):
        entregas(ctx, "2026-11-20", "2026-11-10")
    with pytest.raises(ErrorDeHerramienta, match="el máximo es 62"):
        entregas(ctx, "2026-11-01", "2027-01-03")
    # 62 días justos sí se pueden.
    assert entregas(ctx, "2026-11-01", "2027-01-02").datos["entregas"]["total"] == 3


def test_entregas_no_ve_los_de_otro_taller(ejemplo):
    otro = fabricas.crear_taller()
    fabricas.crear_pedido(otro, estado="confeccion", fecha_entrega=DIA_DEL_DISENO)
    fabricas.crear_pedido(otro, estado="corte", fecha_entrega=DIA_DEL_DISENO - timedelta(days=3))

    del_ejemplo = entregas(contexto(ejemplo), "2026-11-11", "2026-11-11").datos
    del_otro = entregas(contexto(otro), "2026-11-11", "2026-11-11").datos

    assert del_ejemplo["entregas"]["total"] == 0
    assert clientes_de(del_ejemplo["atrasados"]) == ["Ferretería La Esquina"]
    assert del_otro["entregas"]["total"] == 1
    assert del_otro["atrasados"]["total"] == 1


def test_la_tarjeta_de_entregas_pone_primero_los_atrasados(ejemplo):
    resultado = entregas(contexto(ejemplo), "2026-11-11", "2026-11-18")

    filas = resultado.tarjeta.datos["filas"]
    assert [f["cliente"] for f in filas] == [
        "Ferretería La Esquina",
        "Grupo de danza Tambores del Río",
    ]
    html = pintar_las_dos(resultado.tarjeta)
    tambores = pedido_de(ejemplo, "Grupo de danza Tambores del Río")
    assert f'href="{reverse("pedidos:detalle", args=[tambores.pk])}"' in html
    assert "Atrasado 2 días" in html
    assert "Faltan 3 días" in html
    assert "14 de nov" in html


def test_la_tarjeta_de_pedidos_con_saldo_usa_pesos(ejemplo):
    resultado = buscar(contexto(ejemplo), filtro="saldo")

    html = pintar_las_dos(resultado.tarjeta)

    for cifra in ("$ 3.300.000", "$ 1.260.000", "$ 750.000", "$ 480.000"):
        assert cifra in html
    assert "Vencido" in html


# --- Lo que nunca va a Claude ------------------------------------------------------------------


@pytest.fixture
def pedido_con_secretos(taller):
    """Un pedido con todo lo que no debe salir: WhatsApp, notas, tallas con nombre y medidas."""
    cliente = fabricas.crear_cliente(
        taller, nombre="Comparsa Secreta", whatsapp="300 765 4321", notas="Nota privada 7788"
    )
    pedido = fabricas.crear_pedido(taller, cliente, estado="confeccion", tallaje="adulto")
    fabricas.crear_talla(pedido, talla="M", nombre="Persona Escondida")
    fabricas.crear_talla(
        pedido, talla="medida", nombre="Otra Persona Oculta", pecho=Decimal("97.5"),
        cintura=Decimal("81.5"), cadera=Decimal("103.5"),
    )
    fabricas.crear_abono(pedido, valor=150_000)
    return pedido


SECRETOS = ("3007654321", "765 4321", "Nota privada", "Persona Escondida", "Otra Persona Oculta",
            "97.5", "81.5", "103.5")


def test_lo_que_va_a_claude_no_lleva_telefono_notas_token_ni_tallas(taller, pedido_con_secretos):
    pedido = pedido_con_secretos
    ctx = contexto(taller, hoy=pedido.fecha_entrega - timedelta(days=2), pedido=pedido)
    resultados = [
        buscar(ctx),
        buscar(ctx, texto="secreta"),
        ver(ctx, pedido.pk),
        ver(ctx, None),
        entregas(ctx, ctx.hoy.isoformat(), pedido.fecha_entrega.isoformat()),
    ]

    for resultado in resultados:
        texto = json.dumps(resultado.datos, ensure_ascii=False)
        for secreto in (*SECRETOS, pedido.token_tallas):
            assert secreto not in texto
        assert '"whatsapp"' not in texto  # ni una llave "whatsapp" con el número
        assert "notas" not in texto
        sin_float(resultado.datos)
        if resultado.tarjeta:
            sin_float(resultado.tarjeta.datos)
            tarjeta = json.dumps(resultado.tarjeta.datos, ensure_ascii=False)
            for secreto in (*SECRETOS, pedido.token_tallas):
                assert secreto not in tarjeta
    # De las tallas solo va cuántas hay de cada una.
    assert resultados[2].datos["tallas"]["por_talla"] == [
        {"talla": "M", "cantidad": 1},
        {"talla": "medida", "cantidad": 1},
    ]
    assert resultados[2].datos["cliente"]["tiene_whatsapp"] is True


def test_sin_float_en_ninguna_herramienta_de_pedidos(ejemplo):
    ctx = contexto(ejemplo, pedido=pedido_de(ejemplo, "Colegio Nuevo Amanecer"))

    for resultado in (buscar(ctx), ver(ctx, None), entregas(ctx, "2026-11-01", "2026-12-31")):
        sin_float(resultado.datos)
        sin_float(resultado.tarjeta.datos)
