"""Fábricas de datos para las pruebas.

Crean talleres y usuarias de prueba con valores que no se repiten. Son datos inventados
que solo existen dentro de la base temporal de las pruebas.
"""

import itertools

from cuentas.models import Taller, Usuario

CLAVE = "clave-de-prueba-123"

_numero = itertools.count(1)


def crear_taller(nombre=None, **campos):
    numero = next(_numero)
    return Taller.objects.create(nombre=nombre or f"Taller de prueba {numero}", **campos)


def crear_usuaria(taller, rol=Usuario.Rol.DUENA, username=None, password=CLAVE, **campos):
    numero = next(_numero)
    campos.setdefault("nombre_visible", f"Usuaria {numero}")
    return Usuario.objects.create_user(
        username=username or f"usuaria{numero}",
        password=password,
        taller=taller,
        rol=rol,
        **campos,
    )


def crear_administrador(username="admin", password=CLAVE):
    return Usuario.objects.create_superuser(username=username, email="", password=password)


# --- Tanda 2: los demás modelos -------------------------------------------------------------


def _duena_de(taller):
    """La primera dueña del taller; si no hay, crea una."""
    from cuentas.models import Usuario

    return Usuario.objects.filter(taller=taller, rol=Usuario.Rol.DUENA).first() or crear_usuaria(
        taller
    )


def crear_cliente(taller, nombre=None, **campos):
    from pedidos.models import Cliente

    return Cliente.objects.create(
        taller=taller, nombre=nombre or f"Cliente de prueba {next(_numero)}", **campos
    )


def crear_pedido(taller, cliente=None, **campos):
    from datetime import timedelta

    from django.utils import timezone

    from pedidos.models import Pedido

    campos.setdefault("detalle", f"Pedido de prueba {next(_numero)}")
    campos.setdefault("cantidad", 10)
    campos.setdefault("fecha_entrega", timezone.localdate() + timedelta(days=30))
    campos.setdefault("total", 1_000_000)
    campos.setdefault("creado_por", _duena_de(taller))
    return Pedido.objects.create(
        taller=taller, cliente=cliente or crear_cliente(taller), **campos
    )


def crear_abono(pedido, valor=100_000, **campos):
    from pedidos.models import Abono

    campos.setdefault("registrado_por", _duena_de(pedido.taller))
    return Abono.objects.create(pedido=pedido, valor=valor, **campos)


def crear_talla(pedido, talla="M", **campos):
    from pedidos.models import Talla

    campos.setdefault("nombre", f"Persona {next(_numero)}")
    return Talla.objects.create(pedido=pedido, talla=talla, **campos)


def crear_material(pedido, nombre=None, **campos):
    from pedidos.models import Material

    return Material.objects.create(
        pedido=pedido, nombre=nombre or f"Material {next(_numero)}", **campos
    )


def crear_tela(taller, nombre=None, metros=10, minimo=0, **campos):
    from telas.models import Tela

    return Tela.objects.create(
        taller=taller, nombre=nombre or f"Tela {next(_numero)}", metros=metros, minimo=minimo,
        **campos,
    )


def crear_movimiento(tela, metros=5, **campos):
    from telas.models import MovimientoTela

    campos.setdefault("usuario", _duena_de(tela.taller))
    return MovimientoTela.objects.create(tela=tela, metros=metros, **campos)


def crear_gasto(taller, valor=50_000, **campos):
    from finanzas.models import Gasto

    campos.setdefault("concepto", f"Gasto {next(_numero)}")
    return Gasto.objects.create(taller=taller, valor=valor, **campos)


def crear_prenda(taller, nombre=None, **campos):
    from cotizador.models import PrendaGuardada

    return PrendaGuardada.objects.create(
        taller=taller, nombre=nombre or f"Prenda {next(_numero)}", **campos
    )


# --- Tanda 7: el asistente ------------------------------------------------------------------


def crear_uso(taller, fecha=None, preguntas=1, **campos):
    """Un día de uso del asistente. Sin fecha, hoy (hora de Bogotá); si hoy ya tiene registro,
    el día de antes que esté libre (hay uno solo por taller y día)."""
    from datetime import timedelta

    from django.utils import timezone

    from asistente.models import UsoAsistente

    if fecha is None:
        fecha = timezone.localdate()
        while UsoAsistente.objects.filter(taller=taller, fecha=fecha).exists():
            fecha -= timedelta(days=1)
    return UsoAsistente.objects.create(taller=taller, fecha=fecha, preguntas=preguntas, **campos)
