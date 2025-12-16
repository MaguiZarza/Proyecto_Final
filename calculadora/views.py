from django.shortcuts import render
from .forms import CalculadoraForm

def calculadora(request):
    resultado = None
    consumo_seleccionado = None
    metros = None

    if request.method == 'POST':
        form = CalculadoraForm(request.POST)
        if form.is_valid():
            consumo_seleccionado = form.cleaned_data['consumo']
            metros = form.cleaned_data['metros_tela']

            # cálculo correcto
            resultado = consumo_seleccionado.metros_hilo_por_metro_tela * metros
    else:
        form = CalculadoraForm()

    return render(request, 'calculadora/calculadora.html', {
        'form': form,
        'resultado': resultado,
        'consumo': consumo_seleccionado,
        'metros': metros,
    })
