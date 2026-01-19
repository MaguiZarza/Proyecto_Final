from django.db import models
from django.contrib.auth.models import User
# REMOVED: from materiales.models import Producto  # Esta línea causaba el error
from procesos.models import Proceso
import uuid
from datetime import datetime, timedelta

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

# ============ MODELO PEDIDO ============ #
class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', '🟡 Pendiente'),
        ('en_proceso', '🟠 En Proceso'),
        ('completado', '🟢 Completado'),
        ('cancelado', '🔴 Cancelado'),
    ]
    
    PRIORIDAD_CHOICES = [
        (1, '🔵 Baja'),
        (2, '🟡 Media'),
        (3, '🔴 Alta'),
        (4, '⚠️ Urgente'),
    ]

    codigo = models.CharField(max_length=50, unique=True, default=generar_codigo_pedido)
    cliente = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    producto = models.ForeignKey('Producto', on_delete=models.PROTECT)  # Cambiado a string reference
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
        ('estandar', '⚙️ Estándar'),
        ('personalizado', '🎨 Personalizado'),
        ('rapido', '⚡ Rápido'),
        ('premium', '👑 Premium'),
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
    procesos = models.ManyToManyField('procesos.Proceso', through='MetodoProceso', blank=True)  # Cambiado a string reference
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

# ============ MODELO MÉTODO PROCESO ============ #
class MetodoProceso(models.Model):
    metodo = models.ForeignKey(MetodoProduccion, on_delete=models.CASCADE)
    proceso = models.ForeignKey('procesos.Proceso', on_delete=models.CASCADE)  # Cambiado a string reference
    orden = models.PositiveIntegerField(default=0)
    tiempo_estimado = models.PositiveIntegerField(default=0, help_text="Tiempo en minutos")
    responsable = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['orden']
        unique_together = ['metodo', 'proceso']

    def __str__(self):
        return f"{self.metodo.nombre} - {self.proceso.nombre}"

# ============ MODELO ORDEN PRODUCCIÓN ============ #
class OrdenProduccion(models.Model):
    ESTADO_CHOICES = [
        ('programada', '📅 Programada'),
        ('en_proceso', '⚙️ En Proceso'),
        ('pausada', '⏸️ Pausada'),
        ('completada', '✅ Completada'),
        ('cancelada', '❌ Cancelada'),
    ]

    codigo = models.CharField(max_length=50, unique=True, default=generar_codigo_orden)
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

# ============ MODELO PLANIFICACIÓN ============ #
class Planificacion(models.Model):
    TIPO_CHOICES = [
        ('semanal', '📅 Semanal'),
        ('mensual', '📆 Mensual'),
        ('diaria', '📋 Diaria'),
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
        ('manana', '🌅 Mañana'),
        ('tarde', '🌞 Tarde'),
        ('noche', '🌙 Noche'),
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
        ('diario', '📊 Diario'),
        ('semanal', '📈 Semanal'),
        ('mensual', '📉 Mensual'),
        ('anual', '📋 Anual'),
        ('especial', '🎯 Especial'),
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