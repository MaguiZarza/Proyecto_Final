from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import json

# ============ REGISTRO DE OPERACIONES (YA EXISTE) ============ #
class Operacion(models.Model):
    ACCION_CHOICES = [
        ('calculo_materiales', 'Cálculo de materiales'),
        ('calculo_hilo', 'Cálculo de hilo'),
        ('proceso_iniciado', 'Proceso iniciado'),
        ('proceso_finalizado', 'Proceso finalizado'),
        ('control_calidad', 'Control de calidad'),
        ('no_conformidad', 'No conformidad detectada'),
        ('temporizador', 'Temporizador utilizado'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=50, choices=ACCION_CHOICES)
    descripcion = models.TextField()
    referencia = models.CharField(max_length=100, blank=True)  # ID de orden, lote, etc.
    tiempo_empleado = models.DurationField(null=True, blank=True)  # Tiempo si aplica

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Operación'
        verbose_name_plural = 'Operaciones'

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} - {self.get_accion_display()}"

# ============ PROCESOS Y ETAPAS ============ #
class Proceso(models.Model):
    TIPO_CHOICES = [
        ('corte', '✂️ Corte'),
        ('confeccion', '🧵 Confección'),
        ('planchado', '🧺 Planchado'),
        ('revision', '🔍 Revisión'),
        ('empaque', '📦 Empaque'),
        ('almacen', '📦 Almacén'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', '⏳ Pendiente'),
        ('en_proceso', '🔄 En Proceso'),
        ('completado', '✅ Completado'),
        ('detenido', '⛔ Detenido'),
        ('cancelado', '❌ Cancelado'),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='confeccion')
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0)
    
    # Tiempos estimados - AGREGAR VALORES POR DEFECTO
    tiempo_estimado_min = models.DurationField(
        help_text="Tiempo mínimo estimado (HH:MM:SS)",
        default=timezone.timedelta(hours=1)  # VALOR POR DEFECTO: 1 hora
    )
    tiempo_estimado_max = models.DurationField(
        help_text="Tiempo máximo estimado (HH:MM:SS)",
        default=timezone.timedelta(hours=2)  # VALOR POR DEFECTO: 2 horas
    )
    
    # Estado y control
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    activo = models.BooleanField(default=True)
    
    # Materiales requeridos (relación con materiales)
    materiales_necesarios = models.ManyToManyField(
        'materiales.Material', 
        through='MaterialProceso',
        blank=True
    )
    
    # Estadísticas
    veces_ejecutado = models.PositiveIntegerField(default=0)
    tiempo_promedio = models.DurationField(null=True, blank=True)
    eficiencia = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% de eficiencia")
    
    # AGREGAR VALOR POR DEFECTO PARA fecha_creacion
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='procesos_creados')

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Proceso'
        verbose_name_plural = 'Procesos'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"

    def tiempo_estimado_promedio(self):
        """Calcula el tiempo promedio estimado"""
        if self.tiempo_estimado_min and self.tiempo_estimado_max:
            # Conversión a segundos
            min_seg = self.tiempo_estimado_min.total_seconds()
            max_seg = self.tiempo_estimado_max.total_seconds()
            promedio_seg = (min_seg + max_seg) / 2
            return timezone.timedelta(seconds=promedio_seg)
        return timezone.timedelta(seconds=0)

    def actualizar_estadisticas(self, tiempo_real):
        """Actualiza estadísticas después de completar el proceso"""
        if self.veces_ejecutado == 0:
            self.tiempo_promedio = tiempo_real
        else:
            # Promedio ponderado
            total_segundos = (
                self.tiempo_promedio.total_seconds() * self.veces_ejecutado +
                tiempo_real.total_seconds()
            ) / (self.veces_ejecutado + 1)
            self.tiempo_promedio = timezone.timedelta(seconds=total_segundos)
        
        # Calcular eficiencia
        tiempo_estimado_prom = self.tiempo_estimado_promedio().total_seconds()
        if tiempo_estimado_prom > 0:
            self.eficiencia = (tiempo_estimado_prom / tiempo_real.total_seconds()) * 100
        
        self.veces_ejecutado += 1
        self.save()

