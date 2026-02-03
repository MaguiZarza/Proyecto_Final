from django.contrib import admin
from .models import (
    Hilo, Tela, ConfiguracionMaquina, ConfiguracionHilo, ConsumoTela,
    Material, Formula, FormulaDetalle,
    Inventario, MovimientoInventario, HistoricoCosto, AlertaStock,
    ConsumoProducto, PedidoCompra, DetallePedidoCompra, ReporteInventario
)
from produccion.models import Producto  # Importación corregida

import uuid
from datetime import datetime, timedelta
from django.utils import timezone
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

# CONFIGURACIÓN HILO (INLINE)
class ConfiguracionHiloInline(admin.TabularInline):
    model = ConfiguracionHilo
    extra = 1

# CONFIGURACIÓN MÁQUINA
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

# FÓRMULA DETALLE (INLINE)
class FormulaDetalleInline(admin.TabularInline):
    model = FormulaDetalle
    extra = 1

# FÓRMULA
@admin.register(Formula)
class FormulaAdmin(admin.ModelAdmin):
    list_display = ('producto', 'activa')
    inlines = [FormulaDetalleInline]

# PRODUCTO
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'activo')
    search_fields = ('nombre', 'codigo')
    list_filter = ('activo',)

# MATERIAL
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'color', 'codigo_color', 'unidad', 'activo')
    list_filter = ('tipo', 'activo', 'color')
    search_fields = ('nombre', 'color', 'codigo_color')
    list_editable = ('activo',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'tipo', 'unidad', 'activo')
        }),
        ('Color', {
            'fields': ('color', 'codigo_color'),
            'classes': ('collapse',)
        }),
    )
    
    
# ... (admin existente) ...

from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Inventario, MovimientoInventario, HistoricoCosto, 
    AlertaStock, ConsumoProducto, PedidoCompra, 
    DetallePedidoCompra, ReporteInventario
)

# ============ INVENTARIO ============ #
@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('material', 'cantidad_actual', 'unidad_display', 'cantidad_minima', 
                   'cantidad_maxima', 'ubicacion', 'costo_promedio', 'valor_total_display',
                   'necesita_reabastecimiento_badge', 'porcentaje_stock_bar')
    list_filter = ('material__tipo', 'activo', 'bloqueado')
    search_fields = ('material__nombre', 'ubicacion', 'codigo_ubicacion')
    readonly_fields = ('ultima_actualizacion', 'valor_total')
    fieldsets = (
        ('Material', {
            'fields': ('material', 'activo', 'bloqueado')
        }),
        ('Stock', {
            'fields': ('cantidad_actual', 'cantidad_minima', 'cantidad_maxima')
        }),
        ('Costos', {
            'fields': ('costo_promedio', 'costo_ultima_compra')
        }),
        ('Ubicación', {
            'fields': ('ubicacion', 'codigo_ubicacion')
        }),
        ('Auditoría', {
            'fields': ('ultima_actualizacion', 'actualizado_por'),
            'classes': ('collapse',)
        }),
    )
    
    def unidad_display(self, obj):
        return obj.material.unidad
    unidad_display.short_description = 'Unidad'
    
    def valor_total_display(self, obj):
        return f"${obj.valor_total():.2f}"
    valor_total_display.short_description = 'Valor Total'
    
    def necesita_reabastecimiento_badge(self, obj):
        if obj.necesita_reabastecimiento():
            return format_html('<span class="badge bg-danger">⚠️ Necesita</span>')
        return format_html('<span class="badge bg-success">✅ OK</span>')
    necesita_reabastecimiento_badge.short_description = 'Reabastecimiento'
    
    def porcentaje_stock_bar(self, obj):
        porcentaje = obj.porcentaje_stock()
        color = 'success' if porcentaje >= 50 else 'warning' if porcentaje >= 20 else 'danger'
        return format_html(
            '''
            <div class="progress" style="height: 20px; width: 100px;">
                <div class="progress-bar bg-{}" role="progressbar" 
                     style="width: {}%" aria-valuenow="{}" 
                     aria-valuemin="0" aria-valuemax="100">
                    {:.0f}%
                </div>
            </div>
            ''',
            color, porcentaje, porcentaje, porcentaje
        )
    porcentaje_stock_bar.short_description = 'Nivel de Stock'
    
    def save_model(self, request, obj, form, change):
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)

