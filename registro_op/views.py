from django.shortcuts import render
from .models import Operacion

def historial_operaciones(request):
    operaciones = Operacion.objects.all().order_by('-fecha')

    return render(request, 'registro_op/historial.html', {
        'operaciones': operaciones
    })