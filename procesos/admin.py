from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Operacion, Proceso, EtapaProceso, MaterialProceso,
    FlujoTrabajo, ProcesoFlujo, Temporizador,
    ControlCalidad, ControlCalidadDetalle, NoConformidad
)

# ============ OPERACIONES ============ #
@admin.register(Operacion)
class OperacionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'usuario', 'accion_display', 'descripcion_corta', 'referencia')
    list_filter = ('accion', 'fecha', 'usuario')
    search_fields = ('descripcion', 'referencia')
    readonly_fields = ('fecha',)
    fieldsets = (
        ('Información', {
            'fields': ('usuario', 'accion', 'referencia', 'tiempo_empleado')
        }),
        ('Detalles', {
            'fields': ('descripcion',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha',),
            'classes': ('collapse',)
        }),
    )
    
    def accion_display(self, obj):
        return obj.get_accion_display()
    accion_display.short_description = 'Acción'
    
    def descripcion_corta(self, obj):
        return obj.descripcion[:100] + '...' if len(obj.descripcion) > 100 else obj.descripcion
    descripcion_corta.short_description = 'Descripción'

# ============ PROCESOS ============ #
class EtapaProcesoInline(admin.TabularInline):
    model = EtapaProceso
    extra = 1
    fields = ('nombre', 'orden', 'tiempo_estimado', 'asignado_a', 'completada')
    readonly_fields = ('fecha_inicio', 'fecha_fin', 'tiempo_real')

class MaterialProcesoInline(admin.TabularInline):
    model = MaterialProceso
    extra = 1
    fields = ('material', 'cantidad_necesaria', 'unidad', 'desperdicio_estimado')

@admin.register(Proceso)
class ProcesoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_display', 'estado_badge', 'orden', 
                   'tiempo_estimado_promedio_display', 'eficiencia_display', 
                   'veces_ejecutado', 'activo_badge')
    list_filter = ('tipo', 'estado', 'activo')
    search_fields = ('nombre', 'descripcion')
    inlines = [EtapaProcesoInline, MaterialProcesoInline]
    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'tipo', 'descripcion', 'orden')
        }),
        ('Tiempos', {
            'fields': ('tiempo_estimado_min', 'tiempo_estimado_max', 'tiempo_promedio')
        }),
        ('Estado', {
            'fields': ('estado', 'activo')
        }),
        ('Estadísticas', {
            'fields': ('veces_ejecutado', 'eficiencia'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )
    
    def tipo_display(self, obj):
        return obj.get_tipo_display()
    tipo_display.short_description = 'Tipo'
    
    def estado_badge(self, obj):
        color_map = {
            'pendiente': 'warning',
            'en_proceso': 'info',
            'completado': 'success',
            'detenido': 'danger',
            'cancelado': 'secondary'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def tiempo_estimado_promedio_display(self, obj):
        return str(obj.tiempo_estimado_promedio())
    tiempo_estimado_promedio_display.short_description = 'Tiempo Estimado'
    
    def eficiencia_display(self, obj):
        if obj.eficiencia == 0:
            return format_html('<span class="text-secondary">N/A</span>')
        
        color = 'success' if obj.eficiencia >= 90 else 'warning' if obj.eficiencia >= 70 else 'danger'
        return format_html(
            '<span class="badge bg-{}">{:.1f}%</span>',
            color, obj.eficiencia
        )
    eficiencia_display.short_description = 'Eficiencia'
    
    def activo_badge(self, obj):
        if obj.activo:
            return format_html('<span class="badge bg-success">✅ Activo</span>')
        return format_html('<span class="badge bg-danger">❌ Inactivo</span>')
    activo_badge.short_description = 'Activo'

# ============ FLUJOS DE TRABAJO ============ #
# DEFINIR ProcesoFlujoInline AQUÍ ANTES de FlujoTrabajoAdmin
class ProcesoFlujoInline(admin.TabularInline):
    model = ProcesoFlujo
    extra = 1
    fields = ('proceso', 'orden', 'requiere_completar_anterior', 'puede_paralelizar', 'es_opcional')

@admin.register(FlujoTrabajo)
class FlujoTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo_badge', 'tiempo_total_estimado', 
                   'veces_utilizado', 'eficiencia_promedio_display')
    list_filter = ('activo',)
    search_fields = ('nombre', 'descripcion')
    inlines = [ProcesoFlujoInline]
    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
        ('Tiempos', {
            'fields': ('tiempo_total_estimado',)
        }),
        ('Estadísticas', {
            'fields': ('veces_utilizado', 'eficiencia_promedio'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )
    
    def activo_badge(self, obj):
        if obj.activo:
            return format_html('<span class="badge bg-success">✅ Activo</span>')
        return format_html('<span class="badge bg-danger">❌ Inactivo</span>')
    activo_badge.short_description = 'Activo'
    
    def eficiencia_promedio_display(self, obj):
        if obj.eficiencia_promedio == 0:
            return format_html('<span class="text-secondary">N/A</span>')
        
        color = 'success' if obj.eficiencia_promedio >= 90 else 'warning' if obj.eficiencia_promedio >= 70 else 'danger'
        return format_html(
            '<span class="badge bg-{}">{:.1f}%</span>',
            color, obj.eficiencia_promedio
        )
    eficiencia_promedio_display.short_description = 'Eficiencia Prom.'

# ============ TEMPORIZADORES ============ #
@admin.register(Temporizador)
class TemporizadorAdmin(admin.ModelAdmin):
    list_display = ('id', 'proceso_link', 'estado_badge', 'operario', 
                   'tiempo_transcurrido', 'tiempo_restante_display', 
                   'porcentaje_bar', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion', 'operario')
    search_fields = ('proceso__nombre', 'etapa__nombre')
    readonly_fields = ('fecha_creacion', 'ultima_actualizacion', 'tiempo_transcurrido')
    fieldsets = (
        ('Información', {
            'fields': ('proceso', 'etapa', 'orden_produccion', 'operario')
        }),
        ('Tiempos', {
            'fields': ('tiempo_objetivo', 'tiempo_transcurrido', 'fecha_inicio', 'fecha_fin')
        }),
        ('Estado', {
            'fields': ('estado', 'activo')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'ultima_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def proceso_link(self, obj):
        if obj.proceso:
            url = reverse('admin:procesos_proceso_change', args=[obj.proceso.id])
            return format_html('<a href="{}">{}</a>', url, obj.proceso.nombre)
        elif obj.etapa:
            return f"Etapa: {obj.etapa.nombre}"
        return "Sin proceso"
    proceso_link.short_description = 'Proceso/Etapa'
    
    def estado_badge(self, obj):
        color_map = {
            'inactivo': 'secondary',
            'activo': 'success',
            'pausado': 'warning',
            'completado': 'info'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def tiempo_restante_display(self, obj):
        tiempo = obj.tiempo_restante()
        if tiempo.total_seconds() < 0:
            return format_html('<span class="text-danger">⚠ Excedido</span>')
        return str(tiempo)
    tiempo_restante_display.short_description = 'Tiempo Restante'
    
    def porcentaje_bar(self, obj):
        porcentaje = obj.porcentaje_completado()
        color = 'success' if porcentaje < 70 else 'warning' if porcentaje < 90 else 'danger'
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
    porcentaje_bar.short_description = 'Progreso'

# ============ CONTROL DE CALIDAD ============ #
class ControlCalidadDetalleInline(admin.TabularInline):
    model = ControlCalidadDetalle
    extra = 1
    fields = ('tipo_defecto', 'descripcion', 'severidad', 'requiere_reparacion')

@admin.register(ControlCalidad)
class ControlCalidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'proceso_link', 'fecha', 'inspector', 
                   'resultado_badge', 'puntuacion_total', 'cantidad_defectos')
    list_filter = ('resultado', 'fecha', 'inspector')
    search_fields = ('observaciones', 'proceso__nombre')
    inlines = [ControlCalidadDetalleInline]
    fieldsets = (
        ('Información', {
            'fields': ('proceso', 'etapa', 'orden_produccion', 'lote', 'inspector')
        }),
        ('Resultados', {
            'fields': ('resultado', 'observaciones', 'recomendaciones')
        }),
        ('Métricas', {
            'fields': ('puntuacion_total', 'cantidad_defectos', 'costo_reparacion')
        }),
        ('Auditoría', {
            'fields': ('revisado_por', 'fecha_revision'),
            'classes': ('collapse',)
        }),
    )
    
    def proceso_link(self, obj):
        if obj.proceso:
            url = reverse('admin:procesos_proceso_change', args=[obj.proceso.id])
            return format_html('<a href="{}">{}</a>', url, obj.proceso.nombre)
        return "General"
    proceso_link.short_description = 'Proceso'
    
    def resultado_badge(self, obj):
        color_map = {
            'aprobado': 'success',
            'rechazado': 'danger',
            'reparacion': 'warning',
            'revision': 'info'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.resultado, 'secondary'),
            obj.get_resultado_display()
        )
    resultado_badge.short_description = 'Resultado'

# ============ NO CONFORMIDADES ============ #
@admin.register(NoConformidad)
class NoConformidadAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion_corta', 'estado_badge', 
                   'prioridad_badge', 'reportado_por', 'fecha_reporte',
                   'dias_abiertos', 'responsable_correccion')
    list_filter = ('estado', 'prioridad', 'fecha_reporte')
    search_fields = ('codigo', 'descripcion', 'causa_raiz')
    readonly_fields = ('fecha_reporte', 'codigo')
    fieldsets = (
        ('Información', {
            'fields': ('codigo', 'proceso', 'control_calidad', 'orden_produccion')
        }),
        ('Descripción', {
            'fields': ('descripcion',)
        }),
        ('Estado', {
            'fields': ('estado', 'prioridad', 'fecha_limite')
        }),
        ('Análisis', {
            'fields': ('causa_raiz', 'accion_correctiva', 'accion_preventiva')
        }),
        ('Responsables', {
            'fields': ('reportado_por', 'responsable_correccion', 'verificada_por')
        }),
        ('Impacto', {
            'fields': ('cantidad_afectada', 'costo_estimado', 'impacto_produccion')
        }),
        ('Cierre', {
            'fields': ('fecha_cierre',),
            'classes': ('collapse',)
        }),
    )
    
    def descripcion_corta(self, obj):
        return obj.descripcion[:100] + '...' if len(obj.descripcion) > 100 else obj.descripcion
    descripcion_corta.short_description = 'Descripción'
    
    def estado_badge(self, obj):
        color_map = {
            'reportada': 'warning',
            'analisis': 'info',
            'correccion': 'primary',
            'verificada': 'success',
            'cerrada': 'secondary'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def prioridad_badge(self, obj):
        color_map = {
            1: 'success',
            2: 'warning',
            3: 'danger',
            4: 'dark'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.prioridad, 'secondary'),
            obj.get_prioridad_display()
        )
    prioridad_badge.short_description = 'Prioridad'
    
    def dias_abiertos(self, obj):
        return obj.dias_abierta()
    dias_abiertos.short_description = 'Días Abierta'

# ============ REGISTRO DE MODELOS RESTANTES ============ #
@admin.register(EtapaProceso)
class EtapaProcesoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proceso', 'orden', 'completada_badge', 
                   'asignado_a', 'tiempo_estimado', 'tiempo_real')
    list_filter = ('completada', 'proceso')
    search_fields = ('nombre', 'descripcion')
    
    def completada_badge(self, obj):
        if obj.completada:
            return format_html('<span class="badge bg-success">✅ Completada</span>')
        return format_html('<span class="badge bg-warning">⏳ Pendiente</span>')
    completada_badge.short_description = 'Completada'

@admin.register(MaterialProceso)
class MaterialProcesoAdmin(admin.ModelAdmin):
    list_display = ('proceso', 'material', 'cantidad_necesaria', 
                   'unidad', 'desperdicio_estimado')
    list_filter = ('proceso', 'material')
    search_fields = ('proceso__nombre', 'material__nombre')

@admin.register(ProcesoFlujo)
class ProcesoFlujoAdmin(admin.ModelAdmin):
    list_display = ('flujo_trabajo', 'proceso', 'orden', 
                   'requiere_completar_anterior', 'puede_paralelizar')
    list_filter = ('flujo_trabajo',)
    search_fields = ('flujo_trabajo__nombre', 'proceso__nombre')

@admin.register(ControlCalidadDetalle)
class ControlCalidadDetalleAdmin(admin.ModelAdmin):
    list_display = ('control_calidad', 'tipo_defecto', 'severidad_badge', 
                   'requiere_reparacion', 'ubicacion_defecto')
    list_filter = ('tipo_defecto', 'severidad')
    search_fields = ('descripcion', 'ubicacion_defecto')
    
    def severidad_badge(self, obj):
        color_map = {
            1: 'success',
            2: 'warning',
            3: 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.severidad, 'secondary'),
            obj.get_severidad_display()
        )
    severidad_badge.short_description = 'Severidad'