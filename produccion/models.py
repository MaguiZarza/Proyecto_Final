from django.db import models
from django.contrib.auth.models import User
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q

## Models de produccion

# ============ FUNCIONES AUXILIARES ============ #
def generar_codigo_pedido():
    """Genera un código único para pedidos"""
    return f"PED-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

def generar_codigo_orden():
    """Genera un código único para órdenes de producción"""
    return f"OP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

def fecha_entrega_default():
    """Fecha de entrega por defecto (7 días a partir de hoy)"""
    return datetime.now().date() + timedelta(days=7)

def fecha_programada_default():
    """Fecha programada por defecto (hoy)"""
    return datetime.now().date()

# ============ MODELO PRODUCTO ============ #
class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
    
    def __str__(self):
        return self.nombre
    
    @classmethod
    def crear_productos_predeterminados(cls):
        """Crea los productos predeterminados para un taller textil"""
        productos_data = [
            # Productos literales como los pediste
            {'nombre': 'remera', 'codigo': 'REM-001', 'costo_estimado': 1500, 'precio_venta': 3500},
            {'nombre': 'pantalon', 'codigo': 'PAN-001', 'costo_estimado': 3500, 'precio_venta': 7500},
            {'nombre': 'short', 'codigo': 'SHR-001', 'costo_estimado': 2000, 'precio_venta': 4500},
            {'nombre': 'chomba', 'codigo': 'CHO-001', 'costo_estimado': 2800, 'precio_venta': 6500},
            {'nombre': 'buzos', 'codigo': 'BUZ-001', 'costo_estimado': 4500, 'precio_venta': 9500},
            {'nombre': 'manga largas', 'codigo': 'MAN-001', 'costo_estimado': 2200, 'precio_venta': 4800},
            {'nombre': 'musculosas', 'codigo': 'MUS-001', 'costo_estimado': 1200, 'precio_venta': 2800},
            {'nombre': 'bolsos', 'codigo': 'BOL-001', 'costo_estimado': 2800, 'precio_venta': 6500},
            {'nombre': 'ropa de muñeca', 'codigo': 'ROM-001', 'costo_estimado': 800, 'precio_venta': 2000},
            {'nombre': 'calzas', 'codigo': 'CAL-001', 'costo_estimado': 3000, 'precio_venta': 6800},
            {'nombre': 'bikers', 'codigo': 'BIK-001', 'costo_estimado': 3200, 'precio_venta': 7200},
        ]
        
        productos_creados = []
        for data in productos_data:
            # Verificar si el producto ya existe
            if not cls.objects.filter(codigo=data['codigo']).exists():
                producto = cls.objects.create(
                    nombre=data['nombre'],
                    codigo=data['codigo'],
                    costo_estimado=data['costo_estimado'],
                    precio_venta=data['precio_venta'],
                    descripcion=f"Producto estándar de producción textil"
                )
                productos_creados.append(producto)
        
        return productos_creados

