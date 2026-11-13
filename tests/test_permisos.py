"""T21. Permisos por rol (docs/04-permisos.md y "Permisos" de docs/06-pruebas.md).

Una prueba por cada fila de la tabla de permisos, como dueña y como costurera. Además:

- la costurera no recibe plata en ninguna página ni respuesta (con los datos de ejemplo);
- lo prohibido responde 403 aunque el formulario se envíe a mano, y no cambia nada;
- el número de algo de otro taller responde 404 también a la costurera (primero el taller,
  después el rol);
- el menú de cada rol, la página "Sin permiso", las usuarias desactivadas y el
  administrador.
"""

import re
from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from cotizador.models import PrendaGuardada
from cuentas.models import Taller, Usuario
from cuentas.permisos import SOLO_LA_DUENA, SOLO_LA_ENCARGADA
from finanzas.models import Gasto
from pedidos import calculos, ejemplos
from pedidos.models import Abono, Cliente, Material, Pedido, Talla
from telas.models import MovimientoTela, Tela
from tests import fabricas
from tests.fabricas import CLAVE
from tests.test_esqueleto import (
    MODELO_DE_LA_DIRECCION,
    SIN_TALLER,
    _patron,
    direcciones_con_numero,
    registro_de_otro_taller,
)

pytestmark = pytest.mark.django_db

DUENA, COSTURERA = "duena", "costurera"
ROLES = (DUENA, COSTURERA)
HTMX = {"HX-Request": "true"}
Estado = Pedido.Estado

# Plata como la muestra la aplicación ("$ 1.234.000", "-$ 200.000") o dentro de un enlace de
# WhatsApp ("%24%201.234.000"). Las fechas y los conteos no llevan "$".
PLATA = re.compile(r"\$\s?\d|%24(%20|\+)?\d")


def sin_plata(html):
    encontrado = PLATA.search(html)
    return encontrado is None


def es_prohibido(respuesta):
    """403 con la página "Sin permiso" en español."""
    return respuesta.status_code == 403


