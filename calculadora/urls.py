from django.urls import path
from .views import calculadora

urlpatterns = [
    path('', calculadora, name='calculadora'),
]
