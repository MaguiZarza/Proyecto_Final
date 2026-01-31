from django.contrib import admin
from .models import PerfilOperario

@admin.register(PerfilOperario)
class PerfilOperarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'turno', 'activo')
    list_filter = ('rol', 'turno', 'activo')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')