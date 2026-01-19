from django.urls import path
from . import views

urlpatterns = [
    # Calculadoras
    path('calculadora-hilo/', views.calculadora_hilo, name='calculadora_hilo'),
    path('calculadora-materiales/', views.calculadora_materiales, name='calculadora_materiales'),
    
    # Inventario
    path('inventario/', views.inventario_lista, name='inventario_lista'),
    path('inventario/nuevo/', views.inventario_crear, name='inventario_crear'),
    path('inventario/<int:pk>/', views.inventario_detalle, name='inventario_detalle'),
    
    # Movimientos
    path('movimientos/nuevo/', views.movimiento_crear, name='movimiento_crear'),
    path('ajuste-inventario/', views.ajuste_inventario, name='ajuste_inventario'),
    
    # Alertas
    path('alertas/', views.alertas_stock, name='alertas_stock'),
    path('alertas/<int:pk>/resolver/', views.alerta_resolver, name='alerta_resolver'),
    
    # Pedidos de Compra
    path('pedidos-compra/', views.pedido_compra_lista, name='pedido_compra_lista'),
    path('pedidos-compra/nuevo/', views.pedido_compra_crear, name='pedido_compra_crear'),
    path('pedidos-compra/<int:pk>/', views.pedido_compra_detalle, name='pedido_compra_detalle'),
    path('pedidos-compra/<int:pk>/recibir/', views.pedido_compra_recibir, name='pedido_compra_recibir'),
    
    # Reportes
    path('reportes/', views.reportes_inventario, name='reportes_inventario'),
    path('exportar-inventario-csv/', views.exportar_inventario_csv, name='exportar_inventario_csv'),
    
    # APIs
    path('api/inventario-datos/', views.api_inventario_datos, name='api_inventario_datos'),
]