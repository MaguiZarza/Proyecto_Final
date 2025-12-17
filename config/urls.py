from django.contrib import admin
from django.urls import path, include
from calculadora.views import calculadora

urlpatterns = [
    path('admin/', admin.site.urls),
    path('calculadora/', include('calculadora.urls')),
    path('operaciones/', include('registro_op.urls')),
]

