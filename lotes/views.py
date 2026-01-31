from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from datetime import datetime, timedelta
import json
import csv

from .models import Lote, MaterialLote, Trazabilidad, Almacen, MovimientoAlmacen
from .forms import (
    LoteForm, MaterialLoteForm, TrazabilidadForm, 
    AlmacenForm, MovimientoAlmacenForm,
    FiltroLotesForm, FiltroMovimientosForm
)
from produccion.models import OrdenProduccion, Producto
from materiales.models import Material
from procesos.models import Operacion

# ============ DASHBOARD LOTES ============ #
@login_required
def dashboard_lotes(request):
    """Dashboard principal de lotes"""
    # Estadísticas generales
    total_lotes = Lote.objects.count()
    lotes_en_produccion = Lote.objects.filter(estado='en_produccion').count()
    lotes_planeados = Lote.objects.filter(estado='planeado').count()
    lotes_completados = Lote.objects.filter(estado='completado').count()
    lotes_almacenados = Lote.objects.filter(estado='almacenado').count()
    
    # Lotes por prioridad
    lotes_criticos = Lote.objects.filter(prioridad=4, estado__in=['planeado', 'en_produccion']).count()
    lotes_altos = Lote.objects.filter(prioridad=3, estado__in=['planeado', 'en_produccion']).count()
    
    # Lotes recientes
    lotes_recientes = Lote.objects.all().order_by('-fecha_creacion')[:10]
    
    # Lotes atrasados
    hoy = timezone.now()
    lotes_atrasados = Lote.objects.filter(
        estado='en_produccion',
        fecha_fin_planeada__lt=hoy
    ).count()
    
    # Estadísticas de producción
    total_producido = Lote.objects.aggregate(
        total=Sum('cantidad_producida')
    )['total'] or 0
    
    total_objetivo = Lote.objects.aggregate(
        total=Sum('cantidad_objetivo')
    )['total'] or 0
    
    tasa_completitud = 0
    if total_objetivo > 0:
        tasa_completitud = (total_producido / total_objetivo) * 100
    
    # Almacenes
    almacenes = Almacen.objects.filter(activo=True)[:5]
    
    # Movimientos pendientes
    movimientos_pendientes = MovimientoAlmacen.objects.filter(
        estado='pendiente'
    ).order_by('-fecha_creacion')[:5]
    
    context = {
        'total_lotes': total_lotes,
        'lotes_en_produccion': lotes_en_produccion,
        'lotes_planeados': lotes_planeados,
        'lotes_completados': lotes_completados,
        'lotes_almacenados': lotes_almacenados,
        'lotes_criticos': lotes_criticos,
        'lotes_altos': lotes_altos,
        'lotes_atrasados': lotes_atrasados,
        'total_producido': total_producido,
        'total_objetivo': total_objetivo,
        'tasa_completitud': round(tasa_completitud, 2),
        'lotes_recientes': lotes_recientes,
        'almacenes': almacenes,
        'movimientos_pendientes': movimientos_pendientes,
    }
    
    return render(request, 'lotes/dashboard.html', context)

# ============ GESTIÓN DE LOTES ============ #
@login_required
def lista_lotes(request):
    """Lista todos los lotes con filtros"""
    lotes = Lote.objects.all().order_by('-fecha_creacion')
    
    form = FiltroLotesForm(request.GET or None)
    
    if form.is_valid():
        estado = form.cleaned_data.get('estado')
        prioridad = form.cleaned_data.get('prioridad')
        resultado_calidad = form.cleaned_data.get('resultado_calidad')
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        responsable_id = form.cleaned_data.get('responsable')
        producto_id = form.cleaned_data.get('producto')
        activo = form.cleaned_data.get('activo')
        
        if estado:
            lotes = lotes.filter(estado=estado)
        if prioridad:
            lotes = lotes.filter(prioridad=prioridad)
        if resultado_calidad:
            lotes = lotes.filter(resultado_control_calidad=resultado_calidad)
        if fecha_inicio:
            lotes = lotes.filter(fecha_creacion__date__gte=fecha_inicio)
        if fecha_fin:
            lotes = lotes.filter(fecha_creacion__date__lte=fecha_fin)
        if responsable_id:
            lotes = lotes.filter(responsable_id=responsable_id)
        if producto_id:
            lotes = lotes.filter(producto_id=producto_id)
        if activo == 'true':
            lotes = lotes.filter(activo=True)
        elif activo == 'false':
            lotes = lotes.filter(activo=False)
    
    # Estadísticas de la lista filtrada
    total_lotes = lotes.count()
    cantidad_total = lotes.aggregate(
        total_objetivo=Sum('cantidad_objetivo'),
        total_producido=Sum('cantidad_producida'),
        total_aprobado=Sum('cantidad_aprobada')
    )
    
    # Paginación
    paginator = Paginator(lotes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opciones para filtros
    productos = Producto.objects.filter(activo=True)
    usuarios = request.user.__class__.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_lotes': total_lotes,
        'cantidad_total': cantidad_total,
        'productos': productos,
        'usuarios': usuarios,
    }
    
    return render(request, 'lotes/lista_lotes.html', context)

@login_required
@permission_required('lotes.add_lote', raise_exception=True)
def crear_lote(request):
    """Crear un nuevo lote"""
    if request.method == 'POST':
        form = LoteForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    lote = form.save(commit=False)
                    lote.creado_por = request.user
                    
                    # Si no se especifica responsable, asignar al usuario actual
                    if not lote.responsable:
                        lote.responsable = request.user
                    
                    # Calcular costos estimados iniciales
                    if lote.producto and lote.cantidad_objetivo > 0:
                        lote.costo_estimado = lote.producto.costo_estimado * lote.cantidad_objetivo
                        lote.precio_venta_estimado = lote.producto.precio_venta * lote.cantidad_objetivo
                    
                    lote.save()
                    
                    # Crear registro de trazabilidad
                    Trazabilidad.objects.create(
                        lote=lote,
                        tipo_evento='creacion',
                        etapa='Creación del lote',
                        observaciones=f'Lote {lote.codigo} creado por {request.user.username}',
                        usuario=request.user
                    )
                    
                    # Registrar operación
                    Operacion.objects.create(
                        usuario=request.user,
                        accion='proceso_iniciado',
                        descripcion=f"Lote '{lote.codigo}' creado",
                        referencia=f"LOTE-{lote.id}"
                    )
                    
                    messages.success(request, f'Lote "{lote.codigo}" creado exitosamente.')
                    
                    # Redirigir a agregar materiales
                    return redirect('materiales_lote', lote_id=lote.id)
                    
            except Exception as e:
                messages.error(request, f'Error al crear el lote: {str(e)}')
    else:
        form = LoteForm()
    
    return render(request, 'lotes/lote_form.html', {'form': form})

@login_required
def detalle_lote(request, pk):
    """Detalle de un lote específico"""
    lote = get_object_or_404(
        Lote.objects.select_related(
            'producto', 'orden_produccion', 'responsable', 'supervisor', 'creado_por'
        ), 
        pk=pk
    )
    
    # Materiales asignados
    materiales = lote.materiales_detalle.all().select_related('material')
    
    # Trazabilidad
    trazabilidad = lote.trazabilidad.all().order_by('-fecha')[:20]
    
    # Estadísticas
    progreso = lote.progreso_produccion()
    tiempo_transcurrido = lote.tiempo_transcurrido()
    tiempo_restante = lote.tiempo_restante_estimado()
    
    # Calcular costos de materiales
    costo_materiales = materiales.aggregate(
        total=Sum(F('cantidad_asignada') * F('costo_unitario'))
    )['total'] or 0
    
    # Porcentaje de materiales entregados
    materiales_entregados = materiales.filter(entregado=True).count()
    porcentaje_entregado = 0
    if materiales.count() > 0:
        porcentaje_entregado = (materiales_entregados / materiales.count()) * 100
    
    context = {
        'lote': lote,
        'materiales': materiales,
        'trazabilidad': trazabilidad,
        'progreso': progreso,
        'tiempo_transcurrido': tiempo_transcurrido,
        'tiempo_restante': tiempo_restante,
        'costo_materiales': costo_materiales,
        'porcentaje_entregado': porcentaje_entregado,
    }
    
    return render(request, 'lotes/detalle_lote.html', context)

@login_required
@permission_required('lotes.change_lote', raise_exception=True)
def editar_lote(request, pk):
    """Editar un lote existente"""
    lote = get_object_or_404(Lote, pk=pk)
    
    if request.method == 'POST':
        form = LoteForm(request.POST, instance=lote)
        if form.is_valid():
            lote = form.save()
            
            # Registrar trazabilidad
            Trazabilidad.objects.create(
                lote=lote,
                tipo_evento='modificacion',
                etapa='Edición del lote',
                observaciones=f'Lote editado por {request.user.username}',
                usuario=request.user
            )
            
            messages.success(request, f'Lote "{lote.codigo}" actualizado exitosamente.')
            return redirect('detalle_lote', pk=lote.pk)
    else:
        form = LoteForm(instance=lote)
    
    return render(request, 'lotes/lote_form.html', {'form': form, 'lote': lote})

