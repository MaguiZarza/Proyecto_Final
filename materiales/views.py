from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Sum, Avg, Count, F
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
import csv
from decimal import Decimal

from .models import (
    Formula, ConsumoTela, Material, Inventario,  # Removido: Producto
    MovimientoInventario, HistoricoCosto, AlertaStock, ConsumoProducto,
    PedidoCompra, DetallePedidoCompra, ReporteInventario
)
from produccion.models import Producto  # Añadido: importar desde produccion
from .forms import (
    CalculadoraHiloForm, CalculadoraMaterialesForm, InventarioForm,
    MovimientoInventarioForm, AlertaStockForm, PedidoCompraForm,
    FiltroInventarioForm, AjusteInventarioForm, GenerarReporteForm
)
from procesos.models import Operacion

# ============ CALCULADORAS ============ #
@login_required
def calculadora_hilo(request):
    resultado = None
    consumo_seleccionado = None
    metros = None

    if request.method == 'POST':
        form = CalculadoraHiloForm(request.POST)
        if form.is_valid():
            consumo_seleccionado = form.cleaned_data['consumo']
            metros = form.cleaned_data['metros_tela']
            resultado = consumo_seleccionado.calcular_consumo(metros)
    else:
        form = CalculadoraHiloForm()

    return render(request, 'materiales/calculadora_hilo.html', {
        'form': form,
        'resultado': resultado,
        'consumo': consumo_seleccionado,
        'metros': metros,
    })

@login_required
def calculadora_materiales(request):
    form = CalculadoraMaterialesForm()
    resultados = None
    producto = None
    cantidad = None

    if request.method == 'POST':
        form = CalculadoraMaterialesForm(request.POST)
        if form.is_valid():
            producto = form.cleaned_data['producto']
            cantidad = form.cleaned_data['cantidad']

            try:
                formula = Formula.objects.get(producto=producto, activa=True)
                resultados = []
                for detalle in formula.detalles.all():
                    total = detalle.cantidad_por_unidad * cantidad
                    resultados.append({
                        'material': detalle.material.nombre,
                        'unidad': detalle.material.unidad,
                        'cantidad': total
                    })
            except Formula.DoesNotExist:
                resultados = []

            Operacion.objects.create(
                usuario=request.user,
                accion='calculo_materiales',
                descripcion=f'Cálculo de materiales - Producto: {producto.nombre} - Cantidad: {cantidad}'
            )

    return render(request, 'materiales/calculadora_materiales.html', {
        'form': form,
        'resultados': resultados,
        'producto': producto,
        'cantidad': cantidad
    })

# ============ INVENTARIO ============ #
@login_required
def inventario_lista(request):
    form = FiltroInventarioForm(request.GET or None)
    inventarios = Inventario.objects.filter(activo=True).select_related('material')
    
    if form.is_valid():
        tipo = form.cleaned_data.get('tipo')
        estado = form.cleaned_data.get('estado')
        necesita_reab = form.cleaned_data.get('necesita_reabastecimiento')
        ubicacion = form.cleaned_data.get('ubicacion')
        
        if tipo:
            inventarios = inventarios.filter(material__tipo=tipo)
        if estado == 'bajo':
            inventarios = inventarios.filter(cantidad_actual__lte=F('cantidad_minima'))
        elif estado == 'alto':
            inventarios = inventarios.filter(cantidad_actual__gte=F('cantidad_maxima') * 0.8)
        if necesita_reab:
            inventarios = inventarios.filter(cantidad_actual__lte=F('cantidad_minima'))
        if ubicacion:
            inventarios = inventarios.filter(ubicacion__icontains=ubicacion)
    
    # Estadísticas
    total_materiales = inventarios.count()
    materiales_bajos = inventarios.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    
    valor_total = 0
    for inv in inventarios:
        valor_total += float(inv.valor_total())
    
    context = {
        'inventarios': inventarios,
        'form': form,
        'total_materiales': total_materiales,
        'materiales_bajos': materiales_bajos,
        'valor_total': valor_total,
    }
    return render(request, 'materiales/inventario_lista.html', context)