# ============ MODELO PEDIDO ============ #
class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', ' Pendiente'),
        ('en_proceso', ' En Proceso'),
        ('completado', ' Completado'),
        ('cancelado', ' Cancelado'),
    ]
    
    PRIORIDAD_CHOICES = [
        (1, ' Baja'),
        (2, ' Media'),
        (3, ' Alta'),
        (4, ' Urgente'),
    ]

    codigo = models.CharField(max_length=50, unique=True, default=generar_codigo_pedido)
    cliente = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    fecha_pedido = models.DateField(auto_now_add=True)
    fecha_entrega = models.DateField(default=fecha_entrega_default)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    prioridad = models.IntegerField(choices=PRIORIDAD_CHOICES, default=1)
    
    # Campos técnicos
    especificaciones = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    archivo_diseno = models.FileField(upload_to='disenos/', blank=True, null=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pedidos_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return f"{self.codigo} - {self.cliente} - {self.producto.nombre}"

    def dias_restantes(self):
        from django.utils import timezone
        hoy = timezone.now().date()
        return (self.fecha_entrega - hoy).days

    def es_urgente(self):
        return self.dias_restantes() <= 2 and self.estado != 'completado'


# ============ MODELO MÉTODO PRODUCCIÓN ============ #
class MetodoProduccion(models.Model):
    TIPO_CHOICES = [
        ('estandar', ' Estándar'),
        ('personalizado', ' Personalizado'),
        ('rapido', ' Rápido'),
        ('premium', ' Premium'),
    ]

    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='estandar')
    descripcion = models.TextField(blank=True)
    
    # Tiempos en minutos
    tiempo_preparacion = models.PositiveIntegerField(default=30, help_text="Tiempo en minutos")
    tiempo_confeccion = models.PositiveIntegerField(default=60, help_text="Tiempo en minutos por unidad")
    tiempo_acabado = models.PositiveIntegerField(default=15, help_text="Tiempo en minutos")
    
    # Costos
    costo_mano_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_maquinaria = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_adicional = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Configuración
    instrucciones = models.TextField(blank=True)
    imagen_referencia = models.ImageField(upload_to='metodos/', blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Método de Producción'
        verbose_name_plural = 'Métodos de Producción'

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    def tiempo_total_por_unidad(self):
        return self.tiempo_preparacion + self.tiempo_confeccion + self.tiempo_acabado

    def costo_total_por_unidad(self):
        return self.costo_mano_obra + self.costo_maquinaria + self.costo_adicional

    @classmethod
    def crear_metodos_produccion_predeterminados(cls):
        """Crea métodos de producción predeterminados"""
        metodos_data = [
            {
                'nombre': 'Producción Estándar',
                'codigo': 'MET-EST-001',
                'tipo': 'estandar',
                'descripcion': 'Método estándar para producción en serie',
                'tiempo_preparacion': 45,
                'tiempo_confeccion': 75,
                'tiempo_acabado': 25,
                'costo_mano_obra': 1200,
                'costo_maquinaria': 800,
                'costo_adicional': 200
            },
            {
                'nombre': 'Producción Rápida',
                'codigo': 'MET-RAP-001',
                'tipo': 'rapido',
                'descripcion': 'Método rápido para pedidos urgentes',
                'tiempo_preparacion': 20,
                'tiempo_confeccion': 45,
                'tiempo_acabado': 15,
                'costo_mano_obra': 1800,
                'costo_maquinaria': 1200,
                'costo_adicional': 500
            },
        ]
        
        metodos_creados = []
        for data in metodos_data:
            if not cls.objects.filter(codigo=data['codigo']).exists():
                metodo = cls.objects.create(**data)
                metodos_creados.append(metodo)
        
        return metodos_creados


# ============ MODELO MÉTODO PROCESO ============ #
class MetodoProceso(models.Model):
    metodo = models.ForeignKey(MetodoProduccion, on_delete=models.CASCADE)
    # Comenta esto temporalmente:
    # proceso = models.ForeignKey('procesos.Proceso', on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(default=0)
    tiempo_estimado = models.PositiveIntegerField(default=0, help_text="Tiempo en minutos")
    responsable = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['orden']
        # unique_together = ['metodo', 'proceso']  # Comenta esto también

    def __str__(self):
        # return f"{self.metodo.nombre} - {self.proceso.nombre}"  # Comenta esto
        return f"{self.metodo.nombre} - Proceso en orden {self.orden}"  # Cambia esto


# ============ MODELO ESTADO TRAZABILIDAD ============ #
class EstadoTrazabilidad(models.Model):
    """Estados para la trazabilidad del lote"""
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=20, default='#6c757d')
    icono = models.CharField(max_length=50, default='fa-circle')
    
    class Meta:
        ordering = ['orden']
        verbose_name = 'Estado de Trazabilidad'
        verbose_name_plural = 'Estados de Trazabilidad'
    
    def __str__(self):
        return self.nombre
    
    @classmethod
    def crear_estados_predeterminados(cls):
        """Crea los estados predeterminados para trazabilidad"""
        estados = [
            {'nombre': '📋 Planeado', 'orden': 1, 'color': '#6c757d', 'icono': 'fa-clipboard'},
            {'nombre': '✂️ Corte', 'orden': 2, 'color': '#dc3545', 'icono': 'fa-cut'},
            {'nombre': '🧵 Confección', 'orden': 3, 'color': '#fd7e14', 'icono': 'fa-thread'},
            {'nombre': '🔍 Revisión', 'orden': 4, 'color': '#ffc107', 'icono': 'fa-search'},
            {'nombre': '📦 Empaque', 'orden': 5, 'color': '#17a2b8', 'icono': 'fa-box'},
            {'nombre': '✅ Completado', 'orden': 6, 'color': '#28a745', 'icono': 'fa-check-circle'},
            {'nombre': '🚚 Despachado', 'orden': 7, 'color': '#007bff', 'icono': 'fa-truck'},
        ]
        
        for estado in estados:
            cls.objects.get_or_create(
                nombre=estado['nombre'],
                defaults=estado
            )
        return cls.objects.all()


