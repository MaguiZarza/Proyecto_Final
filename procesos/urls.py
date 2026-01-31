from django.urls import path
from . import views

urlpatterns = [
    # Dashboard y página principal
    path('', views.dashboard_procesos, name='dashboard_procesos'),
    
    # Gestión de procesos
    path('procesos/', views.lista_procesos, name='lista_procesos'),
    path('procesos/nuevo/', views.crear_proceso, name='crear_proceso'),
    path('procesos/<int:pk>/', views.detalle_proceso, name='detalle_proceso'),
    path('procesos/<int:pk>/editar/', views.editar_proceso, name='editar_proceso'),
    path('procesos/<int:pk>/eliminar/', views.eliminar_proceso, name='eliminar_proceso'),
    path('procesos/<int:pk>/iniciar/', views.iniciar_proceso, name='iniciar_proceso'),
    path('procesos/<int:pk>/finalizar/', views.finalizar_proceso, name='finalizar_proceso'),
    
    # Etapas de proceso
    path('procesos/<int:proceso_id>/etapas/nuevo/', views.crear_etapa, name='crear_etapa'),
    path('etapas/<int:etapa_id>/iniciar/', views.iniciar_etapa, name='iniciar_etapa'),
    path('etapas/<int:etapa_id>/finalizar/', views.finalizar_etapa, name='finalizar_etapa'),
    
    # Temporizador
    path('temporizador/', views.panel_temporizador, name='panel_temporizador'),
    path('temporizador/iniciar/', views.iniciar_temporizador, name='iniciar_temporizador'),
    path('temporizador/<int:temporizador_id>/pausar/', views.pausar_temporizador, name='pausar_temporizador'),
    path('temporizador/<int:temporizador_id>/reanudar/', views.reanudar_temporizador, name='reanudar_temporizador'),
    path('temporizador/<int:temporizador_id>/detener/', views.detener_temporizador, name='detener_temporizador'),
    path('api/temporizador/<int:temporizador_id>/', views.api_temporizador_estado, name='api_temporizador_estado'),
    
    # Control de calidad
    path('control-calidad/', views.lista_controles_calidad, name='lista_controles_calidad'),
    path('control-calidad/nuevo/', views.crear_control_calidad, name='crear_control_calidad'),
    path('control-calidad/<int:pk>/', views.detalle_control_calidad, name='detalle_control_calidad'),
    path('control-calidad/<int:control_id>/detalles/nuevo/', views.agregar_detalle_control, name='agregar_detalle_control'),
    path('control-calidad/<int:control_id>/no-conformidad/', views.generar_no_conformidad, name='generar_no_conformidad'),
    
    # No conformidades
    path('no-conformidades/', views.lista_no_conformidades, name='lista_no_conformidades'),
    path('no-conformidades/<int:pk>/', views.detalle_no_conformidad, name='detalle_no_conformidad'),
    path('no-conformidades/<int:pk>/cerrar/', views.cerrar_no_conformidad, name='cerrar_no_conformidad'),
    
    # Flujos de trabajo
    path('flujos-trabajo/', views.lista_flujos_trabajo, name='lista_flujos_trabajo'),
    path('flujos-trabajo/nuevo/', views.crear_flujo_trabajo, name='crear_flujo_trabajo'),
    path('flujos-trabajo/<int:pk>/', views.detalle_flujo_trabajo, name='detalle_flujo_trabajo'),
    path('flujos-trabajo/<int:flujo_id>/procesos/agregar/', views.agregar_proceso_flujo, name='agregar_proceso_flujo'),
    
    # Asignación rápida
    path('asignacion-rapida/', views.asignacion_rapida, name='asignacion_rapida'),
    
    # Historial
    path('historial/', views.historial_operaciones, name='historial_operaciones'),
    
    # APIs
    path('api/estadisticas-procesos/', views.api_estadisticas_procesos, name='api_estadisticas_procesos'),
    path('api/temporizadores-activos/', views.api_temporizadores_activos, name='api_temporizadores_activos'),
    
    # Exportación
    path('exportar/procesos-csv/', views.exportar_procesos_csv, name='exportar_procesos_csv'),
    path('exportar/controles-calidad-csv/', views.exportar_controles_calidad_csv, name='exportar_controles_calidad_csv'),
    
    path('tiempos/', views.lista_tiempos, name='lista_tiempos'),
    path('tiempos/nuevo/', views.registrar_tiempo, name='registrar_tiempo'),
]