@login_required
def iniciar_produccion_lote(request, lote_id):
    """Iniciar la producción de un lote"""
    lote = get_object_or_404(Lote, pk=lote_id)
    
    # Verificar que el lote esté en estado planeado
    if lote.estado != 'planeado':
        messages.error(request, f'El lote {lote.codigo} no está en estado "Planeado".')
        return redirect('detalle_lote', pk=lote.id)
    
    # Verificar que todos los materiales estén entregados
    materiales_pendientes = lote.materiales_detalle.filter(entregado=False).count()
    if materiales_pendientes > 0:
        messages.warning(
            request, 
            f'Hay {materiales_pendientes} materiales pendientes de entrega. '
            '¿Desea iniciar la producción de todas formas?'
        )
        # Podríamos redirigir a una página de confirmación aquí
    
    if request.method == 'POST':
        lote.iniciar_produccion()
        messages.success(request, f'Producción del lote {lote.codigo} iniciada.')
        return redirect('detalle_lote', pk=lote.id)
    
    return render(request, 'lotes/iniciar_produccion.html', {'lote': lote})

@login_required
def finalizar_produccion_lote(request, lote_id):
    """Finalizar la producción de un lote"""
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if lote.estado != 'en_produccion':
        messages.error(request, f'El lote {lote.codigo} no está en estado "En Producción".')
        return redirect('detalle_lote', pk=lote.id)
    
    if request.method == 'POST':
        cantidad_producida = request.POST.get('cantidad_producida', 0)
        
        try:
            cantidad_producida = int(cantidad_producida)
            if cantidad_producida <= 0:
                messages.error(request, 'La cantidad producida debe ser mayor a 0.')
                return redirect('detalle_lote', pk=lote.id)
            
            # Actualizar cantidad producida
            lote.cantidad_producida = cantidad_producida
            lote.cantidad_aprobada = cantidad_producida  # Inicialmente igual, puede cambiar en control de calidad
            
            # Calcular costos reales
            lote.calcular_costos()
            
            # Finalizar producción
            lote.finalizar_produccion()
            
            messages.success(request, f'Producción del lote {lote.codigo} finalizada. Cantidad: {cantidad_producida}')
            return redirect('detalle_lote', pk=lote.id)
            
        except ValueError:
            messages.error(request, 'La cantidad producida debe ser un número válido.')
    
    return render(request, 'lotes/finalizar_produccion.html', {'lote': lote})

@login_required
def aprobar_control_calidad(request, lote_id):
    """Aprobar un lote después del control de calidad"""
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if lote.estado != 'control_calidad':
        messages.error(request, f'El lote {lote.codigo} no está en estado "Control de Calidad".')
        return redirect('detalle_lote', pk=lote.id)
    
    if request.method == 'POST':
        lote.aprobar_control_calidad()
        messages.success(request, f'Lote {lote.codigo} aprobado en control de calidad.')
        return redirect('detalle_lote', pk=lote.id)
    
    return render(request, 'lotes/aprobar_calidad.html', {'lote': lote})

@login_required
def rechazar_lote(request, lote_id):
    """Rechazar un lote (total o parcialmente)"""
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if lote.estado != 'control_calidad':
        messages.error(request, f'El lote {lote.codigo} no está en estado "Control de Calidad".')
        return redirect('detalle_lote', pk=lote.id)
    
    if request.method == 'POST':
        cantidad_rechazada = request.POST.get('cantidad_rechazada', 0)
        motivo = request.POST.get('motivo', '')
        
        try:
            cantidad_rechazada = int(cantidad_rechazada)
            if cantidad_rechazada < 0 or cantidad_rechazada > lote.cantidad_producida:
                messages.error(request, f'Cantidad rechazada inválida. Debe estar entre 0 y {lote.cantidad_producida}.')
                return redirect('detalle_lote', pk=lote.id)
            
            lote.rechazar_lote(cantidad_rechazada, motivo)
            
            if cantidad_rechazada == 0:
                messages.success(request, f'Lote {lote.codigo} no tuvo rechazos.')
            elif cantidad_rechazada >= lote.cantidad_producida:
                messages.error(request, f'Lote {lote.codigo} rechazado completamente.')
            else:
                messages.warning(request, f'Lote {lote.codigo} rechazado parcialmente: {cantidad_rechazada} unidades.')
            
            return redirect('detalle_lote', pk=lote.id)
            
        except ValueError:
            messages.error(request, 'La cantidad rechazada debe ser un número válido.')
    
    return render(request, 'lotes/rechazar_lote.html', {'lote': lote})