@login_required
@permission_required('materiales.add_inventario', raise_exception=True)
def inventario_crear(request):
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            inventario = form.save(commit=False)
            inventario.actualizado_por = request.user
            inventario.save()
            
            # Crear movimiento inicial
            MovimientoInventario.objects.create(
                inventario=inventario,
                tipo='inicial',
                origen='ajuste_inventario',
                cantidad_anterior=0,
                cantidad_movimiento=inventario.cantidad_actual,
                cantidad_actual=inventario.cantidad_actual,
                costo_unitario=inventario.costo_promedio,
                motivo='Stock inicial creado',
                realizado_por=request.user
            )
            
            messages.success(request, f'Inventario para {inventario.material.nombre} creado exitosamente.')
            return redirect('inventario_lista')
    else:
        form = InventarioForm()
    
    return render(request, 'materiales/inventario_form.html', {'form': form})

@login_required
def inventario_detalle(request, pk):
    inventario = get_object_or_404(Inventario.objects.select_related('material'), pk=pk)
    movimientos = MovimientoInventario.objects.filter(inventario=inventario).order_by('-fecha_movimiento')[:50]
    
    # Alertas activas para este material
    alertas = AlertaStock.objects.filter(
        material=inventario.material,
        resuelta=False
    ).order_by('-fecha_deteccion')
    
    # Pedidos de compra pendientes
    pedidos_compra = PedidoCompra.objects.filter(
        detalles__material=inventario.material,
        estado__in=['pendiente', 'aprobado', 'ordenado']
    ).distinct()
    
    context = {
        'inventario': inventario,
        'movimientos': movimientos,
        'alertas': alertas,
        'pedidos_compra': pedidos_compra,
    }
    return render(request, 'materiales/inventario_detalle.html', context)

# ============ MOVIMIENTOS DE INVENTARIO ============ #
@login_required
@permission_required('materiales.add_movimientoinventario', raise_exception=True)
def movimiento_crear(request):
    if request.method == 'POST':
        form = MovimientoInventarioForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.realizado_por = request.user
            movimiento.cantidad_anterior = movimiento.inventario.cantidad_actual
            movimiento.save()
            
            # Registrar histórico de costo si es entrada
            if movimiento.tipo in ['entrada', 'inicial'] and movimiento.costo_unitario > 0:
                HistoricoCosto.objects.create(
                    material=movimiento.inventario.material,
                    fecha=movimiento.fecha_documento or timezone.now().date(),
                    costo_unitario=movimiento.costo_unitario,
                    cantidad=movimiento.cantidad_movimiento,
                    origen=movimiento.get_origen_display(),
                    referencia=movimiento.referencia
                )
            
            messages.success(request, f'Movimiento registrado exitosamente.')
            return redirect('inventario_detalle', pk=movimiento.inventario.pk)
    else:
        form = MovimientoInventarioForm()
    
    return render(request, 'materiales/movimiento_form.html', {'form': form})

@login_required
@permission_required('materiales.add_movimientoinventario', raise_exception=True)
def ajuste_inventario(request):
    if request.method == 'POST':
        form = AjusteInventarioForm(request.POST)
        if form.is_valid():
            inventario = form.cleaned_data['inventario']
            tipo = form.cleaned_data['tipo']
            cantidad = form.cleaned_data['cantidad']
            costo_unitario = form.cleaned_data['costo_unitario'] or 0
            motivo = form.cleaned_data['motivo']
            
            # Crear movimiento
            movimiento = MovimientoInventario.objects.create(
                inventario=inventario,
                tipo=tipo,
                origen='ajuste_inventario',
                cantidad_anterior=inventario.cantidad_actual,
                cantidad_movimiento=cantidad,
                costo_unitario=costo_unitario,
                motivo=motivo,
                realizado_por=request.user
            )
            
            messages.success(request, f'Ajuste de inventario registrado exitosamente.')
            return redirect('inventario_detalle', pk=inventario.pk)
    else:
        form = AjusteInventarioForm()
    
    return render(request, 'materiales/ajuste_inventario.html', {'form': form})

