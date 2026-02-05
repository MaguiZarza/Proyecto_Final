# usuarios/context_processors.py
from .models import Profile

def empresa_context(request):
    """
    Context processor para añadir el nombre de la empresa del usuario autenticado
    a todas las plantillas.
    """
    context = {}
    
    if request.user.is_authenticated:
        try:
            # Intentar obtener el perfil del usuario
            profile = Profile.objects.get(user=request.user)
            # Si el usuario tiene empresa configurada, usarla
            if profile.company and profile.company.strip():
                context['empresa_nombre'] = profile.company
            else:
                context['empresa_nombre'] = "Taller Textil"  # Nombre por defecto
        except Profile.DoesNotExist:
            context['empresa_nombre'] = "Taller Textil"  # Nombre por defecto
    else:
        context['empresa_nombre'] = "Taller Textil"  # Nombre por defecto para usuarios no autenticados
    
    return context