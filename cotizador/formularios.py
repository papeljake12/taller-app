"""Formulario del cotizador (T15): para quién, qué prenda, cuánto cuesta hacer una y la
ganancia.

Un solo formulario sirve para todo: calcular mientras se escribe, guardar la prenda en
"Mis prendas" y crear el pedido. Para calcular nada es obligatorio (lo vacío cuenta como 0,
como en la demo); lo que se exige para crear el pedido o guardar la prenda se pide aparte,
con exigir_para_pedido y exigir_nombre.

Los valores se escriben como los escribe la gente:
- la plata con o sin puntos de mil y con o sin el signo $ ("18000", "18.000", "$ 18.000"),
  con la misma regla de los abonos y los gastos (pedidos/formularios/comun.py);
- los metros con coma o con punto ("1,2" o "1.2");
- los porcentajes, en números enteros ("30").

Las cuentas no se hacen aquí: cotizacion() le pasa los valores a calculos.cotizar.
"""

from decimal import Decimal, InvalidOperation

from django import forms

from cotizador.models import PrendaGuardada
from pedidos import calculos
from pedidos.formularios.comun import MAXIMO_PESOS, CampoPesos
from pedidos.formularios.lista import NuevoPedidoForm
from pedidos.models import Cliente

# Los metros de tela por prenda caben en PrendaGuardada.metros: hasta 9999,99.
METROS_MAXIMOS = Decimal("9999.99")

# Los campos que entran en el precio, en el orden en que los pide calculos.cotizar.
CAMPOS_DEL_PRECIO = (
    "metros", "precio_metro", "insumos", "mano_obra", "extra", "ganancia", "cantidad", "abono",
)

# Los costos que se guardan en "Mis prendas" (con el nombre de la prenda).
CAMPOS_DE_LA_PRENDA = ("metros", "precio_metro", "insumos", "mano_obra", "extra")


class CampoCosto(CampoPesos):
    """Un costo en pesos. Vacío o 0 se aceptan: es lo que no lleva la prenda (cuenta como 0)."""

    default_error_messages = {
        "invalid": "Escribe solo el valor en pesos, por ejemplo 18.000.",
        "grande": "Revisa el valor: es demasiado grande.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault(
            "widget", forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"})
        )
        super().__init__(**kwargs)

    def validate(self, value):
        if value is not None and value > MAXIMO_PESOS:
            raise forms.ValidationError(self.error_messages["grande"], code="grande")


def texto_de_metros(numero):
    """1.20 -> "1,2": los metros como se escriben en el campo (coma y sin ceros de más)."""
    if not numero:
        return ""
    return f"{Decimal(numero).normalize():f}".replace(".", ",")


def _entero(texto):
    """'18000' para el campo; '' si es 0 (el campo queda vacío, como en la demo)."""
    return str(texto) if texto else ""


