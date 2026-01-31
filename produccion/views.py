from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
import csv
from django.contrib.auth.models import User
from .models import (
    Pedido, MetodoProduccion, OrdenProduccion, Planificacion, 
    ReporteProduccion, PlanificacionOrden, EstadoTrazabilidad
)
from .forms import PedidoForm, OrdenProduccionForm, PlanificacionForm, FiltroReporteForm, AvanceProduccionForm
from procesos.models import Operacion, ControlCalidad

# ============ DASHBOARD MEJORADO ============ #
@login_required
def dashboard(request):
    # Estadísticas principales
    hoy = timezone.now().date()
    semana_pasada = hoy - timedelta(days=7)
    
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado='pendiente').count()
    pedidos_en_proceso = Pedido.objects.filter(estado='en_proceso').count()
    pedidos_completados = Pedido.objects.filter(estado='completado').count()
    pedidos_urgentes = Pedido.objects.filter(fecha_entrega__lte=hoy + timedelta(days=2), estado__in=['pendiente', 'en_proceso']).count()
    
    # Estadísticas de producción
    ordenes_activas = OrdenProduccion.objects.filter(estado='en_proceso').count()
    ordenes_completadas_hoy = OrdenProduccion.objects.filter(
        estado='completada',
        fecha_fin__date=hoy
    ).count()
    
    # Estadísticas de lotes (nuevo)
    total_lotes = OrdenProduccion.objects.count()
    lotes_en_produccion = OrdenProduccion.objects.filter(estado='en_proceso').count()
    lotes_pendientes_calidad = OrdenProduccion.objects.filter(resultado_control_calidad='pendiente', estado='completada').count()
    lotes_aprobados = OrdenProduccion.objects.filter(resultado_control_calidad='aprobado').count()
    
    # Planificaciones activas
    planificaciones_activas = Planificacion.objects.filter(activa=True, completada=False).count()
    
    # Métricas de eficiencia
    tiempo_promedio = OrdenProduccion.objects.filter(
        estado='completada',
        fecha_fin__isnull=False
    ).aggregate(
        avg_time=Avg(
            timezone.now() - timezone.now()  # Esto es un placeholder
        )
    )
    
    # Pedidos recientes
    pedidos_recientes = Pedido.objects.all().order_by('-fecha_creacion')[:10]
    
    # Órdenes en progreso
    ordenes_en_progreso = OrdenProduccion.objects.filter(
        estado='en_proceso'
    ).order_by('fecha_programada')[:5]
    
    # Lotes recientes (nuevo)
    lotes_recientes = OrdenProduccion.objects.all().order_by('-fecha_creacion')[:5]
    
    # Planificaciones próximas
    planificaciones_proximas = Planificacion.objects.filter(
        fecha_inicio__lte=hoy + timedelta(days=7),
        fecha_fin__gte=hoy,
        activa=True
    ).order_by('fecha_inicio')[:3]
    
    # Gráficos de datos (simplificados)
    pedidos_por_estado = {
    'pendientes': pedidos_pendientes,
    'en_proceso': pedidos_en_proceso,
    'completados': pedidos_completados,
}
    
    # Operaciones recientes
    operaciones_recientes = Operacion.objects.all().order_by('-fecha')[:5]
    
    context = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_en_proceso': pedidos_en_proceso,
        'pedidos_completados': pedidos_completados,
        'pedidos_urgentes': pedidos_urgentes,
        'ordenes_activas': ordenes_activas,
        'ordenes_completadas_hoy': ordenes_completadas_hoy,
        'total_lotes': total_lotes,
        'lotes_en_produccion': lotes_en_produccion,
        'lotes_pendientes_calidad': lotes_pendientes_calidad,
        'lotes_aprobados': lotes_aprobados,
        'planificaciones_activas': planificaciones_activas,
        'pedidos_recientes': pedidos_recientes,
        'ordenes_en_progreso': ordenes_en_progreso,
        'lotes_recientes': lotes_recientes,
        'planificaciones_proximas': planificaciones_proximas,
        'pedidos_por_estado': pedidos_por_estado,
        'operaciones_recientes': operaciones_recientes,
        'hoy': hoy,
    }
    return render(request, 'produccion/dashboard.html', context)

