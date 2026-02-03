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
    path('pedidos/<int:pk>/eliminar/', views.eliminar_pedido, name='eliminar_pedido'),
    
    # Órdenes de Producción
    path('ordenes-produccion/', OrdenProduccionListView.as_view(), name='ordenproduccion_list'),
    path('ordenes-produccion/nueva/', views.crear_orden_produccion, name='ordenproduccion_create'),
    # ELIMINAR o CORREGIR: path('ordenes-produccion/nueva/<int:pedido_id>/', views.crear_orden_produccion, name='ordenproduccion_create_from_pedido'),
    path('ordenes-produccion/<int:pk>/', views.orden_produccion_detail, name='ordenproduccion_detail'),  # NUEVA VISTA
    path('ordenes-produccion/<int:pk>/avance/', views.actualizar_avance, name='actualizar_avance'),
    path('ordenes-produccion/<int:pk>/cambiar-estado/', views.cambiar_estado_orden, name='cambiar_estado_orden'),
    
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
]