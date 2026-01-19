from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, Q
from decimal import Decimal
import uuid

# ============ MODELOS DE LOTE ============ #
class Lote(models.Model):
    ESTADO_CHOICES = [
        ('planeado', '📋 Planeado'),
        ('en_produccion', '🔄 En Producción'),
        ('completado', '✅ Completado'),
        ('detenido', '⛔ Detenido'),
        ('cancelado', '❌ Cancelado'),
        ('control_calidad', '🔍 En Control de Calidad'),
        ('almacenado', '📦 Almacenado'),
        ('despachado', '🚚 Despachado'),
    ]

    PRIORIDAD_CHOICES = [
        (1, '🟢 Baja'),
        (2, '🟡 Media'),
        (3, '🔴 Alta'),
        (4, '⚫ Crítica'),
    ]

    # Identificación única
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    # Relaciones
    orden_produccion = models.ForeignKey(
        'produccion.OrdenProduccion', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lotes'
    )
    producto = models.ForeignKey(
        'produccion.Producto', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lotes'
    )
    
    # Cantidades
    cantidad_objetivo = models.PositiveIntegerField(default=0)
    cantidad_producida = models.PositiveIntegerField(default=0)
    cantidad_rechazada = models.PositiveIntegerField(default=0)
    cantidad_aprobada = models.PositiveIntegerField(default=0)
    
    # Tiempos
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_inicio_planeada = models.DateTimeField(null=True, blank=True)
    fecha_fin_planeada = models.DateTimeField(null=True, blank=True)
    fecha_inicio_real = models.DateTimeField(null=True, blank=True)
    fecha_fin_real = models.DateTimeField(null=True, blank=True)
    
    # Estado y prioridad
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='planeado')
    prioridad = models.IntegerField(choices=PRIORIDAD_CHOICES, default=2)
    
    # Costos y precios
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_real = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_venta_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    margen_estimado = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Ubicación
    ubicacion_actual = models.CharField(max_length=100, blank=True)
    almacen_destino = models.ForeignKey(
        'Almacen', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lotes_almacenados'
    )
    
    # Control de calidad
    requiere_control_calidad = models.BooleanField(default=True)
    control_calidad_completado = models.BooleanField(default=False)
    resultado_control_calidad = models.CharField(
        max_length=20, 
        choices=[
            ('pendiente', 'Pendiente'), 
            ('aprobado', 'Aprobado'), 
            ('rechazado', 'Rechazado'), 
            ('parcial', 'Parcial')
        ],
        default='pendiente'
    )
    
    # Responsables
    responsable = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lotes_responsable'
    )
    supervisor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lotes_supervisados'
    )
    
    # Auditoría
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='lotes_creados'
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Campos adicionales
    observaciones = models.TextField(blank=True)
    etiquetas = models.JSONField(default=list, blank=True)  # Tags para búsqueda y filtrado
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_creacion']),
        ]

    def __str__(self):
        return f"Lote {self.codigo} - {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Generar código automático
            year = timezone.now().year
            ultimo_lote = Lote.objects.filter(codigo__startswith=f'LOT-{year}-').order_by('-id').first()
            
            if ultimo_lote:
                try:
                    ultimo_numero = int(ultimo_lote.codigo.split('-')[-1])
                except:
                    ultimo_numero = 0
            else:
                ultimo_numero = 0
            
            self.codigo = f"LOT-{year}-{ultimo_numero + 1:04d}"
        
        # Calcular cantidad aprobada
        self.cantidad_aprobada = max(0, self.cantidad_producida - self.cantidad_rechazada)
        
        super().save(*args, **kwargs)

    def progreso_produccion(self):
        """Calcula el porcentaje de progreso de producción"""
        if self.cantidad_objetivo == 0:
            return 0
        return (self.cantidad_producida / self.cantidad_objetivo) * 100

    def tiempo_transcurrido(self):
        """Calcula el tiempo transcurrido desde el inicio"""
        if self.fecha_inicio_real:
            if self.fecha_fin_real:
                return self.fecha_fin_real - self.fecha_inicio_real
            return timezone.now() - self.fecha_inicio_real
        return timezone.timedelta(0)

    def tiempo_restante_estimado(self):
        """Calcula el tiempo restante estimado"""
        if self.fecha_fin_planeada and self.fecha_inicio_real:
            tiempo_total_planeado = self.fecha_fin_planeada - self.fecha_inicio_real
            progreso = self.progreso_produccion() / 100
            
            if progreso > 0:
                tiempo_total_estimado = self.tiempo_transcurrido() / progreso
                return tiempo_total_estimado - self.tiempo_transcurrido()
            
        return None

    def calcular_costos(self):
        """Calcula costos estimados y reales"""
        # Calcular costo de materiales
        costo_materiales = MaterialLote.objects.filter(lote=self).aggregate(
            total=Sum(F('cantidad_usada') * F('costo_unitario'))
        )['total'] or 0
        
        self.costo_real = Decimal(str(costo_materiales))
        
        # Actualizar margen
        if self.precio_venta_estimado > 0:
            self.margen_estimado = ((self.precio_venta_estimado - self.costo_real) / self.precio_venta_estimado) * 100
        
        self.save()

    def iniciar_produccion(self):
        """Inicia la producción del lote"""
        if self.estado == 'planeado':
            self.estado = 'en_produccion'
            self.fecha_inicio_real = timezone.now()
            self.save()
            
            # Registrar trazabilidad
            Trazabilidad.objects.create(
                lote=self,
                etapa='Inicio de producción',
                observaciones=f'Inicio de producción del lote {self.codigo}',
                usuario=self.responsable
            )

    def finalizar_produccion(self):
        """Finaliza la producción del lote"""
        if self.estado == 'en_produccion':
            self.estado = 'control_calidad'
            self.fecha_fin_real = timezone.now()
            self.save()
            
            # Registrar trazabilidad
            Trazabilidad.objects.create(
                lote=self,
                etapa='Finalización de producción',
                observaciones=f'Producción finalizada. Cantidad producida: {self.cantidad_producida}',
                usuario=self.responsable
            )

    def aprobar_control_calidad(self):
        """Aprueba el lote después del control de calidad"""
        if self.estado == 'control_calidad':
            self.estado = 'almacenado'
            self.control_calidad_completado = True
            self.resultado_control_calidad = 'aprobado'
            self.save()
            
            # Registrar trazabilidad
            Trazabilidad.objects.create(
                lote=self,
                etapa='Control de calidad aprobado',
                observaciones='Lote aprobado para almacenamiento',
                usuario=self.supervisor
            )

    def rechazar_lote(self, cantidad_rechazada, motivo=""):
        """Rechaza total o parcialmente el lote"""
        self.cantidad_rechazada = cantidad_rechazada
        self.cantidad_aprobada = max(0, self.cantidad_producida - cantidad_rechazada)
        
        if cantidad_rechazada >= self.cantidad_producida:
            self.resultado_control_calidad = 'rechazado'
            self.estado = 'detenido'
        else:
            self.resultado_control_calidad = 'parcial'
        
        self.observaciones += f"\nRechazo: {motivo}"
        self.save()
        
        # Registrar trazabilidad
        Trazabilidad.objects.create(
            lote=self,
            etapa='Rechazo en control de calidad',
            observaciones=f'{cantidad_rechazada} unidades rechazadas. Motivo: {motivo}',
            usuario=self.supervisor
        )

