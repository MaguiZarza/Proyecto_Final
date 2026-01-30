# Reemplaza TODO el contenido de urls.py con esto:

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import registro, CustomLoginView

urlpatterns = [
    # Rutas básicas de autenticación
    path('registro/', registro, name='registro'),
    path('login/', CustomLoginView.as_view(), name='login'),  # Usamos nuestra vista personalizada
    
    # Logout con mensaje personalizado (opcional)
    path('logout/', 
         auth_views.LogoutView.as_view(
             template_name='usuarios/logged_out.html',
             next_page='login'
         ), 
         name='logout'),
    
    # Restablecimiento de contraseña (opcional pero recomendado)
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='usuarios/password_reset.html',
             email_template_name='usuarios/password_reset_email.html',
             subject_template_name='usuarios/password_reset_subject.txt'
         ), 
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='usuarios/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='usuarios/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='usuarios/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]