# ============ PEDIDOS ============ #
class PedidoListView(LoginRequiredMixin, ListView):
    model = Pedido
    template_name = 'produccion/pedido_list.html'
    context_object_name = 'pedidos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Pedido.objects.all().select_related('producto', 'creado_por')
        
        # Filtros
        estado = self.request.GET.get('estado')
        prioridad = self.request.GET.get('prioridad')
        cliente = self.request.GET.get('cliente')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if estado:
            queryset = queryset.filter(estado=estado)
        if prioridad:
            queryset = queryset.filter(prioridad=prioridad)
        if cliente:
            queryset = queryset.filter(cliente__icontains=cliente)
        if fecha_desde:
            queryset = queryset.filter(fecha_entrega__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_entrega__lte=fecha_hasta)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Pedido.ESTADO_CHOICES
        context['prioridades'] = Pedido.PRIORIDAD_CHOICES
        return context

class PedidoCreateView(LoginRequiredMixin, CreateView):
    model = Pedido
    form_class = PedidoForm
    template_name = 'produccion/pedido_form.html'
    success_url = reverse_lazy('pedido_list')
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        form.instance.codigo = f"PED-{timezone.now().strftime('%Y%m%d')}-{Pedido.objects.count() + 1:04d}"
        
        response = super().form_valid(form)
        
        # Registrar operación
        Operacion.objects.create(
            usuario=self.request.user,
            accion='pedido_creado',
            descripcion=f'Creó el pedido {form.instance.codigo} para {form.instance.cliente}'
        )
        
        messages.success(self.request, f'Pedido {form.instance.codigo} creado exitosamente.')
        return response

class PedidoUpdateView(LoginRequiredMixin, UpdateView):
    model = Pedido
    form_class = PedidoForm
    template_name = 'produccion/pedido_form.html'
    success_url = reverse_lazy('pedido_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        Operacion.objects.create(
            usuario=self.request.user,
            accion='pedido_actualizado',
            descripcion=f'Actualizó el pedido {form.instance.codigo}'
        )
        
        messages.success(self.request, f'Pedido {form.instance.codigo} actualizado exitosamente.')
        return response

class PedidoDetailView(LoginRequiredMixin, DetailView):
    model = Pedido
    template_name = 'produccion/pedido_detail.html'
    context_object_name = 'pedido'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ordenes'] = self.object.ordenes_produccion.all()
        return context

@login_required
def cambiar_estado_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Pedido.ESTADO_CHOICES):
            estado_anterior = pedido.get_estado_display()
            pedido.estado = nuevo_estado
            pedido.save()
            
            Operacion.objects.create(
                usuario=request.user,
                accion='cambio_estado_pedido',
                descripcion=f'Cambió el estado del pedido {pedido.codigo} de {estado_anterior} a {pedido.get_estado_display()}'
            )
            
            messages.success(request, f'Estado del pedido {pedido.codigo} actualizado a {pedido.get_estado_display()}.')
    
    return redirect('pedido_detail', pk=pk)

# ============ ÓRDENES DE PRODUCCIÓN ============ #
class OrdenProduccionListView(LoginRequiredMixin, ListView):
    model = OrdenProduccion
    template_name = 'produccion/ordenproduccion_list.html'
    context_object_name = 'ordenes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = OrdenProduccion.objects.all().select_related('pedido', 'metodo', 'supervisor')
        
        estado = self.request.GET.get('estado')
        supervisor = self.request.GET.get('supervisor')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if estado:
            queryset = queryset.filter(estado=estado)
        if supervisor:
            queryset = queryset.filter(supervisor__username__icontains=supervisor)
        if fecha_desde:
            queryset = queryset.filter(fecha_programada__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_programada__lte=fecha_hasta)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = OrdenProduccion.ESTADO_CHOICES
        context['supervisores'] = User.objects.filter(groups__name='Supervisores')
        return context