# ============ ETAPAS DE PROCESO ============ #
class EtapaProceso(models.Model):
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE, related_name='etapas')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0)
    
    # Tiempos
    tiempo_estimado = models.DurationField(default=timezone.timedelta(minutes=30))  # Valor por defecto
    tiempo_real = models.DurationField(null=True, blank=True)
    
    # Estado
    completada = models.BooleanField(default=False)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    
    # Responsable
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='etapas_asignadas')

    class Meta:
        ordering = ['orden']
        verbose_name = 'Etapa de Proceso'
        verbose_name_plural = 'Etapas de Proceso'
        unique_together = ['proceso', 'orden']

    def __str__(self):
        return f"{self.proceso.nombre} - {self.nombre}"

    def iniciar_etapa(self):
        self.fecha_inicio = timezone.now()
        self.completada = False
        self.save()

    def finalizar_etapa(self):
        if self.fecha_inicio and not self.completada:
            self.fecha_fin = timezone.now()
            self.tiempo_real = self.fecha_fin - self.fecha_inicio
            self.completada = True
            self.save()

# ============ MATERIALES POR PROCESO ============ #
class MaterialProceso(models.Model):
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE)
    material = models.ForeignKey('materiales.Material', on_delete=models.CASCADE)
    cantidad_necesaria = models.DecimalField(max_digits=10, decimal_places=3)
    unidad = models.CharField(max_length=20, default='unidad')
    desperdicio_estimado = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% de desperdicio")

    class Meta:
        verbose_name = 'Material por Proceso'
        verbose_name_plural = 'Materiales por Proceso'
        unique_together = ['proceso', 'material']

    def __str__(self):
        return f"{self.proceso.nombre} - {self.material.nombre}"

    def cantidad_total_con_desperdicio(self):
        desperdicio = (self.desperdicio_estimado / 100) + 1
        return self.cantidad_necesaria * Decimal(str(desperdicio))

# ============ FLUJO DE TRABAJO ============ #
class FlujoTrabajo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    # Procesos en secuencia (usando orden en ProcesoFlujo)
    procesos = models.ManyToManyField(Proceso, through='ProcesoFlujo')
    
    # Configuración
    activo = models.BooleanField(default=True)
    tiempo_total_estimado = models.DurationField(null=True, blank=True)
    
    # Estadísticas
    veces_utilizado = models.PositiveIntegerField(default=0)
    eficiencia_promedio = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # AGREGAR VALOR POR DEFECTO
    fecha_creacion = models.DateTimeField(default=timezone.now)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'Flujo de Trabajo'
        verbose_name_plural = 'Flujos de Trabajo'

    def __str__(self):
        return self.nombre

    def calcular_tiempo_total(self):
        """Calcula tiempo total estimado sumando tiempos de procesos"""
        total_segundos = 0
        for proceso_flujo in self.procesoflujo_set.all().order_by('orden'):
            if proceso_flujo.proceso.tiempo_estimado_promedio():
                total_segundos += proceso_flujo.proceso.tiempo_estimado_promedio().total_seconds()
        
        self.tiempo_total_estimado = timezone.timedelta(seconds=total_segundos)
        self.save()
        return self.tiempo_total_estimado

class ProcesoFlujo(models.Model):
    flujo_trabajo = models.ForeignKey(FlujoTrabajo, on_delete=models.CASCADE)
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(default=0)
    
    # Dependencias
    requiere_completar_anterior = models.BooleanField(default=True)
    puede_paralelizar = models.BooleanField(default=False)
    
    # Configuración
    es_opcional = models.BooleanField(default=False)
    tiempo_maximo_espera = models.DurationField(null=True, blank=True, help_text="Tiempo máximo de espera antes del siguiente proceso")

    class Meta:
        ordering = ['orden']
        unique_together = ['flujo_trabajo', 'orden']
        verbose_name = 'Proceso en Flujo'
        verbose_name_plural = 'Procesos en Flujo'

    def __str__(self):
        return f"{self.flujo_trabajo.nombre} - {self.proceso.nombre} (Orden: {self.orden})"

