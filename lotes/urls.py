from django.urls import path
from . import views

urlpatterns = [
    # Dashboard y página principal
    path('', views.dashboard_lotes, name='dashboard_lotes'),
    
    # Gestión de lotes
    path('lotes/', views.lista_lotes, name='lista_lotes'),
    path('lotes/nuevo/', views.crear_lote, name='crear_lote'),
    path('lotes/<int:pk>/', views.detalle_lote, name='detalle_lote'),
    path('lotes/<int:pk>/editar/', views.editar_lote, name='editar_lote'),
    path('lotes/<int:lote_id>/iniciar/', views.iniciar_produccion_lote, name='iniciar_produccion_lote'),
    path('lotes/<int:lote_id>/finalizar/', views.finalizar_produccion_lote, name='finalizar_produccion_lote'),
    path('lotes/<int:lote_id>/aprobar/', views.aprobar_control_calidad, name='aprobar_control_calidad'),
    path('lotes/<int:lote_id>/rechazar/', views.rechazar_lote, name='rechazar_lote'),
    
    # Materiales por lote
    path('lotes/<int:lote_id>/materiales/', views.materiales_lote, name='materiales_lote'),
    path('lotes/<int:lote_id>/materiales/agregar/', views.agregar_material_lote, name='agregar_material_lote'),
    path('lotes/<int:lote_id>/materiales/<int:material_id>/entregar/', views.entregar_material, name='entregar_material'),
    
    # Trazabilidad
    path('lotes/<int:lote_id>/trazabilidad/', views.trazabilidad_lote, name='trazabilidad_lote'),
    path('lotes/<int:lote_id>/trazabilidad/agregar/', views.agregar_trazabilidad, name='agregar_trazabilidad'),
    
    # Almacenes
    path('almacenes/', views.lista_almacenes, name='lista_almacenes'),
    path('almacenes/nuevo/', views.crear_almacen, name='crear_almacen'),
    path('almacenes/<int:pk>/', views.detalle_almacen, name='detalle_almacen'),
    
    # Movimientos de almacén
    path('movimientos/', views.lista_movimientos, name='lista_movimientos'),
    path('movimientos/nuevo/', views.crear_movimiento, name='crear_movimiento'),
    path('movimientos/<int:pk>/autorizar/', views.autorizar_movimiento, name='autorizar_movimiento'),
    path('movimientos/<int:pk>/ejecutar/', views.ejecutar_movimiento, name='ejecutar_movimiento'),
    path('movimientos/<int:pk>/cancelar/', views.cancelar_movimiento, name='cancelar_movimiento'),
    
    # Reportes y exportación
    path('reportes/estado-lotes/', views.reporte_estado_lotes, name='reporte_estado_lotes'),
    path('reportes/movimientos/', views.reporte_movimientos, name='reporte_movimientos'),
    path('exportar/lotes-csv/', views.exportar_lotes_csv, name='exportar_lotes_csv'),
    path('exportar/movimientos-csv/', views.exportar_movimientos_csv, name='exportar_movimientos_csv'),
]