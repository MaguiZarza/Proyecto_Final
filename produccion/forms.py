from django import forms
from django.contrib.auth.models import User
from .models import Pedido, MetodoProduccion, OrdenProduccion, Planificacion, ReporteProduccion
from .models import Producto
import datetime

## forms produccion

class PedidoForm(forms.ModelForm):
    # Crear un queryset que incluya todos los productos activos y una opción "Otro"
    producto_choice = forms.ChoiceField(
        choices=[],
        label="Producto",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_producto_choice'})
    )
    
    producto_otro = forms.CharField(
        required=False,
        label='Especificar otro producto',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Describe el producto personalizado...'})
    )
    
    fecha_entrega = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=datetime.date.today() + datetime.timedelta(days=7)
    )
    
    class Meta:
        model = Pedido
        fields = ['cliente', 'contacto', 'telefono', 'email', 
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Obtener productos activos
        productos = Producto.objects.filter(activo=True)
        
        # Crear opciones: primero productos normales, luego "Otro"
        choices = [(str(p.id), p.nombre) for p in productos]
        choices.append(('otro', 'Otro (Personalizado)'))
        
        self.fields['producto_choice'].choices = choices
        
        # Si estamos editando un pedido existente, configurar el valor inicial
        if self.instance and self.instance.pk:
            if self.instance.producto:
                self.fields['producto_choice'].initial = str(self.instance.producto.id)
            else:
                # Si no tiene producto (caso de "otro" guardado)
                self.fields['producto_choice'].initial = 'otro'
                # Mostrar el nombre del producto en especificaciones como referencia
                if self.instance.especificaciones:
                    lines = self.instance.especificaciones.split('\n')
                    for line in lines:
                        if line.startswith('Producto personalizado:'):
                            self.fields['producto_otro'].initial = line.replace('Producto personalizado:', '').strip()
                            break
    
    def clean(self):
        cleaned_data = super().clean()
        producto_choice = cleaned_data.get('producto_choice')
        producto_otro = cleaned_data.get('producto_otro')
        
        # Validar que si se selecciona "Otro", se especifique el producto
        if producto_choice == 'otro' and not producto_otro:
            self.add_error('producto_otro', 'Debe especificar el producto personalizado.')
        
        return cleaned_data
    
    def save(self, commit=True):
        pedido = super().save(commit=False)
        producto_choice = self.cleaned_data.get('producto_choice')
        producto_otro = self.cleaned_data.get('producto_otro', '')
        
        # Manejar la selección del producto
        if producto_choice == 'otro':
            # Si es "Otro", buscar o crear un producto genérico "Personalizado"
            producto_personalizado, created = Producto.objects.get_or_create(
                nombre='Personalizado',
                codigo='PER-001',
                defaults={
                    'descripcion': 'Producto personalizado según especificaciones del cliente',
                    'costo_estimado': 0,
                    'precio_venta': 0,
                    'activo': True
                }
            )
            pedido.producto = producto_personalizado
            
            # Agregar información del producto personalizado a especificaciones
            if producto_otro:
                especificaciones_original = self.cleaned_data.get('especificaciones', '')
                especificaciones_con_producto = f"Producto personalizado: {producto_otro}\n\n{especificaciones_original}"
                pedido.especificaciones = especificaciones_con_producto.strip()
        else:
            # Si es un producto normal, asignarlo directamente
            try:
                producto = Producto.objects.get(id=int(producto_choice))
                pedido.producto = producto
            except (ValueError, Producto.DoesNotExist):
                pass
        
        if commit:
            pedido.save()
        
        return pedido

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
    fecha_desde = forms.DateField(
        required=False,
        label='Fecha desde',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        label='Fecha hasta',
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