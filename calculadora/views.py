from django.shortcuts import render
from .forms import CalculadoraForm, CalculadoraMaterialesForm
from .models import Formula
from registro_op.models import Operacion
>>>>>>> 5bb4188 (Registro de operaciones de la calculadora de materiales)

def calculadora(request):
    resultado = None
    consumo_seleccionado = None
    metros = None

    if request.method == 'POST':
        form = CalculadoraForm(request.POST)
        if form.is_valid():
            consumo_seleccionado = form.cleaned_data['consumo']
            metros = form.cleaned_data['metros_tela']

            resultado = consumo_seleccionado.metros_hilo_por_metro_tela * metros
    else:
        form = CalculadoraForm()

    return render(request, 'calculadora/calculadora.html', {
        'form': form,
        'resultado': resultado,
        'consumo': consumo_seleccionado,
        'metros': metros,
    })
<<<<<<< HEAD
=======

# Calculadora Materiales
def calculadora_materiales(request):
    form = CalculadoraMaterialesForm()
    resultados = None
    producto = None
    cantidad = None

    if request.method == 'POST':
        form = CalculadoraMaterialesForm(request.POST)
        if form.is_valid():
            producto = form.cleaned_data['producto']
            cantidad = form.cleaned_data['cantidad']

            try:
                formula = Formula.objects.get(producto=producto, activa=True)
                resultados = []

                for detalle in formula.detalles.all():
                    total = detalle.cantidad_por_unidad * cantidad
                    resultados.append({
                        'material': detalle.material.nombre,
                        'unidad': detalle.material.unidad,
                        'cantidad': total
                    })

            except Formula.DoesNotExist:
                resultados = []

            Operacion.objects.create(
                usuario=request.user if request.user.is_authenticated else None,
                accion='calculo_materiales',
                descripcion=f'Cálculo de materiales - Producto: {producto.nombre} - Cantidad: {cantidad}'
            )

    return render(request, 'calculadora/calculadora_materiales.html', {
        'form': form,
        'resultados': resultados,
        'producto': producto,
        'cantidad': cantidad
    })
>>>>>>> 5bb4188 (Registro de operaciones de la calculadora de materiales)
