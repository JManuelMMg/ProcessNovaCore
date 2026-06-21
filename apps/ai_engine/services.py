from openai import OpenAI
from django.conf import settings
from django.core.exceptions import PermissionDenied
import json
from typing import List, Dict, Optional
from .models import Conversation, Message
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal


# Configuración de permisos por rol
TOOL_PERMISSIONS = {
    'analizar_inventario_y_sugerir_compras': ['admin_central', 'branch_manager'],
    'analizar_cliente_crm': ['admin_central', 'branch_manager', 'employee'],
    'analizar_finanzas': ['admin_central', 'branch_manager'],
    'analizar_rrhh': ['admin_central'],
    'analizar_logistica': ['admin_central', 'branch_manager'],
    'recomendar_precios': ['admin_central', 'branch_manager'],
    'obtener_ventas_recientes': ['admin_central', 'branch_manager', 'employee'],
    'obtener_productos_bajo_stock': ['admin_central', 'branch_manager'],
    'obtener_clientes_top': ['admin_central', 'branch_manager'],
    'generar_reporte_ventas': ['admin_central', 'branch_manager'],
}


def get_user_role(user):
    from core.permissions import get_user_role as _get_role
    return _get_role(user)


def check_tool_permission(tool_name: str, user) -> bool:
    """
    Verifica si un usuario tiene permiso para usar una herramienta.
    """
    if user.is_superuser:
        return True
    role = get_user_role(user)
    allowed_roles = TOOL_PERMISSIONS.get(tool_name, [])
    return role in allowed_roles


def get_openrouter_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY
    )


# Definimos las herramientas (functions) para Function Calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analizar_inventario_y_sugerir_compras",
            "description": "Analiza el stock actual y ventas para generar sugerencias de compras automáticas. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dias": {
                        "type": "integer",
                        "description": "Número de días históricos para analizar ventas (default: 30)",
                        "default": 30
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_cliente_crm",
            "description": "Analiza sentimiento y resumen del historial de interacciones de TODOS los clientes o uno específico. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_id": {
                        "type": "integer",
                        "description": "ID del cliente específico (opcional, si no se proporciona analiza todos)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_finanzas",
            "description": "Analiza ingresos, gastos y rentabilidad en un período determinado. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "periodo_inicio": {"type": "string", "format": "date", "description": "Fecha de inicio del período (YYYY-MM-DD)"},
                    "periodo_fin": {"type": "string", "format": "date", "description": "Fecha de fin del período (YYYY-MM-DD)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recomendar_precios",
            "description": "Recomienda precios óptimos para productos basados en demanda y costos. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria_id": {
                        "type": "integer",
                        "description": "ID de categoría para filtrar productos (opcional)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_rrhh",
            "description": "Analiza indicadores de recursos humanos: empleados, asistencia, permisos y nómina. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dias": {
                        "type": "integer",
                        "description": "Número de días históricos para analizar (default: 30)",
                        "default": 30
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_logistica",
            "description": "Analiza pedidos, envíos, intentos de entrega, rutas y costos logísticos. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dias": {
                        "type": "integer",
                        "description": "Número de días históricos para analizar (default: 30)",
                        "default": 30
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_ventas_recientes",
            "description": "Obtiene las ventas más recientes con detalles. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de ventas a obtener (default: 10)",
                        "default": 10
                    },
                    "estado": {
                        "type": "string",
                        "description": "Filtrar por estado de venta (draft, pending, paid, refunded, cancelled)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_productos_bajo_stock",
            "description": "Obtiene la lista de productos con stock por debajo del mínimo. Devuelve JSON.",
            "parameters": {
                "type": "object"
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_clientes_top",
            "description": "Obtiene los clientes con mayor valor de vida útil (LTV). Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de clientes a obtener (default: 10)",
                        "default": 10
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generar_reporte_ventas",
            "description": "Genera un reporte de ventas para un período específico. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "periodo": {
                        "type": "string",
                        "description": "Período del reporte (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"],
                        "default": "monthly"
                    },
                    "fecha_inicio": {"type": "string", "format": "date", "description": "Fecha de inicio del período (YYYY-MM-DD)"},
                    "fecha_fin": {"type": "string", "format": "date", "description": "Fecha de fin del período (YYYY-MM-DD)"}
                }
            }
        }
    }
]

