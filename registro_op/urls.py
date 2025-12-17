from django.urls import path
from .views import historial_operaciones

urlpatterns = [
    path('historial/', historial_operaciones, name='historial_operaciones'),
]