# ============ TEMPORIZADOR/CONTADOR ============ #
class Temporizador(models.Model):
    ESTADO_CHOICES = [
        ('inactivo', '⏸️ Inactivo'),
        ('activo', '▶️ Activo'),
        ('pausado', '⏸️ Pausado'),
        ('completado', '✅ Completado'),
    ]

    # Relaciones
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE, null=True, blank=True)
    etapa = models.ForeignKey(EtapaProceso, on_delete=models.CASCADE, null=True, blank=True)
    orden_produccion = models.ForeignKey('produccion.OrdenProduccion', on_delete=models.CASCADE, null=True, blank=True)
    
    # Tiempos
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    tiempo_objetivo = models.DurationField(help_text="Tiempo objetivo para completar")
    tiempo_transcurrido = models.DurationField(default=timezone.timedelta(seconds=0))
    
    # Estado y control
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='inactivo')
    activo = models.BooleanField(default=True)
    
    # Operario
    operario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='temporizadores')
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='temporizadores_creados')
    fecha_creacion = models.DateTimeField(default=timezone.now)  # Cambiar auto_now_add=True por default=timezone.now
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Temporizador'
        verbose_name_plural = 'Temporizadores'

    def __str__(self):
        nombre = self.proceso.nombre if self.proceso else self.etapa.nombre if self.etapa else "Sin proceso"
        return f"Temporizador - {nombre} - {self.get_estado_display()}"

    def iniciar(self):
        if self.estado == 'inactivo':
            self.fecha_inicio = timezone.now()
            self.estado = 'activo'
            self.save()
            
            # Registrar operación
            Operacion.objects.create(
                usuario=self.creado_por,
                accion='proceso_iniciado',
                descripcion=f"Temporizador iniciado para {self}",
                referencia=f"TEMP-{self.id}"
            )

    def pausar(self):
        if self.estado == 'activo':
            self.estado = 'pausado'
            # Actualizar tiempo transcurrido
            if self.fecha_inicio:
                ahora = timezone.now()
                tiempo_trans = ahora - self.fecha_inicio
                self.tiempo_transcurrido += tiempo_trans
                self.fecha_inicio = None
            self.save()

    def reanudar(self):
        if self.estado == 'pausado':
            self.estado = 'activo'
            self.fecha_inicio = timezone.now()
            self.save()

    def detener(self):
        if self.estado in ['activo', 'pausado']:
            self.estado = 'completado'
            self.fecha_fin = timezone.now()
            
            # Calcular tiempo total
            if self.fecha_inicio:
                tiempo_total = self.fecha_fin - self.fecha_inicio
                self.tiempo_transcurrido += tiempo_total
            
            self.save()
            
            # Registrar operación
            Operacion.objects.create(
                usuario=self.operario or self.creado_por,
                accion='proceso_finalizado',
                descripcion=f"Temporizador finalizado para {self}. Tiempo: {self.tiempo_transcurrido}",
                referencia=f"TEMP-{self.id}",
                tiempo_empleado=self.tiempo_transcurrido
            )
            
            # Actualizar estadísticas del proceso si existe
            if self.proceso:
                self.proceso.actualizar_estadisticas(self.tiempo_transcurrido)

    def tiempo_restante(self):
        if self.tiempo_objetivo and self.tiempo_transcurrido:
            restante = self.tiempo_objetivo - self.tiempo_transcurrido
            return max(timezone.timedelta(seconds=0), restante)
        return self.tiempo_objetivo or timezone.timedelta(seconds=0)

    def porcentaje_completado(self):
        if self.tiempo_objetivo and self.tiempo_transcurrido:
            if self.tiempo_objetivo.total_seconds() > 0:
                porcentaje = (self.tiempo_transcurrido.total_seconds() / self.tiempo_objetivo.total_seconds()) * 100
                return min(100, max(0, porcentaje))
        return 0

# ============ CONTROL DE CALIDAD AVANZADO ============ #
class ControlCalidad(models.Model):
    RESULTADO_CHOICES = [
        ('aprobado', '✅ Aprobado'),
        ('rechazado', '❌ Rechazado'),
        ('reparacion', '🔧 Requiere reparación'),
        ('revision', '🔍 En revisión'),
    ]

    # Relaciones
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE, null=True, blank=True)
    etapa = models.ForeignKey(EtapaProceso, on_delete=models.CASCADE, null=True, blank=True)
    orden_produccion = models.ForeignKey('produccion.OrdenProduccion', on_delete=models.SET_NULL, null=True, blank=True)
    lote = models.ForeignKey('lotes.Lote', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Información básica
    fecha = models.DateTimeField(auto_now_add=True)
    inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='controles_calidad')
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, default='revision')
    
    # Detalles
    observaciones = models.TextField(blank=True)
    recomendaciones = models.TextField(blank=True)
    
    # Métricas (para análisis estadístico)
    puntuacion_total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cantidad_defectos = models.PositiveIntegerField(default=0)
    costo_reparacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Auditoría
    revisado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='controles_revisados')
    fecha_revision = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Control de Calidad'
        verbose_name_plural = 'Controles de Calidad'

    def __str__(self):
        return f"Control {self.proceso.nombre if self.proceso else 'General'} - {self.fecha:%d/%m/%Y}"

    def marcar_como_revisado(self, usuario):
        self.revisado_por = usuario
        self.fecha_revision = timezone.now()
        self.save()