SYSTEM_PROMPT_OPERATIVO = """Eres Nova, el Motor de Inteligencia Operativa y asistente amigable de ProcessNova, un ERP para PYMES mexicanas.

TU DOBLE FUNCIÓN:
1. **Interacción conversacional normal**: Cuando el usuario hable de temas generales, respondes en español de forma natural, amigable y útil.
2. **Análisis técnico con Function Calling**: Cuando el usuario pida análisis de inventario, CRM, finanzas, RRHH, logística, ventas o recomendaciones de precios, usa las herramientas disponibles para generar resultados estructurados.

REGLAS:
- Para conversaciones normales (saludos, preguntas sobre el sistema, ayuda general): responde de forma conversacional, clara y en español.
- Para análisis técnicos: usa las funciones (function calling) disponibles.
- Si detectas stock crítico o problemas financieros, marca 'alerta' como true en tu respuesta.
- Siempre prioriza la precisión cuando uses funciones, pero mantén la naturalidad en conversaciones normales.
- Cuando presentes datos de las herramientas, hazlo de forma clara y fácil de entender para el usuario.
- Si un usuario no tiene permisos para usar una herramienta, explícaselo amablemente y sugiere alternativas si las hay."""


def call_gemma_with_function_calling(messages, tools=TOOLS):
    """
    Realiza consulta con Function Calling activado.
    """
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY no está configurado")
    
    client = get_openrouter_client()
    
    # Añadimos el system prompt al principio
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT_OPERATIVO}]
    full_messages.extend(messages)
    
    response = client.chat.completions.create(
        model=settings.OPENROUTER_MODEL,
        messages=full_messages,
        temperature=0.2,
        max_tokens=4096,
        tools=tools
    )
    
    return response.choices[0].message


def analizar_inventario_y_sugerir_compras(organization, dias=30):
    """
    Analiza inventario y genera sugerencias de compras.
    """
    from apps.inventory.models import Product, Stock
    from apps.sales.models import SaleItem
    from django.db.models import Sum
    
    hoy = timezone.localdate()
    inicio = hoy - timedelta(days=dias)
    
    productos_db = Product.objects.filter(organization=organization).prefetch_related('stocks')
    
    productos = []
    for p in productos_db:
        stock_total = sum(s.quantity for s in p.stocks.all())
        stock_minimo = sum(s.min_quantity for s in p.stocks.all()) or 10
        
        ventas = SaleItem.objects.filter(
            organization=organization,
            product=p,
            sale__status='paid',
            sale__created_at__date__gte=inicio
        ).aggregate(total=Sum('quantity'))['total'] or 0
        ventas = int(ventas)
        
        productos.append({
            "id": p.id,
            "nombre": p.name,
            "sku": p.sku,
            "stock_actual": stock_total,
            "stock_minimo": stock_minimo,
            "ventas_ultimos_dias": ventas,
            "precio_costo": float(p.cost) if p.cost else 0.0
        })
    
    sugerencias = []
    alerta_general = False
    
    for producto in productos:
        demanda_mensual = producto["ventas_ultimos_dias"]
        stock_actual = producto["stock_actual"]
        stock_minimo = producto["stock_minimo"]
        
        nivel_reorden = int(demanda_mensual * 1.5)
        cantidad_a_comprar = 0
        alerta = False
        
        if stock_actual < stock_minimo:
            alerta = True
            alerta_general = True
            cantidad_a_comprar = nivel_reorden - stock_actual if nivel_reorden > stock_actual else stock_minimo
        elif stock_actual < nivel_reorden:
            cantidad_a_comprar = nivel_reorden - stock_actual
        
        if cantidad_a_comprar > 0:
            sugerencias.append({
                "producto_id": producto["id"],
                "producto_nombre": producto["nombre"],
                "sku": producto["sku"],
                "stock_actual": stock_actual,
                "stock_minimo": stock_minimo,
                "demanda_mensual": demanda_mensual,
                "nivel_reorden": nivel_reorden,
                "cantidad_sugerida": cantidad_a_comprar,
                "costo_total": float(cantidad_a_comprar * producto["precio_costo"]),
                "alerta": alerta,
                "prioridad": "alta" if alerta else "media" if stock_actual < nivel_reorden else "baja"
            })
    
    return {
        "alerta_general": alerta_general,
        "total_productos_analizados": len(productos),
        "productos_con_alerta": len([s for s in sugerencias if s["alerta"]]),
        "sugerencias_compras": sugerencias,
        "costo_total_estimado": float(sum(s["costo_total"] for s in sugerencias))
    }