# ============ MODELO ORDEN PRODUCCIÓN CON LOTE INTEGRADO ============ #
class OrdenProduccion(models.Model):
    ESTADO_CHOICES = [
        ('programada', ' Programada'),
        ('en_proceso', ' En Proceso'),
        ('pausada', ' Pausada'),
        ('completada', ' Completada'),
        ('cancelada', ' Cancelada'),
    ]

    codigo = models.CharField(max_length=50, blank=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='ordenes_produccion')
    metodo = models.ForeignKey(MetodoProduccion, on_delete=models.PROTECT)
    
    # Fechas
    fecha_programada = models.DateField(default=fecha_programada_default)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Estado y progreso
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='programada')
    progreso = models.PositiveIntegerField(default=0, help_text="Progreso en porcentaje (0-100)")
    
    # Responsables
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ordenes_supervisadas')
    equipo = models.ManyToManyField(User, related_name='ordenes_asignadas', blank=True)
    
    # Detalles
    cantidad_a_producir = models.PositiveIntegerField()
    cantidad_producida = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True)
    incidencias = models.TextField(blank=True)
    
    # === CAMPOS NUEVOS DE LOTE INTEGRADO === #
    # Código de lote simplificado (generado automáticamente)
    codigo_lote = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    
    # Trazabilidad
    estado_trazabilidad = models.ForeignKey(
        EstadoTrazabilidad, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ordenes'
    )
    
    # Cantidades específicas de lote
    cantidad_rechazada = models.PositiveIntegerField(default=0)
    cantidad_aprobada = models.PositiveIntegerField(default=0)
    
    # Ubicación actual
    ubicacion_actual = models.CharField(max_length=100, blank=True)
    
    # Control de calidad integrado
    requiere_control_calidad = models.BooleanField(default=True)
    resultado_control_calidad = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', '⏳ Pendiente'),
            ('aprobado', '✅ Aprobado'),
            ('rechazado', '❌ Rechazado'),
            ('reparacion', '🔧 Requiere Reparación'),
            ('parcial', '⚠️ Parcial'),
        ],
        default='pendiente'
    )
    
    # Fechas específicas de lote
    fecha_inicio_produccion = models.DateTimeField(null=True, blank=True)
    fecha_fin_produccion = models.DateTimeField(null=True, blank=True)
    fecha_control_calidad = models.DateTimeField(null=True, blank=True)
    fecha_almacenamiento = models.DateTimeField(null=True, blank=True)
    fecha_despacho = models.DateTimeField(null=True, blank=True)
    
    # Auditoría de lote
    revisado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lotes_revisados'
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)
    
    # Tags para búsqueda
    etiquetas = models.JSONField(default=list, blank=True)
    
    # Añadir campo activo si es necesario
    activo = models.BooleanField(default=True)
    # === FIN CAMPOS NUEVOS === #

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Orden de Producción'
        verbose_name_plural = 'Órdenes de Producción'

    def __str__(self):
        return f"{self.codigo} - {self.pedido.cliente}"

    def tiempo_transcurrido(self):
        if self.fecha_inicio and self.fecha_fin:
            return self.fecha_fin - self.fecha_inicio
        elif self.fecha_inicio:
            from django.utils import timezone
            return timezone.now() - self.fecha_inicio
        return None

    def actualizar_progreso(self):
        if self.cantidad_a_producir > 0:
            self.progreso = int((self.cantidad_producida / self.cantidad_a_producir) * 100)
        else:
            self.progreso = 0
        self.save()

    def _obtener_codigo_producto_para_lote(self):
        """Obtiene el código abreviado para el lote según el producto"""
        # Mapeo de productos a códigos abreviados (según tu ejemplo)
        mapeo_codigos = {
            'remera': 'REM',
            'pantalon': 'PAN',
            'short': 'SHR',
            'chomba': 'CHO',
            'buzos': 'BUZ',
            'manga largas': 'MAN',
            'musculosas': 'MUS',
            'bolsos': 'BOL',
            'ropa de muñeca': 'ROM',
            'calzas': 'CAL',
            'bikers': 'BIK',
        }
        
        nombre_producto = self.pedido.producto.nombre.lower()
        return mapeo_codigos.get(nombre_producto, 'GEN')

    def generar_codigo_lote_simplificado(self):
        """Genera un código de lote simple - VERSIÓN TEMPORAL"""
        # Por ahora usa un formato simple, luego integraremos tu formato
        fecha = timezone.now().strftime('%y%m%d')
        
        # Obtener código de producto abreviado
        producto_cod = self._obtener_codigo_producto_para_lote()
        
        # Contar cuántos lotes del mismo producto hoy
        hoy = timezone.now().date()
        mismo_producto_hoy = OrdenProduccion.objects.filter(
            pedido__producto__nombre__iexact=self.pedido.producto.nombre,
            fecha_creacion__date=hoy
        ).count()
        
        secuencia = mismo_producto_hoy + 1
        return f"{producto_cod}-{fecha}-{secuencia:03d}"

    def save(self, *args, **kwargs):
        # Si no tiene código, usar el código del pedido con sufijo para múltiples órdenes
        if not self.codigo and self.pedido:
            ordenes_existentes = OrdenProduccion.objects.filter(pedido=self.pedido).exclude(id=self.id).count()
            
            if ordenes_existentes == 0:
                self.codigo = self.pedido.codigo
            else:
                self.codigo = f"{self.pedido.codigo}-{ordenes_existentes + 1:02d}"
        
        # Generar código de lote si no existe
        if not self.codigo_lote:
            self.codigo_lote = self.generar_codigo_lote_simplificado()
        
        # Actualizar cantidad aprobada
        self.cantidad_aprobada = max(0, self.cantidad_producida - self.cantidad_rechazada)
        
        # Si se completa la producción, actualizar fechas
        if self.estado == 'completada' and not self.fecha_fin_produccion:
            self.fecha_fin_produccion = timezone.now()
        
        super().save(*args, **kwargs)

    def registrar_trazabilidad(self, etapa, observaciones="", usuario=None):
        """Registra un evento en la trazabilidad del lote"""
        from procesos.models import Operacion
        
        Operacion.objects.create(
            usuario=usuario,
            accion='trazabilidad_lote',
            descripcion=f"Lote {self.codigo_lote}: {etapa}. {observaciones}",
            referencia=self.codigo_lote
        )
        
        # Actualizar ubicación según etapa
        self.ubicacion_actual = etapa
        self.save()

    def iniciar_control_calidad(self):
        """Inicia el control de calidad del lote"""
        self.resultado_control_calidad = 'pendiente'
        self.fecha_control_calidad = timezone.now()
        self.save()
        self.registrar_trazabilidad("Control de calidad iniciado")

    def aprobar_control_calidad(self, usuario):
        """Aprueba el lote en control de calidad"""
        self.resultado_control_calidad = 'aprobado'
        self.revisado_por = usuario
        self.fecha_revision = timezone.now()
        self.save()
        self.registrar_trazabilidad("Control de calidad aprobado", usuario=usuario)

    def rechazar_control_calidad(self, cantidad_rechazada, motivo, usuario):
        """Rechaza total o parcialmente el lote"""
        self.cantidad_rechazada = cantidad_rechazada
        self.cantidad_aprobada = max(0, self.cantidad_producida - cantidad_rechazada)
        
        if cantidad_rechazada >= self.cantidad_producida:
            self.resultado_control_calidad = 'rechazado'
        else:
            self.resultado_control_calidad = 'parcial'
        
        self.revisado_por = usuario
        self.fecha_revision = timezone.now()
        self.save()
        
        self.registrar_trazabilidad(
            f"Control de calidad: {cantidad_rechazada} unidades rechazadas. Motivo: {motivo}",
            usuario=usuario
        )

    def marcar_como_almacenado(self):
        """Marca el lote como almacenado"""
        self.fecha_almacenamiento = timezone.now()
        self.save()
        self.registrar_trazabilidad("Lote almacenado")

    def marcar_como_despachado(self):
        """Marca el lote como despachado"""
        self.fecha_despacho = timezone.now()
        self.save()
        self.registrar_trazabilidad("Lote despachado")

