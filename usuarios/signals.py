# Archivo: usuarios/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

@receiver(pre_save, sender=User)
def ensure_email_unique(sender, instance, **kwargs):
    """
    Asegura que el email sea único antes de guardar un usuario.
    """
    if instance.email:
        # Buscar otros usuarios con el mismo email (ignorando mayúsculas/minúsculas)
        existing_users = User.objects.filter(email__iexact=instance.email)
        
        # Si estamos actualizando un usuario, excluirlo de la búsqueda
        if instance.pk:
            existing_users = existing_users.exclude(pk=instance.pk)
        
        if existing_users.exists():
            raise ValidationError(
                f"El correo electrónico '{instance.email}' ya está registrado por otro usuario. "
                f"Por favor usa un correo diferente."
            )

@receiver(post_save, sender=User)
def log_user_creation(sender, instance, created, **kwargs):
    """
    Registra cuando se crea un nuevo usuario (útil para debugging).
    """
    if created:
        print(f"[SIGNAL] Nuevo usuario creado: ID={instance.id}, Email={instance.email}, "
              f"Username={instance.username}")