def analizar_cliente_crm(organization, cliente_id=None):
    """
    Analiza clientes del CRM.
    """
    from apps.crm.models import Customer, Interaction
    from django.db.models import Count, Sum
    
    if cliente_id:
        clientes_db = Customer.objects.filter(organization=organization, id=cliente_id).prefetch_related('interactions', 'sales')
    else:
        clientes_db = Customer.objects.filter(organization=organization).prefetch_related('interactions', 'sales')
    
    palabras_positivas = ["excelente", "feliz", "contento", "perfecto", "gracias", "mejor", "genial", "satisfactorio", "amar", "encantar"]
    palabras_negativas = ["mal", "enojo", "problema", "defectuoso", "queja", "insatisfecho", "horrible", "devolver", "odiar", "terrible"]
    
    resumen_clientes = []
    total_positivo = 0
    total_negativo = 0
    total_interacciones = 0
    total_gastado_todos = 0
    total_ventas_todas = 0
    
    for cliente in clientes_db:
        interacciones = cliente.interactions.all()
        conteo_positivo = 0
        conteo_negativo = 0
        puntos_clave = []
        
        for interaccion in interacciones:
            contenido = interaccion.notes.lower() if interaccion.notes else ""
            for palabra in palabras_positivas:
                if palabra in contenido:
                    conteo_positivo += 1
            for palabra in palabras_negativas:
                if palabra in contenido:
                    conteo_negativo += 1
            puntos_clave.append({
                "fecha": interaccion.created_at.strftime("%Y-%m-%d %H:%M"),
                "tipo": interaccion.type,
                "contenido": interaccion.notes[:200] if interaccion.notes else ""
            })
        
        total_positivo += conteo_positivo
        total_negativo += conteo_negativo
        total_interacciones += len(interacciones)
        
        ventas_cliente = cliente.sales.filter(status='paid')
        total_ventas_cliente = ventas_cliente.count()
        total_gastado_cliente = ventas_cliente.aggregate(total=Sum('total'))['total'] or 0
        total_gastado_todos += total_gastado_cliente
        total_ventas_todas += total_ventas_cliente
        
        if conteo_positivo > conteo_negativo:
            sentimiento = "positivo"
        elif conteo_negativo > conteo_positivo:
            sentimiento = "negativo"
        else:
            sentimiento = "neutral"
        
        resumen_clientes.append({
            "cliente_id": cliente.id,
            "cliente_nombre": cliente.name,
            "cliente_email": cliente.email,
            "cliente_telefono": cliente.phone if hasattr(cliente, 'phone') else "",
            "sentimiento_general": sentimiento,
            "conteo_sentimiento": {"positivo": conteo_positivo, "negativo": conteo_negativo, "neutral": max(0, len(interacciones) - conteo_positivo - conteo_negativo)},
            "total_interacciones": len(interacciones),
            "total_ventas": total_ventas_cliente,
            "total_gastado": float(total_gastado_cliente),
            "lifetime_value": float(cliente.lifetime_value) if cliente.lifetime_value else 0,
            "ultima_interaccion": interacciones.last().created_at.strftime("%Y-%m-%d %H:%M") if interacciones.exists() else None,
            "puntos_clave": puntos_clave[-10:],
            "recomendacion": "Seguimiento personalizado y ofertas exclusivas" if sentimiento == "positivo" else "Contacto inmediato para resolver problemas" if sentimiento == "negativo" else "Mantenimiento de relación regular"
        })
    
    if total_positivo > total_negativo:
        sentimiento_general = "positivo"
    elif total_negativo > total_positivo:
        sentimiento_general = "negativo"
    else:
        sentimiento_general = "neutral"
    
    return {
        "total_clientes": len(clientes_db),
        "total_interacciones": total_interacciones,
        "total_ventas": total_ventas_todas,
        "total_gastado": float(total_gastado_todos),
        "sentimiento_general_global": sentimiento_general,
        "conteo_sentimiento_global": {"positivo": total_positivo, "negativo": total_negativo, "neutral": max(0, total_interacciones - total_positivo - total_negativo)},
        "resumen_por_cliente": resumen_clientes,
        "recomendaciones_generales": [
            "Continuar con el trato personalizado y mantener la calidad del servicio" if sentimiento_general == "positivo" else "Implementar plan de mejora de experiencia del cliente y encuestas de satisfacción",
            f"Enfocarse en los {len([c for c in resumen_clientes if c['sentimiento_general'] == 'negativo'])} clientes con sentimiento negativo",
            f"Promover ofertas a los {len([c for c in resumen_clientes if c['total_gastado'] > 0])} clientes que ya han comprado"
        ]
    }