# ============ ALERTAS DE STOCK ============ #
@login_required
def alertas_stock(request):
    # Generar alertas automáticas
    generar_alertas_automaticas(request.user)
    
    alertas = AlertaStock.objects.filter(resuelta=False).select_related('material').order_by('-fecha_deteccion')
    
    context = {
        'alertas': alertas,
    }
    return render(request, 'materiales/alertas_stock.html', context)

def generar_alertas_automaticas(usuario):
    """Genera alertas automáticas para stock bajo"""
    inventarios = Inventario.objects.filter(activo=True, bloqueado=False)
    
    for inventario in inventarios:
        # Verificar stock bajo
        if inventario.necesita_reabastecimiento():
            # Verificar si ya existe alerta activa
            existe_alerta = AlertaStock.objects.filter(
                material=inventario.material,
                tipo='stock_minimo',
                resuelta=False
            ).exists()
            
            if not existe_alerta:
                AlertaStock.objects.create(
                    material=inventario.material,
                    inventario=inventario,
                    tipo='stock_minimo',
                    nivel='bajo',
                    descripcion=f'Stock de {inventario.material.nombre} está por debajo del mínimo ({inventario.cantidad_actual} < {inventario.cantidad_minima})',
                    cantidad_actual=inventario.cantidad_actual,
                    cantidad_umbral=inventario.cantidad_minima,
                    activa=True
                )
        
        # Verificar stock alto (más del 90% del máximo)
        if inventario.cantidad_maxima > 0 and inventario.cantidad_actual >= inventario.cantidad_maxima * Decimal('0.9'):
            existe_alerta = AlertaStock.objects.filter(
                material=inventario.material,
                tipo='stock_maximo',
                resuelta=False
            ).exists()
            
            if not existe_alerta:
                AlertaStock.objects.create(
                    material=inventario.material,
                    inventario=inventario,
                    tipo='stock_maximo',
                    nivel='alto',
                    descripcion=f'Stock de {inventario.material.nombre} está por encima del 90% del máximo ({inventario.cantidad_actual} > {inventario.cantidad_maxima * Decimal("0.9")})',
                    cantidad_actual=inventario.cantidad_actual,
                    cantidad_umbral=inventario.cantidad_maxima * Decimal('0.9'),
                    activa=True
                )

@login_required
def alerta_resolver(request, pk):
    alerta = get_object_or_404(AlertaStock, pk=pk)
    
    if request.method == 'POST':
        accion = request.POST.get('accion_tomada', '')
        alerta.marcar_resuelta(request.user, accion)
        
        messages.success(request, f'Alerta marcada como resuelta.')
        return redirect('alertas_stock')
    
    return render(request, 'materiales/alerta_resolver.html', {'alerta': alerta})

# ============ PEDIDOS DE COMPRA ============ #
@login_required
@permission_required('materiales.add_pedidocompra', raise_exception=True)
def pedido_compra_lista(request):
    pedidos = PedidoCompra.objects.all().order_by('-fecha_solicitud')
    
    # Filtros
    estado = request.GET.get('estado')
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    context = {
        'pedidos': pedidos,
    }
    return render(request, 'materiales/pedido_compra_lista.html', context)

@login_required
@permission_required('materiales.add_pedidocompra', raise_exception=True)
def pedido_compra_crear(request):
    if request.method == 'POST':
        form = PedidoCompraForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.solicitado_por = request.user
            pedido.codigo = f"PC-{timezone.now().strftime('%Y%m%d')}-{PedidoCompra.objects.count() + 1:04d}"
            pedido.save()
            
            messages.success(request, f'Pedido de compra {pedido.codigo} creado exitosamente.')
            return redirect('pedido_compra_detalle', pk=pedido.pk)
    else:
        form = PedidoCompraForm()
    
    return render(request, 'materiales/pedido_compra_form.html', {'form': form})

