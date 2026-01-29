# usuarios/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
import re

class CustomUserCreationForm(UserCreationForm):
    # Campos para el usuario
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Juan'
        }),
        label="Nombre (se mostrará en la aplicación)"
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Pérez'
        }),
        label="Apellido"
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@tallertextil.com'
        }),
        label="Correo Electrónico (para iniciar sesión)",
        help_text="Usarás este correo para iniciar sesión"
    )
    
    # Campos extras para el perfil
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+34 123 456 789'
        }),
        label="Teléfono"
    )
    
    company = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de tu taller textil'
        }),
        label="Taller/Compañía"
    )
    
    class Meta:
        model = User
        # IMPORTANTE: Incluimos username pero lo generaremos automáticamente
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remover el campo username del formulario (no lo mostramos al usuario)
        if 'username' in self.fields:
            del self.fields['username']
        
        # Personalizar los widgets de contraseña
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', '')
        first_name = cleaned_data.get('first_name', '').strip()
        
        # Generar username automáticamente combinando nombre y email
        if email and first_name:
            # Tomar el nombre sin espacios y en minúsculas
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', first_name).lower()
            
            # Si el nombre es muy corto, usar parte del email
            if len(clean_name) < 3:
                # Tomar la parte antes del @ del email
                email_part = email.split('@')[0]
                clean_name = email_part
            
            # Asegurar que el username sea único
            base_username = clean_name
            username = base_username
            counter = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                if counter > 100:  # Prevenir bucle infinito
                    username = f"user{User.objects.count() + 1}"
                    break
            
            cleaned_data['username'] = username
        
        return cleaned_data
    
    def save(self, commit=True):
        # Asegurar que tenemos un username
        if 'username' not in self.cleaned_data:
            # Generar username de emergencia
            email = self.cleaned_data.get('email', '')
            if email:
                base = email.split('@')[0]
                username = base
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base}{counter}"
                    counter += 1
                self.cleaned_data['username'] = username
        
        user = super().save(commit=False)
        
        # Configurar los campos del usuario
        user.username = self.cleaned_data['username']  # Username generado
        user.email = self.cleaned_data['email']        # Email (para login)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            
            # Guardar los campos extras en el perfil
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data.get('phone', '')
            profile.company = self.cleaned_data.get('company', '')
            profile.save()
        
        return user