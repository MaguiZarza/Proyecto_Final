from django.urls import path
from . import views
from .views import (
    PedidoListView, PedidoCreateView, PedidoUpdateView, PedidoDetailView,
    OrdenProduccionListView, PlanificacionListView
)

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Pedidos
    path('pedidos/', PedidoListView.as_view(), name='pedido_list'),
    path('pedidos/nuevo/', PedidoCreateView.as_view(), name='pedido_create'),
    path('pedidos/<int:pk>/', PedidoDetailView.as_view(), name='pedido_detail'),
    path('pedidos/<int:pk>/editar/', PedidoUpdateView.as_view(), name='pedido_update'),
    path('pedidos/<int:pk>/cambiar-estado/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    
    # Órdenes de Producción (con lote integrado)
    path('ordenes-produccion/', OrdenProduccionListView.as_view(), name='ordenproduccion_list'),
    path('ordenes-produccion/nueva/', views.crear_orden_produccion, name='ordenproduccion_create'),
    path('ordenes-produccion/<int:pk>/', views.orden_produccion_detail, name='ordenproduccion_detail'),
    path('ordenes-produccion/<int:pk>/avance/', views.actualizar_avance, name='actualizar_avance'),
    path('ordenes-produccion/<int:pk>/cambiar-estado/', views.cambiar_estado_orden, name='cambiar_estado_orden'),
    
    # Trazabilidad y Control de Lote
    path('ordenes-produccion/<int:pk>/actualizar-trazabilidad/', views.actualizar_estado_trazabilidad, name='actualizar_estado_trazabilidad'),
    path('ordenes-produccion/<int:pk>/control-calidad/', views.control_calidad_lote, name='control_calidad_lote'),
    path('ordenes-produccion/<int:pk>/almacenar/', views.marcar_como_almacenado, name='marcar_almacenado'),
    path('ordenes-produccion/<int:pk>/despachar/', views.marcar_como_despachado, name='marcar_despachado'),
    
    # Reportes de Lotes
    path('lotes/reporte/', views.reporte_lotes, name='reporte_lotes'),
    
    # Planificación
    path('planificacion/', PlanificacionListView.as_view(), name='planificacion_list'),
    path('planificacion/calendario/', views.vista_calendario, name='calendario'),
    path('planificacion/generar-semanal/', views.generar_planificacion_semanal, name='generar_planificacion_semanal'),
    path('planificacion/<int:pk>/', views.PedidoDetailView.as_view(), name='planificacion_detail'),  # Reutilizar vista
    
    # Reportes y Estadísticas
    path('reportes/', views.reportes_produccion, name='reportes_produccion'),
    path('reportes/generar-rapido/', views.generar_reporte_rapido, name='generar_reporte_rapido'),
    path('reportes/<int:pk>/exportar-csv/', views.exportar_reporte_csv, name='exportar_reporte_csv'),
    
    # APIs para gráficos
    path('api/estadisticas/', views.api_estadisticas, name='api_estadisticas'),
    # En el archivo urls.py
    path('planificacion/<int:pk>/detalle/', views.planificacion_detail, name='planificacion_detail'),
    path('planificacion/', PlanificacionListView.as_view(), name='planificacion_list'),
    path('planificacion/calendario/', views.vista_calendario, name='calendario'),
    path('planificacion/generar-semanal/', views.generar_planificacion_semanal, name='generar_planificacion_semanal'),
    path('planificacion/<int:pk>/detalle/', views.planificacion_detail, name='planificacion_detail'),
    
    # Planificación - Acciones
    path('planificacion/<int:pk>/completar/', views.marcar_planificacion_completada, name='planificacion_completar'),
    path('planificacion/<int:pk>/activar-desactivar/', views.activar_desactivar_planificacion, name='planificacion_activar_desactivar'),
    path('planificacion/<int:pk>/eliminar/', views.eliminar_planificacion, name='planificacion_eliminar'),
    path('planificacion/<int:pk>/editar/', views.editar_planificacion, name='planificacion_editar'),
    path('planificacion/<int:pk>/agregar-orden/', views.agregar_orden_a_planificacion, name='planificacion_agregar_orden'),
    path('planificacion/<int:pk>/remover-orden/', views.remover_orden_de_planificacion, name='planificacion_remover_orden'),
    path('planificacion/<int:pk>/estadisticas-pedidos/', views.obtener_estadisticas_pedidos_planificacion, name='planificacion_estadisticas_pedidos'),
    
    
]