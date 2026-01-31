from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Pedido, MetodoProduccion, MetodoProceso, OrdenProduccion,
    Planificacion, PlanificacionOrden, ReporteProduccion
)

# ============ INLINES ============ #
class MetodoProcesoInline(admin.TabularInline):
    model = MetodoProceso
    extra = 1
    ordering = ['orden']

class OrdenProduccionInline(admin.TabularInline):
    model = OrdenProduccion
    extra = 0
    readonly_fields = ['codigo', 'estado', 'progreso']
    can_delete = False

class PlanificacionOrdenInline(admin.TabularInline):
    model = PlanificacionOrden
    extra = 1
    ordering = ['fecha_asignada', 'turno']

# ============ PEDIDOS ============ #
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'cliente', 'producto', 'cantidad', 'fecha_entrega', 
                   'estado_badge', 'prioridad_badge', 'dias_restantes_display')
    list_filter = ('estado', 'prioridad', 'fecha_pedido', 'fecha_entrega')
    search_fields = ('codigo', 'cliente', 'producto__nombre', 'contacto')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion', 'codigo')
    fieldsets = (
        ('Información del Cliente', {
            'fields': ('cliente', 'contacto', 'telefono', 'email')
        }),
        ('Detalles del Pedido', {
            'fields': ('codigo', 'producto', 'cantidad', 'fecha_entrega', 
                      'prioridad', 'especificaciones')
        }),
        ('Estado y Seguimiento', {
            'fields': ('estado', 'observaciones', 'archivo_diseno')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def estado_badge(self, obj):
        color_map = {
            'pendiente': 'warning',
            'en_proceso': 'info',
            'completado': 'success',
            'cancelado': 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    estado_badge.admin_order_field = 'estado'
    
    def prioridad_badge(self, obj):
        color_map = {1: 'primary', 2: 'warning', 3: 'danger', 4: 'dark'}
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.prioridad, 'secondary'),
            obj.get_prioridad_display()
        )
    prioridad_badge.short_description = 'Prioridad'
    
    def dias_restantes_display(self, obj):
        dias = obj.dias_restantes()
        if dias < 0:
            return format_html('<span class="text-danger">⚠️ {} días atrasado</span>', abs(dias))
        elif dias == 0:
            return format_html('<span class="text-warning">⚠️ Hoy</span>')
        elif dias <= 2:
            return format_html('<span class="text-warning">⏳ {} días</span>', dias)
        else:
            return format_html('<span class="text-success">📅 {} días</span>', dias)
    dias_restantes_display.short_description = 'Días Restantes'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

# ============ MÉTODOS DE PRODUCCIÓN ============ #
@admin.register(MetodoProduccion)
class MetodoProduccionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'tipo', 'tiempo_total_por_unidad', 
                   'costo_total_por_unidad', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre', 'codigo', 'descripcion')
    inlines = [MetodoProcesoInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'tipo', 'descripcion', 'activo')
        }),
        ('Tiempos Estimados (minutos)', {
            'fields': ('tiempo_preparacion', 'tiempo_confeccion', 'tiempo_acabado')
        }),
        ('Costos', {
            'fields': ('costo_mano_obra', 'costo_maquinaria', 'costo_adicional')
        }),
        ('Documentación', {
            'fields': ('instrucciones', 'imagen_referencia'),
            'classes': ('collapse',)
        }),
    )

