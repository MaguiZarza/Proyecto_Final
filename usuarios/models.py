# usuarios/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    company = models.CharField(max_length=100, blank=True, null=True, verbose_name="Compañía/Taller")
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"

# Señales para crear/actualizar automáticamente el perfil
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)

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