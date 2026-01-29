# usuarios/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import CustomUserCreationForm
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