# ============ MOVIMIENTOS DE INVENTARIO ============ #
class DetallePedidoCompraInline(admin.TabularInline):
    model = DetallePedidoCompra
    extra = 1

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('fecha_movimiento', 'inventario_link', 'tipo_badge', 
                   'cantidad_movimiento', 'costo_unitario', 'costo_total', 
                   'realizado_por', 'referencia')
    list_filter = ('tipo', 'origen', 'fecha_movimiento')
    search_fields = ('inventario__material__nombre', 'referencia', 'motivo')
    readonly_fields = ('cantidad_anterior', 'cantidad_actual', 'costo_total', 'fecha_movimiento')
    fieldsets = (
        ('Movimiento', {
            'fields': ('inventario', 'tipo', 'origen', 'referencia')
        }),
        ('Cantidades', {
            'fields': ('cantidad_anterior', 'cantidad_movimiento', 'cantidad_actual')
        }),
        ('Costos', {
            'fields': ('costo_unitario', 'costo_total')
        }),
        ('Referencias', {
            'fields': ('orden_produccion', 'lote', 'fecha_documento'),
            'classes': ('collapse',)
        }),
        ('Detalles', {
            'fields': ('motivo', 'observaciones'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('realizado_por', 'fecha_movimiento'),
            'classes': ('collapse',)
        }),
    )
    
    def inventario_link(self, obj):
        url = reverse('admin:materiales_inventario_change', args=[obj.inventario.id])
        return format_html('<a href="{}">{}</a>', url, obj.inventario.material.nombre)
    inventario_link.short_description = 'Inventario'
    
    def tipo_badge(self, obj):
        color_map = {
            'entrada': 'success',
            'salida': 'danger',
            'ajuste': 'warning',
            'inicial': 'info',
            'transferencia': 'primary',
            'devolucion': 'secondary'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.tipo, 'secondary'),
            obj.get_tipo_display()
        )
    tipo_badge.short_description = 'Tipo'

# ============ HISTÓRICO DE COSTOS ============ #
@admin.register(HistoricoCosto)
class HistoricoCostoAdmin(admin.ModelAdmin):
    list_display = ('material', 'fecha', 'costo_unitario', 'cantidad', 'costo_total_display', 'origen')
    list_filter = ('material__tipo', 'fecha')
    search_fields = ('material__nombre', 'origen', 'referencia')
    readonly_fields = ('costo_total',)
    
    def costo_total_display(self, obj):
        return f"${obj.costo_total():.2f}"
    costo_total_display.short_description = 'Costo Total'

# ============ ALERTAS DE STOCK ============ #
@admin.register(AlertaStock)
class AlertaStockAdmin(admin.ModelAdmin):
    list_display = ('fecha_deteccion', 'material_link', 'tipo_badge', 'nivel_badge',
                   'cantidad_actual', 'cantidad_umbral', 'resuelta_badge')
    list_filter = ('tipo', 'nivel', 'resuelta', 'fecha_deteccion')
    search_fields = ('material__nombre', 'descripcion')
    readonly_fields = ('fecha_deteccion', 'fecha_resolucion')
    fieldsets = (
        ('Alerta', {
            'fields': ('material', 'inventario', 'tipo', 'nivel', 'activa')
        }),
        ('Detalles', {
            'fields': ('descripcion', 'cantidad_actual', 'cantidad_umbral')
        }),
        ('Resolución', {
            'fields': ('resuelta', 'accion_tomada', 'resuelta_por', 'fecha_resolucion')
        }),
    )
    actions = ['marcar_como_resueltas']
    
    def material_link(self, obj):
        url = reverse('admin:materiales_material_change', args=[obj.material.id])
        return format_html('<a href="{}">{}</a>', url, obj.material.nombre)
    material_link.short_description = 'Material'
    
    def tipo_badge(self, obj):
        color_map = {
            'stock_minimo': 'danger',
            'stock_maximo': 'warning',
            'sin_movimientos': 'info',
            'costo_alto': 'secondary'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.tipo, 'secondary'),
            obj.get_tipo_display()
        )
    tipo_badge.short_description = 'Tipo'
    
    def nivel_badge(self, obj):
        color_map = {
            'bajo': 'danger',
            'medio': 'warning',
            'alto': 'success'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.nivel, 'secondary'),
            obj.get_nivel_display()
        )
    nivel_badge.short_description = 'Nivel'
    
    def resuelta_badge(self, obj):
        if obj.resuelta:
            return format_html('<span class="badge bg-success">✅ Resuelta</span>')
        return format_html('<span class="badge bg-danger">⚠️ Pendiente</span>')
    resuelta_badge.short_description = 'Estado'
    
    def marcar_como_resueltas(self, request, queryset):
        updated = queryset.update(resuelta=True, resuelta_por=request.user, 
                                 fecha_resolucion=timezone.now())
        self.message_user(request, f'{updated} alertas marcadas como resueltas.')
    marcar_como_resueltas.short_description = "Marcar como resueltas"

