from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum
from datetime import timedelta
from django.utils import timezone
from .services import (
    chat_with_ai,
    analizar_inventario_y_sugerir_compras,
    analizar_cliente_crm,
    analizar_finanzas,
    analizar_rrhh,
    analizar_logistica,
    recomendar_precios,
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
        'can_analyze_crm': 'analizar_cliente_crm' in allowed_tools,
        'can_analyze_finance': 'analizar_finanzas' in allowed_tools,
        'can_analyze_hr': 'analizar_rrhh' in allowed_tools,
        'can_analyze_logistics': 'analizar_logistica' in allowed_tools,
        'can_recommend_prices': 'recomendar_precios' in allowed_tools,
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
        
        result = chat_with_ai(
            user_message,
            conversation_history,
            user=request.user,
            organization=getattr(request, 'organization', None),
        )
        
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
        from apps.inventory.models import Product
        
        # Filtrar por organización + prefetch para evitar N+1
        productos_db = Product.objects.filter(
            organization=request.organization
        ).prefetch_related('stocks').all()
        
        productos = []
        for p in productos_db:
            # Ahora es una query precargada, no multiple queries
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
        from apps.crm.models import Customer
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


@login_required
@require_POST
def api_analizar_finanzas(request):
    if not check_tool_permission('analizar_finanzas', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para analizar finanzas'}, status=403)

    try:
        from apps.finance.models import Income, Expense

        today = timezone.localdate()
        start = today - timedelta(days=30)
        incomes_qs = Income.objects.for_org(request.organization).filter(date__gte=start, date__lte=today)
        expenses_qs = Expense.objects.for_org(request.organization).filter(date__gte=start, date__lte=today)

        ingresos = [{
            "fecha": i.date.isoformat(),
            "monto": float(i.amount),
            "categoria": i.get_type_display() if hasattr(i, 'get_type_display') else i.type,
        } for i in incomes_qs]
        gastos = [{
            "fecha": e.date.isoformat(),
            "monto": float(e.amount),
            "categoria": e.get_category_display() if hasattr(e, 'get_category_display') else e.category,
        } for e in expenses_qs]

        resultado = analizar_finanzas(start.isoformat(), today.isoformat(), ingresos, gastos)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_recomendar_precios(request):
    if not check_tool_permission('recomendar_precios', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para recomendar precios'}, status=403)

    try:
        from apps.inventory.models import Product
        from apps.sales.models import SaleItem

        today = timezone.localdate()
        start = today - timedelta(days=30)
        productos = []
        for product in Product.objects.for_org(request.organization).filter(is_active=True)[:50]:
            ventas = SaleItem.objects.filter(
                organization=request.organization,
                product=product,
                sale__status='paid',
                sale__created_at__date__gte=start,
            ).aggregate(total=Sum('quantity'))['total'] or 0
            ventas = int(ventas)
            demanda = 'alta' if ventas >= 20 else 'media' if ventas >= 5 else 'baja'
            productos.append({
                "id": product.id,
                "nombre": product.name,
                "precio_actual": float(product.price),
                "precio_costo": float(product.cost or 0),
                "ventas_ultimos_30d": ventas,
                "demanda": demanda,
            })

        resultado = recomendar_precios(productos)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_analizar_rrhh(request):
    if not check_tool_permission('analizar_rrhh', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para analizar RRHH'}, status=403)

    try:
        from apps.hr.models import Employee, Attendance, LeaveRequest, Payroll

        today = timezone.localdate()
        start = today - timedelta(days=30)
        empleados = [{
            "id": e.id,
            "nombre": e.full_name,
            "department": e.department.name if e.department else '',
            "position": e.position.title if e.position else '',
            "status": e.status,
            "salary": float(e.salary),
            "years_of_service": e.years_of_service,
        } for e in Employee.objects.for_org(request.organization).select_related('department', 'position')]
        asistencias = [{
            "employee_id": a.employee_id,
            "fecha": a.date.isoformat(),
            "status": a.status,
            "worked_hours": float(a.worked_hours),
            "overtime_hours": float(a.overtime_hours),
        } for a in Attendance.objects.for_org(request.organization).filter(date__gte=start, date__lte=today).select_related('employee')]
        permisos = [{
            "employee_id": p.employee_id,
            "type": p.type,
            "status": p.status,
            "days": p.days,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
        } for p in LeaveRequest.objects.for_org(request.organization).filter(created_at__date__gte=start)]
        nominas = [{
            "employee_id": n.employee_id,
            "period_start": n.period_start.isoformat(),
            "period_end": n.period_end.isoformat(),
            "gross_salary": float(n.gross_salary),
            "net_salary": float(n.net_salary),
            "status": n.status,
        } for n in Payroll.objects.for_org(request.organization).filter(period_end__gte=start)]

        resultado = analizar_rrhh(empleados, asistencias, permisos, nominas)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_analizar_logistica(request):
    if not check_tool_permission('analizar_logistica', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para analizar logística'}, status=403)

    try:
        from apps.logistics.models import Shipment, Order, Route

        today = timezone.localdate()
        start = today - timedelta(days=30)
        envios = [{
            "id": s.id,
            "tracking_number": s.tracking_number,
            "status": s.status,
            "carrier": s.carrier.name if s.carrier else '',
            "route": s.route.name if s.route else '',
            "shipping_city": s.shipping_city,
            "shipping_state": s.shipping_state,
            "shipping_cost": float(s.shipping_cost),
            "delivery_attempts": s.delivery_attempts,
            "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
        } for s in Shipment.objects.for_org(request.organization).filter(created_at__date__gte=start).select_related('carrier', 'route')]
        pedidos = [{
            "id": o.id,
            "number": o.number,
            "status": o.status,
            "total": float(o.total),
            "shipping_city": o.shipping_city,
            "shipping_state": o.shipping_state,
        } for o in Order.objects.for_org(request.organization).filter(created_at__date__gte=start)]
        rutas = [{
            "id": r.id,
            "name": r.name,
            "driver_name": r.driver_name,
            "vehicle_plate": r.vehicle_plate,
            "distance_km": float(r.distance_km or 0),
            "estimated_hours": float(r.estimated_hours or 0),
            "is_active": r.is_active,
        } for r in Route.objects.for_org(request.organization)]

        resultado = analizar_logistica(envios, pedidos, rutas)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