# ============ MATERIALES POR LOTE ============ #
@login_required
def materiales_lote(request, lote_id):
    """Gestión de materiales asignados a un lote"""
    lote = get_object_or_404(Lote, pk=lote_id)
    materiales = lote.materiales_detalle.all().select_related('material')
    
    # Estadísticas de materiales
    materiales_entregados = materiales.filter(entregado=True).count()
    materiales_pendientes = materiales.filter(entregado=False).count()
    
    # Costo total estimado
    costo_total = materiales.aggregate(
        total=Sum(F('cantidad_asignada') * F('costo_unitario'))
    )['total'] or 0
    
    # Materiales disponibles para agregar
    materiales_disponibles = Material.objects.filter(
        activo=True
    ).exclude(
        id__in=materiales.values_list('material_id', flat=True)
    )[:20]
    
    context = {
        'lote': lote,
        'materiales': materiales,
        'materiales_entregados': materiales_entregados,
        'materiales_pendientes': materiales_pendientes,
        'costo_total': costo_total,
        'materiales_disponibles': materiales_disponibles,
    }
    
    return render(request, 'lotes/materiales_lote.html', context)

@login_required
def agregar_material_lote(request, lote_id):
    """Agregar un material a un lote"""
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if request.method == 'POST':
        form = MaterialLoteForm(request.POST)
        if form.is_valid():
            material_lote = form.save(commit=False)
            material_lote.lote = lote
            
            # Obtener el costo actual del material
            if not material_lote.costo_unitario:
                material_lote.costo_unitario = material_lote.material.costo_promedio
            
            material_lote.save()
            
            # Registrar trazabilidad
            Trazabilidad.objects.create(
                lote=lote,
                tipo_evento='modificacion',
                etapa='Material agregado',
                observaciones=f'Material {material_lote.material.nombre} agregado al lote',
                usuario=request.user
            )
            
            messages.success(request, f'Material "{material_lote.material.nombre}" agregado al lote.')
            return redirect('materiales_lote', lote_id=lote.id)
    else:
        form = MaterialLoteForm(initial={'lote': lote})
    
    return render(request, 'lotes/agregar_material.html', {'form': form, 'lote': lote})

@login_required
def entregar_material(request, lote_id, material_id):
    """Marcar un material como entregado"""
    lote = get_object_or_404(Lote, pk=lote_id)
    material_lote = get_object_or_404(MaterialLote, lote=lote, pk=material_id)
    
    if request.method == 'POST':
        if not material_lote.entregado:
            material_lote.entregado = True
            material_lote.fecha_entrega = timezone.now()
            material_lote.recibido_por = request.user
            material_lote.save()
            
            # Registrar trazabilidad
            Trazabilidad.objects.create(
                lote=lote,
                tipo_evento='observacion',
                etapa='Material entregado',
                observaciones=f'Material {material_lote.material.nombre} entregado para el lote',
                usuario=request.user
            )
            
            messages.success(request, f'Material "{material_lote.material.nombre}" marcado como entregado.')
        else:
            messages.info(request, f'El material "{material_lote.material.nombre}" ya estaba entregado.')
    
    return redirect('materiales_lote', lote_id=lote.id)

# ============ TRAZABILIDAD ============ #
@login_required
def trazabilidad_lote(request, lote_id):
    """Ver la trazabilidad completa de un lote"""
    lote = get_object_or_404(Lote, pk=lote_id)
    eventos = lote.trazabilidad.all().order_by('-fecha')
    
    # Estadísticas de eventos
    total_eventos = eventos.count()
    eventos_por_tipo = eventos.values('tipo_evento').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')
    
    # Paginación
    paginator = Paginator(eventos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'lote': lote,
        'page_obj': page_obj,
        'total_eventos': total_eventos,
        'eventos_por_tipo': eventos_por_tipo,
    }
    
    return render(request, 'lotes/trazabilidad.html', context)

@login_required
def agregar_trazabilidad(request, lote_id):
    """Agregar un evento de trazabilidad a un lote"""
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if request.method == 'POST':
        form = TrazabilidadForm(request.POST, request.FILES)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.lote = lote
            evento.usuario = request.user
            
            # Procesar archivos adjuntos
            if 'archivo' in request.FILES:
                evento.archivo = request.FILES['archivo']
            if 'foto' in request.FILES:
                evento.foto = request.FILES['foto']
            
            evento.save()
            
            messages.success(request, 'Evento de trazabilidad registrado exitosamente.')
            return redirect('trazabilidad_lote', lote_id=lote.id)
    else:
        form = TrazabilidadForm()
    
    return render(request, 'lotes/agregar_trazabilidad.html', {'form': form, 'lote': lote})

# ============ ALMACENES ============ #
@login_required
def lista_almacenes(request):
    """Lista todos los almacenes"""
    almacenes = Almacen.objects.all().order_by('codigo')
    
    # Filtros
    tipo = request.GET.get('tipo')
    activo = request.GET.get('activo')
    
    if tipo:
        almacenes = almacenes.filter(tipo=tipo)
    if activo == 'true':
        almacenes = almacenes.filter(activo=True)
    elif activo == 'false':
        almacenes = almacenes.filter(activo=False)
    
    # Estadísticas
    total_almacenes = almacenes.count()
    capacidad_total = almacenes.aggregate(
        total_max=Sum('capacidad_maxima'),
        total_actual=Sum('capacidad_actual')
    )
    
    # Lotes almacenados por tipo de almacén
    lotes_por_tipo = {}
    for almacen in almacenes:
        if almacen.tipo not in lotes_por_tipo:
            lotes_por_tipo[almacen.tipo] = 0
        lotes_por_tipo[almacen.tipo] += almacen.capacidad_actual
    
    context = {
        'almacenes': almacenes,
        'total_almacenes': total_almacenes,
        'capacidad_total': capacidad_total,
        'lotes_por_tipo': lotes_por_tipo,
    }
    
    return render(request, 'lotes/lista_almacenes.html', context)

@login_required
@permission_required('lotes.add_almacen', raise_exception=True)
def crear_almacen(request):
    """Crear un nuevo almacén"""
    if request.method == 'POST':
        form = AlmacenForm(request.POST)
        if form.is_valid():
            almacen = form.save()
            messages.success(request, f'Almacén "{almacen.codigo}" creado exitosamente.')
            return redirect('detalle_almacen', pk=almacen.pk)
    else:
        form = AlmacenForm()
    
    return render(request, 'lotes/almacen_form.html', {'form': form})

@login_required
def detalle_almacen(request, pk):
    """Detalle de un almacén específico"""
    almacen = get_object_or_404(
        Almacen.objects.select_related('encargado'), 
        pk=pk
    )
    
    # Lotes almacenados
    lotes_almacenados = Lote.objects.filter(
        almacen_destino=almacen,
        estado='almacenado'
    ).order_by('-fecha_creacion')[:20]
    
    # Movimientos recientes
    movimientos_recientes = MovimientoAlmacen.objects.filter(
        Q(almacen_origen=almacen) | Q(almacen_destino=almacen)
    ).order_by('-fecha_creacion')[:10]
    
    # Estadísticas de ocupación
    capacidad_disponible = almacen.capacidad_disponible()
    porcentaje_ocupacion = almacen.porcentaje_ocupacion()
    
    context = {
        'almacen': almacen,
        'lotes_almacenados': lotes_almacenados,
        'movimientos_recientes': movimientos_recientes,
        'capacidad_disponible': capacidad_disponible,
        'porcentaje_ocupacion': porcentaje_ocupacion,
    }
    
    return render(request, 'lotes/detalle_almacen.html', context)

# ============ MOVIMIENTOS DE ALMACÉN ============ #
@login_required
def lista_movimientos(request):
    """Lista todos los movimientos de almacén"""
    movimientos = MovimientoAlmacen.objects.all().order_by('-fecha_creacion')
    
    form = FiltroMovimientosForm(request.GET or None)
    
    if form.is_valid():
        tipo_movimiento = form.cleaned_data.get('tipo_movimiento')
        estado = form.cleaned_data.get('estado')
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        lote_codigo = form.cleaned_data.get('lote_codigo')
        
        if tipo_movimiento:
            movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)
        if estado:
            movimientos = movimientos.filter(estado=estado)
        if fecha_inicio:
            movimientos = movimientos.filter(fecha_creacion__date__gte=fecha_inicio)
        if fecha_fin:
            movimientos = movimientos.filter(fecha_creacion__date__lte=fecha_fin)
        if lote_codigo:
            movimientos = movimientos.filter(lote__codigo__icontains=lote_codigo)
    
    # Estadísticas
    total_movimientos = movimientos.count()
    pendientes = movimientos.filter(estado='pendiente').count()
    completados = movimientos.filter(estado='completado').count()
    
    # Paginación
    paginator = Paginator(movimientos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_movimientos': total_movimientos,
        'pendientes': pendientes,
        'completados': completados,
    }
    
    return render(request, 'lotes/lista_movimientos.html', context)