# ============ ÓRDENES DE PRODUCCIÓN ============ #
@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'pedido_link', 'metodo', 'estado_badge', 
                   'progreso_bar', 'fecha_programada', 'supervisor')
    list_filter = ('estado', 'fecha_programada', 'metodo')
    search_fields = ('codigo', 'pedido__codigo', 'pedido__cliente', 'supervisor__username')
    readonly_fields = ('codigo', 'fecha_creacion', 'progreso')
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'pedido', 'metodo')
        }),
        ('Programación', {
            'fields': ('fecha_programada', 'fecha_inicio', 'fecha_fin')
        }),
        ('Producción', {
            'fields': ('cantidad_a_producir', 'cantidad_producida', 'progreso')
        }),
        ('Equipo y Estado', {
            'fields': ('estado', 'supervisor', 'equipo')
        }),
        ('Observaciones', {
            'fields': ('observaciones', 'incidencias'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ('equipo',)
    
    def pedido_link(self, obj):
        url = reverse('admin:produccion_pedido_change', args=[obj.pedido.id])
        return format_html('<a href="{}">{}</a>', url, obj.pedido.codigo)
    pedido_link.short_description = 'Pedido'
    
    def estado_badge(self, obj):
        color_map = {
            'programada': 'secondary',
            'en_proceso': 'info',
            'pausada': 'warning',
            'completada': 'success',
            'cancelada': 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def progreso_bar(self, obj):
        color = 'success' if obj.progreso >= 80 else 'warning' if obj.progreso >= 50 else 'danger'
        return format_html(
            '''
            <div class="progress" style="height: 20px; width: 100px;">
                <div class="progress-bar bg-{}" role="progressbar" 
                     style="width: {}%" aria-valuenow="{}" 
                     aria-valuemin="0" aria-valuemax="100">
                    {}%
                </div>
            </div>
            ''',
            color, obj.progreso, obj.progreso, obj.progreso
        )
    progreso_bar.short_description = 'Progreso'

# ============ PLANIFICACIÓN ============ #
@admin.register(Planificacion)
class PlanificacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'fecha_inicio', 'fecha_fin', 
                   'completada_badge', 'porcentaje_completado_display')
    list_filter = ('tipo', 'activa', 'completada')
    search_fields = ('nombre', 'descripcion')
    inlines = [PlanificacionOrdenInline]  # Usamos el inline para manejar las órdenes
    filter_horizontal = ('responsables',)  # Solo responsables, no ordenes
    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'tipo', 'activa', 'completada')
        }),
        ('Período', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Contenido', {
            'fields': ('descripcion', 'objetivos', 'responsables')
            # NOTA: No incluimos 'ordenes' aquí porque usa un modelo intermedio
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'actualizado_por'),
            'classes': ('collapse',)
        }),
    )
    
    def completada_badge(self, obj):
        if obj.completada:
            return format_html('<span class="badge bg-success">✅ Completada</span>')
        elif obj.activa:
            return format_html('<span class="badge bg-info">🔄 Activa</span>')
        else:
            return format_html('<span class="badge bg-secondary">⏸️ Inactiva</span>')
    completada_badge.short_description = 'Estado'
    
    def porcentaje_completado_display(self, obj):
        return format_html(
            '''
            <div class="progress" style="height: 20px; width: 100px;">
                <div class="progress-bar" role="progressbar" 
                     style="width: {}%; background-color: {}" 
                     aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">
                    {}%
                </div>
            </div>
            ''',
            obj.porcentaje_completado(),
            '#28a745' if obj.porcentaje_completado() >= 80 else 
            '#ffc107' if obj.porcentaje_completado() >= 50 else '#dc3545',
            obj.porcentaje_completado(),
            obj.porcentaje_completado()
        )
    porcentaje_completado_display.short_description = 'Completado'
# ============ REPORTES ============ #
@admin.register(ReporteProduccion)
class ReporteProduccionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'periodo_inicio', 'periodo_fin', 
                   'tasa_completacion_display', 'fecha_generacion')
    list_filter = ('tipo', 'periodo_inicio')
    search_fields = ('titulo', 'resumen')
    readonly_fields = ('fecha_generacion',)
    fieldsets = (
        ('Información del Reporte', {
            'fields': ('titulo', 'tipo', 'periodo_inicio', 'periodo_fin')
        }),
        ('Métricas', {
            'fields': ('total_pedidos', 'pedidos_completados', 'pedidos_pendientes',
                      'eficiencia', 'tiempo_promedio')
        }),
        ('Costos', {
            'fields': ('costo_total', 'costo_materiales', 'costo_mano_obra')
        }),
        ('Contenido', {
            'fields': ('resumen', 'hallazgos', 'recomendaciones', 'archivo')
        }),
        ('Generación', {
            'fields': ('generado_por', 'fecha_generacion'),
            'classes': ('collapse',)
        }),
    )
    
    def tasa_completacion_display(self, obj):
        tasa = obj.tasa_completacion()
        color = 'success' if tasa >= 80 else 'warning' if tasa >= 60 else 'danger'
        return format_html(
            '<span class="badge bg-{}">{:.1f}%</span>',
            color, tasa
        )
    tasa_completacion_display.short_description = 'Tasa de Completación'