@login_required
def crear_orden_produccion(request, pedido_id=None):
    pedido = None
    if pedido_id:
        pedido = get_object_or_404(Pedido, pk=pedido_id)
    
    if request.method == 'POST':
        form = OrdenProduccionForm(request.POST)
        if form.is_valid():
            orden = form.save(commit=False)
            if pedido:
                orden.pedido = pedido
            
            orden.save()
            form.save_m2m()  # Guardar relación muchos-a-muchos (equipo)
            
            # Asignar estado inicial de trazabilidad
            if not orden.estado_trazabilidad:
                estado_inicial = EstadoTrazabilidad.objects.filter(orden=1).first()
                if estado_inicial:
                    orden.estado_trazabilidad = estado_inicial
                    orden.save()
            
            Operacion.objects.create(
                usuario=request.user,
                accion='orden_creada',
                descripcion=f'Creó la orden de producción {orden.codigo} con lote {orden.codigo_lote}'
            )
            
            messages.success(request, f'Orden de producción {orden.codigo} creada exitosamente. Lote: {orden.codigo_lote}')
            return redirect('ordenproduccion_detail', pk=orden.pk)
    else:
        initial = {}
        if pedido:
            initial = {
                'pedido': pedido,
                'cantidad_a_producir': pedido.cantidad
            }
        form = OrdenProduccionForm(initial=initial)
    
    return render(request, 'produccion/ordenproduccion_form.html', {
        'form': form,
        'pedido': pedido
    })

@login_required
def orden_produccion_detail(request, pk):
    """Vista para ver el detalle de una orden de producción (lote)"""
    orden = get_object_or_404(OrdenProduccion.objects.select_related(
        'pedido', 'metodo', 'supervisor', 'estado_trazabilidad', 'revisado_por'
    ), pk=pk)
    
    # Formulario para actualizar avance
    avance_form = AvanceProduccionForm()
    
    # Obtener el equipo asignado
    equipo = orden.equipo.all()
    
    # Obtener trazabilidad (operaciones relacionadas)
    operaciones = Operacion.objects.filter(referencia=orden.codigo_lote).order_by('-fecha')[:10]
    
    # Obtener controles de calidad relacionados
    controles_calidad = ControlCalidad.objects.filter(orden_produccion=orden).order_by('-fecha')
    
    # Obtener todos los estados de trazabilidad
    estados_trazabilidad = EstadoTrazabilidad.objects.all().order_by('orden')
    
    context = {
        'orden': orden,
        'avance_form': avance_form,
        'equipo': equipo,
        'estados': OrdenProduccion.ESTADO_CHOICES,
        'operaciones': operaciones,
        'controles_calidad': controles_calidad,
        'estados_trazabilidad': estados_trazabilidad,
    }
    
    return render(request, 'produccion/ordenproduccion_detail.html', context)

@login_required
def actualizar_avance(request, pk):
    orden = get_object_or_404(OrdenProduccion, pk=pk)
    
    if request.method == 'POST':
        form = AvanceProduccionForm(request.POST)
        if form.is_valid():
            cantidad_producida = form.cleaned_data['cantidad_producida']
            observaciones = form.cleaned_data['observaciones']
            
            # Actualizar cantidad producida
            orden.cantidad_producida += cantidad_producida
            orden.actualizar_progreso()
            
            # Si se completó la orden
            if orden.cantidad_producida >= orden.cantidad_a_producir:
                orden.estado = 'completada'
                orden.fecha_fin = timezone.now()
                orden.fecha_fin_produccion = timezone.now()
                orden.progreso = 100
                
                # Registrar en trazabilidad
                orden.registrar_trazabilidad("Producción completada", observaciones, request.user)
            
            orden.save()
            
            # Registrar operación
            Operacion.objects.create(
                usuario=request.user,
                accion='avance_produccion',
                descripcion=f'Registró avance en orden {orden.codigo} (Lote {orden.codigo_lote}): {cantidad_producida} unidades producidas. {observaciones}'
            )
            
            messages.success(request, f'Avance registrado en orden {orden.codigo} (Lote {orden.codigo_lote}).')
            return redirect('ordenproduccion_detail', pk=orden.pk)
    
    return redirect('ordenproduccion_detail', pk=orden.pk)

