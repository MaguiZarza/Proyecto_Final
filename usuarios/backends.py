# Archivo: usuarios/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class EmailBackend(ModelBackend):
    """
    Backend de autenticación que permite autenticar con email en lugar de username.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Sobreescribimos el método authenticate.
        El parámetro 'username' realmente será el email.
        """
        # Si se pasa email en kwargs, úsalo
        email = kwargs.get('email', username)
        
        if email is None or password is None:
            return None
        
        try:
            # Buscar usuario por email (case-insensitive)
            user = User.objects.get(email__iexact=email)
            
            # Verificar la contraseña
            if user.check_password(password):
                return user
            else:
                return None
                
        except User.DoesNotExist:
            # No hay usuario con ese email
            return None
        except User.MultipleObjectsReturned:
            # Si por alguna razón hay duplicados, tomamos el primero
            users = User.objects.filter(email__iexact=email)
            for user in users:
                if user.check_password(password):
                    return user
            return None
    
    def get_user(self, user_id):
        """
        Obtener usuario por ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None