def analizar_finanzas(organization, periodo_inicio=None, periodo_fin=None):
    """
    Analiza finanzas del período.
    """
    from apps.finance.models import Income, Expense
    from django.db.models import Sum
    
    hoy = timezone.localdate()
    if not periodo_inicio:
        periodo_inicio = (hoy - timedelta(days=30)).isoformat()
    if not periodo_fin:
        periodo_fin = hoy.isoformat()
    
    ingresos_qs = Income.objects.filter(
        organization=organization,
        date__gte=periodo_inicio,
        date__lte=periodo_fin
    )
    gastos_qs = Expense.objects.filter(
        organization=organization,
        date__gte=periodo_inicio,
        date__lte=periodo_fin
    )
    
    total_ingresos = float(ingresos_qs.aggregate(Sum('amount'))['amount__sum'] or 0)
    total_gastos = float(gastos_qs.aggregate(Sum('amount'))['amount__sum'] or 0)
    utilidad = total_ingresos - total_gastos
    margen = (utilidad / total_ingresos * 100) if total_ingresos > 0 else 0
    
    # Categorizar gastos
    gastos_por_categoria = {}
    for gasto in gastos_qs:
        cat = gasto.get_category_display() if hasattr(gasto, 'get_category_display') else gasto.category
        if cat not in gastos_por_categoria:
            gastos_por_categoria[cat] = 0
        gastos_por_categoria[cat] += float(gasto.amount)
    
    # Categorizar ingresos
    ingresos_por_categoria = {}
    for ingreso in ingresos_qs:
        cat = ingreso.get_type_display() if hasattr(ingreso, 'get_type_display') else ingreso.type
        if cat not in ingresos_por_categoria:
            ingresos_por_categoria[cat] = 0
        ingresos_por_categoria[cat] += float(ingreso.amount)
    
    alerta = margen < 10 or total_gastos > total_ingresos * 0.9
    
    return {
        "periodo": {"inicio": periodo_inicio, "fin": periodo_fin},
        "resumen": {
            "total_ingresos": float(total_ingresos),
            "total_gastos": float(total_gastos),
            "utilidad": float(utilidad),
            "margen_porcentaje": float(round(margen, 2))
        },
        "gastos_por_categoria": gastos_por_categoria,
        "ingresos_por_categoria": ingresos_por_categoria,
        "alerta": alerta,
        "recomendaciones": [
            "Revisar gastos mayores" if alerta else "Mantener estrategia actual",
            "Aumentar ventas en categorías con mejor margen"
        ]
    }