class ControlCalidadDetalle(models.Model):
    TIPO_DEFECTO_CHOICES = [
        ('costura', 'Problema de costura'),
        ('tela', 'Defecto en tela'),
        ('color', 'Problema de color'),
        ('talla', 'Error de talla'),
        ('terminacion', 'Terminación deficiente'),
        ('otro', 'Otro'),
    ]

    control_calidad = models.ForeignKey(ControlCalidad, on_delete=models.CASCADE, related_name='detalles')
    tipo_defecto = models.CharField(max_length=20, choices=TIPO_DEFECTO_CHOICES)
    descripcion = models.TextField()
    severidad = models.IntegerField(choices=[(1, 'Leve'), (2, 'Moderado'), (3, 'Grave')], default=1)
    
    # Ubicación del defecto (para prendas)
    ubicacion_defecto = models.CharField(max_length=100, blank=True, help_text="Ej: manga izquierda, espalda, etc.")
    
    # Acciones tomadas
    accion_tomada = models.TextField(blank=True)
    requiere_reparacion = models.BooleanField(default=False)
    tiempo_reparacion = models.DurationField(null=True, blank=True)
    
    # Evidencia
    foto = models.ImageField(upload_to='control_calidad/', null=True, blank=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Detalle de Control de Calidad'
        verbose_name_plural = 'Detalles de Control de Calidad'

    def __str__(self):
        return f"{self.get_tipo_defecto_display()} - {self.descripcion[:50]}..."

# ============ NO CONFORMIDADES ============ #
class NoConformidad(models.Model):
    ESTADO_CHOICES = [
        ('reportada', '📋 Reportada'),
        ('analisis', '🔍 En análisis'),
        ('correccion', '🔧 En corrección'),
        ('verificada', '✅ Verificada'),
        ('cerrada', '📦 Cerrada'),
    ]

    PRIORIDAD_CHOICES = [
        (1, '🟢 Baja'),
        (2, '🟡 Media'),
        (3, '🔴 Alta'),
        (4, '⚫ Crítica'),
    ]

    # Relaciones
    proceso = models.ForeignKey(Proceso, on_delete=models.SET_NULL, null=True, blank=True)
    control_calidad = models.ForeignKey(ControlCalidad, on_delete=models.SET_NULL, null=True, blank=True)
    orden_produccion = models.ForeignKey('produccion.OrdenProduccion', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Información básica
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField()
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    reportado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='no_conformidades_reportadas')
    
    # Estado y prioridad
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='reportada')
    prioridad = models.IntegerField(choices=PRIORIDAD_CHOICES, default=2)
    
    # Análisis
    causa_raiz = models.TextField(blank=True)
    accion_correctiva = models.TextField(blank=True)
    accion_preventiva = models.TextField(blank=True)
    
    # Fechas
    fecha_limite = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    
    # Responsables
    responsable_correccion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='no_conformidades_responsable')
    verificada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='no_conformidades_verificadas')
    
    # Impacto
    cantidad_afectada = models.PositiveIntegerField(default=1)
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    impacto_produccion = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-fecha_reporte']
        verbose_name = 'No Conformidad'
        verbose_name_plural = 'No Conformidades'

    def __str__(self):
        return f"NC-{self.codigo} - {self.get_estado_display()}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Generar código automático
            ultima_nc = NoConformidad.objects.order_by('-id').first()
            numero = 1 if not ultima_nc else ultima_nc.id + 1
            self.codigo = f"NC-{timezone.now().year}-{numero:04d}"
        
        super().save(*args, **kwargs)

    def cerrar(self, usuario, comentarios=""):
        self.estado = 'cerrada'
        self.fecha_cierre = timezone.now()
        self.verificada_por = usuario
        self.save()
        
        # Registrar operación
        Operacion.objects.create(
            usuario=usuario,
            accion='no_conformidad',
            descripcion=f"No conformidad {self.codigo} cerrada. {comentarios}",
            referencia=self.codigo
        )

    def dias_abierta(self):
        if self.fecha_cierre:
            return (self.fecha_cierre.date() - self.fecha_reporte.date()).days
        return (timezone.now().date() - self.fecha_reporte.date()).days