from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from .services import (
    chat_with_ai,
    analizar_inventario_y_sugerir_compras,
    analizar_cliente_crm,
    check_tool_permission,
    get_user_role,
    TOOL_PERMISSIONS
)
import json


@login_required
def ai_assistant(request):
    """
    Vista principal del asistente AI, pasa el rol del usuario al frontend.
    """
    user_role = get_user_role(request.user)
    # Preparamos información de permisos para el frontend
    allowed_tools = []
    for tool_name, roles in TOOL_PERMISSIONS.items():
        if request.user.is_superuser or user_role in roles:
            allowed_tools.append(tool_name)
    
    context = {
        'user_role': user_role,
        'allowed_tools': allowed_tools,
        'can_analyze_inventory': 'analizar_inventario_y_sugerir_compras' in allowed_tools,
        'can_analyze_crm': 'analizar_cliente_crm' in allowed_tools
    }
    return render(request, 'ai/assistant.html', context)


@login_required
@require_POST
def api_ai_chat(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message')
        conversation_history = data.get('history', [])
        
        if not user_message:
            return JsonResponse({'error': 'No se proporcionó mensaje'}, status=400)
        
        result = chat_with_ai(user_message, conversation_history)
        
        # Si se llamó a una función, verificamos permisos
        if result.get('function_called'):
            if not check_tool_permission(result['function_called'], request.user):
                return JsonResponse({
                    'error': 'No tienes permisos suficientes para usar esta herramienta.',
                    'response': 'Lo siento, no tienes permisos para realizar este análisis. Por favor contacta a un administrador.',
                    'function_called': None,
                    'tool_result': None
                }, status=403)
        
        return JsonResponse({
            'response': result['response'],
            'function_called': result['function_called'],
            'tool_result': result['tool_result']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_analizar_inventario(request):
    # Verificación de permisos
    if not check_tool_permission('analizar_inventario_y_sugerir_compras', request.user):
        return JsonResponse({
            'error': 'No tienes permisos suficientes para analizar el inventario'
        }, status=403)
    
    try:
        from apps.inventory.models import Product, Stock
        productos_db = Product.objects.all()
        
        productos = []
        for p in productos_db:
            stock_total = sum(s.quantity for s in p.stocks.all())
            productos.append({
                "id": p.id,
                "nombre": p.name,
                "stock_actual": stock_total,
                "stock_minimo": 10, 
                "ventas_ultimos_30d": 20,
                "precio_costo": float(p.cost) if p.cost else 0.0
            })
        
        if not productos:
            productos = [
                {"id": 1, "nombre": "Café Molido Premium", "stock_actual": 5, "stock_minimo": 20, "ventas_ultimos_30d": 35, "precio_costo": 120.50},
                {"id": 2, "nombre": "Azúcar Morena 1kg", "stock_actual": 100, "stock_minimo": 50, "ventas_ultimos_30d": 80, "precio_costo": 25.00}
            ]
        
        resultado = analizar_inventario_y_sugerir_compras(productos)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_analizar_cliente_crm(request):
    # Verificación de permisos
    if not check_tool_permission('analizar_cliente_crm', request.user):
        return JsonResponse({
            'error': 'No tienes permisos suficientes para analizar el CRM'
        }, status=403)
    
    try:
        from apps.crm.models import Customer, Interaction
        cliente_db = Customer.objects.first()
        
        if cliente_db:
            cliente = {"id": cliente_db.id, "nombre": cliente_db.name, "email": cliente_db.email}
            interacciones_db = cliente_db.interactions.all()[:5]
            interacciones = [
                {"tipo": i.type, "fecha": i.created_at.strftime("%Y-%m-%d"), "contenido": i.notes}
                for i in interacciones_db
            ]
        else:
            cliente = {"id": 1, "nombre": "María González", "email": "maria@ejemplo.com"}
            interacciones = [
                {"tipo": "email", "fecha": "2026-06-01", "contenido": "¡Excelente servicio! Estoy muy contenta con mis compras."},
                {"tipo": "call", "fecha": "2026-06-05", "contenido": "Consulta sobre la garantía del producto, respondida satisfactoriamente."},
                {"tipo": "chat", "fecha": "2026-06-08", "contenido": "Pregunta sobre disponibilidad de stock, todo perfecto."}
            ]
        
        resultado = analizar_cliente_crm(cliente, interacciones)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