@login_required
def pedido_compra_detalle(request, pk):
    pedido = get_object_or_404(PedidoCompra.objects.prefetch_related('detalles'), pk=pk)
    
    # Materiales que necesitan reabastecimiento para sugerir
    materiales_necesarios = Inventario.objects.filter(
        cantidad_actual__lte=F('cantidad_minima'),
        activo=True
    ).select_related('material')
    
    if request.method == 'POST':
        # Agregar material al pedido
        material_id = request.POST.get('material_id')
        cantidad = request.POST.get('cantidad')
        costo_estimado = request.POST.get('costo_estimado')
        
        if material_id and cantidad:
            material = get_object_or_404(Material, pk=material_id)
            DetallePedidoCompra.objects.create(
                pedido_compra=pedido,
                material=material,
                cantidad_solicitada=cantidad,
                costo_unitario_estimado=costo_estimado or 0
            )
            
            messages.success(request, f'Material {material.nombre} agregado al pedido.')
            return redirect('pedido_compra_detalle', pk=pedido.pk)
    
    context = {
        'pedido': pedido,
        'materiales_necesarios': materiales_necesarios,
    }
    return render(request, 'materiales/pedido_compra_detalle.html', context)

@login_required
@permission_required('materiales.change_pedidocompra', raise_exception=True)
def pedido_compra_recibir(request, pk):
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    
    if request.method == 'POST':
        # Procesar recepción de materiales
        for detalle in pedido.detalles.all():
            cantidad_recibida = request.POST.get(f'cantidad_recibida_{detalle.id}')
            costo_real = request.POST.get(f'costo_real_{detalle.id}')
            
            if cantidad_recibida:
                detalle.cantidad_recibida = cantidad_recibida
                if costo_real:
                    detalle.costo_unitario_real = costo_real
                detalle.save()
        
        # Marcar pedido como recibido
        pedido.recibir_pedido(request.user)
        
        messages.success(request, f'Pedido de compra {pedido.codigo} recibido exitosamente.')
        return redirect('pedido_compra_lista')
    
    return render(request, 'materiales/pedido_compra_recibir.html', {'pedido': pedido})

# ============ REPORTES Y ESTADÍSTICAS ============ #
@login_required
def reportes_inventario(request):
    form = GenerarReporteForm(request.GET or None)
    
    if form.is_valid():
        tipo = form.cleaned_data['tipo']
        fecha_inicio = form.cleaned_data['fecha_inicio']
        fecha_fin = form.cleaned_data['fecha_fin']
        
        # Generar reporte
        if tipo == 'diario':
            titulo = f'Reporte Diario de Inventario - {fecha_inicio}'
        elif tipo == 'semanal':
            titulo = f'Reporte Semanal de Inventario - {fecha_inicio} a {fecha_fin}'
        else:
            titulo = f'Reporte Mensual de Inventario - {fecha_inicio.strftime("%B %Y")}'
        
        # Calcular métricas
        inventarios = Inventario.objects.filter(activo=True)
        total_materiales = inventarios.count()
        materiales_bajos = inventarios.filter(cantidad_actual__lte=F('cantidad_minima')).count()
        
        valor_total = sum(float(inv.valor_total()) for inv in inventarios)
        
        # Movimientos en el período
        movimientos = MovimientoInventario.objects.filter(
            fecha_movimiento__date__range=[fecha_inicio, fecha_fin]
        )
        movimientos_totales = movimientos.count()
        
        # Crear reporte en base de datos
        reporte = ReporteInventario.objects.create(
            titulo=titulo,
            tipo=tipo,
            periodo_inicio=fecha_inicio,
            periodo_fin=fecha_fin,
            total_materiales=total_materiales,
            materiales_bajos=materiales_bajos,
            valor_total_inventario=valor_total,
            movimientos_totales=movimientos_totales,
            generado_por=request.user,
            resumen=f'Reporte de inventario generado automáticamente para el período {fecha_inicio} a {fecha_fin}.'
        )
        
        messages.success(request, f'Reporte {tipo} generado exitosamente.')
        return redirect('reportes_inventario')
    
    # Reportes existentes
    reportes = ReporteInventario.objects.all().order_by('-fecha_generacion')[:10]
    
    # Estadísticas actuales
    inventarios = Inventario.objects.filter(activo=True)
    total_materiales = inventarios.count()
    materiales_bajos = inventarios.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    
    valor_total = sum(float(inv.valor_total()) for inv in inventarios)
    
    # Alertas activas
    alertas_activas = AlertaStock.objects.filter(resuelta=False).count()
    
    # Pedidos de compra pendientes
    pedidos_pendientes = PedidoCompra.objects.filter(estado__in=['pendiente', 'aprobado', 'ordenado']).count()
    
    context = {
        'form': form,
        'reportes': reportes,
        'total_materiales': total_materiales,
        'materiales_bajos': materiales_bajos,
        'valor_total': valor_total,
        'alertas_activas': alertas_activas,
        'pedidos_pendientes': pedidos_pendientes,
    }
    return render(request, 'materiales/reportes_inventario.html', context)