@login_required
@permission_required('lotes.add_movimientoalmacen', raise_exception=True)
def crear_movimiento(request):
    """Crear un nuevo movimiento de almacén"""
    if request.method == 'POST':
        form = MovimientoAlmacenForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.creado_por = request.user
            movimiento.solicitante = request.user
            
            # Para movimientos de entrada, el destino es obligatorio
            if movimiento.tipo_movimiento == 'entrada' and not movimiento.almacen_destino:
                form.add_error('almacen_destino', 'Este campo es obligatorio para movimientos de entrada.')
                return render(request, 'lotes/movimiento_form.html', {'form': form})
            
            # Para movimientos de salida, el origen es obligatorio
            if movimiento.tipo_movimiento == 'salida' and not movimiento.almacen_origen:
                form.add_error('almacen_origen', 'Este campo es obligatorio para movimientos de salida.')
                return render(request, 'lotes/movimiento_form.html', {'form': form})
            
            # Para transferencias, ambos son obligatorios
            if movimiento.tipo_movimiento == 'transferencia':
                if not movimiento.almacen_origen:
                    form.add_error('almacen_origen', 'Este campo es obligatorio para transferencias.')
                if not movimiento.almacen_destino:
                    form.add_error('almacen_destino', 'Este campo es obligatorio para transferencias.')
                if form.errors:
                    return render(request, 'lotes/movimiento_form.html', {'form': form})
            
            movimiento.save()
            
            messages.success(request, f'Movimiento "{movimiento.referencia}" creado exitosamente.')
            
            # Si el usuario tiene permisos para autorizar, redirigir a autorización
            if request.user.has_perm('lotes.change_movimientoalmacen'):
                return redirect('autorizar_movimiento', pk=movimiento.pk)
            else:
                return redirect('lista_movimientos')
    else:
        form = MovimientoAlmacenForm()
    
    return render(request, 'lotes/movimiento_form.html', {'form': form})

@login_required
@permission_required('lotes.change_movimientoalmacen', raise_exception=True)
def autorizar_movimiento(request, pk):
    """Autorizar un movimiento pendiente"""
    movimiento = get_object_or_404(MovimientoAlmacen, pk=pk)
    
    if movimiento.estado != 'pendiente':
        messages.error(request, f'El movimiento {movimiento.referencia} no está pendiente de autorización.')
        return redirect('detalle_lote', pk=movimiento.lote.pk if movimiento.lote else 0)
    
    if request.method == 'POST':
        movimiento.autorizar(request.user)
        messages.success(request, f'Movimiento {movimiento.referencia} autorizado.')
        return redirect('lista_movimientos')
    
    return render(request, 'lotes/autorizar_movimiento.html', {'movimiento': movimiento})

@login_required
@permission_required('lotes.change_movimientoalmacen', raise_exception=True)
def ejecutar_movimiento(request, pk):
    """Ejecutar un movimiento autorizado"""
    movimiento = get_object_or_404(MovimientoAlmacen, pk=pk)
    
    if movimiento.estado != 'autorizado':
        messages.error(request, f'El movimiento {movimiento.referencia} no está autorizado para ejecución.')
        return redirect('detalle_lote', pk=movimiento.lote.pk if movimiento.lote else 0)
    
    # Verificar que el almacén destino tenga capacidad disponible
    if movimiento.almacen_destino:
        if movimiento.almacen_destino.capacidad_disponible() < movimiento.cantidad:
            messages.error(
                request, 
                f'El almacén {movimiento.almacen_destino.codigo} no tiene capacidad suficiente. '
                f'Disponible: {movimiento.almacen_destino.capacidad_disponible()}, '
                f'Necesario: {movimiento.cantidad}'
            )
            return redirect('detalle_lote', pk=movimiento.lote.pk if movimiento.lote else 0)
    
    if request.method == 'POST':
        try:
            movimiento.ejecutar(request.user)
            messages.success(request, f'Movimiento {movimiento.referencia} ejecutado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al ejecutar el movimiento: {str(e)}')
        
        return redirect('lista_movimientos')
    
    return render(request, 'lotes/ejecutar_movimiento.html', {'movimiento': movimiento})

@login_required
def cancelar_movimiento(request, pk):
    """Cancelar un movimiento"""
    movimiento = get_object_or_404(MovimientoAlmacen, pk=pk)
    
    if movimiento.estado in ['completado', 'cancelado']:
        messages.error(request, f'El movimiento {movimiento.referencia} no puede ser cancelado en su estado actual.')
        return redirect('lista_movimientos')
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        movimiento.cancelar(request.user, motivo)
        messages.warning(request, f'Movimiento {movimiento.referencia} cancelado.')
        return redirect('lista_movimientos')
    
    return render(request, 'lotes/cancelar_movimiento.html', {'movimiento': movimiento})

