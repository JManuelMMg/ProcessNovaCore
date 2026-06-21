import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from core.permissions import tenant_required
from .services import (
    chat_with_ai,
    analizar_inventario_y_sugerir_compras,
    analizar_cliente_crm,
    analizar_finanzas,
    analizar_rrhh,
    analizar_logistica,
    recomendar_precios,
    obtener_ventas_recientes,
    obtener_productos_bajo_stock,
    obtener_clientes_top,
    generar_reporte_ventas,
    check_tool_permission,
    get_user_role,
    TOOL_PERMISSIONS
)
import json

logger = logging.getLogger(__name__)


@login_required
@tenant_required
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
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='30/m', block=True)
def api_ai_chat(request):
    try:
        logger.info("Iniciando chat con AI")
        data = json.loads(request.body)
        user_message = data.get('message')
        conversation_history = data.get('history', [])
        
        if not user_message:
            logger.warning("No se proporcionó mensaje en el chat")
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
                logger.warning(f"Usuario {request.user.username} no tiene permisos para {result['function_called']}")
                return JsonResponse({
                    'error': 'No tienes permisos suficientes para usar esta herramienta.',
                    'response': 'Lo siento, no tienes permisos para realizar este análisis. Por favor contacta a un administrador.',
                    'function_called': None,
                    'tool_result': None
                }, status=403)
        
        logger.info("Chat completado exitosamente")
        return JsonResponse({
            'response': result['response'],
            'function_called': result['function_called'],
            'tool_result': result['tool_result'],
            'conversation_id': result.get('conversation_id')
        })
    except Exception as e:
        logger.error(f"Error en chat AI: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_analizar_inventario(request):
    logger.info("Iniciando análisis de inventario")
    if not check_tool_permission('analizar_inventario_y_sugerir_compras', request.user):
        logger.warning(f"Usuario {request.user.username} sin permisos para analizar inventario")
        return JsonResponse({
            'error': 'No tienes permisos suficientes para analizar el inventario'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        dias = data.get('dias', 30)
        resultado = analizar_inventario_y_sugerir_compras(request.organization, dias=dias)
        logger.info("Análisis de inventario completado")
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error en análisis de inventario: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_analizar_cliente_crm(request):
    logger.info("Iniciando análisis de CRM")
    if not check_tool_permission('analizar_cliente_crm', request.user):
        logger.warning(f"Usuario {request.user.username} sin permisos para analizar CRM")
        return JsonResponse({
            'error': 'No tienes permisos suficientes para analizar el CRM'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        cliente_id = data.get('cliente_id')
        resultado = analizar_cliente_crm(request.organization, cliente_id=cliente_id)
        logger.info("Análisis de CRM completado exitosamente")
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error en análisis de CRM: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_analizar_finanzas(request):
    if not check_tool_permission('analizar_finanzas', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para analizar finanzas'}, status=403)

    try:
        data = json.loads(request.body)
        periodo_inicio = data.get('periodo_inicio')
        periodo_fin = data.get('periodo_fin')
        resultado = analizar_finanzas(request.organization, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_recomendar_precios(request):
    if not check_tool_permission('recomendar_precios', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para recomendar precios'}, status=403)

    try:
        data = json.loads(request.body)
        categoria_id = data.get('categoria_id')
        resultado = recomendar_precios(request.organization, categoria_id=categoria_id)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_analizar_rrhh(request):
    if not check_tool_permission('analizar_rrhh', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para analizar RRHH'}, status=403)

    try:
        data = json.loads(request.body)
        dias = data.get('dias', 30)
        resultado = analizar_rrhh(request.organization, dias=dias)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_analizar_logistica(request):
    if not check_tool_permission('analizar_logistica', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para analizar logística'}, status=403)

    try:
        data = json.loads(request.body)
        dias = data.get('dias', 30)
        resultado = analizar_logistica(request.organization, dias=dias)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_obtener_ventas_recientes(request):
    if not check_tool_permission('obtener_ventas_recientes', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para ver ventas'}, status=403)
    
    try:
        data = json.loads(request.body)
        limite = data.get('limite', 10)
        estado = data.get('estado')
        resultado = obtener_ventas_recientes(request.organization, limite=limite, estado=estado)
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error en obtener ventas recientes: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_obtener_productos_bajo_stock(request):
    if not check_tool_permission('obtener_productos_bajo_stock', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para ver productos bajo stock'}, status=403)
    
    try:
        resultado = obtener_productos_bajo_stock(request.organization)
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error en obtener productos bajo stock: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_obtener_clientes_top(request):
    if not check_tool_permission('obtener_clientes_top', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para ver clientes top'}, status=403)
    
    try:
        data = json.loads(request.body)
        limite = data.get('limite', 10)
        resultado = obtener_clientes_top(request.organization, limite=limite)
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error en obtener clientes top: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@tenant_required
@require_POST
@ratelimit(key='user_or_ip', rate='20/m', block=True)
def api_generar_reporte_ventas(request):
    if not check_tool_permission('generar_reporte_ventas', request.user):
        return JsonResponse({'error': 'No tienes permisos suficientes para generar reportes de ventas'}, status=403)
    
    try:
        data = json.loads(request.body)
        periodo = data.get('periodo', 'monthly')
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        resultado = generar_reporte_ventas(request.organization, periodo=periodo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        return JsonResponse(resultado)
    except Exception as e:
        logger.error(f"Error en generar reporte de ventas: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
