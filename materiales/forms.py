from django import forms
from django.utils import timezone
from .models import ConsumoTela, Inventario, MovimientoInventario, AlertaStock, PedidoCompra
from datetime import datetime, timedelta
from produccion.models import Producto

# ============ FORMULARIOS EXISTENTES ============ #
class CalculadoraHiloForm(forms.Form):
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
        self.fields['consumo'].label_from_instance = lambda obj: f"{obj.tela.nombre} ({obj.configuracion.nombre})"
        self.fields['consumo'].widget.attrs.update({'class': 'form-select'})

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

# ============ FORMULARIOS NUEVOS ============ #
class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['material', 'cantidad_actual', 'cantidad_minima', 'cantidad_maxima',
                 'ubicacion', 'codigo_ubicacion', 'costo_promedio', 'costo_ultima_compra',
                 'activo', 'bloqueado']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_actual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'cantidad_minima': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'cantidad_maxima': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'costo_promedio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'costo_ultima_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class MovimientoInventarioForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = ['inventario', 'tipo', 'origen', 'cantidad_movimiento',
                 'costo_unitario', 'referencia', 'orden_produccion', 'lote',
                 'motivo', 'observaciones', 'fecha_documento']
        widgets = {
            'inventario': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'origen': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_movimiento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control'}),
            'orden_produccion': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'fecha_documento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class AlertaStockForm(forms.ModelForm):
    class Meta:
        model = AlertaStock
        fields = ['material', 'inventario', 'tipo', 'nivel', 'descripcion',
                 'cantidad_actual', 'cantidad_umbral', 'activa']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select'}),
            'inventario': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cantidad_actual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'cantidad_umbral': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
        }

class PedidoCompraForm(forms.ModelForm):
    fecha_esperada = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=datetime.now().date() + timedelta(days=7)
    )
    
    class Meta:
        model = PedidoCompra
        fields = ['proveedor', 'contacto_proveedor', 'telefono_proveedor',
                 'fecha_esperada', 'prioridad', 'numero_orden_compra', 'observaciones']
        widgets = {
            'proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto_proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono_proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'numero_orden_compra': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class FiltroInventarioForm(forms.Form):
    TIPO_CHOICES = [
        ('', 'Todos'),
        ('tela', 'Tela'),
        ('hilo', 'Hilo'),
        ('avios', 'Avíos'),
        ('otro', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('', 'Todos'),
        ('bajo', 'Stock Bajo'),
        ('normal', 'Stock Normal'),
        ('alto', 'Stock Alto'),
    ]
    
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    necesita_reabastecimiento = forms.BooleanField(
        required=False,
        label="Solo necesita reabastecimiento",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    ubicacion = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ubicación'})
    )

class AjusteInventarioForm(forms.Form):
    inventario = forms.ModelChoiceField(
        queryset=Inventario.objects.filter(activo=True, bloqueado=False),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo = forms.ChoiceField(
        choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    cantidad = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    
    costo_unitario = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

class GenerarReporteForm(forms.Form):
    TIPO_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
    ]
    
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )