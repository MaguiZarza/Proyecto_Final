from django import forms
from django.utils import timezone
from .models import Lote, MaterialLote, Trazabilidad, Almacen, MovimientoAlmacen
from materiales.models import Material
from produccion.models import Producto, OrdenProduccion
from django.contrib.auth.models import User

# forms de lotes 

# ============ FORMULARIOS DE LOTE ============ #
class LoteForm(forms.ModelForm):
    fecha_inicio_planeada = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    fecha_fin_planeada = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = Lote
        fields = [
            'nombre', 'descripcion', 'producto', 'orden_produccion',
            'cantidad_objetivo', 'fecha_inicio_planeada', 'fecha_fin_planeada',
            'prioridad', 'responsable', 'supervisor', 'requiere_control_calidad',
            'observaciones', 'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'orden_produccion': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_objetivo': forms.NumberInput(attrs={'class': 'form-control'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'responsable': forms.Select(attrs={'class': 'form-select'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'requiere_control_calidad': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar productos activos
        self.fields['producto'].queryset = Producto.objects.filter(activo=True)
        # OrdenProduccion NO tiene campo 'activo', solo filtramos por estado no cancelado
        self.fields['orden_produccion'].queryset = OrdenProduccion.objects.exclude(estado='cancelada')
        # Filtrar usuarios activos
        self.fields['responsable'].queryset = User.objects.filter(is_active=True)
        self.fields['supervisor'].queryset = User.objects.filter(is_active=True)

# ============ FORMULARIOS DE MATERIAL POR LOTE ============ #
class MaterialLoteForm(forms.ModelForm):
    class Meta:
        model = MaterialLote
        fields = ['material', 'cantidad_asignada', 'costo_unitario', 'desperdicio_estimado']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_asignada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'desperdicio_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar materiales activos
        self.fields['material'].queryset = Material.objects.filter(activo=True)

# ============ FORMULARIOS DE TRAZABILIDAD ============ #
class TrazabilidadForm(forms.ModelForm):
    class Meta:
        model = Trazabilidad
        fields = ['tipo_evento', 'etapa', 'observaciones', 'cantidad_afectada', 'ubicacion', 'documento_referencia']
        widgets = {
            'tipo_evento': forms.Select(attrs={'class': 'form-select'}),
            'etapa': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cantidad_afectada': forms.NumberInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'documento_referencia': forms.TextInput(attrs={'class': 'form-control'}),
        }

# ============ FORMULARIOS DE ALMACÉN ============ #
class AlmacenForm(forms.ModelForm):
    class Meta:
        model = Almacen
        fields = [
            'codigo', 'nombre', 'tipo', 'descripcion', 'ubicacion', 
            'capacidad_maxima', 'temperatura_controlada', 'temperatura_min',
            'temperatura_max', 'humedad_controlada', 'humedad_min', 'humedad_max',
            'encargado', 'activo'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'capacidad_maxima': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperatura_controlada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'temperatura_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'temperatura_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'humedad_controlada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'humedad_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'humedad_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'encargado': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encargado'].queryset = User.objects.filter(is_active=True)

# ============ FORMULARIOS DE MOVIMIENTO DE ALMACÉN ============ #
class MovimientoAlmacenForm(forms.ModelForm):
    class Meta:
        model = MovimientoAlmacen
        fields = [
            'tipo_movimiento', 'lote', 'almacen_origen', 'almacen_destino',
            'cantidad', 'motivo', 'documento_referencia'
        ]
        widgets = {
            'tipo_movimiento': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'almacen_origen': forms.Select(attrs={'class': 'form-select'}),
            'almacen_destino': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'documento_referencia': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar lotes en estado apropiado
        self.fields['lote'].queryset = Lote.objects.filter(activo=True)
        self.fields['almacen_origen'].queryset = Almacen.objects.filter(activo=True)
        self.fields['almacen_destino'].queryset = Almacen.objects.filter(activo=True)

# ============ FORMULARIOS DE FILTRO ============ #
class FiltroLotesForm(forms.Form):
    ESTADO_CHOICES = [('', 'Todos')] + Lote.ESTADO_CHOICES
    PRIORIDAD_CHOICES = [('', 'Todas')] + Lote.PRIORIDAD_CHOICES
    RESULTADO_CALIDAD_CHOICES = [
        ('', 'Todos'),
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('parcial', 'Parcial'),
    ]
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    prioridad = forms.ChoiceField(
        choices=PRIORIDAD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    resultado_calidad = forms.ChoiceField(
        choices=RESULTADO_CALIDAD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    responsable = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    activo = forms.ChoiceField(
        choices=[('', 'Todos'), ('true', 'Activos'), ('false', 'Inactivos')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class FiltroMovimientosForm(forms.Form):
    TIPO_MOVIMIENTO_CHOICES = [('', 'Todos')] + MovimientoAlmacen.TIPO_MOVIMIENTO_CHOICES
    ESTADO_CHOICES = [
        ('', 'Todos'),
        ('pendiente', 'Pendiente'),
        ('autorizado', 'Autorizado'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]
    
    tipo_movimiento = forms.ChoiceField(
        choices=TIPO_MOVIMIENTO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    lote_codigo = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código de lote'})
    )