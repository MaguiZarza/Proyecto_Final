from django import forms
from django.contrib.auth.models import User
from .models import Pedido, MetodoProduccion, OrdenProduccion, Planificacion, ReporteProduccion
from .models import Producto
import datetime

## forms produccion

class PedidoForm(forms.ModelForm):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=True),
        label="Producto",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_entrega = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=datetime.date.today() + datetime.timedelta(days=7)
    )
    
    class Meta:
        model = Pedido
        fields = ['cliente', 'contacto', 'telefono', 'email', 'producto', 
                 'cantidad', 'fecha_entrega', 'prioridad', 'especificaciones', 
                 'observaciones', 'archivo_diseno']
        widgets = {
            'cliente': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'especificaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class OrdenProduccionForm(forms.ModelForm):
    fecha_programada = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=datetime.date.today()
    )
    
    equipo = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = OrdenProduccion
        fields = ['pedido', 'metodo', 'fecha_programada', 'supervisor', 
                 'equipo', 'cantidad_a_producir', 'observaciones']
        widgets = {
            'pedido': forms.Select(attrs={'class': 'form-select'}),
            'metodo': forms.Select(attrs={'class': 'form-select'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_a_producir': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PlanificacionForm(forms.ModelForm):
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=datetime.date.today()
    )
    
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=datetime.date.today() + datetime.timedelta(days=6)
    )
    
    class Meta:
        model = Planificacion
        fields = ['nombre', 'tipo', 'fecha_inicio', 'fecha_fin', 
                 'descripcion', 'objetivos', 'responsables', 'ordenes']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'objetivos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class FiltroReporteForm(forms.Form):
    TIPO_CHOICES = [
        ('', 'Todos'),
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('anual', 'Anual'),
    ]
    
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_desde = cleaned_data.get('fecha_desde')
        fecha_hasta = cleaned_data.get('fecha_hasta')
        
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            self.add_error('fecha_hasta', 'La fecha hasta debe ser mayor o igual a la fecha desde')
        
        return cleaned_data

class AvanceProduccionForm(forms.Form):
    cantidad_producida = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )