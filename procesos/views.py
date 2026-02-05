from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg, Sum, F
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json
import csv
from .forms import RegistroTiempoManualForm
 ## views de procesos
from .models import (
    Operacion, Proceso, EtapaProceso, MaterialProceso,
    FlujoTrabajo, ProcesoFlujo, Temporizador,
    ControlCalidad, ControlCalidadDetalle, NoConformidad
)
from .forms import (
    ProcesoForm, EtapaProcesoForm, MaterialProcesoForm,
    FlujoTrabajoForm, ProcesoFlujoForm, TemporizadorForm,
    IniciarTemporizadorForm, ControlCalidadForm,
    ControlCalidadDetalleForm, NoConformidadForm,
    FiltroProcesosForm, FiltroControlCalidadForm,
    AsignarProcesoForm, FiltroTiempoForm
)
from produccion.models import OrdenProduccion

# ============ DASHBOARD Y PÁGINA PRINCIPAL ============ #
@login_required
def dashboard_procesos(request):
    """Dashboard principal de procesos"""
    # Estadísticas generales
    total_procesos = Proceso.objects.count()
    procesos_activos = Proceso.objects.filter(activo=True).count()
    procesos_en_ejecucion = Proceso.objects.filter(estado='en_proceso').count()
    procesos_pendientes = Proceso.objects.filter(estado='pendiente').count()
    
    # Temporizadores activos
    temporizadores_activos = Temporizador.objects.filter(estado='activo').count()
    temporizadores_pausados = Temporizador.objects.filter(estado='pausado').count()
    
    # Control de calidad reciente
    controles_hoy = ControlCalidad.objects.filter(fecha__date=timezone.now().date()).count()
    controles_rechazados = ControlCalidad.objects.filter(resultado='rechazado', 
                                                        fecha__date=timezone.now().date()).count()
    
    # No conformidades abiertas
    no_conformidades_abiertas = NoConformidad.objects.exclude(estado='cerrada').count()
    no_conformidades_criticas = NoConformidad.objects.filter(prioridad=4, 
                                                            estado__in=['reportada', 'analisis']).count()
    
    # Operaciones recientes
    operaciones_recientes = Operacion.objects.all().order_by('-fecha')[:10]
    
    # Procesos en ejecución con detalles
    procesos_ejecucion = Proceso.objects.filter(estado='en_proceso').select_related('creado_por')[:5]
    
    # Gráfico de eficiencia por tipo de proceso
    eficiencia_por_tipo = Proceso.objects.values('tipo').annotate(
        promedio=Avg('eficiencia'),
        cantidad=Count('id')
    ).order_by('-promedio')
    
    context = {
        'total_procesos': total_procesos,
        'procesos_activos': procesos_activos,
        'procesos_en_ejecucion': procesos_en_ejecucion,
        'procesos_pendientes': procesos_pendientes,
        'temporizadores_activos': temporizadores_activos,
        'temporizadores_pausados': temporizadores_pausados,
        'controles_hoy': controles_hoy,
        'controles_rechazados': controles_rechazados,
        'no_conformidades_abiertas': no_conformidades_abiertas,
        'no_conformidades_criticas': no_conformidades_criticas,
        'operaciones_recientes': operaciones_recientes,
        'procesos_ejecucion': procesos_ejecucion,
        'eficiencia_por_tipo': eficiencia_por_tipo,
    }
    
    return render(request, 'procesos/dashboard.html', context)

# ============ GESTIÓN DE PROCESOS ============ #
@login_required
def lista_procesos(request):
    """Lista todos los procesos con filtros"""
    procesos = Proceso.objects.all().order_by('orden', 'nombre')
    
    form = FiltroProcesosForm(request.GET or None)
    
    if form.is_valid():
        tipo = form.cleaned_data.get('tipo')
        estado = form.cleaned_data.get('estado')
        activo = form.cleaned_data.get('activo')
        
        if tipo:
            procesos = procesos.filter(tipo=tipo)
        if estado:
            procesos = procesos.filter(estado=estado)
        if activo == 'true':
            procesos = procesos.filter(activo=True)
        elif activo == 'false':
            procesos = procesos.filter(activo=False)
    
    # Paginación
    paginator = Paginator(procesos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_procesos': procesos.count(),
    }
    
    return render(request, 'procesos/lista_procesos.html', context)

@login_required
@permission_required('procesos.add_proceso', raise_exception=True)
def crear_proceso(request):
    """Crear un nuevo proceso"""
    if request.method == 'POST':
        form = ProcesoForm(request.POST)
        if form.is_valid():
            proceso = form.save(commit=False)
            proceso.creado_por = request.user
            proceso.save()
            
            # Registrar operación
            Operacion.objects.create(
                usuario=request.user,
                accion='proceso_iniciado',
                descripcion=f"Proceso '{proceso.nombre}' creado",
                referencia=f"PROC-{proceso.id}"
            )
            
            messages.success(request, f'Proceso "{proceso.nombre}" creado exitosamente.')
            return redirect('detalle_proceso', pk=proceso.pk)
    else:
        form = ProcesoForm()
    
    return render(request, 'procesos/proceso_form.html', {'form': form})

@login_required
def detalle_proceso(request, pk):
    """Detalle de un proceso específico"""
    proceso = get_object_or_404(Proceso.objects.prefetch_related('etapas', 'materialproceso_set'), pk=pk)
    etapas = proceso.etapas.all().order_by('orden')
    materiales = proceso.materialproceso_set.all()
    
    # Temporizadores activos para este proceso
    temporizadores = Temporizador.objects.filter(proceso=proceso, estado__in=['activo', 'pausado'])
    
    # Controles de calidad recientes
    controles = ControlCalidad.objects.filter(proceso=proceso).order_by('-fecha')[:5]
    
    # Estadísticas de ejecución
    veces_ejecutado = proceso.veces_ejecutado
    eficiencia = proceso.eficiencia
    
    context = {
        'proceso': proceso,
        'etapas': etapas,
        'materiales': materiales,
        'temporizadores': temporizadores,
        'controles': controles,
        'veces_ejecutado': veces_ejecutado,
        'eficiencia': eficiencia,
    }
    
    return render(request, 'procesos/detalle_proceso.html', context)

@login_required
@permission_required('procesos.change_proceso', raise_exception=True)
def editar_proceso(request, pk):
    """Editar un proceso existente"""
    proceso = get_object_or_404(Proceso, pk=pk)
    
    if request.method == 'POST':
        form = ProcesoForm(request.POST, instance=proceso)
        if form.is_valid():
            proceso = form.save()
            messages.success(request, f'Proceso "{proceso.nombre}" actualizado exitosamente.')
            return redirect('detalle_proceso', pk=proceso.pk)
    else:
        form = ProcesoForm(instance=proceso)
    
    return render(request, 'procesos/proceso_form.html', {'form': form, 'proceso': proceso})

@login_required
@permission_required('procesos.delete_proceso', raise_exception=True)
def eliminar_proceso(request, pk):
    """Eliminar un proceso (desactivar)"""
    proceso = get_object_or_404(Proceso, pk=pk)
    
    if request.method == 'POST':
        proceso.activo = False
        proceso.save()
        
        messages.success(request, f'Proceso "{proceso.nombre}" desactivado.')
        return redirect('lista_procesos')
    
    return render(request, 'procesos/eliminar_proceso.html', {'proceso': proceso})

@login_required
def iniciar_proceso(request, pk):
    """Iniciar la ejecución de un proceso"""
    proceso = get_object_or_404(Proceso, pk=pk)
    
    if request.method == 'POST':
        proceso.estado = 'en_proceso'
        proceso.save()
        
        # Crear temporizador automático
        temporizador = Temporizador.objects.create(
            proceso=proceso,
            tiempo_objetivo=proceso.tiempo_estimado_promedio(),
            operario=request.user,
            creado_por=request.user
        )
        temporizador.iniciar()
        
        # Registrar operación
        Operacion.objects.create(
            usuario=request.user,
            accion='proceso_iniciado',
            descripcion=f"Proceso '{proceso.nombre}' iniciado",
            referencia=f"PROC-{proceso.id}",
            tiempo_empleado=timezone.timedelta(0)
        )
        
        messages.success(request, f'Proceso "{proceso.nombre}" iniciado.')
        return redirect('detalle_proceso', pk=proceso.pk)
    
    return render(request, 'procesos/iniciar_proceso.html', {'proceso': proceso})

@login_required
def finalizar_proceso(request, pk):
    """Finalizar la ejecución de un proceso"""
    proceso = get_object_or_404(Proceso, pk=pk)
    
    if request.method == 'POST':
        # Detener temporizadores activos
        temporizadores = Temporizador.objects.filter(
            proceso=proceso,
            estado__in=['activo', 'pausado']
        )
        
        for temp in temporizadores:
            temp.detener()
        
        # Actualizar proceso
        proceso.estado = 'completado'
        proceso.save()
        
        # Registrar operación
        Operacion.objects.create(
            usuario=request.user,
            accion='proceso_finalizado',
            descripcion=f"Proceso '{proceso.nombre}' finalizado",
            referencia=f"PROC-{proceso.id}"
        )
        
        messages.success(request, f'Proceso "{proceso.nombre}" finalizado.')
        return redirect('detalle_proceso', pk=proceso.pk)
    
    return render(request, 'procesos/finalizar_proceso.html', {'proceso': proceso})

# ============ GESTIÓN DE ETAPAS ============ #
@login_required
def crear_etapa(request, proceso_id):
    """Crear una etapa para un proceso"""
    proceso = get_object_or_404(Proceso, pk=proceso_id)
    
    if request.method == 'POST':
        form = EtapaProcesoForm(request.POST)
        if form.is_valid():
            etapa = form.save(commit=False)
            etapa.proceso = proceso
            etapa.save()
            
            messages.success(request, f'Etapa "{etapa.nombre}" creada.')
            return redirect('detalle_proceso', pk=proceso.pk)
    else:
        form = EtapaProcesoForm(initial={'proceso': proceso})
    
    return render(request, 'procesos/etapa_form.html', {'form': form, 'proceso': proceso})

@login_required
def iniciar_etapa(request, etapa_id):
    """Iniciar una etapa específica"""
    etapa = get_object_or_404(EtapaProceso, pk=etapa_id)
    
    if not etapa.completada:
        etapa.iniciar_etapa()
        messages.success(request, f'Etapa "{etapa.nombre}" iniciada.')
    else:
        messages.warning(request, f'Etapa "{etapa.nombre}" ya está completada.')
    
    return redirect('detalle_proceso', pk=etapa.proceso.pk)

@login_required
def finalizar_etapa(request, etapa_id):
    """Finalizar una etapa específica"""
    etapa = get_object_or_404(EtapaProceso, pk=etapa_id)
    
    if not etapa.completada:
        etapa.finalizar_etapa()
        messages.success(request, f'Etapa "{etapa.nombre}" finalizada.')
        
        # Registrar operación
        Operacion.objects.create(
            usuario=request.user,
            accion='proceso_finalizado',
            descripcion=f"Etapa '{etapa.nombre}' finalizada. Tiempo: {etapa.tiempo_real}",
            referencia=f"ETAPA-{etapa.id}",
            tiempo_empleado=etapa.tiempo_real
        )
    else:
        messages.warning(request, f'Etapa "{etapa.nombre}" ya está completada.')
    
    return redirect('detalle_proceso', pk=etapa.proceso.pk)

# ============ TEMPORIZADOR EN TIEMPO REAL ============ #
@login_required
def panel_temporizador(request):
    """Panel principal del temporizador"""
    # Temporizadores activos del usuario
    temporizadores_usuario = Temporizador.objects.filter(
        operario=request.user,
        estado__in=['activo', 'pausado']
    ).order_by('-fecha_creacion')
    
    # Procesos disponibles para iniciar
    procesos_disponibles = Proceso.objects.filter(
        activo=True,
        estado='pendiente'
    )[:10]
    
    form = IniciarTemporizadorForm()
    
    context = {
        'temporizadores_usuario': temporizadores_usuario,
        'procesos_disponibles': procesos_disponibles,
        'form': form,
    }
    
    return render(request, 'procesos/panel_temporizador.html', context)

@login_required
def iniciar_temporizador(request):
    """Iniciar un nuevo temporizador"""
    if request.method == 'POST':
        form = IniciarTemporizadorForm(request.POST)
        if form.is_valid():
            proceso = form.cleaned_data['proceso']
            tiempo_objetivo = form.cleaned_data['tiempo_objetivo']
            referencia = form.cleaned_data.get('referencia', '')
            
            # Crear temporizador
            temporizador = Temporizador.objects.create(
                proceso=proceso,
                tiempo_objetivo=tiempo_objetivo,
                operario=request.user,
                creado_por=request.user
            )
            
            # Iniciar temporizador
            temporizador.iniciar()
            
            # Actualizar estado del proceso
            proceso.estado = 'en_proceso'
            proceso.save()
            
            messages.success(request, f'Temporizador iniciado para "{proceso.nombre}"')
            return redirect('panel_temporizador')
    else:
        form = IniciarTemporizadorForm()
    
    return render(request, 'procesos/iniciar_temporizador.html', {'form': form})

@login_required
def pausar_temporizador(request, temporizador_id):
    """Pausar un temporizador activo"""
    temporizador = get_object_or_404(Temporizador, pk=temporizador_id, operario=request.user)
    
    if temporizador.estado == 'activo':
        temporizador.pausar()
        messages.success(request, 'Temporizador pausado.')
    
    return redirect('panel_temporizador')

@login_required
def reanudar_temporizador(request, temporizador_id):
    """Reanudar un temporizador pausado"""
    temporizador = get_object_or_404(Temporizador, pk=temporizador_id, operario=request.user)
    
    if temporizador.estado == 'pausado':
        temporizador.reanudar()
        messages.success(request, 'Temporizador reanudado.')
    
    return redirect('panel_temporizador')

@login_required
def detener_temporizador(request, temporizador_id):
    """Detener y finalizar un temporizador"""
    temporizador = get_object_or_404(Temporizador, pk=temporizador_id, operario=request.user)
    
    if temporizador.estado in ['activo', 'pausado']:
        temporizador.detener()
        
        # Si es un proceso, actualizar estado
        if temporizador.proceso:
            temporizador.proceso.estado = 'completado'
            temporizador.proceso.save()
        
        messages.success(request, 'Temporizador detenido y proceso finalizado.')
    
    return redirect('panel_temporizador')

@login_required
def api_temporizador_estado(request, temporizador_id):
    """API para obtener estado del temporizador en tiempo real"""
    temporizador = get_object_or_404(Temporizador, pk=temporizador_id)
    
    data = {
        'id': temporizador.id,
        'estado': temporizador.estado,
        'tiempo_transcurrido': str(temporizador.tiempo_transcurrido),
        'tiempo_restante': str(temporizador.tiempo_restante()),
        'porcentaje_completado': temporizador.porcentaje_completado(),
        'nombre_proceso': temporizador.proceso.nombre if temporizador.proceso else 'Sin proceso',
    }
    
    return JsonResponse(data)

# ============ CONTROL DE CALIDAD ============ #
@login_required
def lista_controles_calidad(request):
    """Lista de controles de calidad"""
    controles = ControlCalidad.objects.all().order_by('-fecha')
    
    form = FiltroControlCalidadForm(request.GET or None)
    
    if form.is_valid():
        resultado = form.cleaned_data.get('resultado')
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        inspector = form.cleaned_data.get('inspector')
        
        if resultado:
            controles = controles.filter(resultado=resultado)
        if fecha_inicio:
            controles = controles.filter(fecha__date__gte=fecha_inicio)
        if fecha_fin:
            controles = controles.filter(fecha__date__lte=fecha_fin)
        if inspector:
            controles = controles.filter(inspector=inspector)
    
    # Estadísticas
    total_controles = controles.count()
    aprobados = controles.filter(resultado='aprobado').count()
    rechazados = controles.filter(resultado='rechazado').count()
    
    # Paginación
    paginator = Paginator(controles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_controles': total_controles,
        'aprobados': aprobados,
        'rechazados': rechazados,
    }
    
    return render(request, 'procesos/lista_controles_calidad.html', context)

@login_required
def crear_control_calidad(request):
    """Crear un nuevo control de calidad"""
    if request.method == 'POST':
        form = ControlCalidadForm(request.POST)
        if form.is_valid():
            control = form.save(commit=False)
            control.inspector = request.user
            control.save()
            
            # Registrar operación - CORREGIDO
            Operacion.objects.create(
                usuario=request.user,
                accion='control_calidad',
                descripcion=f"Control de calidad creado para proceso: {control.proceso}",
                referencia=f"CC-{control.id}"
            )
            
            messages.success(request, 'Control de calidad creado exitosamente.')
            
            # Redirigir a agregar detalles si hay defectos
            if control.resultado in ['rechazado', 'reparacion']:
                return redirect('agregar_detalle_control', control_id=control.pk)
            else:
                return redirect('detalle_control_calidad', pk=control.pk)
    else:
        form = ControlCalidadForm()
    
    return render(request, 'procesos/control_calidad_form.html', {'form': form})
@login_required
def detalle_control_calidad(request, pk):
    """Detalle de un control de calidad"""
    control = get_object_or_404(ControlCalidad.objects.prefetch_related('detalles'), pk=pk)
    detalles = control.detalles.all()
    
    context = {
        'control': control,
        'detalles': detalles,
    }
    
    return render(request, 'procesos/detalle_control_calidad.html', context)

@login_required
def agregar_detalle_control(request, control_id):
    """Agregar detalles a un control de calidad"""
    control = get_object_or_404(ControlCalidad, pk=control_id)
    
    if request.method == 'POST':
        form = ControlCalidadDetalleForm(request.POST, request.FILES)
        if form.is_valid():
            detalle = form.save(commit=False)
            detalle.control_calidad = control
            
            # Si hay foto, procesarla
            if 'foto' in request.FILES:
                detalle.foto = request.FILES['foto']
            
            detalle.save()
            
            # Actualizar estadísticas del control
            control.cantidad_defectos += 1
            control.puntuacion_total += detalle.severidad
            control.save()
            
            messages.success(request, 'Detalle de defecto agregado.')
            
            # Preguntar si quiere agregar más
            if 'agregar_otro' in request.POST:
                return redirect('agregar_detalle_control', control_id=control.pk)
            else:
                return redirect('detalle_control_calidad', pk=control.pk)
    else:
        form = ControlCalidadDetalleForm()
    
    context = {
        'control': control,
        'form': form,
    }
    
    return render(request, 'procesos/agregar_detalle_control.html', context)

@login_required
@login_required
def generar_no_conformidad(request, control_id):
    """Generar una no conformidad a partir de un control de calidad"""
    control = get_object_or_404(ControlCalidad, pk=control_id)
    
    if request.method == 'POST':
        form = NoConformidadForm(request.POST)
        if form.is_valid():
            no_conformidad = form.save(commit=False)
            no_conformidad.control_calidad = control
            
            # NO intentes asignar proceso porque es un string, no un objeto
            # no_conformidad.proceso = control.proceso  # ¡ELIMINA ESTA LÍNEA!
            
            no_conformidad.reportado_por = request.user
            no_conformidad.save()
            
            # Actualizar estado del control
            control.resultado = 'rechazado'
            control.save()
            
            messages.success(request, f'No conformidad {no_conformidad.codigo} generada.')
            return redirect('detalle_no_conformidad', pk=no_conformidad.pk)
    else:
        # Pre-cargar datos del control - CORREGIDO
        initial_data = {
            'descripcion': f"No conformidad detectada en control de calidad #{control.id} para proceso: {control.proceso}",
        }
        form = NoConformidadForm(initial=initial_data)
    
    context = {
        'control': control,
        'form': form,
    }
    
    return render(request, 'procesos/generar_no_conformidad.html', context)
# ============ NO CONFORMIDADES ============ #
@login_required
def lista_no_conformidades(request):
    """Lista de no conformidades"""
    no_conformidades = NoConformidad.objects.all().order_by('-fecha_reporte')
    
    # Filtros
    estado = request.GET.get('estado')
    prioridad = request.GET.get('prioridad')
    
    if estado:
        no_conformidades = no_conformidades.filter(estado=estado)
    if prioridad:
        no_conformidades = no_conformidades.filter(prioridad=prioridad)
    
    # Estadísticas
    total_nc = no_conformidades.count()
    abiertas = no_conformidades.exclude(estado='cerrada').count()
    criticas = no_conformidades.filter(prioridad=4, estado__in=['reportada', 'analisis']).count()
    
    # Calcular días promedio de resolución
    cerradas = no_conformidades.filter(estado='cerrada')
    dias_promedio = 0
    if cerradas.exists():
        total_dias = sum(nc.dias_abierta() for nc in cerradas)
        dias_promedio = total_dias / cerradas.count()
    
    # Paginación
    paginator = Paginator(no_conformidades, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_nc': total_nc,
        'abiertas': abiertas,
        'criticas': criticas,
        'dias_promedio': round(dias_promedio, 1),
    }
    
    return render(request, 'procesos/lista_no_conformidades.html', context)

@login_required
def detalle_no_conformidad(request, pk):
    """Detalle de una no conformidad"""
    no_conformidad = get_object_or_404(NoConformidad, pk=pk)
    
    context = {
        'no_conformidad': no_conformidad,
    }
    
    return render(request, 'procesos/detalle_no_conformidad.html', context)

@login_required
def cerrar_no_conformidad(request, pk):
    """Cerrar una no conformidad"""
    no_conformidad = get_object_or_404(NoConformidad, pk=pk)
    
    if request.method == 'POST':
        comentarios = request.POST.get('comentarios', '')
        no_conformidad.cerrar(request.user, comentarios)
        
        messages.success(request, f'No conformidad {no_conformidad.codigo} cerrada.')
        return redirect('detalle_no_conformidad', pk=no_conformidad.pk)
    
    return render(request, 'procesos/cerrar_no_conformidad.html', {'no_conformidad': no_conformidad})

# ============ FLUJOS DE TRABAJO ============ #
@login_required
def lista_flujos_trabajo(request):
    """Lista de flujos de trabajo"""
    flujos = FlujoTrabajo.objects.all().order_by('-fecha_creacion')
    
    context = {
        'flujos': flujos,
    }
    
    return render(request, 'procesos/lista_flujos_trabajo.html', context)

@login_required
def detalle_flujo_trabajo(request, pk):
    """Detalle de un flujo de trabajo"""
    flujo = get_object_or_404(FlujoTrabajo.objects.prefetch_related('procesoflujo_set__proceso'), pk=pk)
    procesos_flujo = flujo.procesoflujo_set.all().order_by('orden')
    
    context = {
        'flujo': flujo,
        'procesos_flujo': procesos_flujo,
    }
    
    return render(request, 'procesos/detalle_flujo_trabajo.html', context)

@login_required
@permission_required('procesos.add_flujotrabajo', raise_exception=True)
def crear_flujo_trabajo(request):
    """Crear un nuevo flujo de trabajo"""
    if request.method == 'POST':
        form = FlujoTrabajoForm(request.POST)
        if form.is_valid():
            flujo = form.save(commit=False)
            flujo.creado_por = request.user
            flujo.save()
            
            messages.success(request, f'Flujo de trabajo "{flujo.nombre}" creado.')
            return redirect('detalle_flujo_trabajo', pk=flujo.pk)
    else:
        form = FlujoTrabajoForm()
    
    return render(request, 'procesos/flujo_trabajo_form.html', {'form': form})

@login_required
def agregar_proceso_flujo(request, flujo_id):
    """Agregar un proceso a un flujo de trabajo"""
    flujo = get_object_or_404(FlujoTrabajo, pk=flujo_id)
    
    if request.method == 'POST':
        form = ProcesoFlujoForm(request.POST)
        if form.is_valid():
            proceso_flujo = form.save(commit=False)
            proceso_flujo.flujo_trabajo = flujo
            
            # Calcular orden automático si no se especifica
            if not proceso_flujo.orden:
                ultimo_orden = ProcesoFlujo.objects.filter(flujo_trabajo=flujo).aggregate(models.Max('orden'))['orden__max']
                proceso_flujo.orden = (ultimo_orden or 0) + 1
            
            proceso_flujo.save()
            
            # Recalcular tiempo total del flujo
            flujo.calcular_tiempo_total()
            
            messages.success(request, f'Proceso "{proceso_flujo.proceso.nombre}" agregado al flujo.')
            return redirect('detalle_flujo_trabajo', pk=flujo.pk)
    else:
        form = ProcesoFlujoForm(initial={'flujo_trabajo': flujo})
    
    context = {
        'flujo': flujo,
        'form': form,
    }
    
    return render(request, 'procesos/agregar_proceso_flujo.html', context)

# ============ ASIGNACIÓN RÁPIDA ============ #
@login_required
def asignacion_rapida(request):
    """Asignación rápida de procesos a operarios"""
    if request.method == 'POST':
        form = AsignarProcesoForm(request.POST)
        if form.is_valid():
            proceso = form.cleaned_data['proceso']
            operario = form.cleaned_data['operario']
            tiempo_objetivo = form.cleaned_data['tiempo_objetivo']
            
            # Crear temporizador
            temporizador = Temporizador.objects.create(
                proceso=proceso,
                tiempo_objetivo=tiempo_objetivo,
                operario=operario,
                creado_por=request.user
            )
            temporizador.iniciar()
            
            # Actualizar proceso
            proceso.estado = 'en_proceso'
            proceso.save()
            
            messages.success(request, f'Proceso "{proceso.nombre}" asignado a {operario.username}.')
            return redirect('panel_temporizador')
    else:
        form = AsignarProcesoForm()
    
    # Procesos disponibles para asignar
    procesos_disponibles = Proceso.objects.filter(
        activo=True,
        estado='pendiente'
    )[:10]
    
    context = {
        'form': form,
        'procesos_disponibles': procesos_disponibles,
    }
    
    return render(request, 'procesos/asignacion_rapida.html', context)

# ============ HISTORIAL DE OPERACIONES ============ #
@login_required
def historial_operaciones(request):
    """Historial completo de operaciones del sistema"""
    operaciones = Operacion.objects.all().order_by('-fecha')
    
    # Filtros
    accion = request.GET.get('accion')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    usuario_id = request.GET.get('usuario')
    
    if accion:
        operaciones = operaciones.filter(accion=accion)
    if fecha_desde:
        try:
            operaciones = operaciones.filter(fecha__date__gte=fecha_desde)
        except:
            pass
    if fecha_hasta:
        try:
            operaciones = operaciones.filter(fecha__date__lte=fecha_hasta)
        except:
            pass
    if usuario_id:
        operaciones = operaciones.filter(usuario_id=usuario_id)
    
    # Conteo de operaciones de hoy
    hoy = timezone.now().date()
    operaciones_today = Operacion.objects.filter(fecha__date=hoy).count()
    
    # Usuarios para filtro
    from django.contrib.auth.models import User
    usuarios = User.objects.filter(is_active=True)
    
    # Paginación
    paginator = Paginator(operaciones, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'procesos/historial.html', {
        'page_obj': page_obj,
        'operaciones_today': operaciones_today,
        'usuarios': usuarios,
    })

# ============ APIS PARA GRÁFICOS Y DATOS ============ #
@login_required
def api_estadisticas_procesos(request):
    """API para gráficos de procesos"""
    # Eficiencia por tipo de proceso
    eficiencia_tipo = Proceso.objects.values('tipo').annotate(
        promedio=Avg('eficiencia'),
        cantidad=Count('id')
    ).order_by('tipo')
    
    # Procesos por estado
    procesos_estado = Proceso.objects.values('estado').annotate(
        cantidad=Count('id')
    ).order_by('estado')
    
    # No conformidades por prioridad
    nc_prioridad = NoConformidad.objects.exclude(estado='cerrada').values('prioridad').annotate(
        cantidad=Count('id')
    ).order_by('prioridad')
    
    # Controles de calidad por resultado
    cc_resultado = ControlCalidad.objects.filter(
        fecha__gte=timezone.now() - timedelta(days=30)
    ).values('resultado').annotate(
        cantidad=Count('id')
    ).order_by('resultado')
    
    data = {
        'eficiencia_tipo': list(eficiencia_tipo),
        'procesos_estado': list(procesos_estado),
        'nc_prioridad': list(nc_prioridad),
        'cc_resultado': list(cc_resultado),
    }
    
    return JsonResponse(data)

@login_required
def api_temporizadores_activos(request):
    """API para temporizadores activos"""
    temporizadores = Temporizador.objects.filter(
        estado__in=['activo', 'pausado']
    ).select_related('proceso', 'operario')
    
    data = []
    for temp in temporizadores:
        data.append({
            'id': temp.id,
            'proceso': temp.proceso.nombre if temp.proceso else 'Sin proceso',
            'operario': temp.operario.username if temp.operario else 'Sin asignar',
            'estado': temp.estado,
            'tiempo_transcurrido': str(temp.tiempo_transcurrido),
            'tiempo_restante': str(temp.tiempo_restante()),
            'porcentaje': temp.porcentaje_completado(),
        })
    
    return JsonResponse({'temporizadores': data})

