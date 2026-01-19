from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Lote, MaterialLote, Trazabilidad, Almacen, MovimientoAlmacen

# ============ INLINES ============ #
class MaterialLoteInline(admin.TabularInline):
    model = MaterialLote
    extra = 1
    fields = ('material', 'cantidad_asignada', 'costo_unitario', 'entregado', 'fecha_entrega')
    readonly_fields = ('costo_total',)

class TrazabilidadInline(admin.TabularInline):
    model = Trazabilidad
    extra = 0
    readonly_fields = ('fecha', 'usuario')
    fields = ('tipo_evento', 'etapa', 'observaciones', 'fecha', 'usuario')
    can_delete = False

# ============ LOTE ============ #
@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = (
        'codigo', 
        'nombre_display', 
        'producto_link', 
        'estado_badge', 
        'cantidad_display', 
        'progreso_bar', 
        'fecha_creacion_short',
        'responsable_display'
    )
    list_filter = ('estado', 'prioridad', 'fecha_creacion', 'resultado_control_calidad')
    search_fields = ('codigo', 'nombre', 'descripcion', 'producto__nombre')
    readonly_fields = ('codigo', 'fecha_creacion', 'fecha_actualizacion', 'cantidad_aprobada')
    inlines = [MaterialLoteInline, TrazabilidadInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'descripcion', 'producto', 'orden_produccion')
        }),
        ('Cantidades', {
            'fields': (
                'cantidad_objetivo', 
                'cantidad_producida', 
                'cantidad_rechazada', 
                'cantidad_aprobada'
            )
        }),
        ('Tiempos', {
            'fields': (
                'fecha_inicio_planeada',
                'fecha_fin_planeada',
                'fecha_inicio_real',
                'fecha_fin_real'
            ),
            'classes': ('collapse',)
        }),
        ('Estado y Prioridad', {
            'fields': ('estado', 'prioridad', 'activo')
        }),
        ('Control de Calidad', {
            'fields': (
                'requiere_control_calidad',
                'control_calidad_completado',
                'resultado_control_calidad'
            )
        }),
        ('Costos y Precios', {
            'fields': ('costo_estimado', 'costo_real', 'precio_venta_estimado', 'margen_estimado'),
            'classes': ('collapse',)
        }),
        ('Ubicación', {
            'fields': ('ubicacion_actual', 'almacen_destino')
        }),
        ('Responsables', {
            'fields': ('responsable', 'supervisor', 'creado_por')
        }),
        ('Observaciones', {
            'fields': ('observaciones', 'etiquetas'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def nombre_display(self, obj):
        return obj.nombre[:30] + '...' if len(obj.nombre) > 30 else obj.nombre
    nombre_display.short_description = 'Nombre'
    
    def producto_link(self, obj):
        if obj.producto:
            url = reverse('admin:produccion_producto_change', args=[obj.producto.id])
            return format_html('<a href="{}">{}</a>', url, obj.producto.nombre)
        return "Sin producto"
    producto_link.short_description = 'Producto'
    
    def estado_badge(self, obj):
        color_map = {
            'planeado': 'secondary',
            'en_produccion': 'info',
            'completado': 'success',
            'detenido': 'warning',
            'cancelado': 'danger',
            'control_calidad': 'primary',
            'almacenado': 'dark',
            'despachado': 'success'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def cantidad_display(self, obj):
        return format_html(
            '<strong>{} / {} / {}</strong>',
            obj.cantidad_producida,
            obj.cantidad_objetivo,
            obj.cantidad_aprobada
        )
    cantidad_display.short_description = 'Prod / Obj / Aprob'
    
    def progreso_bar(self, obj):
        porcentaje = obj.progreso_produccion()
        color = 'success' if porcentaje >= 90 else 'warning' if porcentaje >= 70 else 'danger'
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
    progreso_bar.short_description = 'Progreso'
    
    def fecha_creacion_short(self, obj):
        return obj.fecha_creacion.strftime('%d/%m/%y')
    fecha_creacion_short.short_description = 'Creado'
    
    def responsable_display(self, obj):
        if obj.responsable:
            return obj.responsable.username
        return "Sin asignar"
    responsable_display.short_description = 'Responsable'

# ============ MATERIAL LOTE ============ #
@admin.register(MaterialLote)
class MaterialLoteAdmin(admin.ModelAdmin):
    list_display = (
        'lote_link',
        'material_link',
        'cantidad_display',
        'costo_display',
        'entregado_badge',
        'desperdicio_display'
    )
    list_filter = ('entregado', 'lote__estado')
    search_fields = ('lote__codigo', 'material__nombre')
    readonly_fields = ('costo_total', 'fecha_creacion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Información', {
            'fields': ('lote', 'material')
        }),
        ('Cantidades', {
            'fields': ('cantidad_asignada', 'cantidad_usada', 'cantidad_devolucion')
        }),
        ('Costos', {
            'fields': ('costo_unitario', 'costo_total')
        }),
        ('Desperdicio', {
            'fields': ('desperdicio_estimado', 'desperdicio_real')
        }),
        ('Entrega', {
            'fields': ('entregado', 'fecha_entrega', 'recibido_por')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def lote_link(self, obj):
        url = reverse('admin:lotes_lote_change', args=[obj.lote.id])
        return format_html('<a href="{}">{}</a>', url, obj.lote.codigo)
    lote_link.short_description = 'Lote'
    
    def material_link(self, obj):
        url = reverse('admin:materiales_material_change', args=[obj.material.id])
        return format_html('<a href="{}">{}</a>', url, obj.material.nombre)
    material_link.short_description = 'Material'
    
    def cantidad_display(self, obj):
        return format_html(
            '<strong>{} / {} / {}</strong><br><small>Disponible: {}</small>',
            obj.cantidad_usada,
            obj.cantidad_asignada,
            obj.cantidad_devolucion,
            obj.cantidad_disponible()
        )
    cantidad_display.short_description = 'Usada / Asignada / Devol'
    
    def costo_display(self, obj):
        return format_html(
            '${} / ${}',
            obj.costo_unitario,
            obj.costo_total
        )
    costo_display.short_description = 'Unitario / Total'
    
    def entregado_badge(self, obj):
        if obj.entregado:
            return format_html('<span class="badge bg-success">✅ Entregado</span>')
        return format_html('<span class="badge bg-warning">⏳ Pendiente</span>')
    entregado_badge.short_description = 'Entregado'
    
    def desperdicio_display(self, obj):
        if obj.desperdicio_real > 0:
            color = 'success' if obj.desperdicio_real <= 5 else 'warning' if obj.desperdicio_real <= 10 else 'danger'
            return format_html(
                '<span class="badge bg-{}">Est: {}% | Real: {}%</span>',
                color, obj.desperdicio_estimado, obj.desperdicio_real
            )
        return format_html(
            '<span class="badge bg-secondary">Est: {}%</span>',
            obj.desperdicio_estimado
        )
    desperdicio_display.short_description = 'Desperdicio'

# ============ TRAZABILIDAD ============ #
@admin.register(Trazabilidad)
class TrazabilidadAdmin(admin.ModelAdmin):
    list_display = (
        'lote_link',
        'tipo_evento_display',
        'etapa',
        'observaciones_short',
        'usuario_display',
        'fecha_short'
    )
    list_filter = ('tipo_evento', 'fecha')
    search_fields = ('lote__codigo', 'observaciones', 'etapa')
    readonly_fields = ('fecha',)
    
    def lote_link(self, obj):
        url = reverse('admin:lotes_lote_change', args=[obj.lote.id])
        return format_html('<a href="{}">{}</a>', url, obj.lote.codigo)
    lote_link.short_description = 'Lote'
    
    def tipo_evento_display(self, obj):
        color_map = {
            'creacion': 'success',
            'inicio_produccion': 'info',
            'fin_produccion': 'primary',
            'control_calidad': 'warning',
            'almacenamiento': 'dark',
            'despacho': 'success',
            'modificacion': 'secondary',
            'observacion': 'light',
            'problema': 'danger',
            'solucion': 'success'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.tipo_evento, 'secondary'),
            obj.get_tipo_evento_display()
        )
    tipo_evento_display.short_description = 'Tipo Evento'
    
    def observaciones_short(self, obj):
        return obj.observaciones[:50] + '...' if len(obj.observaciones) > 50 else obj.observaciones
    observaciones_short.short_description = 'Observaciones'
    
    def usuario_display(self, obj):
        if obj.usuario:
            return obj.usuario.username
        return "Sistema"
    usuario_display.short_description = 'Usuario'
    
    def fecha_short(self, obj):
        return obj.fecha.strftime('%d/%m/%y %H:%M')
    fecha_short.short_description = 'Fecha'

# ============ ALMACEN ============ #
@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'nombre',
        'tipo_display',
        'capacidad_display',
        'porcentaje_ocupacion_bar',
        'encargado_display',
        'activo_badge'
    )
    list_filter = ('tipo', 'activo')
    search_fields = ('codigo', 'nombre', 'descripcion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'capacidad_actual')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'tipo', 'descripcion')
        }),
        ('Ubicación', {
            'fields': ('ubicacion', 'capacidad_maxima', 'capacidad_actual')
        }),
        ('Condiciones de Almacenamiento', {
            'fields': (
                'temperatura_controlada',
                'temperatura_min',
                'temperatura_max',
                'humedad_controlada',
                'humedad_min',
                'humedad_max'
            ),
            'classes': ('collapse',)
        }),
        ('Personal', {
            'fields': ('encargado',)
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def tipo_display(self, obj):
        tipo_map = {
            'materia_prima': 'Materia Prima',
            'producto_terminado': 'Producto Terminado',
            'insumos': 'Insumos',
            'despacho': 'Despacho',
            'temporal': 'Temporal'
        }
        return tipo_map.get(obj.tipo, obj.tipo)
    tipo_display.short_description = 'Tipo'
    
    def capacidad_display(self, obj):
        return f"{obj.capacidad_actual} / {obj.capacidad_maxima}"
    capacidad_display.short_description = 'Ocupación'
    
    def porcentaje_ocupacion_bar(self, obj):
        porcentaje = obj.porcentaje_ocupacion()
        color = 'success' if porcentaje < 70 else 'warning' if porcentaje < 90 else 'danger'
        return format_html(
            '''
            <div class="progress" style="height: 20px; width: 80px;">
                <div class="progress-bar bg-{}" role="progressbar" 
                     style="width: {}%" aria-valuenow="{}" 
                     aria-valuemin="0" aria-valuemax="100">
                    {:.0f}%
                </div>
            </div>
            ''',
            color, porcentaje, porcentaje, porcentaje
        )
    porcentaje_ocupacion_bar.short_description = 'Ocupación %'
    
    def encargado_display(self, obj):
        if obj.encargado:
            return obj.encargado.username
        return "Sin asignar"
    encargado_display.short_description = 'Encargado'
    
    def activo_badge(self, obj):
        if obj.activo:
            return format_html('<span class="badge bg-success">✅ Activo</span>')
        return format_html('<span class="badge bg-danger">❌ Inactivo</span>')
    activo_badge.short_description = 'Activo'

# ============ MOVIMIENTOS DE ALMACÉN ============ #
@admin.register(MovimientoAlmacen)
class MovimientoAlmacenAdmin(admin.ModelAdmin):
    list_display = (
        'referencia',
        'tipo_movimiento_badge',
        'lote_link',
        'almacenes_display',
        'cantidad',
        'estado_badge',
        'fechas_display'
    )
    list_filter = ('tipo_movimiento', 'estado', 'fecha_creacion')
    search_fields = ('referencia', 'lote__codigo', 'motivo')
    readonly_fields = ('referencia', 'fecha_creacion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('referencia', 'tipo_movimiento')
        }),
        ('Relaciones', {
            'fields': ('lote', 'almacen_origen', 'almacen_destino')
        }),
        ('Cantidad', {
            'fields': ('cantidad',)
        }),
        ('Responsables', {
            'fields': ('solicitante', 'autorizador', 'ejecutor', 'creado_por')
        }),
        ('Fechas', {
            'fields': ('fecha_solicitud', 'fecha_autorizacion', 'fecha_ejecucion')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Documentación', {
            'fields': ('motivo', 'observaciones', 'documento_referencia'),
            'classes': ('collapse',)
        }),
    )
    
    def tipo_movimiento_badge(self, obj):
        color_map = {
            'entrada': 'success',
            'salida': 'danger',
            'transferencia': 'info',
            'ajuste': 'warning',
            'devolucion': 'secondary'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.tipo_movimiento, 'secondary'),
            obj.get_tipo_movimiento_display()
        )
    tipo_movimiento_badge.short_description = 'Tipo Movimiento'
    
    def lote_link(self, obj):
        if obj.lote:
            url = reverse('admin:lotes_lote_change', args=[obj.lote.id])
            return format_html('<a href="{}">{}</a>', url, obj.lote.codigo)
        return "Sin lote"
    lote_link.short_description = 'Lote'
    
    def almacenes_display(self, obj):
        origen = obj.almacen_origen.codigo if obj.almacen_origen else "N/A"
        destino = obj.almacen_destino.codigo if obj.almacen_destino else "N/A"
        
        if obj.tipo_movimiento == 'transferencia':
            return f"{origen} → {destino}"
        elif obj.tipo_movimiento == 'entrada':
            return f"→ {destino}"
        elif obj.tipo_movimiento == 'salida':
            return f"{origen} →"
        else:
            return origen or destino
    almacenes_display.short_description = 'Almacenes'
    
    def estado_badge(self, obj):
        color_map = {
            'pendiente': 'warning',
            'autorizado': 'info',
            'completado': 'success',
            'cancelado': 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color_map.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def fechas_display(self, obj):
        if obj.fecha_ejecucion:
            return obj.fecha_ejecucion.strftime('%d/%m')
        elif obj.fecha_autorizacion:
            return obj.fecha_autorizacion.strftime('%d/%m') + " (Auth)"
        else:
            return obj.fecha_solicitud.strftime('%d/%m') + " (Solic)"
    fechas_display.short_description = 'Fechas'