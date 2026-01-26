from django import forms
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Proceso, EtapaProceso, MaterialProceso, FlujoTrabajo,
    ProcesoFlujo, Temporizador, ControlCalidad, 
    ControlCalidadDetalle, NoConformidad
)
from materiales.models import Material
## forms procesos
# ============ FORMULARIOS DE PROCESOS ============ #
class ProcesoForm(forms.ModelForm):
    class Meta:
        model = Proceso
        fields = ['nombre', 'tipo', 'descripcion', 'orden', 
                 'tiempo_estimado_min', 'tiempo_estimado_max',
                 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'orden': forms.NumberInput(attrs={'class': 'form-control'}),
            'tiempo_estimado_min': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'}),
            'tiempo_estimado_max': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class EtapaProcesoForm(forms.ModelForm):
    class Meta:
        model = EtapaProceso
        fields = ['proceso', 'nombre', 'descripcion', 'orden',
                 'tiempo_estimado', 'asignado_a']
        widgets = {
            'proceso': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'orden': forms.NumberInput(attrs={'class': 'form-control'}),
            'tiempo_estimado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'}),
            'asignado_a': forms.Select(attrs={'class': 'form-select'}),
        }

class MaterialProcesoForm(forms.ModelForm):
    class Meta:
        model = MaterialProceso
        fields = ['proceso', 'material', 'cantidad_necesaria', 
                 'unidad', 'desperdicio_estimado']
        widgets = {
            'proceso': forms.Select(attrs={'class': 'form-select'}),
            'material': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_necesaria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unidad': forms.TextInput(attrs={'class': 'form-control'}),
            'desperdicio_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

# ============ FORMULARIOS DE FLUJOS DE TRABAJO ============ #
class FlujoTrabajoForm(forms.ModelForm):
    class Meta:
        model = FlujoTrabajo
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ProcesoFlujoForm(forms.ModelForm):
    class Meta:
        model = ProcesoFlujo
        fields = ['flujo_trabajo', 'proceso', 'orden',
                 'requiere_completar_anterior', 'puede_paralelizar',
                 'es_opcional', 'tiempo_maximo_espera']
        widgets = {
            'flujo_trabajo': forms.Select(attrs={'class': 'form-select'}),
            'proceso': forms.Select(attrs={'class': 'form-select'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control'}),
            'requiere_completar_anterior': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'puede_paralelizar': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_opcional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiempo_maximo_espera': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'}),
        }

# ============ FORMULARIOS DE TEMPORIZADOR ============ #
class TemporizadorForm(forms.ModelForm):
    class Meta:
        model = Temporizador
        # Quita 'orden_produccion' de los fields ya que lo comentamos
        fields = ['proceso', 'etapa', 'tiempo_objetivo', 'operario']
        widgets = {
            'proceso': forms.Select(attrs={'class': 'form-select'}),
            'etapa': forms.Select(attrs={'class': 'form-select'}),
            'tiempo_objetivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'}),
            'operario': forms.Select(attrs={'class': 'form-select'}),
        }

class IniciarTemporizadorForm(forms.Form):
    proceso = forms.ModelChoiceField(
        queryset=Proceso.objects.filter(activo=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tiempo_objetivo = forms.DurationField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'})
    )
    referencia = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Orden/Lote/Referencia'})
    )

# ============ FORMULARIOS DE CONTROL DE CALIDAD ============ #
class ControlCalidadForm(forms.ModelForm):
    class Meta:
        model = ControlCalidad
        # Quita 'orden_produccion' y 'lote' de los fields
        fields = ['proceso', 'etapa', 'resultado', 'observaciones', 'recomendaciones',
                 'puntuacion_total', 'cantidad_defectos', 'costo_reparacion']
        widgets = {
            'proceso': forms.Select(attrs={'class': 'form-select'}),
            'etapa': forms.Select(attrs={'class': 'form-select'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'recomendaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'puntuacion_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cantidad_defectos': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_reparacion': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class ControlCalidadDetalleForm(forms.ModelForm):
    class Meta:
        model = ControlCalidadDetalle
        fields = ['tipo_defecto', 'descripcion', 'severidad',
                 'ubicacion_defecto', 'accion_tomada',
                 'requiere_reparacion', 'tiempo_reparacion']
        widgets = {
            'tipo_defecto': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'severidad': forms.Select(attrs={'class': 'form-select'}),
            'ubicacion_defecto': forms.TextInput(attrs={'class': 'form-control'}),
            'accion_tomada': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'requiere_reparacion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiempo_reparacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'}),
        }

# ============ FORMULARIOS DE NO CONFORMIDADES ============ #
class NoConformidadForm(forms.ModelForm):
    fecha_limite = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = NoConformidad
        # Quita 'orden_produccion' de los fields
        fields = ['proceso', 'control_calidad', 'descripcion', 'prioridad', 'causa_raiz',
                 'accion_correctiva', 'accion_preventiva',
                 'fecha_limite', 'responsable_correccion',
                 'cantidad_afectada', 'costo_estimado', 'impacto_produccion']
        widgets = {
            'proceso': forms.Select(attrs={'class': 'form-select'}),
            'control_calidad': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'causa_raiz': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'accion_correctiva': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'accion_preventiva': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'responsable_correccion': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_afectada': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'impacto_produccion': forms.TextInput(attrs={'class': 'form-control'}),
        }

# ============ FORMULARIOS DE FILTRO ============ #
class FiltroProcesosForm(forms.Form):
    TIPO_CHOICES = [('', 'Todos')] + Proceso.TIPO_CHOICES
    ESTADO_CHOICES = [('', 'Todos')] + Proceso.ESTADO_CHOICES
    
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
    
    activo = forms.ChoiceField(
        choices=[('', 'Todos'), ('true', 'Activos'), ('false', 'Inactivos')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class FiltroControlCalidadForm(forms.Form):
    RESULTADO_CHOICES = [('', 'Todos')] + ControlCalidad.RESULTADO_CHOICES
    
    resultado = forms.ChoiceField(
        choices=RESULTADO_CHOICES,
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
    
    inspector = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        self.fields['inspector'].queryset = User.objects.filter(is_active=True)

# ============ FORMULARIO DE ASIGNACIÓN RÁPIDA ============ #
class AsignarProcesoForm(forms.Form):
    proceso = forms.ModelChoiceField(
        queryset=Proceso.objects.filter(activo=True, estado='pendiente'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    operario = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tiempo_objetivo = forms.DurationField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        self.fields['operario'].queryset = User.objects.filter(is_active=True, groups__name='Operarios')