# ============ REPORTES ============ #
@login_required
def reporte_estado_lotes(request):
    """Reporte del estado de los lotes"""
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    
    lotes = Lote.objects.all()
    
    if fecha_inicio:
        lotes = lotes.filter(fecha_creacion__date__gte=fecha_inicio)
    if fecha_fin:
        lotes = lotes.filter(fecha_creacion__date__lte=fecha_fin)
    if estado:
        lotes = lotes.filter(estado=estado)
    
    # Agrupar por estado
    lotes_por_estado = lotes.values('estado').annotate(
        cantidad=Count('id'),
        total_objetivo=Sum('cantidad_objetivo'),
        total_producido=Sum('cantidad_producida'),
        total_aprobado=Sum('cantidad_aprobada')
    ).order_by('-cantidad')
    
    # Agrupar por prioridad
    lotes_por_prioridad = lotes.values('prioridad').annotate(
        cantidad=Count('id')
    ).order_by('prioridad')
    
    # Lotes atrasados
    hoy = timezone.now()
    lotes_atrasados = lotes.filter(
        estado='en_produccion',
        fecha_fin_planeada__lt=hoy
    )
    
    context = {
        'lotes': lotes,
        'lotes_por_estado': lotes_por_estado,
        'lotes_por_prioridad': lotes_por_prioridad,
        'lotes_atrasados': lotes_atrasados,
        'total_lotes': lotes.count(),
    }
    
    return render(request, 'lotes/reportes/estado_lotes.html', context)

@login_required
def reporte_movimientos(request):
    """Reporte de movimientos de almacén"""
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo_movimiento = request.GET.get('tipo_movimiento')
    
    movimientos = MovimientoAlmacen.objects.all()
    
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_creacion__date__gte=fecha_inicio)
    if fecha_fin:
        movimientos = movimientos.filter(fecha_creacion__date__lte=fecha_fin)
    if tipo_movimiento:
        movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)
    
    # Agrupar por tipo
    movimientos_por_tipo = movimientos.values('tipo_movimiento').annotate(
        cantidad=Count('id'),
        total_unidades=Sum('cantidad')
    ).order_by('-cantidad')
    
    # Agrupar por estado
    movimientos_por_estado = movimientos.values('estado').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')
    
    # Movimientos por almacén
    movimientos_por_almacen_origen = movimientos.values('almacen_origen__codigo').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')[:10]
    
    movimientos_por_almacen_destino = movimientos.values('almacen_destino__codigo').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')[:10]
    
    context = {
        'movimientos': movimientos,
        'movimientos_por_tipo': movimientos_por_tipo,
        'movimientos_por_estado': movimientos_por_estado,
        'movimientos_por_almacen_origen': movimientos_por_almacen_origen,
        'movimientos_por_almacen_destino': movimientos_por_almacen_destino,
        'total_movimientos': movimientos.count(),
    }
    
    return render(request, 'lotes/reportes/movimientos.html', context)

