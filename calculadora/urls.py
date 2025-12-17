from django.urls import path
from .views import calculadora, calculadora_materiales

urlpatterns = [
    path('', calculadora, name='calculadora'),
    path('materiales/', calculadora_materiales, name='calculadora_materiales'),
]
