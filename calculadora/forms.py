# calculadora/forms.py
from django import forms
from .models import ConsumoTela, Producto

class CalculadoraForm(forms.Form):
    consumo = forms.ModelChoiceField(
        queryset=ConsumoTela.objects.all(),
        label="Seleccionar Consumo",
        empty_label="-- Seleccione --"
    )
    metros_tela = forms.DecimalField(
        label="Metros de tela",
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostramos tela + configuración en el select
        self.fields['consumo'].label_from_instance = lambda obj: f"{obj.tela.nombre} ({obj.configuracion.nombre})"
        # Agregamos clase bootstrap al select
        self.fields['consumo'].widget.attrs.update({'class': 'form-select'})

# Calculadora Materiales
class CalculadoraMaterialesForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=True),
        label="Producto",
        empty_label="-- Seleccione un producto --"
    )

    cantidad = forms.DecimalField(
        label="Cantidad a producir",
        min_value=1,
        decimal_places=2
    )