# ============ MODELO PLANIFICACIÓN ============ #
class Planificacion(models.Model):
    TIPO_CHOICES = [
        ('semanal', ' Semanal'),
        ('mensual', ' Mensual'),
        ('diaria', ' Diaria'),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    
    # Relaciones
    ordenes = models.ManyToManyField(OrdenProduccion, through='PlanificacionOrden', blank=True)
    responsables = models.ManyToManyField(User, related_name='planificaciones', blank=True)
    
    # Metadatos
    descripcion = models.TextField(blank=True)
    objetivos = models.TextField(blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='planificaciones_actualizadas')
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Estado
    activa = models.BooleanField(default=True)
    completada = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Planificación'
        verbose_name_plural = 'Planificaciones'

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    def duracion_dias(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def porcentaje_completado(self):
        ordenes = self.ordenes.all()
        if not ordenes:
            return 0
        total = ordenes.count()
        completadas = ordenes.filter(estado='completada').count()
        return int((completadas / total) * 100) if total > 0 else 0


# ============ MODELO PLANIFICACIÓN ORDEN ============ #
class PlanificacionOrden(models.Model):
    planificacion = models.ForeignKey(Planificacion, on_delete=models.CASCADE)
    orden = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE)
    fecha_asignada = models.DateField()
    turno = models.CharField(max_length=20, choices=[
        ('manana', ' Mañana'),
        ('tarde', ' Tarde'),
        ('noche', ' Noche'),
    ], default='manana')
    
    prioridad = models.IntegerField(default=1)
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha_asignada', 'turno', 'prioridad']
        unique_together = ['orden', 'fecha_asignada', 'turno']

    def __str__(self):
        return f"{self.orden.codigo} - {self.fecha_asignada} ({self.get_turno_display()})"


# ============ MODELO REPORTE PRODUCCIÓN ============ #
class ReporteProduccion(models.Model):
    TIPO_CHOICES = [
        ('diario', ' Diario'),
        ('semanal', ' Semanal'),
        ('mensual', ' Mensual'),
        ('anual', ' Anual'),
        ('especial', ' Especial'),
    ]

    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    
    # Métricas
    total_pedidos = models.PositiveIntegerField(default=0)
    pedidos_completados = models.PositiveIntegerField(default=0)
    pedidos_pendientes = models.PositiveIntegerField(default=0)
    eficiencia = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tiempo_promedio = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Costos
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_materiales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_mano_obra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Archivo
    archivo = models.FileField(upload_to='reportes/', blank=True, null=True)
    generado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    
    # Contenido
    resumen = models.TextField(blank=True)
    hallazgos = models.TextField(blank=True)
    recomendaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-periodo_fin']
        verbose_name = 'Reporte de Producción'
        verbose_name_plural = 'Reportes de Producción'

    def __str__(self):
        return f"{self.titulo} ({self.periodo_inicio} al {self.periodo_fin})"

    def tasa_completacion(self):
        if self.total_pedidos > 0:
            return (self.pedidos_completados / self.total_pedidos) * 100
        return 0


# ============ FUNCIÓN PARA CREAR DATOS PREDETERMINADOS ============ #
def crear_datos_predeterminados():
    """Función para crear todos los datos predeterminados"""
    # Crear productos predeterminados
    productos = Producto.crear_productos_predeterminados()
    
    # Crear métodos de producción predeterminados
    metodos = MetodoProduccion.crear_metodos_produccion_predeterminados()
    
    # Crear estados de trazabilidad predeterminados
    estados = EstadoTrazabilidad.crear_estados_predeterminados()
    
    return {
        'productos_creados': len(productos),
        'metodos_creados': len(metodos),
        'estados_creados': len(estados)
    }