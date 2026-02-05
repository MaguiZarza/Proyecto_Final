# usuarios/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from .models import Profile

import re
import os


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
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'username' in self.fields:
            del self.fields['username']

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

        if email and first_name:
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', first_name).lower()

            if len(clean_name) < 3:
                clean_name = email.split('@')[0]

            base_username = clean_name
            username = base_username
            counter = 1

            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                if counter > 100:
                    username = f"user{User.objects.count() + 1}"
                    break

            cleaned_data['username'] = username

        return cleaned_data

    def save(self, commit=True):
        if 'username' not in self.cleaned_data:
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

        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data.get('phone', '')
            profile.company = self.cleaned_data.get('company', '')
            profile.save()

        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tuemail@tallertextil.com',
            'autocomplete': 'email'
        }),
        help_text="Ingresa tu correo electrónico registrado"
    )

    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'form-control',
            'placeholder': 'Tu contraseña'
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Correo Electrónico"
        self.fields['password'].label = "Contraseña"

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            try:
                user_by_email = User.objects.get(email__iexact=email)

                user = authenticate(
                    request=self.request,
                    username=user_by_email.username,
                    password=password
                )

                if user is None:
                    raise ValidationError("Correo electrónico o contraseña incorrectos.")

                self.cleaned_data['username'] = user.username
                self.user_cache = user

            except User.DoesNotExist:
                raise ValidationError(
                    "No existe una cuenta con este correo electrónico. Regístrate primero."
                )

            except User.MultipleObjectsReturned:
                users = User.objects.filter(email__iexact=email)
                for user_obj in users:
                    user = authenticate(
                        request=self.request,
                        username=user_obj.username,
                        password=password
                    )
                    if user is not None:
                        self.cleaned_data['username'] = user.username
                        self.user_cache = user
                        break
                else:
                    raise ValidationError("Correo electrónico o contraseña incorrectos.")

        return self.cleaned_data


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
        }


class ProfileUpdateForm(forms.ModelForm):
    profile_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        label="Foto de perfil"
    )

    class Meta:
        model = Profile
        fields = ['phone', 'company', 'profile_image']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+569 1234 5678'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la compañía'
            }),
        }

    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')

        if image:
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("La imagen es demasiado grande. Máximo 2MB.")

            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            ext = os.path.splitext(image.name)[1].lower()

            if ext not in valid_extensions:
                raise forms.ValidationError("Formato no válido. Usa JPG, PNG o GIF.")

        return image


class PasswordChangeCustomForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    new_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_image']
        widgets = {
            'profile_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
