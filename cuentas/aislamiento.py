"""Aislamiento entre talleres: la única forma de leer y escribir datos de un taller.

Reglas (docs/04-permisos.md):

1. Toda consulta se filtra por el taller de la usuaria que inició sesión.
2. Pedir por la dirección algo de otro taller responde 404 ("no encontrado"), nunca
   "sin permiso", para no revelar que existe.

Cómo se declara un modelo que guarda datos de un taller:

    from cuentas.aislamiento import DelTallerQuerySet, ModeloDeTaller

    class Cliente(ModeloDeTaller):         # trae el campo `taller` y `.del_taller()`
        nombre = models.CharField(...)

    class Abono(models.Model):             # no tiene taller propio: lo toma de su pedido
        ruta_taller = "pedido__taller"
        objects = DelTallerQuerySet.as_manager()

Cómo se usa en una vista:

    from cuentas.aislamiento import del_taller, obtener_o_404

    def lista(request):
        pedidos = del_taller(request, Pedido)            # solo los de su taller

    def detalle(request, pk):
        pedido = obtener_o_404(request, Pedido, pk=pk)   # 404 si es de otro taller

    def crear(request):
        cliente.taller = request.taller                  # el taller nunca llega del formulario

Y en formularios, las listas para elegir también se filtran:

    form.fields["encargada"].queryset = del_taller(request, Usuario)
"""

from django.db import models
from django.shortcuts import get_object_or_404, redirect


class DelTallerQuerySet(models.QuerySet):
    """Consultas que saben filtrar por taller."""

    def del_taller(self, taller):
        """Solo los registros de ese taller. Sin taller, ninguno."""
        if taller is None:
            return self.none()
        ruta = getattr(self.model, "ruta_taller", "taller")
        return self.filter(**{ruta: taller})


class ModeloDeTaller(models.Model):
    """Base para los modelos que pertenecen a un taller.

    El campo `taller` no aparece en los formularios (editable=False): siempre lo pone la
    vista con `request.taller`, nunca llega de lo que envía el navegador.
    """

    taller = models.ForeignKey(
        "cuentas.Taller",
        verbose_name="taller",
        on_delete=models.CASCADE,
        editable=False,
    )

    objects = DelTallerQuerySet.as_manager()

    class Meta:
        abstract = True


def del_taller(request, modelo_o_consulta):
    """Los registros del taller de la usuaria. Acepta un modelo o una consulta ya armada."""
    if isinstance(modelo_o_consulta, type):
        consulta = modelo_o_consulta._default_manager.all()
    else:
        consulta = modelo_o_consulta
    return consulta.del_taller(getattr(request, "taller", None))


def obtener_o_404(request, modelo_o_consulta, **filtros):
    """Un registro del taller de la usuaria. Si no existe o es de otro taller: 404."""
    return get_object_or_404(del_taller(request, modelo_o_consulta), **filtros)


def sin_taller(vista):
    """Marca una vista que también puede usar el administrador, que no tiene taller."""
    vista.necesita_taller = False
    return vista


class TallerMiddleware:
    """Deja en `request.taller` el taller de la usuaria que inició sesión.

    El administrador no tiene taller. Si abre una pantalla de la aplicación, se le lleva
    al panel de administración, que es lo suyo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        request.taller = usuario.taller if usuario.is_authenticated else None
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.taller is not None or not request.user.is_authenticated:
            return None
        es_publica = getattr(view_func, "login_required", True) is False
        no_lo_necesita = getattr(view_func, "necesita_taller", True) is False
        es_del_panel = "admin" in request.resolver_match.namespaces
        if es_publica or no_lo_necesita or es_del_panel:
            return None
        return redirect("admin:index")
