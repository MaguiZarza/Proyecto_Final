from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import json
from django.core.exceptions import ValidationError

## models de Materiales

# ============ MODELOS BASE (deben estar primero) ============ #
class Material(models.Model):
    TIPO_CHOICES = [
        ('tela', 'Tela'),
        ('hilo', 'Hilo'),
        ('avios', 'Avíos'),
        ('otro', 'Otro'),
    ]
    
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    unidad = models.CharField(max_length=20, default='unidad')
    # Nuevos campos para colores
    color = models.CharField(max_length=50, blank=True, null=True)
    codigo_color = models.CharField(max_length=20, blank=True, null=True, help_text="Código interno del color")
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        if self.color:
            return f"{self.nombre} - {self.color}"
        return self.nombre
    
    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'
        unique_together = ['nombre', 'tipo', 'color']  # Evita duplicados

class Tela(models.Model):
    nombre = models.CharField(max_length=100)
    color = models.CharField(max_length=50, blank=True, null=True)
    codigo_color = models.CharField(max_length=20, blank=True, null=True)
    tipo_tela = models.CharField(max_length=50, blank=True, null=True, help_text="Ej: Algodón, Poliéster, etc.")
    ancho = models.DecimalField(max_digits=5, decimal_places=2, default=1.5, help_text="Ancho en metros")
    
    def __str__(self):
        if self.color:
            return f"{self.nombre} - {self.color}"
        return self.nombre
    
    class Meta:
        verbose_name = 'Tela'
        verbose_name_plural = 'Telas'
        unique_together = ['nombre', 'color']

class Hilo(models.Model):
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50)
    color = models.CharField(max_length=50, blank=True, null=True)
    codigo_color = models.CharField(max_length=20, blank=True, null=True)
    metros_por_cono = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        if self.color:
            return f"{self.nombre} - {self.color}"
        return self.nombre
    
    class Meta:
        verbose_name = 'Hilo'
        verbose_name_plural = 'Hilos'
        unique_together = ['nombre', 'color']

class Formula(models.Model):
    # Usamos string para evitar dependencia circular
    producto = models.ForeignKey('produccion.Producto', on_delete=models.CASCADE, related_name='formulas')
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Fórmula de {self.producto.nombre}"
    
    class Meta:
        verbose_name = 'Fórmula'
        verbose_name_plural = 'Fórmulas'

class FormulaDetalle(models.Model):
    formula = models.ForeignKey(Formula, on_delete=models.CASCADE, related_name='detalles')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    cantidad_por_unidad = models.DecimalField(max_digits=10, decimal_places=3)
    
    def __str__(self):
        return f"{self.material.nombre} - {self.cantidad_por_unidad}"
    
    class Meta:
        verbose_name = 'Detalle de Fórmula'
        verbose_name_plural = 'Detalles de Fórmula'

# ============ CONFIGURACIONES DE MÁQUINA ============ #
class ConfiguracionMaquina(models.Model):
    nombre = models.CharField(max_length=100)
    tipo_maquina = models.CharField(max_length=50)
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = 'Configuración de Máquina'
        verbose_name_plural = 'Configuraciones de Máquina'

class ConfiguracionHilo(models.Model):
    configuracion = models.ForeignKey(ConfiguracionMaquina, on_delete=models.CASCADE, related_name='hilos')
    hilo = models.ForeignKey(Hilo, on_delete=models.CASCADE, null=True, blank=True)
    tension = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"{self.configuracion.nombre} - {self.hilo.nombre if self.hilo else 'Sin hilo'}"
    
    class Meta:
        verbose_name = 'Configuración de Hilo'
        verbose_name_plural = 'Configuraciones de Hilo'