@pytest.fixture(autouse=True)
def carpeta_de_fotos(settings, tmp_path):
    """Las fotos de estas pruebas se guardan en una carpeta temporal, nunca en media/."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def usuarias(duena, costurera):
    return {DUENA: duena, COSTURERA: costurera}


@pytest.fixture
def entrar(client, usuarias):
    """entrar("duena") o entrar("costurera"): el navegador con esa sesión abierta."""

    def _entrar(rol):
        client.force_login(usuarias[rol])
        return client

    return _entrar


@pytest.fixture
def pedido(taller, duena):
    """Un pedido confirmado de $ 1.234.000 con un abono, una talla y un material."""
    cliente = fabricas.crear_cliente(taller, nombre="Cliente de prueba")
    pedido = fabricas.crear_pedido(
        taller, cliente=cliente, detalle="20 camisas de prueba", total=1_234_000,
        estado=Estado.CONFIRMADO,
    )
    fabricas.crear_abono(pedido, valor=234_000)
    fabricas.crear_talla(pedido, nombre="Persona de prueba")
    fabricas.crear_material(pedido, nombre="Botones de prueba")
    return pedido


def foto_de_prueba():
    salida = BytesIO()
    Image.new("RGB", (300, 200), (37, 99, 201)).save(salida, "JPEG")
    return SimpleUploadedFile("foto.jpg", salida.getvalue(), content_type="image/jpeg")


def datos_de_pedido():
    return {
        "cliente": "Cliente nuevo de prueba", "tipo": "empresa", "detalle": "10 overoles",
        "cantidad": "10", "tallaje": "adulto",
        "fecha_entrega": (timezone.localdate() + timedelta(days=30)).isoformat(),
        "total": "500.000", "whatsapp": "",
    }


# --- Una prueba por cada fila de la tabla ---------------------------------------------------


@pytest.mark.parametrize("rol", ROLES)
def test_ver_la_lista_de_pedidos(entrar, rol, pedido):
    """Dueña: todos con sus valores. Costurera: todos, sin valores."""
    cliente = entrar(rol)

    respuesta = cliente.get(reverse("pedidos:lista"))
    con_saldo = cliente.get(reverse("pedidos:lista") + "?filtro=saldo")
    buscando = cliente.get(reverse("pedidos:lista") + "?q=camisas", headers=HTMX)

    assert respuesta.status_code == con_saldo.status_code == buscando.status_code == 200
    for html in (respuesta.text, con_saldo.text, buscando.text):
        assert "Cliente de prueba" in html
    if rol == DUENA:
        assert ">Saldo</th>" in respuesta.text
        assert "$ 1.000.000" in respuesta.text
        assert "Con saldo" in respuesta.text
    else:
        for html in (respuesta.text, con_saldo.text, buscando.text):
            assert ">Saldo</th>" not in html
            assert "Con saldo" not in html
            assert "Pagado" not in html
            assert sin_plata(html)


@pytest.mark.parametrize("rol", ROLES)
def test_ver_un_pedido_por_dentro(entrar, rol, pedido):
    """Dueña: con la tarjeta Pagos. Costurera: sin la sección de pagos."""
    respuesta = entrar(rol).get(reverse("pedidos:detalle", args=[pedido.pk]))

    html = respuesta.text
    assert respuesta.status_code == 200
    assert "20 camisas de prueba" in html
    assert 'id="tarjeta-tallas"' in html and 'id="pedido-materiales"' in html
    if rol == DUENA:
        assert 'id="pagos"' in html
        assert "Registrar abono" in html
        assert "$ 1.000.000" in html
    else:
        assert 'id="pagos"' not in html
        assert "Registrar abono" not in html
        assert "Abonado" not in html and "Falta por pagar" not in html
        assert sin_plata(html)


@pytest.mark.parametrize("rol", ROLES)
def test_crear_editar_y_eliminar_pedidos(entrar, rol, pedido, taller):
    """Solo la dueña crea, edita (fecha de entrega y WhatsApp del cliente) y elimina."""
    cliente = entrar(rol)
    antes = Pedido.objects.count()
    fecha_antes = pedido.fecha_entrega
    otra_fecha = (fecha_antes + timedelta(days=10)).isoformat()

    ventana_nuevo = cliente.get(reverse("pedidos:nuevo"), headers=HTMX)
    nuevo = cliente.post(reverse("pedidos:nuevo"), datos_de_pedido())
    entrega = cliente.post(
        reverse("pedidos:entrega", args=[pedido.pk]), {"fecha_entrega": otra_fecha}, headers=HTMX
    )
    whatsapp = cliente.post(
        reverse("pedidos:whatsapp", args=[pedido.pk]), {"whatsapp": "3001234567"}, headers=HTMX
    )
    ventana_eliminar = cliente.get(reverse("pedidos:eliminar", args=[pedido.pk]), headers=HTMX)
    pedido.refresh_from_db()
    pedido.cliente.refresh_from_db()

    if rol == DUENA:
        assert ventana_nuevo.status_code == 200 and nuevo.status_code == 302
        assert Pedido.objects.count() == antes + 1
        assert entrega.status_code == 200 and pedido.fecha_entrega.isoformat() == otra_fecha
        assert whatsapp.status_code == 200 and pedido.cliente.whatsapp == "3001234567"
        assert ventana_eliminar.status_code == 200
        eliminar = cliente.post(reverse("pedidos:eliminar", args=[pedido.pk]))
        assert eliminar.status_code == 302
        assert not Pedido.objects.filter(pk=pedido.pk).exists()
    else:
        for respuesta in (ventana_nuevo, nuevo, entrega, whatsapp, ventana_eliminar):
            assert es_prohibido(respuesta)
        eliminar = cliente.post(reverse("pedidos:eliminar", args=[pedido.pk]))
        assert es_prohibido(eliminar)
        assert Pedido.objects.count() == antes
        assert pedido.fecha_entrega == fecha_antes
        assert pedido.cliente.whatsapp == ""
        assert Pedido.objects.filter(pk=pedido.pk).exists()


@pytest.mark.parametrize(
    "quien, puede",
    [("duena", True), ("costurera encargada", True), ("costurera sin ser la encargada", False)],
)
def test_cambiar_la_etapa_de_un_pedido(client, taller, duena, costurera, pedido, quien, puede):
    """Dueña: sí. Costurera: solo si es la encargada, en el pedido y en "Qué hacer hoy"."""
    otra = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Otra")
    pedido.encargada = costurera if quien == "costurera encargada" else otra
    pedido.save()
    client.force_login(duena if quien == "duena" else costurera)

    pagina = client.get(reverse("pedidos:detalle", args=[pedido.pk])).text
    etapa = client.post(
        reverse("pedidos:etapa", args=[pedido.pk]), {"estado": Estado.CONFECCION}, headers=HTMX
    )
    desde_hoy = client.post(reverse("pedidos:hoy_accion", args=[pedido.pk, "listo"]))
    pedido.refresh_from_db()

    url_etapa = reverse("pedidos:etapa", args=[pedido.pk])
    if puede:
        assert f'hx-post="{url_etapa}"' in pagina
        assert etapa.status_code == 200
        assert desde_hoy.status_code == 302
        assert pedido.estado == Estado.LISTO
    else:
        assert f'hx-post="{url_etapa}"' not in pagina
        assert 'class="paso paso--actual" name="estado" value="confirmado" disabled' in pagina
        assert "Solo Otra o la dueña del taller pueden mover este pedido." in pagina
        assert es_prohibido(etapa) and es_prohibido(desde_hoy)
        assert SOLO_LA_ENCARGADA in etapa.text
        assert pedido.estado == Estado.CONFIRMADO


@pytest.mark.parametrize("rol", ROLES)
def test_elegir_la_encargada(entrar, rol, pedido, costurera):
    """Dueña: sí. Costurera: no, ni siquiera para ponerse a sí misma."""
    cliente = entrar(rol)

    pagina = cliente.get(reverse("pedidos:detalle", args=[pedido.pk])).text
    respuesta = cliente.post(
        reverse("pedidos:encargada", args=[pedido.pk]), {"encargada": costurera.pk},
        headers=HTMX,
    )
    pedido.refresh_from_db()

    url = reverse("pedidos:encargada", args=[pedido.pk])
    if rol == DUENA:
        assert url in pagina
        assert respuesta.status_code == 200
        assert pedido.encargada == costurera
    else:
        # La ve, pero el campo no se puede cambiar y no hay a dónde enviarlo.
        assert url not in pagina
        assert re.search(r'<select name="encargada"[^>]* disabled', pagina)
        assert es_prohibido(respuesta)
        assert pedido.encargada is None


@pytest.mark.parametrize("rol", ROLES)
def test_registrar_y_quitar_abonos(entrar, rol, pedido):
    """Dueña: sí. Costurera: no, aunque envíe el formulario a mano."""
    cliente = entrar(rol)
    abono = pedido.abonos.get()
    tarjeta = {**HTMX, "HX-Target": "pagos"}
    datos = {"valor": "100.000", "fecha": timezone.localdate().isoformat()}

    nuevo = cliente.post(reverse("pedidos:abono_nuevo", args=[pedido.pk]), datos, headers=tarjeta)
    a_mano = cliente.post(reverse("pedidos:abono_nuevo", args=[pedido.pk]), datos)
    url_quitar = reverse("pedidos:abono_quitar", args=[pedido.pk, abono.pk])
    pregunta = cliente.get(url_quitar, headers=tarjeta)
    quitar = cliente.post(url_quitar, headers=tarjeta)

    if rol == DUENA:
        assert nuevo.status_code == 200 and a_mano.status_code == 302
        assert pregunta.status_code == 200 and quitar.status_code == 200
        assert not Abono.objects.filter(pk=abono.pk).exists()
        assert pedido.abonos.count() == 2
    else:
        for respuesta in (nuevo, a_mano, pregunta, quitar):
            assert es_prohibido(respuesta)
        assert list(pedido.abonos.all()) == [abono]


@pytest.mark.parametrize("rol", ROLES)
def test_descargar_recibos(entrar, rol, pedido):
    abono = pedido.abonos.get()

    respuesta = entrar(rol).get(reverse("pedidos:recibo", args=[pedido.pk, abono.pk]))

    if rol == DUENA:
        assert respuesta.status_code == 200
        assert respuesta["Content-Type"] == "application/pdf"
    else:
        assert es_prohibido(respuesta)
        assert respuesta["Content-Type"] != "application/pdf"


@pytest.mark.parametrize("rol", ROLES)
def test_ver_tallas(entrar, rol, pedido):
    """Las dos ven las tallas y pueden copiar el enlace para el cliente."""
    html = entrar(rol).get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert "Persona de prueba" in html
    assert "1 de 10" in html
    assert "Copiar enlace para el cliente" in html


@pytest.mark.parametrize("rol", ROLES)
def test_abrir_y_cerrar_el_enlace_de_tallas_es_de_la_duena(entrar, rol, pedido):
    """Decisión de T21: abrir o cerrar el enlace público es manejar el pedido."""
    cliente = entrar(rol)

    html = cliente.get(reverse("pedidos:detalle", args=[pedido.pk])).text
    respuesta = cliente.post(
        reverse("pedidos:tallas_enlace", args=[pedido.pk]), {"abiertas": "no"}, headers=HTMX
    )
    pedido.refresh_from_db()

    assert "Enlace abierto" in html
    if rol == DUENA:
        assert "Cerrar el enlace" in html
        assert respuesta.status_code == 200 and not pedido.tallas_abiertas
    else:
        assert "Cerrar el enlace" not in html
        assert es_prohibido(respuesta) and pedido.tallas_abiertas


@pytest.mark.parametrize("rol", ROLES)
def test_agregar_tallas_a_mano(entrar, rol, pedido):
    cliente = entrar(rol)

    agregar = cliente.post(
        reverse("pedidos:talla_nueva", args=[pedido.pk]), {"nombre": "Nueva persona", "talla": "M"},
        headers=HTMX,
    )
    nueva = Talla.objects.get(pedido=pedido, nombre="Nueva persona")
    quitar = cliente.post(
        reverse("pedidos:talla_quitar", args=[pedido.pk, nueva.pk]), headers=HTMX
    )

    assert agregar.status_code == 200 and quitar.status_code == 200
    assert not Talla.objects.filter(pk=nueva.pk).exists()


def test_enviar_su_propia_talla_es_del_cliente_con_enlace(client, pedido):
    """No aplica a la dueña ni a la costurera: el enlace abre sin sesión."""
    url = reverse("pedidos:publico_tallas", args=[pedido.token_tallas])

    respuesta = client.get(url)

    assert respuesta.status_code == 200
    assert sin_plata(respuesta.text)


@pytest.mark.parametrize("rol", ROLES)
def test_marcar_materiales_como_comprados(entrar, rol, pedido):
    material = pedido.materiales.get()

    respuesta = entrar(rol).post(
        reverse("pedidos:material_comprado", args=[pedido.pk, material.pk]), {"comprado": "si"},
        headers=HTMX,
    )
    material.refresh_from_db()

    assert respuesta.status_code == 200
    assert material.comprado


@pytest.mark.parametrize("rol", ROLES)
def test_agregar_y_quitar_materiales(entrar, rol, pedido):
    cliente = entrar(rol)

    agregar = cliente.post(
        reverse("pedidos:material_nuevo", args=[pedido.pk]), {"nombre": "Hilo azul"},
        headers=HTMX,
    )
    nuevo = Material.objects.get(pedido=pedido, nombre="Hilo azul")
    quitar = cliente.post(
        reverse("pedidos:material_quitar", args=[pedido.pk, nuevo.pk]), headers=HTMX
    )

    assert agregar.status_code == 200 and quitar.status_code == 200
    assert not Material.objects.filter(pk=nuevo.pk).exists()


@pytest.mark.parametrize("rol", ROLES)
def test_subir_la_foto_del_diseno(entrar, rol, pedido):
    respuesta = entrar(rol).post(
        reverse("pedidos:foto", args=[pedido.pk]), {"foto": foto_de_prueba()},
        headers={**HTMX, "HX-Target": "pedido-foto"},
    )
    pedido.refresh_from_db()

    assert respuesta.status_code == 200
    assert pedido.foto


@pytest.mark.parametrize("rol", ROLES)
def test_calendario(entrar, rol, pedido):
    mes = pedido.fecha_entrega.strftime("%Y-%m")
    dia = pedido.fecha_entrega.isoformat()
    cliente = entrar(rol)

    pagina = cliente.get(reverse("pedidos:calendario") + f"?mes={mes}")
    del_dia = cliente.get(reverse("pedidos:calendario") + f"?mes={mes}&dia={dia}", headers=HTMX)

    assert pagina.status_code == del_dia.status_code == 200
    assert "Cliente de prueba" in pagina.text and "Cliente de prueba" in del_dia.text
    if rol == COSTURERA:
        assert sin_plata(pagina.text) and sin_plata(del_dia.text)
        assert reverse("pedidos:nuevo") not in pagina.text


@pytest.mark.parametrize("rol", ROLES)
def test_clientes(entrar, rol, taller):
    """Solo la dueña: la lista, crear y editar."""
    cliente = entrar(rol)
    existente = fabricas.crear_cliente(taller, nombre="Cliente existente")
    antes = Cliente.objects.count()

    lista = cliente.get(reverse("pedidos:clientes"))
    escribirles = cliente.get(reverse("pedidos:clientes") + "?escribir=empresas", headers=HTMX)
    ventana = cliente.get(reverse("pedidos:cliente_nuevo"), headers=HTMX)
    nuevo = cliente.post(
        reverse("pedidos:cliente_nuevo"), {"nombre": "Cliente a mano", "tipo": "empresa"}
    )
    editar = cliente.post(
        reverse("pedidos:cliente_editar", args=[existente.pk]),
        {"nombre": "Nombre cambiado", "tipo": "empresa"},
    )
    existente.refresh_from_db()

    if rol == DUENA:
        assert lista.status_code == escribirles.status_code == ventana.status_code == 200
        assert nuevo.status_code == editar.status_code == 302
        assert Cliente.objects.count() == antes + 1
        assert existente.nombre == "Nombre cambiado"
    else:
        for respuesta in (lista, escribirles, ventana, nuevo, editar):
            assert es_prohibido(respuesta)
        assert Cliente.objects.count() == antes
        assert existente.nombre == "Cliente existente"


CAMISA = {
    "cliente": "Cliente de prueba", "tipo": "empresa", "whatsapp": "",
    "prenda": "Camisa de prueba", "cantidad": "20", "entrega": "", "metros": "1,2",
    "precio_metro": "18000", "insumos": "3000", "mano_obra": "12000", "extra": "5000",
    "ganancia": "30", "abono": "50",
}


@pytest.mark.parametrize("rol", ROLES)
def test_cotizador(entrar, rol, taller):
    """Solo la dueña: ver, calcular, guardar y quitar prendas y crear el pedido."""
    cliente = entrar(rol)
    prenda = fabricas.crear_prenda(taller, nombre="Prenda guardada")
    pedidos_antes = Pedido.objects.count()

    inicio = cliente.get(reverse("cotizador:inicio"))
    calcular = cliente.get(reverse("cotizador:calcular"), CAMISA, headers=HTMX)
    guardar = cliente.post(reverse("cotizador:prenda_guardar"), CAMISA)
    quitar = cliente.post(
        reverse("cotizador:prenda_quitar", args=[prenda.pk]), {**CAMISA, "confirmar": "si"}
    )
    crear = cliente.post(reverse("cotizador:crear_pedido"), CAMISA)

    if rol == DUENA:
        assert inicio.status_code == calcular.status_code == 200
        assert guardar.status_code == quitar.status_code == 200
        assert crear.status_code == 302
        assert not PrendaGuardada.objects.filter(pk=prenda.pk).exists()
        assert PrendaGuardada.objects.filter(nombre="Camisa de prueba").exists()
        assert Pedido.objects.count() == pedidos_antes + 1
    else:
        for respuesta in (inicio, calcular, guardar, quitar, crear):
            assert es_prohibido(respuesta)
            assert sin_plata(respuesta.text)
        assert list(PrendaGuardada.objects.values_list("nombre", flat=True)) == [
            "Prenda guardada"
        ]
        assert Pedido.objects.count() == pedidos_antes


def _en_telas(url):
    """Una acción que llega con HTMX desde la ventana de la pantalla Telas."""
    return {**HTMX, "HX-Target": "ventana", "HX-Current-URL": f"http://testserver{url}"}


@pytest.mark.parametrize("rol", ROLES)
def test_telas_ver_y_registrar_use(entrar, rol, taller):
    cliente = entrar(rol)
    tela = fabricas.crear_tela(taller, nombre="Dril de prueba", metros=10)
    url = reverse("telas:movimiento", args=[tela.pk])

    pantalla = cliente.get(reverse("telas:inicio"))
    historial = cliente.get(url, headers={**HTMX, "HX-Target": "ventana"})
    ventana_use = cliente.get(url + "?tipo=uso", headers={**HTMX, "HX-Target": "ventana"})
    use = cliente.post(
        url, {"tipo": "uso", "metros": "2"}, headers=_en_telas(reverse("telas:inicio"))
    )
    tela.refresh_from_db()

    assert pantalla.status_code == historial.status_code == ventana_use.status_code == 200
    assert use.status_code == 200
    assert tela.metros == 8
    assert MovimientoTela.objects.filter(tela=tela, metros=-2).exists()
    assert "Dril de prueba" in pantalla.text and "Usé" in pantalla.text
    if rol == DUENA:
        assert "Nueva tela" in pantalla.text and ">Entró</a>" in pantalla.text
        assert "Quitar tela" in historial.text
    else:
        assert "Nueva tela" not in pantalla.text and ">Entró</a>" not in pantalla.text
        assert "Quitar tela" not in historial.text
        assert ">Entró</a>" not in use.text


@pytest.mark.parametrize("rol", ROLES)
def test_telas_entro_agregar_y_quitar(entrar, rol, taller):
    """Solo la dueña, aunque la costurera envíe el formulario a mano."""
    cliente = entrar(rol)
    tela = fabricas.crear_tela(taller, nombre="Dril de prueba", metros=10)
    url = reverse("telas:movimiento", args=[tela.pk])
    desde_telas = _en_telas(reverse("telas:inicio"))

    ventana_entro = cliente.get(url + "?tipo=entro", headers=HTMX)
    entro = cliente.post(url, {"tipo": "entro", "metros": "5"}, headers=desde_telas)
    ventana_nueva = cliente.get(reverse("telas:nueva"), headers=HTMX)
    nueva = cliente.post(
        reverse("telas:nueva"), {"nombre": "Tela a mano", "metros": "3", "minimo": "1"},
        headers=desde_telas,
    )
    ventana_quitar = cliente.get(reverse("telas:quitar", args=[tela.pk]), headers=HTMX)
    tela.refresh_from_db()
    metros_despues_de_entro = tela.metros
    quitar = cliente.post(reverse("telas:quitar", args=[tela.pk]), headers=desde_telas)

    if rol == DUENA:
        for respuesta in (ventana_entro, entro, ventana_nueva, nueva, ventana_quitar, quitar):
            assert respuesta.status_code == 200
        assert metros_despues_de_entro == 15
        assert Tela.objects.filter(nombre="Tela a mano").exists()
        assert not Tela.objects.filter(pk=tela.pk).exists()
    else:
        for respuesta in (ventana_entro, entro, ventana_nueva, nueva, ventana_quitar, quitar):
            assert es_prohibido(respuesta)
        assert metros_despues_de_entro == 10
        assert not Tela.objects.filter(nombre="Tela a mano").exists()
        assert Tela.objects.filter(pk=tela.pk).exists()
        assert tela.movimientos.count() == 0


@pytest.mark.parametrize("rol", ROLES)
def test_resumen_gastos_y_excel(entrar, rol, taller):
    """Solo la dueña: el resumen, registrar y quitar gastos y el Excel."""
    cliente = entrar(rol)
    gasto = fabricas.crear_gasto(taller, concepto="Gasto de prueba", valor=50_000)
    hoy = timezone.localdate()
    datos = {"concepto": "Hilos", "categoria": "insumos", "valor": "20.000",
             "fecha": hoy.isoformat(), "mes": hoy.strftime("%Y-%m")}

    resumen = cliente.get(reverse("finanzas:resumen"))
    formulario = cliente.get(reverse("finanzas:gasto_nuevo"))
    nuevo = cliente.post(reverse("finanzas:gasto_nuevo"), datos)
    pregunta = cliente.get(reverse("finanzas:gasto_quitar", args=[gasto.pk]))
    quitar = cliente.post(reverse("finanzas:gasto_quitar", args=[gasto.pk]))
    excel = cliente.get(reverse("finanzas:excel"))

    if rol == DUENA:
        assert resumen.status_code == formulario.status_code == pregunta.status_code == 200
        assert nuevo.status_code == quitar.status_code == 302
        assert excel.status_code == 200
        assert "spreadsheet" in excel["Content-Type"]
        assert list(Gasto.objects.values_list("concepto", flat=True)) == ["Hilos"]
    else:
        for respuesta in (resumen, formulario, nuevo, pregunta, quitar, excel):
            assert es_prohibido(respuesta)
            assert sin_plata(respuesta.text)
        assert "spreadsheet" not in excel["Content-Type"]
        assert list(Gasto.objects.values_list("concepto", flat=True)) == ["Gasto de prueba"]


@pytest.mark.parametrize("rol", ROLES)
def test_mi_taller(entrar, rol, taller, costurera):
    """Solo la dueña: el taller y las costureras."""
    cliente = entrar(rol)
    nombre_antes = taller.nombre
    url_editar = reverse("cuentas:costurera_editar", args=[costurera.pk])

    pantalla = cliente.get(reverse("cuentas:mi_taller"))
    guardar = cliente.post(reverse("cuentas:mi_taller"), {"nombre": "Nombre cambiado"})
    agregar = cliente.post(
        reverse("cuentas:costurera_nueva"),
        {"nombre_visible": "Carmen", "username": "carmen", "contrasena": "hilo-y-aguja-2026"},
    )
    formulario = cliente.get(url_editar)
    renombrar = cliente.post(url_editar, {"accion": "nombre", "nombre_visible": "Otro nombre"})
    taller.refresh_from_db()
    costurera.refresh_from_db()

    if rol == DUENA:
        assert pantalla.status_code == formulario.status_code == 200
        assert guardar.status_code == agregar.status_code == renombrar.status_code == 302
        assert taller.nombre == "Nombre cambiado"
        assert Usuario.objects.filter(username="carmen").exists()
        assert costurera.nombre_visible == "Otro nombre"
    else:
        for respuesta in (pantalla, guardar, agregar, formulario, renombrar):
            assert es_prohibido(respuesta)
        assert taller.nombre == nombre_antes
        assert not Usuario.objects.filter(username="carmen").exists()
        assert costurera.nombre_visible != "Otro nombre"
        # Tampoco se puede desactivar a sí misma (ni a otra).
        desactivar = cliente.post(url_editar, {"accion": "desactivar"})
        costurera.refresh_from_db()
        assert es_prohibido(desactivar) and costurera.is_active


# --- La costurera no recibe plata en ninguna parte ------------------------------------------


@pytest.fixture
def ejemplo():
    """Los datos de ejemplo (T22): el taller, Marta (costurera) y la dueña de ejemplo."""
    taller = ejemplos.cargar(con_fotos=False)
    marta = Usuario.objects.get(username="ejemplo.marta")
    duena = Usuario.objects.get(username="ejemplo.duena")
    return taller, marta, duena


def respuestas_que_puede_abrir(cliente, taller, marta):
    """Cada página y cada parte (HTMX) que la costurera puede abrir con los datos de ejemplo,
    y algunas de sus acciones. Devuelve [(nombre, respuesta)]."""
    hoy = timezone.localdate()
    pedidos = list(Pedido.objects.filter(taller=taller))
    respuestas = [
        ("hoy", cliente.get(reverse("pedidos:hoy"))),
        ("buscar", cliente.get(reverse("pedidos:buscar") + "?q=a")),
        ("telas", cliente.get(reverse("telas:inicio"))),
    ]
    for filtro in ("todos", "produccion", "semana", "atrasados", "saldo", "entregados"):
        url = reverse("pedidos:lista") + f"?filtro={filtro}"
        respuestas.append((f"lista {filtro}", cliente.get(url)))
        respuestas.append((f"lista {filtro} (HTMX)", cliente.get(url + "&q=e", headers=HTMX)))
    for pedido in pedidos:
        respuestas.append((f"pedido {pedido}", cliente.get(
            reverse("pedidos:detalle", args=[pedido.pk]))))
    for meses in range(-2, 4):
        mes = calculos.sumar_meses(hoy.replace(day=1), meses).strftime("%Y-%m")
        respuestas.append((f"calendario {mes}", cliente.get(
            reverse("pedidos:calendario") + f"?mes={mes}")))
    for pedido in pedidos:
        dia = pedido.fecha_entrega
        url = reverse("pedidos:calendario") + f"?mes={dia:%Y-%m}&dia={dia.isoformat()}"
        respuestas.append((f"calendario día {dia}", cliente.get(url, headers=HTMX)))
    for tela in Tela.objects.filter(taller=taller):
        url = reverse("telas:movimiento", args=[tela.pk])
        ventana = {**HTMX, "HX-Target": "ventana"}
        respuestas.append((f"historial {tela}", cliente.get(url, headers=ventana)))
        respuestas.append((f"usé {tela}", cliente.get(url + "?tipo=uso", headers=ventana)))
    # Sus acciones, con HTMX: las partes que vuelven tampoco traen plata.
    suyos = [p for p in pedidos if p.encargada_id == marta.pk]
    listo = next(p for p in suyos if p.estado == Estado.LISTO)
    en_corte = next(p for p in suyos if p.estado == Estado.CORTE)
    respuestas += [
        ("hoy: marcar como entregado", cliente.post(
            reverse("pedidos:hoy_accion", args=[listo.pk, "entregado"]), headers=HTMX)),
        ("pedido: etapa", cliente.post(
            reverse("pedidos:etapa", args=[en_corte.pk]), {"estado": Estado.LISTO},
            headers=HTMX)),
        ("pedido: etapa sin JavaScript", cliente.post(
            reverse("pedidos:etapa", args=[en_corte.pk]), {"estado": "inventada"})),
        ("pedido: talla", cliente.post(
            reverse("pedidos:talla_nueva", args=[en_corte.pk]),
            {"nombre": "Persona nueva", "talla": "M"}, headers=HTMX)),
        ("pedido: talla con error sin JavaScript", cliente.post(
            reverse("pedidos:talla_nueva", args=[en_corte.pk]), {"nombre": ""})),
        ("pedido: material", cliente.post(
            reverse("pedidos:material_nuevo", args=[en_corte.pk]), {"nombre": "Hilo"},
            headers=HTMX)),
        ("pedido: material con error sin JavaScript", cliente.post(
            reverse("pedidos:material_nuevo", args=[en_corte.pk]), {"nombre": ""})),
        ("pedido: foto con error sin JavaScript", cliente.post(
            reverse("pedidos:foto", args=[en_corte.pk]),
            {"foto": SimpleUploadedFile("foto.jpg", b"no soy una foto", "image/jpeg")})),
        ("telas: usé", cliente.post(
            reverse("telas:movimiento", args=[Tela.objects.filter(taller=taller)[0].pk]),
            {"tipo": "uso", "metros": "1"}, headers=_en_telas(reverse("telas:inicio")))),
    ]
    return respuestas


def test_una_costurera_no_recibe_plata_en_ninguna_parte(client, ejemplo):
    """Con los datos de ejemplo: ni total, ni abonos, ni saldo, ni "Por cobrar", ni precios,
    en ninguna página ni parte que puede abrir."""
    taller, marta, _duena = ejemplo
    totales = [f"{p.total:,}".replace(",", ".") for p in Pedido.objects.filter(taller=taller)]
    client.force_login(marta)

    respuestas = respuestas_que_puede_abrir(client, taller, marta)

    for nombre, respuesta in respuestas:
        html = respuesta.content.decode()
        assert respuesta.status_code in (200, 302, 422), nombre
        assert sin_plata(html), (nombre, PLATA.search(html))
        for total in totales:
            assert total not in html, (nombre, total)
        for palabra in ("Por cobrar", "Quién te debe", "Cobrado y gastado", "Cobrar el saldo",
                        "Debe ", "Cotizado en", "Registrar abono", "Saldo"):
            assert palabra not in html, (nombre, palabra)


def test_la_duena_si_ve_la_plata_en_las_mismas_paginas(client, ejemplo):
    """Prueba de la prueba: con la dueña, la misma búsqueda sí encuentra plata."""
    taller, _marta, duena = ejemplo
    client.force_login(duena)

    for url in (reverse("pedidos:hoy"), reverse("pedidos:lista")):
        assert not sin_plata(client.get(url).text)
    pedido = Pedido.objects.filter(taller=taller).first()
    assert not sin_plata(client.get(reverse("pedidos:detalle", args=[pedido.pk])).text)


def test_hoy_de_la_costurera(client, ejemplo):
    """Las cifras de producción sí; la plata no. "Qué hacer hoy" sin valores, y solo marca
    listo o entregado lo que es suyo."""
    taller, marta, _duena = ejemplo
    client.force_login(marta)

    html = client.get(reverse("pedidos:hoy")).text

    for cifra in ("En producción", "Entregas en 7 días", "Atrasados"):
        assert f">{cifra}<" in html
    assert ">Por cobrar<" not in html
    assert 'id="hoy-grafica"' not in html and 'id="hoy-quien-debe"' not in html
    assert "Qué hacer hoy" in html and "Trabajos del taller" in html
    assert 'id="hoy-etapas"' in html
    # El listo es de Marta: lo puede entregar. El atrasado es de Carmen: solo lo ve.
    listo = Pedido.objects.get(taller=taller, estado=Estado.LISTO)
    atrasado = Pedido.objects.get(taller=taller, estado=Estado.CONFECCION)
    assert reverse("pedidos:hoy_accion", args=[listo.pk, "entregado"]) in html
    assert reverse("pedidos:hoy_accion", args=[atrasado.pk, "listo"]) not in html
    assert "Preguntar si confirma" not in html
    assert reverse("finanzas:excel") not in html and reverse("pedidos:nuevo") not in html


def test_hoy_de_la_duena_sigue_con_todo(client, ejemplo):
    taller, _marta, duena = ejemplo
    client.force_login(duena)

    html = client.get(reverse("pedidos:hoy")).text

    assert ">Por cobrar<" in html
    assert 'id="hoy-grafica"' in html and 'id="hoy-quien-debe"' in html
    assert "Cobrar el saldo" in html or "Preguntar si confirma" in html
    assert reverse("finanzas:excel") in html and reverse("pedidos:nuevo") in html


def test_la_costurera_no_ve_nuevo_pedido_ni_excel_en_ninguna_pantalla(entrar, pedido):
    cliente = entrar(COSTURERA)

    for url in (reverse("pedidos:hoy"), reverse("pedidos:lista"), reverse("pedidos:calendario"),
                reverse("pedidos:buscar") + "?q=camisas", reverse("telas:inicio"),
                reverse("pedidos:detalle", args=[pedido.pk])):
        html = cliente.get(url).text
        assert reverse("pedidos:nuevo") not in html, url
        assert reverse("finanzas:excel") not in html, url
        assert reverse("pedidos:eliminar", args=[pedido.pk]) not in html, url


def test_el_buscador_no_le_muestra_clientes_a_la_costurera(entrar, taller, pedido):
    fabricas.crear_cliente(taller, nombre="Camisería sin pedidos")

    duena = entrar(DUENA).get(reverse("pedidos:buscar") + "?q=cami").text
    costurera = entrar(COSTURERA).get(reverse("pedidos:buscar") + "?q=cami").text

    assert "Camisería sin pedidos" in duena and 't-clientes' in duena
    assert "Camisería sin pedidos" not in costurera and 't-clientes' not in costurera
    assert "20 camisas de prueba" in costurera
    assert sin_plata(costurera)


# --- 403 para lo del propio taller, 404 para lo de otro --------------------------------------


@pytest.mark.parametrize("htmx", [False, True])
def test_lo_prohibido_responde_403_con_una_pagina_clara(entrar, htmx):
    headers = HTMX if htmx else {}

    respuesta = entrar(COSTURERA).get(reverse("finanzas:resumen"), headers=headers)

    assert respuesta.status_code == 403
    assert "<h1>Sin permiso</h1>" in respuesta.text
    assert SOLO_LA_DUENA in respuesta.text
    assert "Volver a Hoy" in respuesta.text
    assert 'class="menu"' in respuesta.text  # con el marco y el menú de siempre


@pytest.mark.parametrize("nombre", [n for n in direcciones_con_numero() if n not in SIN_TALLER])
def test_con_el_numero_de_otro_taller_la_costurera_recibe_404(entrar, nombre):
    """Primero el taller y después el rol: lo de otro taller es "no encontrado", también
    para la costurera, para no revelar que existe."""
    cliente = entrar(COSTURERA)
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

    respuestas = {cliente.get(url).status_code, cliente.post(url).status_code}

    assert 404 in respuestas
    assert respuestas <= {404, 405}


# --- El menú de cada rol --------------------------------------------------------------------

SOLO_DE_LA_DUENA = ("pedidos:clientes", "cotizador:inicio", "finanzas:resumen",
                    "cuentas:mi_taller")


@pytest.mark.parametrize("rol", ROLES)
def test_el_menu_de_cada_rol(entrar, rol):
    """Lateral, barra de abajo y "Más": la costurera no ve lo que no puede abrir."""
    html = entrar(rol).get(reverse("pedidos:hoy")).text
    lateral = re.findall(r'class="menu__texto">([^<]+)<', html)
    barra = re.findall(r'class="navegacion-celular__enlace[^"]*"[^>]*>.*?</svg>([^<]+)<', html)
    mas = html.split('id="panel-mas"')[1]

    if rol == DUENA:
        assert lateral == ["Hoy", "Pedidos", "Calendario", "Clientes", "Cotizador", "Telas",
                           "Resumen", "Mi taller", "Salir"]
        assert barra == ["Hoy", "Pedidos", "Calendario", "Clientes", "Más"]
        for nombre in SOLO_DE_LA_DUENA:
            assert f'href="{reverse(nombre)}"' in html
        assert mas.count("panel-mas__enlace") == 6
    else:
        assert lateral == ["Hoy", "Pedidos", "Calendario", "Telas", "Salir"]
        assert barra == ["Hoy", "Pedidos", "Calendario", "Telas", "Más"]
        for nombre in SOLO_DE_LA_DUENA:
            assert f'href="{reverse(nombre)}"' not in html
        # En "Más" solo quedan "Buscar pedidos" y "Salir".
        assert mas.count("panel-mas__enlace") == 2
        assert "Buscar pedidos<" in mas


# --- Usuarias desactivadas, sesión y administrador ------------------------------------------


def test_una_costurera_desactivada_no_puede_entrar_y_sus_pedidos_quedan(client, taller, duena,
                                                                         pedido):
    marta = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Marta")
    pedido.encargada = marta
    pedido.save()
    client.force_login(duena)
    client.post(reverse("cuentas:costurera_editar", args=[marta.pk]), {"accion": "desactivar"})
    client.logout()

    respuesta = client.post(reverse("cuentas:entrar"),
                            {"username": marta.username, "password": CLAVE})

    assert respuesta.status_code == 200  # se queda en la página de entrada
    assert "_auth_user_id" not in client.session
    pedido.refresh_from_db()
    assert pedido.encargada == marta
    assert Pedido.objects.filter(pk=pedido.pk).exists()


def test_si_la_desactivan_con_la_sesion_abierta_ya_no_entra(client, taller):
    marta = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA)
    client.force_login(marta)
    marta.is_active = False
    marta.save()

    respuesta = client.get(reverse("pedidos:hoy"))

    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse("cuentas:entrar"))


@pytest.mark.parametrize("nombre", ["pedidos:hoy", "pedidos:lista", "pedidos:calendario",
                                    "telas:inicio", "finanzas:resumen", "cuentas:mi_taller"])
def test_sin_sesion_las_pantallas_internas_llevan_a_entrar(client, nombre):
    respuesta = client.get(reverse(nombre))

    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse("cuentas:entrar"))


def test_el_administrador_sigue_yendo_al_panel(sesion_administrador):
    for nombre in ("pedidos:hoy", "finanzas:resumen", "cuentas:mi_taller"):
        respuesta = sesion_administrador.get(reverse(nombre))
        assert respuesta.status_code == 302
        assert respuesta.url == reverse("admin:index")


def test_un_taller_sin_dueña_no_cambia_nada_para_sus_costureras(client):
    """El rol es de la persona, no del taller: una costurera sola sigue sin ver la plata."""
    taller = Taller.objects.create(nombre="Taller solo con costurera")
    sola = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA)
    client.force_login(sola)

    assert client.get(reverse("finanzas:resumen")).status_code == 403
    assert sin_plata(client.get(reverse("pedidos:hoy")).text)