class FormularioCotizacion(forms.Form):
    # --- Para quién ---
    cliente = forms.CharField(
        label="Cliente",
        max_length=80,
        required=False,
        error_messages={"max_length": "El nombre es muy largo: usa máximo 80 letras."},
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    tipo = forms.ChoiceField(
        label="Tipo de cliente",
        choices=Cliente.Tipo.choices,
        # Como en la demo: el cotizador empieza en "Empresa".
        initial=Cliente.Tipo.EMPRESA,
        error_messages={
            "required": "Elige el tipo de cliente.",
            "invalid_choice": "Elige uno de los tipos de la lista.",
        },
    )
    whatsapp = forms.CharField(
        label="WhatsApp (opcional)",
        max_length=40,
        required=False,
        error_messages={"max_length": "El número es muy largo: usa máximo 40 caracteres."},
        widget=forms.TextInput(
            attrs={"type": "tel", "inputmode": "tel", "placeholder": "Ej.: 300 123 4567",
                   "autocomplete": "off"}
        ),
    )

    # --- Qué prenda ---
    guardada = forms.ModelChoiceField(
        label="Mis prendas guardadas",
        queryset=PrendaGuardada.objects.none(),
        required=False,
        empty_label="Mis prendas guardadas",
        error_messages={"invalid_choice": "Elige una de tus prendas guardadas."},
    )
    # La prenda guardada que ya se pasó a los campos. Si `guardada` cambia, hay que pasarla.
    aplicada = forms.CharField(required=False, widget=forms.HiddenInput)
    prenda = forms.CharField(
        label="Prenda",
        max_length=80,
        required=False,
        error_messages={"max_length": "Es muy largo: usa máximo 80 letras."},
        widget=forms.TextInput(
            attrs={"placeholder": "Ej.: Camisa polo bordada", "autocomplete": "off"}
        ),
    )
    cantidad = forms.IntegerField(
        label="Cantidad",
        required=False,
        min_value=1,
        max_value=2000,
        error_messages={
            "invalid": "Escribe la cantidad con un número entero, por ejemplo 20.",
            "min_value": "Escribe una cantidad entre 1 y 2000.",
            "max_value": "Escribe una cantidad entre 1 y 2000.",
        },
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "step": "1"}),
    )
    entrega = forms.DateField(
        label="Entrega estimada",
        required=False,
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        error_messages={"invalid": "Elige una fecha de entrega que exista."},
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    # --- Cuánto cuesta hacer una ---
    metros = forms.CharField(
        label="Metros de tela",
        max_length=12,
        required=False,
        error_messages={"max_length": "Escribe los metros con números, por ejemplo 1,2."},
        widget=forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}),
    )
    precio_metro = CampoCosto(label="Precio del metro")
    insumos = CampoCosto(label="Insumos")
    mano_obra = CampoCosto(label="Mano de obra")
    extra = CampoCosto(label="Bordado o estampado")

    # --- Tu ganancia ---
    ganancia = forms.IntegerField(
        label="Ganancia sobre el costo (%)",
        required=False,
        initial=30,
        min_value=0,
        max_value=1000,
        error_messages={
            "invalid": "Escribe la ganancia con un número entero, por ejemplo 30.",
            "min_value": "La ganancia no puede ser menor que 0.",
            "max_value": "Revisa la ganancia: es demasiado alta.",
        },
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "step": "1"}),
    )
    abono = forms.IntegerField(
        label="Abono para empezar (%)",
        required=False,
        initial=50,
        min_value=0,
        max_value=100,
        error_messages={
            "invalid": "Escribe el abono con un número entero, por ejemplo 50.",
            # "%%" se ve como "%": Django completa estos mensajes con el límite.
            "min_value": "El abono va de 0 a 100 %%.",
            "max_value": "El abono va de 0 a 100 %%.",
        },
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "step": "1"}),
    )

    def __init__(self, *args, prendas, **kwargs):
        """`prendas`: las prendas guardadas del taller (del_taller), para elegir una."""
        # Los ids empiezan por "cot-" para no chocar con los de la ventana "Nuevo pedido",
        # que se puede abrir encima de esta pantalla (también tiene cliente, tipo...).
        kwargs.setdefault("auto_id", "cot-%s")
        super().__init__(*args, **kwargs)
        self.fields["guardada"].queryset = prendas
        # Una prenda que ya no está (se quitó en otra pestaña) o que no es del taller no
        # traba el formulario: se toma como si no se hubiera elegido ninguna.
        elegida = str(self.data.get("guardada", "")) if self.is_bound else ""
        if elegida and not (elegida.isdigit() and prendas.filter(pk=int(elegida)).exists()):
            self.data = self.data.copy()
            self.data["guardada"] = ""

    # --- Limpieza de cada campo ---

    def clean_cliente(self):
        # Sin espacios de más, como en "Nuevo pedido": "Marcela  P." es "Marcela P.".
        return " ".join(self.cleaned_data["cliente"].split())

    def clean_prenda(self):
        return " ".join(self.cleaned_data["prenda"].split())

    # El número de WhatsApp se revisa igual que en "Nuevo pedido".
    clean_whatsapp = NuevoPedidoForm.clean_whatsapp

    def clean_metros(self):
        texto = self.cleaned_data["metros"].strip().replace(",", ".")
        if not texto:
            return None
        try:
            numero = Decimal(texto)
        except InvalidOperation:
            numero = None
        if numero is None or not numero.is_finite() or numero < 0:
            raise forms.ValidationError("Escribe los metros con números, por ejemplo 1,2.")
        if numero.as_tuple().exponent < -2:
            raise forms.ValidationError("Usa máximo dos decimales, por ejemplo 1,25.")
        if numero > METROS_MAXIMOS:
            raise forms.ValidationError("Revisa los metros: son demasiados para una prenda.")
        return numero

    # --- El precio ---

    def valores(self):
        """Lo que entra en el precio. Lo vacío o mal escrito cuenta como 0."""
        if not self.is_bound:
            return {nombre: self.fields[nombre].initial for nombre in CAMPOS_DEL_PRECIO}
        self.is_valid()
        return {nombre: self.cleaned_data.get(nombre) for nombre in CAMPOS_DEL_PRECIO}

    def cotizacion(self):
        """El resultado de calculos.cotizar con lo que se escribió."""
        valores = self.valores()
        return calculos.cotizar(*(valores[nombre] for nombre in CAMPOS_DEL_PRECIO))

    def dato(self, nombre):
        """El valor limpio de un campo ('' o None si falta o está mal escrito)."""
        if not self.is_bound:
            return self.fields[nombre].initial or ""
        self.is_valid()
        return self.cleaned_data.get(nombre) or ""

    def lista(self, cotizacion):
        """True si ya hay algo que mandar: la prenda, una cantidad y un precio."""
        return bool(self.dato("prenda")) and cotizacion.total > 0

    def errores_del_precio(self):
        """Los errores de los campos que cambian el precio, para mostrarlos junto al total.

        Mientras se escribe no se dicen los demás (un WhatsApp a medio escribir, por
        ejemplo): esos se revisan al crear el pedido.
        """
        if not self.is_bound or self.is_valid():
            return []
        return [
            f"{self.fields[nombre].label}: {mensaje}"
            for nombre in CAMPOS_DEL_PRECIO
            for mensaje in self.errors.get(nombre, [])
        ]

    # --- Lo que se exige para cada acción ---

    def exigir_para_pedido(self):
        """True si se puede crear el pedido; si no, deja los mensajes en cada campo."""
        if not self.is_valid():
            return False
        if not self.cleaned_data["cliente"]:
            self.add_error("cliente", "Escribe el nombre del cliente para crear el pedido.")
        if not self.cleaned_data["prenda"]:
            self.add_error("prenda", "Escribe qué prenda es.")
        if not self.cleaned_data["cantidad"]:
            self.add_error("cantidad", "Escribe cuántas prendas son.")
        if not self.errors and self.cotizacion().precio_unidad <= 0:
            self.add_error(None, "Escribe lo que cuesta hacer una para calcular el precio.")
        return not self.errors

    def exigir_nombre(self):
        """True si se puede guardar la prenda: hace falta su nombre (el campo Prenda)."""
        if not self.is_valid():
            return False
        if not self.cleaned_data["prenda"]:
            self.add_error("prenda", "Escribe el nombre de la prenda para guardarla.")
        return not self.errors


def datos_con_la_prenda(datos, prenda):
    """Los datos del formulario con la prenda guardada ya pasada a sus campos.

    Si `prenda` es None (se eligió "Mis prendas guardadas", sin prenda), solo se deja de
    marcar como elegida: lo escrito se queda como estaba.
    """
    nuevos = datos.copy()
    nuevos["guardada"] = nuevos["aplicada"] = str(prenda.pk) if prenda else ""
    if prenda:
        nuevos["prenda"] = prenda.nombre
        nuevos["metros"] = texto_de_metros(prenda.metros)
        for nombre in ("precio_metro", "insumos", "mano_obra", "extra"):
            nuevos[nombre] = _entero(getattr(prenda, nombre))
    return nuevos