# ============ MATERIALES POR LOTE ============ #
class MaterialLote(models.Model):
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='materiales_detalle')
    material = models.ForeignKey('materiales.Material', on_delete=models.CASCADE)
    
    # Cantidades
    cantidad_asignada = models.DecimalField(max_digits=10, decimal_places=3)
    cantidad_usada = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    cantidad_devolucion = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    
    # Costos
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Desperdicio
    desperdicio_estimado = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% de desperdicio")
    desperdicio_real = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Control
    entregado = models.BooleanField(default=False)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    recibido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Material por Lote'
        verbose_name_plural = 'Materiales por Lote'
        unique_together = ['lote', 'material']

    def __str__(self):
        return f"{self.lote.codigo} - {self.material.nombre}"

    def save(self, *args, **kwargs):
        # Calcular costo total
        self.costo_total = self.cantidad_asignada * self.costo_unitario
        super().save(*args, **kwargs)

    def cantidad_disponible(self):
        """Cantidad que aún no se ha usado"""
        return self.cantidad_asignada - self.cantidad_usada

    def registrar_uso(self, cantidad):
        """Registra el uso de material"""
        if cantidad <= self.cantidad_disponible():
            self.cantidad_usada += cantidad
            self.save()
            return True
        return False

    def registrar_devolucion(self, cantidad, motivo=""):
        """Registra devolución de material no utilizado"""
        if cantidad <= self.cantidad_disponible():
            self.cantidad_devolucion += cantidad
            self.observaciones = f"{self.observaciones}\nDevolución: {cantidad} - {motivo}"
            self.save()
            
            # Actualizar inventario del material
            self.material.cantidad_disponible += cantidad
            self.material.save()
            
            return True
        return False

