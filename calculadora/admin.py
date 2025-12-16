from django.contrib import admin

# MODELOS
from .models import (
    Hilo,
    Tela,
    ConfiguracionMaquina,
    ConfiguracionHilo,
    ConsumoTela
)

# HILO
@admin.register(Hilo)
class HiloAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'metros_por_cono')
    list_filter = ('tipo',)
    search_fields = ('nombre',)

# TELA
@admin.register(Tela)
class TelaAdmin(admin.ModelAdmin):
    search_fields = ('nombre',)

# CONFIGURACION HILO (INLINE)
class ConfiguracionHiloInline(admin.TabularInline):
    model = ConfiguracionHilo
    extra = 1

# CONFIGURACION MAQUINA
@admin.register(ConfiguracionMaquina)
class ConfiguracionMaquinaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_maquina')
    list_filter = ('tipo_maquina',)
    inlines = [ConfiguracionHiloInline]

# CONSUMO TELA
@admin.register(ConsumoTela)
class ConsumoTelaAdmin(admin.ModelAdmin):
    list_display = ('tela', 'configuracion', 'metros_hilo_por_metro_tela')
    list_filter = ('configuracion__tipo_maquina',)