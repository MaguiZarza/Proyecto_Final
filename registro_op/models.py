from django.db import models
from django.contrib.auth.models import User

#Registrar el calculo de materiales
class Operacion(models.Model):
    ACCION_CHOICES = [
        ('calculo_materiales', 'Cálculo de materiales'),
        ('calculo_hilo', 'Cálculo de hilo'),
        ('proceso', 'Proceso de producción'),
        ('lote', 'Generación de lote'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    accion = models.CharField(
        max_length=50,
        choices=ACCION_CHOICES
    )

    descripcion = models.TextField()

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} - {self.accion}"