# ============ TRAZABILIDAD DEL LOTE ============ #
class Trazabilidad(models.Model):
    TIPO_EVENTO_CHOICES = [
        ('creacion', 'Creación'),
        ('inicio_produccion', 'Inicio de Producción'),
        ('fin_produccion', 'Fin de Producción'),
        ('control_calidad', 'Control de Calidad'),
        ('almacenamiento', 'Almacenamiento'),
        ('despacho', 'Despacho'),
        ('modificacion', 'Modificación'),
        ('observacion', 'Observación'),
        ('problema', 'Problema Detectado'),
        ('solucion', 'Problema Solucionado'),
    ]

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='trazabilidad')
    fecha = models.DateTimeField(default=timezone.now)
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES, default='observacion')
    etapa = models.CharField(max_length=100)
    observaciones = models.TextField()
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Datos adicionales
    cantidad_afectada = models.PositiveIntegerField(default=0, blank=True, null=True)
    ubicacion = models.CharField(max_length=100, blank=True)
    documento_referencia = models.CharField(max_length=100, blank=True)
    
    # Archivos adjuntos
    archivo = models.FileField(upload_to='trazabilidad_lotes/', null=True, blank=True)
    foto = models.ImageField(upload_to='trazabilidad_lotes/fotos/', null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Registro de Trazabilidad'
        verbose_name_plural = 'Registros de Trazabilidad'

    def __str__(self):
        return f"{self.lote.codigo} - {self.get_tipo_evento_display()} - {self.fecha:%Y-%m-%d %H:%M}"

# ============ ALMACENES ============ #
class Almacen(models.Model):
    TIPO_ALMACEN_CHOICES = [
        ('materia_prima', 'Materia Prima'),
        ('producto_terminado', 'Producto Terminado'),
        ('insumos', 'Insumos'),
        ('despacho', 'Despacho'),
        ('temporal', 'Temporal'),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_ALMACEN_CHOICES, default='producto_terminado')
    descripcion = models.TextField(blank=True)
    
    # Ubicación física
    ubicacion = models.CharField(max_length=200, blank=True)
    capacidad_maxima = models.PositiveIntegerField(default=0, help_text="Capacidad en unidades")
    capacidad_actual = models.PositiveIntegerField(default=0)
    
    # Control de temperatura y humedad (si aplica)
    temperatura_controlada = models.BooleanField(default=False)
    temperatura_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperatura_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humedad_controlada = models.BooleanField(default=False)
    humedad_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humedad_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Responsable
    encargado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='almacenes_encargados')
    
    # Estado
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['codigo']
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def capacidad_disponible(self):
        """Calcula la capacidad disponible del almacén"""
        return max(0, self.capacidad_maxima - self.capacidad_actual)

    def porcentaje_ocupacion(self):
        """Calcula el porcentaje de ocupación"""
        if self.capacidad_maxima == 0:
            return 0
        return (self.capacidad_actual / self.capacidad_maxima) * 100

    def actualizar_capacidad(self):
        """Actualiza la capacidad actual basada en los lotes almacenados"""
        cantidad_lotes = Lote.objects.filter(
            almacen_destino=self,
            estado='almacenado'
        ).count()
        
        self.capacidad_actual = cantidad_lotes
        self.save()