# ============ CONSUMO POR PRODUCTO ============ #
@admin.register(ConsumoProducto)
class ConsumoProductoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'material', 'cantidad_por_unidad', 'desperdicio_estimado',
                   'costo_material_por_unidad', 'calcular_costo_display')
    list_filter = ('producto', 'material__tipo')
    search_fields = ('producto__nombre', 'material__nombre')
    
    def calcular_costo_display(self, obj):
        return f"${obj.calcular_costo():.2f}"
    calcular_costo_display.short_description = 'Costo por Unidad'

# ============ PEDIDOS DE COMPRA ============ #
@admin.register(PedidoCompra)
class PedidoCompraAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'proveedor', 'fecha_solicitud', 'fecha_esperada',
                   'estado_badge', 'costo_estimado', 'costo_real', 'solicitado_por')
    list_filter = ('estado', 'fecha_solicitud', 'fecha_esperada')
    search_fields = ('codigo', 'proveedor', 'numero_orden_compra')
    inlines = [DetallePedidoCompraInline]
    readonly_fields = ('fecha_solicitud', 'costo_estimado', 'costo_real')
    fieldsets = (
        ('Información', {
            'fields': ('codigo', 'proveedor', 'contacto_proveedor', 'telefono_proveedor')
        }),
        ('Fechas', {
            'fields': ('fecha_solicitud', 'fecha_esperada', 'fecha_recepcion')
        }),
        ('Estado', {
            'fields': ('estado', 'prioridad')
        }),
        ('Costos', {
            'fields': ('costo_estimado', 'costo_real')
        }),
        ('Documentación', {
            'fields': ('numero_orden_compra', 'observaciones'),
            'classes': ('collapse',)
        }),
        ('Responsables', {
            'fields': ('solicitado_por', 'aprobado_por', 'recibido_por'),
            'classes': ('collapse',)
        }),
    )
    
    def estado_badge(self, obj):
        color_map = {
            'pendiente': 'warning',
            'aprobado': 'info',
            'ordenado': 'primary',
            'recibido': 'success',
            'cancelado': 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.solicitado_por = request.user
            obj.codigo = f"PC-{timezone.now().strftime('%Y%m%d')}-{PedidoCompra.objects.count() + 1:04d}"
        super().save_model(request, obj, form, change)

# ============ REPORTES DE INVENTARIO ============ #
@admin.register(ReporteInventario)
class ReporteInventarioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'periodo_inicio', 'periodo_fin',
                   'total_materiales', 'materiales_bajos', 'valor_total_inventario',
                   'fecha_generacion')
    list_filter = ('tipo', 'periodo_inicio')
    search_fields = ('titulo', 'resumen')
    readonly_fields = ('fecha_generacion',)
    fieldsets = (
        ('Información del Reporte', {
            'fields': ('titulo', 'tipo', 'periodo_inicio', 'periodo_fin')
        }),
        ('Métricas', {
            'fields': ('total_materiales', 'materiales_bajos', 'valor_total_inventario', 'movimientos_totales')
        }),
        ('Contenido', {
            'fields': ('resumen', 'hallazgos', 'recomendaciones', 'archivo')
        }),
        ('Generación', {
            'fields': ('generado_por', 'fecha_generacion'),
            'classes': ('collapse',)
        }),
    )