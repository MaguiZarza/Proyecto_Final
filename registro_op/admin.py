from django.contrib import admin
from .models import Operacion

@admin.register(Operacion)
class OperacionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'usuario', 'accion')
    list_filter = ('accion', 'fecha')
    search_fields = ('descripcion',)
    readonly_fields = ('fecha',)