# ============ MOVIMIENTOS DE ALMACÉN ============ #
class MovimientoAlmacen(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('transferencia', 'Transferencia'),
        ('ajuste', 'Ajuste'),
        ('devolucion', 'Devolución'),
    ]

    referencia = models.CharField(max_length=50, unique=True)
    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO_CHOICES)
    
    # Relaciones
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, null=True, blank=True, related_name='movimientos')
    almacen_origen = models.ForeignKey(Almacen, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_salida')
    almacen_destino = models.ForeignKey(Almacen, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_entrada')
    
    # Cantidades
    cantidad = models.PositiveIntegerField(default=1)
    
    # Responsables
    solicitante = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='movimientos_solicitados')
    autorizador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_autorizados')
    ejecutor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_ejecutados')
    
    # Fechas
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    fecha_ejecucion = models.DateTimeField(null=True, blank=True)
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente'),
            ('autorizado', 'Autorizado'),
            ('completado', 'Completado'),
            ('cancelado', 'Cancelado'),
        ],
        default='pendiente'
    )
    
    # Documentación
    motivo = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    documento_referencia = models.CharField(max_length=100, blank=True)
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='movimientos_creados')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Movimiento de Almacén'
        verbose_name_plural = 'Movimientos de Almacén'

    def __str__(self):
        return f"{self.referencia} - {self.get_tipo_movimiento_display()}"

    def save(self, *args, **kwargs):
        if not self.referencia:
            # Generar referencia automática
            year = timezone.now().year
            ultimo_mov = MovimientoAlmacen.objects.filter(
                referencia__startswith=f'MOV-{year}-'
            ).order_by('-id').first()
            
            if ultimo_mov:
                try:
                    ultimo_numero = int(ultimo_mov.referencia.split('-')[-1])
                except:
                    ultimo_numero = 0
            else:
                ultimo_numero = 0
            
            self.referencia = f"MOV-{year}-{ultimo_numero + 1:04d}"
        
        super().save(*args, **kwargs)

    def autorizar(self, usuario):
        """Autoriza el movimiento"""
        if self.estado == 'pendiente':
            self.estado = 'autorizado'
            self.autorizador = usuario
            self.fecha_autorizacion = timezone.now()
            self.save()

    def ejecutar(self, usuario):
        """Ejecuta el movimiento"""
        if self.estado == 'autorizado':
            # Actualizar ubicación del lote
            if self.lote and self.almacen_destino:
                self.lote.ubicacion_actual = self.almacen_destino.nombre
                self.lote.almacen_destino = self.almacen_destino
                
                if self.tipo_movimiento == 'entrada':
                    self.lote.estado = 'almacenado'
                elif self.tipo_movimiento == 'salida':
                    self.lote.estado = 'despachado'
                
                self.lote.save()
            
            self.estado = 'completado'
            self.ejecutor = usuario
            self.fecha_ejecucion = timezone.now()
            self.save()
            
            # Actualizar capacidad del almacén
            if self.almacen_destino:
                self.almacen_destino.actualizar_capacidad()
            if self.almacen_origen:
                self.almacen_origen.actualizar_capacidad()

    def cancelar(self, usuario, motivo=""):
        """Cancela el movimiento"""
        if self.estado in ['pendiente', 'autorizado']:
            self.estado = 'cancelado'
            self.observaciones += f"\nCancelado por {usuario.username}: {motivo}"
            self.save()