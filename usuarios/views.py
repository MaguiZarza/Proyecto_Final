# usuarios/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import CustomUserCreationForm
import traceback
from django.contrib.auth.views import LoginView
from .forms import EmailAuthenticationForm, CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.contrib import messages
from .forms import CustomUserCreationForm, EmailAuthenticationForm
import traceback
def registro(request):
    # Si el usuario ya está autenticado, redirigir al dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                print(f"Usuario creado: {user.username}, {user.email}")
                print(f"ID: {user.id}")
                print(f"Perfil creado: {hasattr(user, 'profile')}")
                
                # Iniciar sesión automáticamente después del registro
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password1')
                user = authenticate(username=username, password=password)
                
                if user is not None:
                    login(request, user)
                    messages.success(request, '¡Registro exitoso! Bienvenido al sistema.')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Error al autenticar usuario después del registro.')
            except Exception as e:
                messages.error(request, f'Error al crear el usuario: {str(e)}')
                print(traceback.format_exc())  # Para debugging
        else:
            # Mostrar errores específicos del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})


class CustomLoginView(LoginView):
    """
    Vista personalizada para login que usa EmailAuthenticationForm
    """
    authentication_form = EmailAuthenticationForm
    template_name = 'usuarios/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        # Redirigir al dashboard después del login exitoso
        return '/dashboard/'
    
def custom_logout(request):
    """
    Vista personalizada para logout
    """
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')

# Añade esta vista si necesitas un dashboard
@login_required
def dashboard(request):
    """
    Dashboard principal después del login
    """
    return render(request, 'usuarios/dashboard.html', {'user': request.user})


def registro(request):
    # Si el usuario ya está autenticado, redirigir al dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                print(f"Usuario creado: {user.username}, {user.email}")
                print(f"ID: {user.id}")
                print(f"Perfil creado: {hasattr(user, 'profile')}")
                
                # Iniciar sesión automáticamente después del registro
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password1')
                user = authenticate(username=username, password=password)
                
                if user is not None:
                    login(request, user)
                    messages.success(request, '¡Registro exitoso! Bienvenido al sistema.')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Error al autenticar usuario después del registro.')
            except Exception as e:
                messages.error(request, f'Error al crear el usuario: {str(e)}')
                print(traceback.format_exc())  # Para debugging
        else:
            # Mostrar errores específicos del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})

class CustomLoginView(LoginView):
    """
    Vista personalizada para login que usa EmailAuthenticationForm
    """
    form_class = EmailAuthenticationForm
    template_name = 'usuarios/login.html'
    redirect_authenticated_user = True  # Si ya está logueado, redirige
    
    def get_success_url(self):
        """
        Redirigir después del login exitoso
        Puedes cambiar 'dashboard' por la URL que necesites
        """
        return redirect('dashboard').url if hasattr(self.request, 'resolver_match') else '/dashboard/'
    
    def form_valid(self, form):
        """
        Mensaje de éxito personalizado
        """
        messages.success(self.request, f'¡Bienvenido de nuevo, {form.get_user().first_name}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """
        Manejar errores de autenticación
        """
        messages.error(self.request, 'Error de autenticación. Verifica tus credenciales.')
        return super().form_invalid(form)