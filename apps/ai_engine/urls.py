from django.urls import path
from . import views

app_name = 'ai_engine'

urlpatterns = [
    path('assistant/', views.ai_assistant, name='assistant'),
    path('api/chat/', views.api_ai_chat, name='api_chat'),
    path('api/inventory/analyze/', views.api_analizar_inventario, name='api_analizar_inventario'),
    path('api/crm/analyze/', views.api_analizar_cliente_crm, name='api_analizar_cliente_crm'),
]