def recomendar_precios(organization, categoria_id=None):
    """
    Recomienda precios óptimos.
    """
    from apps.inventory.models import Product, Category
    from apps.sales.models import SaleItem
    from django.db.models import Sum
    
    hoy = timezone.localdate()
    inicio = hoy - timedelta(days=30)
    
    productos_qs = Product.objects.filter(organization=organization, is_active=True)
    if categoria_id:
        productos_qs = productos_qs.filter(category_id=categoria_id)
    
    productos = []
    for product in productos_qs[:50]:
        ventas = SaleItem.objects.filter(
            organization=organization,
            product=product,
            sale__status='paid',
            sale__created_at__date__gte=inicio,
        ).aggregate(total=Sum('quantity'))['total'] or 0
        ventas = int(ventas)
        demanda = 'alta' if ventas >= 20 else 'media' if ventas >= 5 else 'baja'
        
        productos.append({
            "id": product.id,
            "nombre": product.name,
            "precio_actual": float(product.price),
            "precio_costo": float(product.cost) if product.cost else 0,
            "ventas_ultimos_30d": ventas,
            "demanda": demanda,
        })
    
    recomendaciones = []
    
    for producto in productos:
        margen_ideal = 0.5
        precio_minimo = producto["precio_costo"] * 1.2
        precio_sugerido = producto["precio_costo"] * (1 + margen_ideal)
        
        if producto["demanda"] == "alta":
            precio_sugerido *= 1.1
        elif producto["demanda"] == "baja":
            precio_sugerido *= 0.9
        
        recomendaciones.append({
            "producto_id": producto["id"],
            "producto_nombre": producto["nombre"],
            "precio_actual": float(producto["precio_actual"]),
            "precio_costo": float(producto["precio_costo"]),
            "precio_sugerido": float(round(precio_sugerido, 2)),
            "precio_minimo": float(round(precio_minimo, 2)),
            "margen_sugerido": float(round((precio_sugerido - producto["precio_costo"]) / precio_sugerido * 100, 2)) if precio_sugerido > 0 else 0,
            "justificacion": "Demanda alta, puede incrementar precio" if producto["demanda"] == "alta" else "Demanda baja, considera reducir precio" if producto["demanda"] == "baja" else "Demanda media, mantener margen ideal"
        })
    
    return {
        "total_productos": len(productos),
        "recomendaciones": recomendaciones
    }


def analizar_rrhh(organization, dias=30):
    """
    Analiza salud operativa de RRHH con datos resumidos del módulo.
    """
    from apps.hr.models import Employee, Attendance, LeaveRequest, Payroll
    from django.db.models import Count
    
    hoy = timezone.localdate()
    inicio = hoy - timedelta(days=dias)
    
    empleados = Employee.objects.filter(organization=organization).select_related('department', 'position')
    activos = [e for e in empleados if e.status == "active"]
    bajas = [e for e in empleados if e.status in ("inactive", "terminated")]
    
    asistencias = Attendance.objects.filter(organization=organization, date__gte=inicio, date__lte=hoy).select_related('employee')
    tardanzas = [a for a in asistencias if a.status == "late"]
    ausencias = [a for a in asistencias if a.status == "absent"]
    
    permisos = LeaveRequest.objects.filter(organization=organization, created_at__date__gte=inicio)
    permisos_pendientes = [p for p in permisos if p.status == "pending"]
    
    nominas = Payroll.objects.filter(organization=organization, period_end__gte=inicio)
    nomina_total = sum(n.net_salary for n in nominas) if nominas.exists() else 0
    salario_promedio = sum(e.salary for e in activos) / len(activos) if activos else 0
    
    rotacion_riesgo = len(bajas) > max(1, len(empleados) * 0.15)
    asistencia_riesgo = (len(tardanzas) + len(ausencias)) > max(2, len(activos) * 0.2)
    
    recomendaciones = []
    if permisos_pendientes:
        recomendaciones.append("Revisar permisos pendientes para evitar atrasos administrativos.")
    if asistencia_riesgo:
        recomendaciones.append("Analizar patrones de ausencias y retardos por área o turno.")
    if rotacion_riesgo:
        recomendaciones.append("Revisar causas de baja y permanencia del personal.")
    if not recomendaciones:
        recomendaciones.append("Mantener seguimiento mensual de asistencia, rotación y nómina.")
    
    return {
        "resumen": {
            "total_empleados": len(empleados),
            "empleados_activos": len(activos),
            "bajas_o_inactivos": len(bajas),
            "salario_promedio": float(round(salario_promedio, 2)),
            "nomina_neta_periodo": float(round(nomina_total, 2)),
        },
        "asistencia": {
            "registros": len(asistencias),
            "tardanzas": len(tardanzas),
            "ausencias": len(ausencias),
            "riesgo": asistencia_riesgo,
        },
        "permisos": {
            "total": len(permisos),
            "pendientes": len(permisos_pendientes),
        },
        "alerta": rotacion_riesgo or asistencia_riesgo or len(permisos_pendientes) > 0,
        "recomendaciones": recomendaciones,
    }


def analizar_logistica(organization, dias=30):
    """
    Analiza estado operativo de logística y entregas.
    """
    from apps.logistics.models import Shipment, Order, Route
    from django.db.models import Count, Sum
    
    hoy = timezone.localdate()
    inicio = hoy - timedelta(days=dias)
    
    envios = Shipment.objects.filter(organization=organization, created_at__date__gte=inicio).select_related('carrier', 'route')
    pedidos = Order.objects.filter(organization=organization, created_at__date__gte=inicio)
    rutas = Route.objects.filter(organization=organization)
    
    estados = {}
    for envio in envios:
        estado = envio.status
        estados[estado] = estados.get(estado, 0) + 1
    
    fallidos = [e for e in envios if e.status in ("failed", "returned")]
    transito = [e for e in envios if e.status in ("picked_up", "in_transit", "out_for_delivery")]
    intentos_altos = [e for e in envios if e.delivery_attempts >= 2]
    costo_total = sum(e.shipping_cost for e in envios)
    pedidos_pendientes = [p for p in pedidos if p.status in ("pending", "confirmed", "processing")]
    rutas_activas = [r for r in rutas if r.is_active]
    
    recomendaciones = []
    if fallidos:
        recomendaciones.append("Priorizar recontacto de entregas fallidas o devueltas.")
    if intentos_altos:
        recomendaciones.append("Validar dirección y teléfono antes de nuevos intentos.")
    if pedidos_pendientes:
        recomendaciones.append("Revisar pedidos pendientes para programar despacho.")
    if not rutas_activas and envios:
        recomendaciones.append("Asignar rutas activas para mejorar trazabilidad.")
    if not recomendaciones:
        recomendaciones.append("Mantener monitoreo de costo por envío y tiempos de entrega.")
    
    return {
        "resumen": {
            "total_envios": len(envios),
            "total_pedidos": len(pedidos),
            "rutas_activas": len(rutas_activas),
            "envios_en_transito": len(transito),
            "envios_fallidos": len(fallidos),
            "costo_total_envios": float(round(costo_total, 2)),
            "costo_promedio_envio": float(round(costo_total / len(envios), 2)) if envios else 0,
        },
        "estados": estados,
        "intentos_altos": len(intentos_altos),
        "pedidos_pendientes": len(pedidos_pendientes),
        "alerta": bool(fallidos or intentos_altos or pedidos_pendientes),
        "recomendaciones": recomendaciones,
    }


def obtener_ventas_recientes(organization, limite=10, estado=None):
    """
    Obtiene ventas recientes.
    """
    from apps.sales.models import Sale
    
    ventas_qs = Sale.objects.filter(organization=organization).select_related('customer', 'created_by').order_by('-created_at')
    if estado:
        ventas_qs = ventas_qs.filter(status=estado)
    
    ventas = []
    for venta in ventas_qs[:limite]:
        items = []
        for item in venta.items.all():
            items.append({
                "producto": item.product.name if item.product else "Producto eliminado",
                "cantidad": item.quantity,
                "precio_unitario": float(item.unit_price),
                "total": float(item.total)
            })
        
        ventas.append({
            "id": venta.id,
            "numero": venta.number,
            "cliente": venta.customer.name if venta.customer else "Cliente genérico",
            "total": float(venta.total),
            "estado": venta.status,
            "tipo": venta.type,
            "fecha": venta.created_at.strftime("%Y-%m-%d %H:%M"),
            "vendedor": venta.created_by.username if venta.created_by else "Sistema",
            "items": items
        })
    
    return {
        "total_ventas": len(ventas),
        "ventas": ventas
    }


def obtener_productos_bajo_stock(organization):
    """
    Obtiene productos con stock bajo.
    """
    from apps.inventory.models import Product, Stock
    
    productos_bajo_stock = []
    productos = Product.objects.filter(organization=organization).prefetch_related('stocks')
    
    for p in productos:
        stock_total = sum(s.quantity for s in p.stocks.all())
        stock_minimo = sum(s.min_quantity for s in p.stocks.all()) or 10
        
        if stock_total < stock_minimo:
            productos_bajo_stock.append({
                "id": p.id,
                "nombre": p.name,
                "sku": p.sku,
                "stock_actual": stock_total,
                "stock_minimo": stock_minimo,
                "diferencia": stock_minimo - stock_total
            })
    
    return {
        "total_productos": len(productos),
        "productos_bajo_stock": productos_bajo_stock,
        "alerta": len(productos_bajo_stock) > 0
    }


def obtener_clientes_top(organization, limite=10):
    """
    Obtiene clientes con mayor LTV.
    """
    from apps.crm.models import Customer
    
    clientes = Customer.objects.filter(organization=organization).order_by('-lifetime_value')[:limite]
    
    clientes_top = []
    for cliente in clientes:
        clientes_top.append({
            "id": cliente.id,
            "nombre": cliente.name,
            "email": cliente.email,
            "telefono": cliente.phone if hasattr(cliente, 'phone') else "",
            "lifetime_value": float(cliente.lifetime_value),
            "total_compras": cliente.total_orders,
            "ultima_compra": cliente.last_purchase_date.isoformat() if cliente.last_purchase_date else None
        })
    
    return {
        "total_clientes": len(clientes),
        "clientes_top": clientes_top
    }


def generar_reporte_ventas(organization, periodo="monthly", fecha_inicio=None, fecha_fin=None):
    """
    Genera reporte de ventas.
    """
    from apps.sales.models import Sale, SaleItem
    from django.db.models import Sum, Count
    from apps.inventory.models import Product
    
    hoy = timezone.localdate()
    if not fecha_inicio:
        if periodo == "daily":
            fecha_inicio = hoy.isoformat()
            fecha_fin = hoy.isoformat()
        elif periodo == "weekly":
            fecha_inicio = (hoy - timedelta(days=7)).isoformat()
            fecha_fin = hoy.isoformat()
        elif periodo == "monthly":
            fecha_inicio = (hoy - timedelta(days=30)).isoformat()
            fecha_fin = hoy.isoformat()
        elif periodo == "quarterly":
            fecha_inicio = (hoy - timedelta(days=90)).isoformat()
            fecha_fin = hoy.isoformat()
        elif periodo == "yearly":
            fecha_inicio = (hoy - timedelta(days=365)).isoformat()
            fecha_fin = hoy.isoformat()
    
    ventas = Sale.objects.filter(
        organization=organization,
        status='paid',
        created_at__date__gte=fecha_inicio,
        created_at__date__lte=fecha_fin
    )
    
    total_ventas = ventas.aggregate(Sum('total'))['total__sum'] or 0
    total_pedidos = ventas.count()
    promedio_pedido = total_ventas / total_pedidos if total_pedidos > 0 else 0
    
    # Productos top
    items_top = SaleItem.objects.filter(
        organization=organization,
        sale__in=ventas
    ).values('product__id', 'product__name').annotate(
        total_cantidad=Sum('quantity'),
        total_ventas=Sum('total')
    ).order_by('-total_ventas')[:10]
    
    productos_top = []
    for item in items_top:
        productos_top.append({
            "producto_id": item['product__id'],
            "producto_nombre": item['product__name'],
            "total_cantidad": item['total_cantidad'],
            "total_ventas": float(item['total_ventas'])
        })
    
    return {
        "periodo": periodo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "total_ventas": float(total_ventas),
        "total_pedidos": total_pedidos,
        "promedio_pedido": float(round(promedio_pedido, 2)),
        "productos_top": productos_top
    }


