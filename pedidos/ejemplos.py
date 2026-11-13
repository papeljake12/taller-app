"""Datos de ejemplo (T22): los mismos pedidos, tallas, telas y gastos de las páginas de diseno/.

Todo es inventado. Va en un taller aparte ("Taller de ejemplo") y cada cliente lleva la nota
"Dato de ejemplo.". Las fechas se cuentan desde `hoy`, como en la demo: así "Atrasado 2
días" o "Faltan 3 días" se ven igual cualquier día que se carguen.

Lo usan el comando `cargar_ejemplos` y las pruebas que comparan los cálculos con diseno/.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils import timezone

from cotizador.models import PrendaGuardada
from cuentas.models import Taller, Usuario
from finanzas.models import Gasto
from pedidos.models import Abono, Cliente, Material, Pedido, Talla
from telas.models import MovimientoTela, Tela

NOMBRE_TALLER = "Taller de ejemplo"
MARCA = "Dato de ejemplo."
FOTOS = Path(settings.BASE_DIR) / "diseno" / "img"

# Costureras de ejemplo: (usuario, nombre visible). Entran solo si alguien les pone
# contraseña en el panel de administración.
COSTURERAS = (("ejemplo.marta", "Marta"), ("ejemplo.yolima", "Yolima"), ("ejemplo.carmen", "Carmen"))
DUENA = ("ejemplo.duena", "Dueña de ejemplo")


@dataclass
class PedidoDeEjemplo:
    cliente: str
    tipo: str
    detalle: str
    cantidad: int
    tallaje: str
    entrega: int  # días desde hoy (negativo: ya pasó)
    total: int
    estado: str
    creado: int  # días desde hoy
    encargada: str = ""
    abonos: list = field(default_factory=list)  # [(días desde hoy, valor), ...]
    tallas: list = field(default_factory=list)
    materiales: list = field(default_factory=list)  # [(nombre, cantidad, comprado), ...]
    foto: str = ""  # archivo de diseno/img


PEDIDOS = (
    PedidoDeEjemplo(
        "Comparsa Brisa Caribe", "comparsa", "12 vestidos de fantasía", 12, "adulto",
        entrega=-5, total=2_400_000, estado="entregado", creado=-42,
        abonos=[(-40, 1_200_000), (-5, 1_200_000)],
        tallas=["XS", "S", "S", "M", "M", "M", "M", "L", "L", "S", "M", "XL"],
        foto="foto-fiesta.jpg",
    ),
    PedidoDeEjemplo(
        "Restaurante El Fogón Costeño", "empresa", "18 camisas polo bordadas y 18 delantales",
        18, "adulto", entrega=33, total=2_520_000, estado="corte", creado=-8, encargada="Marta",
        abonos=[(-6, 1_260_000)],
        tallas=["S", "M", "M", "L", "M", "S", "L", "XL", "M", "L", "M", "S", "XL", "M"],
        materiales=[
            ("Tela piqué blanca", "22 m", True),
            ("Dril para delantales", "16 m", True),
            ("Hilo para bordar", "6 conos", False),
            ("Botones", "60", False),
        ],
    ),
    PedidoDeEjemplo(
        "Colegio Nuevo Amanecer", "colegio", "40 uniformes de diario", 40, "nino",
        entrega=62, total=4_800_000, estado="confirmado", creado=-4, encargada="Yolima",
        abonos=[(-3, 1_500_000)],
        tallas=["8", "10", "10", "12", "6", "14", "12", "10", "8"],
        materiales=[
            ("Tela para camisas", "50 m", False),
            ("Tela para pantalón y falda", "60 m", False),
        ],
    ),
    PedidoDeEjemplo(
        "Ferretería La Esquina", "empresa", "8 overoles con logo estampado", 8, "adulto",
        entrega=-2, total=960_000, estado="confeccion", creado=-22, encargada="Carmen",
        abonos=[(-20, 480_000)],
        tallas=["M", "L", "L", "XL", "M", "L", "XXL", "L"],
        materiales=[("Dril azul", "24 m", True), ("Cierres largos", "8", True)],
    ),
    PedidoDeEjemplo(
        "Grupo de danza Tambores del Río", "comparsa", "15 polleras con blusa", 15, "adulto",
        entrega=3, total=2_250_000, estado="listo", creado=-27, encargada="Marta",
        abonos=[(-25, 1_000_000), (-9, 500_000)],
        tallas=["S", "S", "M", "M", "M", "S", "L", "M", "XS", "S", "M", "L", "M", "S", "M"],
        materiales=[("Tela estampada", "45 m", True), ("Encaje y boleros", "30 m", True)],
        foto="foto-comparsa.jpg",
    ),
    PedidoDeEjemplo(
        "Marcela P.", "particular", "Vestido de grado a la medida", 1, "adulto",
        entrega=20, total=380_000, estado="cotizado", creado=-1,
        foto="foto-grado.jpg",
    ),
)

NOMBRES_TALLAS = (
    "Laura M.", "Andrés P.", "Yuleidis R.", "Carlos T.", "María J.", "Kevin O.", "Daniela C.",
    "Luis F.", "Paola V.", "Jhon E.", "Sandra B.", "Óscar D.", "Karen L.", "Jesús A.",
    "Natalia G.", "Wilson H.", "Dayana S.", "Roberto N.", "Milena Z.", "Fabián Q.",
)

# (días desde hoy, concepto, categoría, valor)
GASTOS = (
    (-7, "Tela piqué blanca, 22 m", "telas", 396_000),
    (-7, "Dril para delantales, 16 m", "telas", 288_000),
    (-5, "Hilos y botones", "insumos", 85_000),
    (-5, "Transporte de telas", "otros", 30_000),
    (-2, "Recibo de luz del taller", "servicios", 140_000),
)

# (nombre, metros que quedan, mínimo para avisar)
TELAS = (
    ("Dril azul", "18", "10"),
    ("Piqué blanco", "6", "10"),
    ("Tela estampada para polleras", "32", "8"),
    ("Popelina blanca", "4", "12"),
)

# (nombre, metros, precio del metro, insumos, mano de obra, extra)
PRENDAS = (
    ("Camisa polo bordada", "1.2", 18_000, 3_000, 12_000, 5_000),
    ("Overol con logo", "3", 22_000, 6_000, 25_000, 4_000),
    ("Uniforme de diario", "2.2", 16_000, 4_000, 20_000, 0),
    ("Vestido de comparsa", "4", 20_000, 15_000, 45_000, 0),
)


def _usuaria(taller, usuario, nombre, rol):
    persona, creada = Usuario.objects.get_or_create(
        username=usuario,
        defaults={"taller": taller, "rol": rol, "nombre_visible": nombre},
    )
    if creada:
        persona.set_unusable_password()
        persona.save(update_fields=["password"])
    elif persona.taller_id != taller.pk:
        raise ValueError(f"El usuario {usuario} ya existe en otro taller ({persona.taller}).")
    return persona


def _a_las_diez(dia):
    return timezone.make_aware(datetime.combine(dia, time(10, 0)))


def borrar_datos(taller):
    """Borra pedidos, clientes, telas, gastos y prendas del taller. Las usuarias se quedan."""
    Gasto.objects.filter(taller=taller).delete()
    for pedido in Pedido.objects.filter(taller=taller).exclude(foto=""):
        pedido.foto.delete(save=False)
    Pedido.objects.filter(taller=taller).delete()
    Cliente.objects.filter(taller=taller).delete()
    Tela.objects.filter(taller=taller).delete()
    PrendaGuardada.objects.filter(taller=taller).delete()


@transaction.atomic
def cargar(taller=None, hoy=None, con_fotos=True):
    """Carga (o vuelve a cargar) los ejemplos en el taller. Devuelve el taller."""
    hoy = hoy or timezone.localdate()
    if taller is None:
        taller, _ = Taller.objects.get_or_create(nombre=NOMBRE_TALLER)
    borrar_datos(taller)

    def dia(dias):
        return hoy + timedelta(days=dias)

    duena = (
        Usuario.objects.filter(taller=taller, rol=Usuario.Rol.DUENA, is_active=True)
        .order_by("pk")
        .first()
    ) or _usuaria(taller, *DUENA, Usuario.Rol.DUENA)
    equipo = {
        nombre: _usuaria(taller, usuario, nombre, Usuario.Rol.COSTURERA)
        for usuario, nombre in COSTURERAS
    }

    for k, datos in enumerate(PEDIDOS):
        cliente = Cliente.objects.create(
            taller=taller, nombre=datos.cliente, tipo=datos.tipo, notas=MARCA
        )
        pedido = Pedido(
            taller=taller,
            cliente=cliente,
            detalle=datos.detalle,
            cantidad=datos.cantidad,
            tallaje=datos.tallaje,
            fecha_entrega=dia(datos.entrega),
            total=datos.total,
            estado=datos.estado,
            encargada=equipo.get(datos.encargada),
            creado_por=duena,
            creado=_a_las_diez(dia(datos.creado)),
        )
        if con_fotos and datos.foto:
            with open(FOTOS / datos.foto, "rb") as archivo:
                pedido.foto.save(f"ejemplo-{datos.foto}", File(archivo), save=False)
        pedido.save()
        Abono.objects.bulk_create(
            Abono(pedido=pedido, fecha=dia(dias), valor=valor, registrado_por=duena)
            for dias, valor in datos.abonos
        )
        Talla.objects.bulk_create(
            Talla(
                pedido=pedido,
                nombre=NOMBRES_TALLAS[(i + k * 3) % len(NOMBRES_TALLAS)],
                talla=talla,
                origen=Talla.Origen.ENLACE,
            )
            for i, talla in enumerate(datos.tallas)
        )
        Material.objects.bulk_create(
            Material(pedido=pedido, nombre=nombre, cantidad=cantidad, comprado=comprado)
            for nombre, cantidad, comprado in datos.materiales
        )

    Gasto.objects.bulk_create(
        Gasto(taller=taller, fecha=dia(dias), concepto=concepto, categoria=categoria, valor=valor)
        for dias, concepto, categoria, valor in GASTOS
    )
    for nombre, metros, minimo in TELAS:
        tela = Tela.objects.create(
            taller=taller, nombre=nombre, metros=Decimal(metros), minimo=Decimal(minimo)
        )
        MovimientoTela.objects.create(
            tela=tela, metros=Decimal(metros), usuario=duena, fecha=_a_las_diez(dia(-10))
        )
    PrendaGuardada.objects.bulk_create(
        PrendaGuardada(
            taller=taller, nombre=nombre, metros=Decimal(metros), precio_metro=precio,
            insumos=insumos, mano_obra=mano, extra=extra,
        )
        for nombre, metros, precio, insumos, mano, extra in PRENDAS
    )
    return taller