@login_required
def cambiar_estado_orden(request, pk):
    orden = get_object_or_404(OrdenProduccion, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(OrdenProduccion.ESTADO_CHOICES):
            
            # Si se inicia la orden
            if nuevo_estado == 'en_proceso' and orden.estado != 'en_proceso':
                orden.fecha_inicio = timezone.now()
                orden.fecha_inicio_produccion = timezone.now()
                orden.registrar_trazabilidad("Producción iniciada", "", request.user)
            
            # Si se completa la orden
            if nuevo_estado == 'completada' and orden.estado != 'completada':
                orden.fecha_fin = timezone.now()
                orden.fecha_fin_produccion = timezone.now()
                orden.progreso = 100
                orden.cantidad_producida = orden.cantidad_a_producir
            
            estado_anterior = orden.get_estado_display()
            orden.estado = nuevo_estado
            orden.save()
            
            Operacion.objects.create(
                usuario=request.user,
                accion='cambio_estado_orden',
                descripcion=f'Cambió el estado de la orden {orden.codigo} (Lote {orden.codigo_lote}) de {estado_anterior} a {orden.get_estado_display()}'
            )
            
            messages.success(request, f'Estado de la orden {orden.codigo} (Lote {orden.codigo_lote}) actualizado.')
    
    return redirect('ordenproduccion_detail', pk=pk)

# ============ TRAZABILIDAD Y CONTROL DE LOTE ============ #
@login_required
def actualizar_estado_trazabilidad(request, pk):
    """Actualizar el estado de trazabilidad de un lote"""
    orden = get_object_or_404(OrdenProduccion, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado_id = request.POST.get('estado_trazabilidad')
        observaciones = request.POST.get('observaciones', '')
        
        if nuevo_estado_id:
            estado = get_object_or_404(EstadoTrazabilidad, id=nuevo_estado_id)
            orden.estado_trazabilidad = estado
            
            # Registrar en trazabilidad
            orden.registrar_trazabilidad(
                f"Cambio a estado: {estado.nombre}",
                observaciones,
                request.user
            )
            
            messages.success(request, f'Estado del lote actualizado a: {estado.nombre}')
        
        return redirect('ordenproduccion_detail', pk=orden.pk)
    
    # GET: Mostrar formulario
    estados = EstadoTrazabilidad.objects.all()
    
    return render(request, 'produccion/actualizar_estado_trazabilidad.html', {
        'orden': orden,
        'estados': estados,
    })

@login_required
def control_calidad_lote(request, pk):
    """Vista específica para control de calidad de un lote"""
    orden = get_object_or_404(OrdenProduccion, pk=pk)
    
    if request.method == 'POST':
        resultado = request.POST.get('resultado')
        cantidad_rechazada = request.POST.get('cantidad_rechazada', 0)
        observaciones = request.POST.get('observaciones', '')
        
        try:
            cantidad_rechazada = int(cantidad_rechazada)
            
            if resultado == 'aprobado':
                orden.aprobar_control_calidad(request.user)
                messages.success(request, f'Lote {orden.codigo_lote} aprobado.')
            elif resultado in ['rechazado', 'parcial']:
                orden.rechazar_control_calidad(
                    cantidad_rechazada,
                    observaciones,
                    request.user
                )
                if cantidad_rechazada == 0:
                    messages.success(request, f'Lote {orden.codigo_lote} no tuvo rechazos.')
                elif cantidad_rechazada >= orden.cantidad_producida:
                    messages.error(request, f'Lote {orden.codigo_lote} rechazado completamente.')
                else:
                    messages.warning(request, f'Lote {orden.codigo_lote} rechazado parcialmente: {cantidad_rechazada} unidades.')
            
            return redirect('ordenproduccion_detail', pk=orden.pk)
            
        except ValueError:
            messages.error(request, 'Cantidad rechazada inválida.')
    
    return render(request, 'produccion/control_calidad_lote.html', {
        'orden': orden,
    })

@login_required
def marcar_como_almacenado(request, pk):
    """Marcar un lote como almacenado"""
    orden = get_object_or_404(OrdenProduccion, pk=pk)
    
    if request.method == 'POST':
        orden.marcar_como_almacenado()
        messages.success(request, f'Lote {orden.codigo_lote} marcado como almacenado.')
        return redirect('ordenproduccion_detail', pk=orden.pk)
    
    return render(request, 'produccion/marcar_almacenado.html', {'orden': orden})

@login_required
def marcar_como_despachado(request, pk):
    """Marcar un lote como despachado"""
    orden = get_object_or_404(OrdenProduccion, pk=pk)
    
    if request.method == 'POST':
        orden.marcar_como_despachado()
        messages.success(request, f'Lote {orden.codigo_lote} marcado como despachado.')
        return redirect('ordenproduccion_detail', pk=orden.pk)
    
    return render(request, 'produccion/marcar_despachado.html', {'orden': orden})

# ============ REPORTES DE LOTES ============ #
@login_required
def reporte_lotes(request):
    """Reporte consolidado de lotes"""
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    resultado = request.GET.get('resultado')
    estado_trazabilidad = request.GET.get('estado_trazabilidad')
    
    lotes = OrdenProduccion.objects.all().select_related(
        'pedido', 'pedido__producto', 'supervisor', 'estado_trazabilidad', 'revisado_por'
    )
    
    if fecha_inicio:
        lotes = lotes.filter(fecha_creacion__date__gte=fecha_inicio)
    if fecha_fin:
        lotes = lotes.filter(fecha_creacion__date__lte=fecha_fin)
    if resultado:
        lotes = lotes.filter(resultado_control_calidad=resultado)
    if estado_trazabilidad:
        lotes = lotes.filter(estado_trazabilidad_id=estado_trazabilidad)
    
    # Estadísticas
    total_lotes = lotes.count()
    aprobados = lotes.filter(resultado_control_calidad='aprobado').count()
    rechazados = lotes.filter(resultado_control_calidad='rechazado').count()
    pendientes = lotes.filter(resultado_control_calidad='pendiente').count()
    
    # Eficiencia por producto
    eficiencia_producto = lotes.values(
        'pedido__producto__nombre'
    ).annotate(
        total=Count('id'),
        aprobados=Count('id', filter=Q(resultado_control_calidad='aprobado')),
        tasa_aprobacion=100.0 * Count('id', filter=Q(resultado_control_calidad='aprobado')) / Count('id')
    ).order_by('-tasa_aprobacion')
    
    # Lotes por estado de trazabilidad
    lotes_por_estado = lotes.values('estado_trazabilidad__nombre').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')
    
    # Obtener todos los estados de trazabilidad para el filtro
    estados = EstadoTrazabilidad.objects.all()
    
    context = {
        'lotes': lotes,
        'total_lotes': total_lotes,
        'aprobados': aprobados,
        'rechazados': rechazados,
        'pendientes': pendientes,
        'eficiencia_producto': eficiencia_producto,
        'lotes_por_estado': lotes_por_estado,
        'estados': estados,
    }
    
    return render(request, 'produccion/reporte_lotes.html', context)

# ============ PLANIFICACIÓN ============ #
class PlanificacionListView(LoginRequiredMixin, ListView):
    model = Planificacion
    template_name = 'produccion/planificacion_list.html'
    context_object_name = 'planificaciones'
    
    def get_queryset(self):
        queryset = Planificacion.objects.all().prefetch_related('responsables', 'ordenes')
        
        tipo = self.request.GET.get('tipo')
        activa = self.request.GET.get('activa')
        completada = self.request.GET.get('completada')
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if activa == 'true':
            queryset = queryset.filter(activa=True)
        elif activa == 'false':
            queryset = queryset.filter(activa=False)
        if completada == 'true':
            queryset = queryset.filter(completada=True)
        elif completada == 'false':
            queryset = queryset.filter(completada=False)
        
        return queryset

@login_required
def vista_calendario(request):
    # Vista de calendario para planificación semanal/mensual
    hoy = timezone.now().date()
    semana_actual = hoy - timedelta(days=hoy.weekday())  # Lunes de esta semana
    
    # Obtener planificaciones para la semana
    planificaciones_semana = Planificacion.objects.filter(
        fecha_inicio__lte=semana_actual + timedelta(days=6),
        fecha_fin__gte=semana_actual,
        activa=True
    ).prefetch_related('planificacionorden_set__orden')
    
    # Crear estructura para el calendario
    dias_semana = []
    for i in range(7):
        dia = semana_actual + timedelta(days=i)
        ordenes_dia = []
        
        for planificacion in planificaciones_semana:
            ordenes_plan = planificacion.planificacionorden_set.filter(
                fecha_asignada=dia
            )
            for po in ordenes_plan:
                ordenes_dia.append({
                    'orden': po.orden,
                    'turno': po.get_turno_display(),
                    'prioridad': po.prioridad,
                    'planificacion': planificacion
                })
        
        dias_semana.append({
            'fecha': dia,
            'nombre': dia.strftime('%A'),
            'ordenes': ordenes_dia
        })
    
    context = {
        'semana_actual': semana_actual,
        'dias_semana': dias_semana,
        'hoy': hoy,
    }
    return render(request, 'produccion/calendario.html', context)

@login_required
def generar_planificacion_semanal(request):
    if request.method == 'POST':
        # Generar planificación semanal automática
        fecha_inicio = datetime.strptime(request.POST.get('fecha_inicio'), '%Y-%m-%d').date()
        fecha_fin = fecha_inicio + timedelta(days=6)
        
        # Buscar pedidos pendientes
        pedidos_pendientes = Pedido.objects.filter(
            estado__in=['pendiente', 'en_proceso'],
            fecha_entrega__lte=fecha_fin
        ).order_by('prioridad', 'fecha_entrega')
        
        # Crear planificación
        planificacion = Planificacion.objects.create(
            nombre=f'Planificación Semanal {fecha_inicio} a {fecha_fin}',
            tipo='semanal',
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            creado_por=request.user
        )
        
        # Asignar pedidos a la planificación
        for i, pedido in enumerate(pedidos_pendientes[:40]):  # Máximo 20 pedidos por semana
            # Crear orden de producción si no existe
            orden, created = OrdenProduccion.objects.get_or_create(
                pedido=pedido,
                defaults={
                    'metodo': MetodoProduccion.objects.first(),
                    'fecha_programada': fecha_inicio + timedelta(days=i % 7),
                    'supervisor': request.user,
                    'cantidad_a_producir': pedido.cantidad,
                }
            )
            
            if created:
                orden.save()
            
            # Asignar orden a la planificación
            fecha_asignada = fecha_inicio + timedelta(days=i % 7)
            planificacion.ordenes.add(orden)
            
            # Crear asignación específica
            PlanificacionOrden.objects.create(
                planificacion=planificacion,
                orden=orden,
                fecha_asignada=fecha_asignada,
                turno='manana' if i % 2 == 0 else 'tarde',
                prioridad=pedido.prioridad
            )
        
        Operacion.objects.create(
            usuario=request.user,
            accion='planificacion_generada',
            descripcion=f'Generó planificación semanal {planificacion.nombre}'
        )
        
        messages.success(request, f'Planificación semanal {planificacion.nombre} generada exitosamente.')
        return redirect('planificacion_detail', pk=planificacion.pk)
    
    return render(request, 'produccion/generar_planificacion.html')

# ============ REPORTES Y ESTADÍSTICAS ============ #
@login_required
def reportes_produccion(request):
    form = FiltroReporteForm(request.GET or None)
    reportes = ReporteProduccion.objects.all()
    
    # Variable para controlar si se debe generar un nuevo reporte
    generar_nuevo = 'generar' in request.GET

    # Obtener parámetros de filtro de la URL
    filtro_tipo = request.GET.get('tipo', '')

    if filtro_tipo:
        reportes = reportes.filter(tipo=filtro_tipo)

    if form.is_valid():
        fecha_desde = form.cleaned_data.get('fecha_desde')
        fecha_hasta = form.cleaned_data.get('fecha_hasta')
        
        if fecha_desde:
            reportes = reportes.filter(periodo_inicio__gte=fecha_desde)
        if fecha_hasta:
            reportes = reportes.filter(periodo_fin__lte=fecha_hasta)
    
    # Si se hizo clic en "Generar Reporte" y hay fechas
        if generar_nuevo and fecha_desde and fecha_hasta:
            return generar_reporte_personalizado(request, fecha_desde, fecha_hasta)
    # Estadísticas para mostrar
    hoy = timezone.now().date()
    mes_actual = hoy.replace(day=1)

    pedidos_mes = Pedido.objects.filter(
        fecha_creacion__gte=mes_actual
    ).aggregate(
        total=Count('id'),
        completados=Count('id', filter=Q(estado='completado')),
        en_proceso=Count('id', filter=Q(estado='en_proceso'))
    )
    
    if pedidos_mes['total'] > 0:
        tasa_completacion = (pedidos_mes['completados'] / pedidos_mes['total']) * 100
    else:
        tasa_completacion = 0
    
    context = {
        'form': form,
        'reportes': reportes,
        'pedidos_mes': pedidos_mes,
        'tasa_completacion': tasa_completacion,
        'hoy': hoy,
    }
    return render(request, 'produccion/reportes.html', context)

def generar_reporte_personalizado(request, fecha_desde, fecha_hasta):
    """Genera un reporte personalizado basado en fechas específicas"""
    # Calcular días entre fechas para determinar tipo
    dias_diferencia = (fecha_hasta - fecha_desde).days + 1
    
    if dias_diferencia == 1:
        tipo = 'diario'
    elif dias_diferencia <= 7:
        tipo = 'semanal'
    elif dias_diferencia <= 31:
        tipo = 'mensual'
    elif dias_diferencia <= 365:
        tipo = 'anual'
    else:
        tipo = 'especial'

    # Obtener pedidos en el rango de fechas
    pedidos = Pedido.objects.filter(fecha_creacion__date__range=[fecha_desde, fecha_hasta])
    
    # Calcular métricas
    total_pedidos = pedidos.count()
    pedidos_completados = pedidos.filter(estado='completado').count()
    pedidos_pendientes = pedidos.filter(estado__in=['pendiente', 'en_proceso']).count()

    # Título personalizado
    if dias_diferencia == 1:
        titulo = f'Reporte Diario - {fecha_desde.strftime("%d/%m/%Y")}'
    elif dias_diferencia <= 7:
        titulo = f'Reporte Semanal - {fecha_desde.strftime("%d/%m")} al {fecha_hasta.strftime("%d/%m/%Y")}'
    elif dias_diferencia <= 31:
        titulo = f'Reporte Mensual - {fecha_desde.strftime("%B %Y")}'
    else:
        titulo = f'Reporte Personalizado - {fecha_desde.strftime("%d/%m/%Y")} al {fecha_hasta.strftime("%d/%m/%Y")}'
    
    # Crear reporte en base de datos
    reporte = ReporteProduccion.objects.create(
        titulo=titulo,
        tipo=tipo,
        periodo_inicio=fecha_desde,
        periodo_fin=fecha_hasta,
        total_pedidos=total_pedidos,
        pedidos_completados=pedidos_completados,
        pedidos_pendientes=pedidos_pendientes,
        generado_por=request.user,
        resumen=f'Reporte {tipo} del período {fecha_desde.strftime("%d/%m/%Y")} al {fecha_hasta.strftime("%d/%m/%Y")}. Total pedidos: {total_pedidos}, Completados: {pedidos_completados}.'
    )
    
    Operacion.objects.create(
        usuario=request.user,
        accion='reporte_generado',
        descripcion=f'Generó reporte {tipo}: {titulo}'
    )
    
    messages.success(request, f'Reporte {tipo} generado exitosamente.')
    return redirect('reportes_produccion')

@login_required
def generar_reporte_rapido(request):
    # Generar reporte rápido del día/semana/mes
    tipo = request.GET.get('tipo', 'diario')
    hoy = timezone.now().date()
    
    if tipo == 'diario':
        titulo = f'Reporte Diario {hoy}'
        periodo_inicio = hoy
        periodo_fin = hoy
        pedidos = Pedido.objects.filter(fecha_creacion__date=hoy)
    elif tipo == 'semanal':
        lunes = hoy - timedelta(days=hoy.weekday())
        domingo = lunes + timedelta(days=6)
        titulo = f'Reporte Semanal {lunes} a {domingo}'
        periodo_inicio = lunes
        periodo_fin = domingo
        pedidos = Pedido.objects.filter(fecha_creacion__date__range=[lunes, domingo])
    elif tipo == 'mensual':
        primer_dia = hoy.replace(day=1)
        ultimo_dia = (primer_dia + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        titulo = f'Reporte Mensual {primer_dia.strftime("%B %Y")}'
        periodo_inicio = primer_dia
        periodo_fin = ultimo_dia
        pedidos = Pedido.objects.filter(fecha_creacion__date__range=[primer_dia, ultimo_dia])
    elif tipo == 'anual':
        primer_dia = hoy.replace(month=1, day=1)  # 1 de enero
        ultimo_dia = hoy.replace(month=12, day=31)  # 31 de diciembre
        titulo = f'Reporte Anual {hoy.year}'
        periodo_inicio = primer_dia
        periodo_fin = ultimo_dia
        pedidos = Pedido.objects.filter(fecha_creacion__date__range=[primer_dia, ultimo_dia])
    
    # Calcular métricas
    total_pedidos = pedidos.count()
    pedidos_completados = pedidos.filter(estado='completado').count()
    pedidos_pendientes = pedidos.filter(estado__in=['pendiente', 'en_proceso']).count()
    
    # Crear reporte en base de datos
    reporte = ReporteProduccion.objects.create(
        titulo=titulo,
        tipo=tipo,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        total_pedidos=total_pedidos,
        pedidos_completados=pedidos_completados,
        pedidos_pendientes=pedidos_pendientes,
        generado_por=request.user,
        resumen=f'Reporte {tipo} generado automáticamente.'
    )
    
    Operacion.objects.create(
        usuario=request.user,
        accion='reporte_generado',
        descripcion=f'Generó reporte {tipo}: {titulo}'
    )
    
    messages.success(request, f'Reporte {tipo} generado exitosamente.')
    return redirect('reportes_produccion')

@login_required
def exportar_reporte_csv(request, pk):
    reporte = get_object_or_404(ReporteProduccion, pk=pk)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_{reporte.periodo_inicio}_{reporte.periodo_fin}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Reporte de Producción', reporte.titulo])
    writer.writerow(['Período', f'{reporte.periodo_inicio} al {reporte.periodo_fin}'])
    writer.writerow(['Tipo', reporte.get_tipo_display()])
    writer.writerow([])
    writer.writerow(['Métrica', 'Valor'])
    writer.writerow(['Total Pedidos', reporte.total_pedidos])
    writer.writerow(['Pedidos Completados', reporte.pedidos_completados])
    writer.writerow(['Pedidos Pendientes', reporte.pedidos_pendientes])
    writer.writerow(['Tasa de Completación', f'{reporte.tasa_completacion():.1f}%'])
    writer.writerow(['Eficiencia', f'{reporte.eficiencia}%'])
    writer.writerow(['Tiempo Promedio', f'{reporte.tiempo_promedio} min'])
    writer.writerow([])
    writer.writerow(['Costos', ''])
    writer.writerow(['Costo Total', f'${reporte.costo_total}'])
    writer.writerow(['Costo Materiales', f'${reporte.costo_materiales}'])
    writer.writerow(['Costo Mano de Obra', f'${reporte.costo_mano_obra}'])
    
    return response


# ============ API/JSON PARA GRÁFICOS ============ #
@login_required
def api_estadisticas(request):
    # Endpoint para datos de gráficos
    hoy = timezone.now().date()
    ultimos_7_dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]
    
    datos_pedidos = []
    datos_ordenes = []
    
    for dia in ultimos_7_dias:
        pedidos_dia = Pedido.objects.filter(fecha_creacion__date=dia).count()
        ordenes_completadas = OrdenProduccion.objects.filter(
            fecha_fin__date=dia,
            estado='completada'
        ).count()
        
        datos_pedidos.append({
            'fecha': dia.strftime('%Y-%m-%d'),
            'dia': dia.strftime('%a'),
            'cantidad': pedidos_dia
        })
        
        datos_ordenes.append({
            'fecha': dia.strftime('%Y-%m-%d'),
            'dia': dia.strftime('%a'),
            'cantidad': ordenes_completadas
        })
    
    # Estadísticas por estado
    pedidos_por_estado = []
    for estado_val, estado_display in Pedido.ESTADO_CHOICES:
        cantidad = Pedido.objects.filter(estado=estado_val).count()
        pedidos_por_estado.append({
            'estado': estado_display,
            'cantidad': cantidad
        })
    
    return JsonResponse({
        'pedidos_por_dia': datos_pedidos,
        'ordenes_por_dia': datos_ordenes,
        'pedidos_por_estado': pedidos_por_estado,
        'total_pedidos': Pedido.objects.count(),
        'pedidos_hoy': Pedido.objects.filter(fecha_creacion__date=hoy).count(),
    })