@login_required
def exportar_inventario_csv(request):
    # Crear respuesta HTTP con archivo CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventario.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Inventario - Reporte'])
    writer.writerow(['Fecha', timezone.now().strftime('%d/%m/%Y %H:%M')])
    writer.writerow([])
    writer.writerow(['Material', 'Tipo', 'Cantidad Actual', 'Unidad', 'Mínimo', 'Máximo', 
                     'Ubicación', 'Costo Promedio', 'Valor Total', 'Necesita Reabastecimiento'])
    
    inventarios = Inventario.objects.filter(activo=True).select_related('material')
    for inv in inventarios:
        writer.writerow([
            inv.material.nombre,
            inv.material.get_tipo_display(),
            inv.cantidad_actual,
            inv.material.unidad,
            inv.cantidad_minima,
            inv.cantidad_maxima,
            inv.ubicacion,
            f"${inv.costo_promedio:.2f}",
            f"${inv.valor_total():.2f}",
            'Sí' if inv.necesita_reabastecimiento() else 'No'
        ])
    
    return response

# ============ API PARA GRÁFICOS ============ #
@login_required
def api_inventario_datos(request):
    """API para gráficos del inventario"""
    # Datos para gráfico de distribución por tipo
    tipos = ['tela', 'hilo', 'avios', 'otro']
    datos_tipos = []
    
    for tipo in tipos:
        inventarios = Inventario.objects.filter(
            material__tipo=tipo,
            activo=True
        )
        
        cantidad = sum(float(inv.cantidad_actual) for inv in inventarios)
        valor = sum(float(inv.valor_total()) for inv in inventarios)
        
        datos_tipos.append({
            'tipo': tipo,
            'cantidad': cantidad,
            'valor': valor
        })
    
    # Materiales con stock más bajo
    materiales_bajos = Inventario.objects.filter(
        activo=True
    ).order_by('cantidad_actual')[:10].select_related('material')
    
    datos_bajos = []
    for inv in materiales_bajos:
        datos_bajos.append({
            'material': inv.material.nombre,
            'cantidad': float(inv.cantidad_actual),
            'minimo': float(inv.cantidad_minima),
            'porcentaje': float(inv.porcentaje_stock())
        })
    
    # Estadísticas generales
    inventarios = Inventario.objects.filter(activo=True)
    total_materiales = inventarios.count()
    materiales_bajos_count = inventarios.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    valor_total = sum(float(inv.valor_total()) for inv in inventarios)
    
    return JsonResponse({
        'por_tipo': datos_tipos,
        'materiales_bajos': datos_bajos,
        'total_materiales': total_materiales,
        'materiales_bajos_count': materiales_bajos_count,
        'valor_total': valor_total
    })