# ============ EXPORTACIÓN ============ #
@login_required
def exportar_lotes_csv(request):
    """Exportar lotes a CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="lotes.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Lotes - Reporte'])
    writer.writerow(['Fecha', timezone.now().strftime('%d/%m/%Y %H:%M')])
    writer.writerow([])
    writer.writerow([
        'Código', 'Nombre', 'Producto', 'Estado', 'Prioridad', 
        'Cantidad Objetivo', 'Cantidad Producida', 'Cantidad Aprobada',
        'Fecha Creación', 'Fecha Inicio Planeada', 'Fecha Fin Planeada',
        'Fecha Inicio Real', 'Fecha Fin Real', 'Responsable', 
        'Costo Estimado', 'Costo Real', 'Precio Venta Estimado', 'Margen'
    ])
    
    lotes = Lote.objects.all().select_related('producto', 'responsable')
    for lote in lotes:
        writer.writerow([
            lote.codigo,
            lote.nombre,
            lote.producto.nombre if lote.producto else '',
            lote.get_estado_display(),
            lote.get_prioridad_display(),
            lote.cantidad_objetivo,
            lote.cantidad_producida,
            lote.cantidad_aprobada,
            lote.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            lote.fecha_inicio_planeada.strftime('%d/%m/%Y %H:%M') if lote.fecha_inicio_planeada else '',
            lote.fecha_fin_planeada.strftime('%d/%m/%Y %H:%M') if lote.fecha_fin_planeada else '',
            lote.fecha_inicio_real.strftime('%d/%m/%Y %H:%M') if lote.fecha_inicio_real else '',
            lote.fecha_fin_real.strftime('%d/%m/%Y %H:%M') if lote.fecha_fin_real else '',
            lote.responsable.username if lote.responsable else '',
            str(lote.costo_estimado),
            str(lote.costo_real),
            str(lote.precio_venta_estimado),
            f"{lote.margen_estimado:.2f}%" if lote.margen_estimado else '0.00%'
        ])
    
    return response

@login_required
def exportar_movimientos_csv(request):
    """Exportar movimientos de almacén a CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="movimientos_almacen.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Movimientos de Almacén - Reporte'])
    writer.writerow(['Fecha', timezone.now().strftime('%d/%m/%Y %H:%M')])
    writer.writerow([])
    writer.writerow([
        'Referencia', 'Tipo Movimiento', 'Lote', 'Almacén Origen', 
        'Almacén Destino', 'Cantidad', 'Estado', 'Solicitante',
        'Autorizador', 'Ejecutor', 'Fecha Solicitud', 'Fecha Autorización',
        'Fecha Ejecución', 'Motivo'
    ])
    
    movimientos = MovimientoAlmacen.objects.all().select_related(
        'lote', 'almacen_origen', 'almacen_destino',
        'solicitante', 'autorizador', 'ejecutor'
    )
    
    for mov in movimientos:
        writer.writerow([
            mov.referencia,
            mov.get_tipo_movimiento_display(),
            mov.lote.codigo if mov.lote else '',
            mov.almacen_origen.codigo if mov.almacen_origen else '',
            mov.almacen_destino.codigo if mov.almacen_destino else '',
            mov.cantidad,
            mov.get_estado_display(),
            mov.solicitante.username if mov.solicitante else '',
            mov.autorizador.username if mov.autorizador else '',
            mov.ejecutor.username if mov.ejecutor else '',
            mov.fecha_solicitud.strftime('%d/%m/%Y %H:%M'),
            mov.fecha_autorizacion.strftime('%d/%m/%Y %H:%M') if mov.fecha_autorizacion else '',
            mov.fecha_ejecucion.strftime('%d/%m/%Y %H:%M') if mov.fecha_ejecucion else '',
            mov.motivo[:100]  # Limitar a 100 caracteres
        ])
    
    return response

# ============ APIS PARA GRÁFICOS ============ #
@login_required
def api_estadisticas_lotes(request):
    """API para gráficos de lotes"""
    # Lotes por estado
    lotes_estado = Lote.objects.values('estado').annotate(
        cantidad=Count('id'),
        total_objetivo=Sum('cantidad_objetivo')
    ).order_by('estado')
    
    # Lotes por prioridad
    lotes_prioridad = Lote.objects.values('prioridad').annotate(
        cantidad=Count('id')
    ).order_by('prioridad')
    
    # Progreso promedio por tipo de producto
    progreso_por_producto = Lote.objects.filter(
        producto__isnull=False,
        estado='en_produccion'
    ).values('producto__nombre').annotate(
        progreso_promedio=Avg('progreso_produccion')
    ).order_by('-progreso_promedio')[:10]
    
    # Movimientos por tipo
    movimientos_tipo = MovimientoAlmacen.objects.values('tipo_movimiento').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')
    
    data = {
        'lotes_estado': list(lotes_estado),
        'lotes_prioridad': list(lotes_prioridad),
        'progreso_por_producto': list(progreso_por_producto),
        'movimientos_tipo': list(movimientos_tipo),
    }
    
    return JsonResponse(data)

@login_required
def api_lotes_en_produccion(request):
    """API para lotes en producción"""
    lotes = Lote.objects.filter(
        estado='en_produccion'
    ).select_related('producto', 'responsable')
    
    data = []
    for lote in lotes:
        data.append({
            'id': lote.id,
            'codigo': lote.codigo,
            'nombre': lote.nombre,
            'producto': lote.producto.nombre if lote.producto else 'Sin producto',
            'progreso': lote.progreso_produccion(),
            'cantidad_objetivo': lote.cantidad_objetivo,
            'cantidad_producida': lote.cantidad_producida,
            'responsable': lote.responsable.username if lote.responsable else 'Sin asignar',
            'fecha_fin_planeada': lote.fecha_fin_planeada.strftime('%d/%m/%Y') if lote.fecha_fin_planeada else '',
            'prioridad': lote.get_prioridad_display(),
        })
    
    return JsonResponse({'lotes': data})