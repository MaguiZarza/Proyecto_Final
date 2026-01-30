from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import PerfilOperario, Profile

@admin.register(PerfilOperario)
class PerfilOperarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'turno', 'activo')
    list_filter = ('rol', 'turno', 'activo')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')

