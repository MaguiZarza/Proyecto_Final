from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('materiales/', include('materiales.urls')),
    path('procesos/', include('procesos.urls')),
    path('lotes/', include('lotes.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('', include('produccion.urls')),  # dashboard principal
]