class ConsumoTela(models.Model):
    tela = models.ForeignKey(Tela, on_delete=models.CASCADE)
    configuracion = models.ForeignKey(ConfiguracionMaquina, on_delete=models.CASCADE)
    metros_hilo_por_metro_tela = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.tela.nombre} - {self.configuracion.nombre}"
    
    def calcular_consumo(self, metros_tela):
        return self.metros_hilo_por_metro_tela * metros_tela
    
    class Meta:
        verbose_name = 'Consumo de Tela'
        verbose_name_plural = 'Consumos de Tela'

# ============ INVENTARIO ============ #
class Inventario(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='inventarios')
    cantidad_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    cantidad_minima = models.DecimalField(max_digits=12, decimal_places=3, default=10)
    cantidad_maxima = models.DecimalField(max_digits=12, decimal_places=3, default=1000)
    
    ubicacion = models.CharField(max_length=100, blank=True, help_text="Estante, armario, etc.")
    codigo_ubicacion = models.CharField(max_length=50, blank=True)
    
    costo_promedio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_ultima_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    activo = models.BooleanField(default=True)
    bloqueado = models.BooleanField(default=False, help_text="Si está bloqueado, no se puede modificar")
    
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Inventario'
        verbose_name_plural = 'Inventarios'
        unique_together = ['material', 'ubicacion']

    def __str__(self):
        return f"{self.material.nombre} - {self.cantidad_actual} {self.material.unidad}"

    def clean(self):
        if self.cantidad_minima > self.cantidad_maxima:
            raise ValidationError('La cantidad mínima no puede ser mayor que la máxima.')

    def stock_suficiente(self, cantidad_necesaria):
        return self.cantidad_actual >= Decimal(str(cantidad_necesaria))

    def porcentaje_stock(self):
        if self.cantidad_maxima > 0:
            porcentaje = (self.cantidad_actual / self.cantidad_maxima) * 100
            return float(porcentaje)
        return 0

    def necesita_reabastecimiento(self):
        return self.cantidad_actual <= self.cantidad_minima

    def valor_total(self):
        return self.cantidad_actual * self.costo_promedio

# ============ MOVIMIENTOS DE INVENTARIO ============ #
class MovimientoInventario(models.Model):
    TIPO_CHOICES = [
        ('entrada', '➕ Entrada'),
        ('salida', '➖ Salida'),
        ('ajuste', '📝 Ajuste'),
        ('inicial', '📦 Stock Inicial'),
        ('transferencia', '🔄 Transferencia'),
        ('devolucion', '↪️ Devolución'),
    ]

    ORIGEN_CHOICES = [
        ('compra', '🛒 Compra'),
        ('produccion', '🏭 Producción'),
        ('ajuste_inventario', '📊 Ajuste de Inventario'),
        ('venta', '💰 Venta'),
        ('danado', '⚠️ Dañado'),
        ('caducado', '📅 Caducado'),
        ('otros', '❓ Otros'),
    ]

    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default='compra')
    
    cantidad_anterior = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    cantidad_movimiento = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    
    referencia = models.CharField(max_length=100, blank=True, help_text="Nº Factura, Orden, etc.")
    # Usamos string para evitar dependencia circular
    orden_produccion = models.ForeignKey('produccion.OrdenProduccion', on_delete=models.SET_NULL, null=True, blank=True)
    # Comentamos temporalmente la referencia a lotes para evitar dependencia
    lote = models.CharField(max_length=50, blank=True, null=True)
    
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    motivo = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    realizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_documento = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_movimiento']
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.inventario.material.nombre} - {self.cantidad_movimiento}"

    def clean(self):
        if self.tipo in ['salida', 'ajuste', 'transferencia']:
            if self.cantidad_movimiento > self.cantidad_anterior:
                raise ValidationError(f'No hay suficiente stock. Disponible: {self.cantidad_anterior}')

    def save(self, *args, **kwargs):
        is_new = not self.pk
        
        if is_new:
            self.cantidad_anterior = self.inventario.cantidad_actual
            
            if self.tipo in ['entrada', 'inicial', 'devolucion']:
                self.cantidad_actual = self.cantidad_anterior + self.cantidad_movimiento
            elif self.tipo in ['salida', 'ajuste', 'transferencia']:
                self.cantidad_actual = self.cantidad_anterior - self.cantidad_movimiento
        
        self.costo_total = self.cantidad_movimiento * self.costo_unitario
        
        super().save(*args, **kwargs)
        
        if is_new:
            self.inventario.cantidad_actual = self.cantidad_actual
            
            if self.tipo in ['entrada', 'inicial', 'devolucion'] and self.costo_unitario > 0:
                valor_actual = self.inventario.cantidad_actual * self.inventario.costo_promedio
                valor_nuevo = self.cantidad_movimiento * self.costo_unitario
                cantidad_total = self.inventario.cantidad_actual
                
                if cantidad_total > 0:
                    self.inventario.costo_promedio = (valor_actual + valor_nuevo) / cantidad_total
                self.inventario.costo_ultima_compra = self.costo_unitario
            
            self.inventario.save()

