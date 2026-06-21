from django.urls import path
from . import views

app_name = 'ai_engine'

urlpatterns = [
    path('assistant/', views.ai_assistant, name='assistant'),
    path('api/chat/', views.api_ai_chat, name='api_chat'),
    path('api/inventory/analyze/', views.api_analizar_inventario, name='api_analizar_inventario'),
    path('api/crm/analyze/', views.api_analizar_cliente_crm, name='api_analizar_cliente_crm'),
    path('api/finance/analyze/', views.api_analizar_finanzas, name='api_analizar_finanzas'),
    path('api/inventory/prices/', views.api_recomendar_precios, name='api_recomendar_precios'),
    path('api/hr/analyze/', views.api_analizar_rrhh, name='api_analizar_rrhh'),
    path('api/logistics/analyze/', views.api_analizar_logistica, name='api_analizar_logistica'),
    path('api/sales/recent/', views.api_obtener_ventas_recientes, name='api_obtener_ventas_recientes'),
    path('api/inventory/low-stock/', views.api_obtener_productos_bajo_stock, name='api_obtener_productos_bajo_stock'),
    path('api/crm/top-customers/', views.api_obtener_clientes_top, name='api_obtener_clientes_top'),
    path('api/sales/report/', views.api_generar_reporte_ventas, name='api_generar_reporte_ventas'),
]