def chat_with_ai(user_message, conversation_history=None, user=None, organization=None):
    """
    Función de chat general con soporte para function calling y persistencia en BD.
    """
    # Obtener o crear conversación
    if user and organization:
        conversation, created = Conversation.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={"title": user_message[:50] if len(user_message) > 50 else user_message}
        )
    else:
        conversation = None
    
    if not conversation_history:
        conversation_history = []
        # Cargar historial de BD si existe
        if conversation:
            for msg in conversation.messages.all():
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
    
    # Guardar mensaje de usuario
    if conversation:
        Message.objects.create(
            conversation=conversation,
            organization=organization,
            role="user",
            content=user_message
        )
    
    conversation_history.append({"role": "user", "content": user_message})
    
    response_message = call_gemma_with_function_calling(conversation_history)
    
    conversation_history.append(response_message)
    
    tool_response = None
    function_called = None
    
    if response_message.tool_calls:
        tool_call = response_message.tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        # Ejecutar la herramienta correspondiente
        if function_name == "analizar_inventario_y_sugerir_compras":
            tool_response = analizar_inventario_y_sugerir_compras(organization, **function_args)
        elif function_name == "analizar_cliente_crm":
            tool_response = analizar_cliente_crm(organization, **function_args)
        elif function_name == "analizar_finanzas":
            tool_response = analizar_finanzas(organization, **function_args)
        elif function_name == "recomendar_precios":
            tool_response = recomendar_precios(organization, **function_args)
        elif function_name == "analizar_rrhh":
            tool_response = analizar_rrhh(organization, **function_args)
        elif function_name == "analizar_logistica":
            tool_response = analizar_logistica(organization, **function_args)
        elif function_name == "obtener_ventas_recientes":
            tool_response = obtener_ventas_recientes(organization, **function_args)
        elif function_name == "obtener_productos_bajo_stock":
            tool_response = obtener_productos_bajo_stock(organization)
        elif function_name == "obtener_clientes_top":
            tool_response = obtener_clientes_top(organization, **function_args)
        elif function_name == "generar_reporte_ventas":
            tool_response = generar_reporte_ventas(organization, **function_args)
        
        function_called = function_name
        
        if tool_response:
            conversation_history.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(tool_response, ensure_ascii=False, default=str)
            })
            
            # Guardar mensaje de tool
            if conversation:
                Message.objects.create(
                    conversation=conversation,
                    organization=organization,
                    role="tool",
                    content="",
                    tool_call_id=tool_call.id,
                    tool_name=function_name,
                    tool_result=tool_response
                )
            
            final_response = call_gemma_with_function_calling(conversation_history)
            conversation_history.append(final_response)
            
            # Guardar mensaje final del assistant
            if conversation:
                Message.objects.create(
                    conversation=conversation,
                    organization=organization,
                    role="assistant",
                    content=final_response.content
                )
            
            return {
                "response": final_response.content,
                "function_called": function_called,
                "tool_result": tool_response,
                "conversation_id": conversation.id if conversation else None
            }
    
    # Guardar mensaje del assistant sin function calling
    if conversation:
        Message.objects.create(
            conversation=conversation,
            organization=organization,
            role="assistant",
            content=response_message.content
        )
    
    return {
        "response": response_message.content,
        "function_called": None,
        "tool_result": None,
        "conversation_id": conversation.id if conversation else None
    }