# ============ HISTÓRICO DE COSTOS ============ #
class HistoricoCosto(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='historicos_costo')
    fecha = models.DateField()
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    origen = models.CharField(max_length=100, blank=True)
    referencia = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Histórico de Costo'
        verbose_name_plural = 'Históricos de Costos'

    def __str__(self):
        return f"{self.material.nombre} - {self.fecha} - ${self.costo_unitario}"

    def costo_total(self):
        return self.cantidad * self.costo_unitario

# ============ ALERTAS DE STOCK ============ #
class AlertaStock(models.Model):
    NIVEL_CHOICES = [
        ('bajo', '🔴 Crítico'),
        ('medio', '🟡 Bajo'),
        ('alto', '🟢 Normal'),
    ]

    TIPO_CHOICES = [
        ('stock_minimo', '📉 Stock por debajo del mínimo'),
        ('stock_maximo', '📈 Stock por encima del máximo'),
        ('sin_movimientos', '🔄 Sin movimientos recientes'),
        ('costo_alto', '💰 Costo elevado'),
    ]

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='alertas')
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, null=True, blank=True)
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nivel = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='bajo')
    activa = models.BooleanField(default=True)
    
    descripcion = models.TextField()
    cantidad_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    cantidad_umbral = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    
    fecha_deteccion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    
    resuelta = models.BooleanField(default=False)
    accion_tomada = models.TextField(blank=True)
    resuelta_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-fecha_deteccion']
        verbose_name = 'Alerta de Stock'
        verbose_name_plural = 'Alertas de Stock'

    def __str__(self):
        return f"{self.get_nivel_display()} - {self.material.nombre} - {self.get_tipo_display()}"

    def marcar_resuelta(self, usuario, accion=""):
        self.resuelta = True
        self.resuelta_por = usuario
        self.accion_tomada = accion
        self.fecha_resolucion = timezone.now()
        self.save()

# ============ CONSUMO POR PRODUCTO ============ #
class ConsumoProducto(models.Model):
    # Usamos string para evitar dependencia circular
    producto = models.ForeignKey('produccion.Producto', on_delete=models.CASCADE, related_name='consumos')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    cantidad_por_unidad = models.DecimalField(max_digits=10, decimal_places=3)
    desperdicio_estimado = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Porcentaje de desperdicio")
    costo_material_por_unidad = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['producto', 'material']
        verbose_name = 'Consumo por Producto'
        verbose_name_plural = 'Consumos por Producto'

    def __str__(self):
        return f"{self.producto.nombre} - {self.material.nombre}"

    def calcular_costo(self, cantidad_producida=1):
        cantidad_total = self.cantidad_por_unidad * Decimal(str(cantidad_producida))
        cantidad_con_desperdicio = cantidad_total * (1 + (self.desperdicio_estimado / 100))
        
        try:
            inventario = Inventario.objects.get(material=self.material, activo=True)
            costo_unitario = inventario.costo_promedio
        except Inventario.DoesNotExist:
            costo_unitario = Decimal('0')
        
        return cantidad_con_desperdicio * costo_unitario

