from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),

    #apps
    path('materiales/', include('materiales.urls')),
    path('procesos/', include('procesos.urls')),
    # path('lotes/', include('lotes.urls')),  # ¡ELIMINADA!
    path('usuarios/', include('usuarios.urls')),
    path('', include('produccion.urls')),  # dashboard principal

    # Autenticación
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Redirección raíz
    path('', lambda request: redirect('dashboard'), name='home'),
]