# ============ EXPORTACIÓN DE DATOS ============ #
@login_required
def exportar_procesos_csv(request):
    """Exportar procesos a CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="procesos.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Procesos - Reporte'])
    writer.writerow(['Fecha', timezone.now().strftime('%d/%m/%Y %H:%M')])
    writer.writerow([])
    writer.writerow(['Nombre', 'Tipo', 'Estado', 'Tiempo Estimado Mín', 
                     'Tiempo Estimado Máx', 'Tiempo Promedio Real', 
                     'Eficiencia (%)', 'Veces Ejecutado', 'Activo'])
    
    procesos = Proceso.objects.all()
    for proc in procesos:
        writer.writerow([
            proc.nombre,
            proc.get_tipo_display(),
            proc.get_estado_display(),
            str(proc.tiempo_estimado_min),
            str(proc.tiempo_estimado_max),
            str(proc.tiempo_promedio) if proc.tiempo_promedio else '',
            f"{proc.eficiencia:.2f}" if proc.eficiencia else '0.00',
            proc.veces_ejecutado,
            'Sí' if proc.activo else 'No'
        ])
    
    return response

@login_required
@login_required
def exportar_controles_calidad_csv(request):
    """Exportar controles de calidad a CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="controles_calidad.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Controles de Calidad - Reporte'])
    writer.writerow(['Fecha', timezone.now().strftime('%d/%m/%Y %H:%M')])
    writer.writerow([])
    writer.writerow(['Fecha', 'Proceso', 'Inspector', 'Resultado', 
                     'Puntuación', 'Defectos', 'Costo Reparación', 'Observaciones'])
    
    controles = ControlCalidad.objects.all()
    for cc in controles:
        writer.writerow([
            cc.fecha.strftime('%d/%m/%Y %H:%M'),
            cc.proceso,  # Cambiado de cc.proceso.nombre a cc.proceso
            cc.inspector.username if cc.inspector else 'N/A',
            cc.get_resultado_display(),
            cc.puntuacion_total,
            cc.cantidad_defectos,
            cc.costo_reparacion,
            cc.observaciones[:100]
        ])
    
    return response

@login_required
def lista_tiempos(request):
    tiempos = Operacion.objects.filter(
        accion='temporizador'
    ).order_by('-fecha')

    return render(request, 'procesos/tiempos/lista_tiempos.html', {
        'tiempos': tiempos
    })

@login_required
def registrar_tiempo(request):
    if request.method == 'POST':
        form = RegistroTiempoManualForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            Operacion.objects.create(
                usuario=request.user,
                accion='temporizador',
                descripcion=(
                    f"Usuario: {data['nombre_usuario']} | "
                    f"Prenda: {data['prenda']} | "
                    f"{data['descripcion']}"
                ),
                tiempo_empleado=data['tiempo']
            )

            return redirect('lista_tiempos')
    else:
        form = RegistroTiempoManualForm()

    return render(request, 'procesos/tiempos/registrar_tiempo.html', {
        'form': form
    })

@login_required
def lista_tiempos(request):
    tiempos = Operacion.objects.filter(accion='temporizador')

    form = FiltroTiempoForm(request.GET)

    if form.is_valid():
        nombre = form.cleaned_data.get('nombre')
        if nombre:
            tiempos = tiempos.filter(
                descripcion__icontains=nombre
            )

    tiempos = tiempos.order_by('-fecha')

    return render(request, 'procesos/tiempos/lista_tiempos.html', {
        'tiempos': tiempos,
        'form': form
    })
@login_required
def registrar_tiempo(request):
    if request.method == 'POST':
        form = RegistroTiempoManualForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            Operacion.objects.create(
                usuario=request.user,
                accion='temporizador',
                descripcion=(
                    f"Usuario: {data['nombre_usuario']} | "
                    f"Prenda: {data['prenda']} | "
                    f"{data['descripcion']}"
                ),
                tiempo_empleado=data['tiempo']
            )

            return redirect('lista_tiempos')
    else:
        form = RegistroTiempoManualForm()

    return render(request, 'procesos/tiempos/registrar_tiempo.html', {
        'form': form
    })
