"""Piezas comunes para todas las pruebas (pytest las encuentra solas)."""

import pytest

from cuentas.models import Usuario
from tests import fabricas


@pytest.fixture
def taller(db):
    return fabricas.crear_taller()


@pytest.fixture
def duena(taller):
    return fabricas.crear_usuaria(taller, rol=Usuario.Rol.DUENA)


@pytest.fixture
def costurera(taller):
    return fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA)


@pytest.fixture
def administrador(db):
    return fabricas.crear_administrador()


@pytest.fixture
def sesion_duena(client, duena):
    """Un navegador de prueba con la sesión de la dueña ya abierta."""
    client.force_login(duena)
    return client


@pytest.fixture
def sesion_administrador(client, administrador):
    client.force_login(administrador)
    return client