# ============ PEDIDO DE COMPRA ============ #
class PedidoCompra(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', '⏳ Pendiente'),
        ('aprobado', '✅ Aprobado'),
        ('ordenado', '📦 Ordenado'),
        ('recibido', '📥 Recibido'),
        ('cancelado', '❌ Cancelado'),
    ]

    codigo = models.CharField(max_length=50, unique=True)
    proveedor = models.CharField(max_length=200)
    contacto_proveedor = models.CharField(max_length=100, blank=True)
    telefono_proveedor = models.CharField(max_length=20, blank=True)
    
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_esperada = models.DateField()
    fecha_recepcion = models.DateField(null=True, blank=True)
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    prioridad = models.IntegerField(default=1)
    
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_real = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    numero_orden_compra = models.CharField(max_length=50, blank=True)
    observaciones = models.TextField(blank=True)
    
    solicitado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pedidos_compra_solicitados')
    aprobado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_compra_aprobados')
    recibido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_compra_recibidos')

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Pedido de Compra'
        verbose_name_plural = 'Pedidos de Compra'

    def __str__(self):
        return f"PC-{self.codigo} - {self.proveedor}"

    def calcular_costo_estimado(self):
        total = Decimal('0')
        for detalle in self.detalles.all():
            total += detalle.cantidad_solicitada * detalle.costo_unitario_estimado
        return total

    def recibir_pedido(self, usuario):
        self.estado = 'recibido'
        self.recibido_por = usuario
        self.fecha_recepcion = timezone.now().date()
        self.save()
        
        for detalle in self.detalles.all():
            if detalle.cantidad_recibida > 0:
                try:
                    inventario = Inventario.objects.get(material=detalle.material, activo=True)
                    MovimientoInventario.objects.create(
                        inventario=inventario,
                        tipo='entrada',
                        origen='compra',
                        cantidad_anterior=inventario.cantidad_actual,
                        cantidad_movimiento=detalle.cantidad_recibida,
                        costo_unitario=detalle.costo_unitario_real,
                        referencia=self.numero_orden_compra,
                        motivo=f"Recepción de pedido PC-{self.codigo}",
                        realizado_por=usuario,
                        fecha_documento=self.fecha_recepcion
                    )
                except Inventario.DoesNotExist:
                    pass

class DetallePedidoCompra(models.Model):
    pedido_compra = models.ForeignKey(PedidoCompra, on_delete=models.CASCADE, related_name='detalles')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    cantidad_solicitada = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad_recibida = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    costo_unitario_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_unitario_real = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Detalle de Pedido de Compra'
        verbose_name_plural = 'Detalles de Pedidos de Compra'

    def __str__(self):
        return f"{self.material.nombre} - {self.cantidad_solicitada}"

    def costo_total_estimado(self):
        return self.cantidad_solicitada * self.costo_unitario_estimado

    def costo_total_real(self):
        return self.cantidad_recibida * self.costo_unitario_real

# ============ REPORTE DE INVENTARIO ============ #
class ReporteInventario(models.Model):
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
    
    total_materiales = models.PositiveIntegerField(default=0)
    materiales_bajos = models.PositiveIntegerField(default=0)
    valor_total_inventario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    movimientos_totales = models.PositiveIntegerField(default=0)
    
    archivo = models.FileField(upload_to='reportes_inventario/', blank=True, null=True)
    generado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    
    resumen = models.TextField(blank=True)
    hallazgos = models.TextField(blank=True)
    recomendaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-periodo_fin']
        verbose_name = 'Reporte de Inventario'
        verbose_name_plural = 'Reportes de Inventario'

    def __str__(self):
        return f"{self.titulo} ({self.periodo_inicio} al {self.periodo_fin})"