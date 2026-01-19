from django.db import models
from django.contrib.auth.models import User

class PerfilOperario(models.Model):
    ROL_CHOICES = [
        ('operario', 'Operario'),
        ('supervisor', 'Supervisor'),
        ('admin', 'Administrador'),
    ]

    TURNO_CHOICES = [
        ('mañana', 'Mañana'),
        ('tarde', 'Tarde'),
        ('noche', 'Noche'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='operario')
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.rol}"