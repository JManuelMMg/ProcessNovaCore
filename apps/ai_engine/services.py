from openai import OpenAI
from django.conf import settings
from django.core.exceptions import PermissionDenied
import json
from typing import List, Dict, Optional
from .models import Conversation, Message


# Configuración de permisos por rol
TOOL_PERMISSIONS = {
    'analizar_inventario_y_sugerir_compras': ['admin_central', 'branch_manager'],
    'analizar_cliente_crm': ['admin_central', 'branch_manager', 'employee'],
    'analizar_finanzas': ['admin_central', 'branch_manager'],
    'analizar_rrhh': ['admin_central'],
    'analizar_logistica': ['admin_central', 'branch_manager'],
    'recomendar_precios': ['admin_central', 'branch_manager'],
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
                    "productos": {
                        "type": "array",
                        "description": "Lista de productos con datos de stock y ventas",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "description": "ID del producto"},
                                "nombre": {"type": "string", "description": "Nombre del producto"},
                                "stock_actual": {"type": "integer", "description": "Stock disponible"},
                                "stock_minimo": {"type": "integer", "description": "Stock mínimo deseado"},
                                "ventas_ultimos_30d": {"type": "integer", "description": "Ventas últimos 30 días"},
                                "precio_costo": {"type": "number", "description": "Precio de costo"}
                            },
                            "required": ["id", "nombre", "stock_actual", "stock_minimo", "ventas_ultimos_30d", "precio_costo"]
                        }
                    }
                },
                "required": ["productos"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_cliente_crm",
            "description": "Analiza sentimiento y resumen del historial de interacciones del cliente. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente": {
                        "type": "object",
                        "description": "Datos básicos del cliente",
                        "properties": {
                            "id": {"type": "integer"},
                            "nombre": {"type": "string"},
                            "email": {"type": "string"}
                        },
                        "required": ["id", "nombre", "email"]
                    },
                    "interacciones": {
                        "type": "array",
                        "description": "Historial de interacciones con el cliente",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tipo": {"type": "string", "enum": ["call", "email", "meeting", "chat", "other"]},
                                "fecha": {"type": "string", "format": "date"},
                                "contenido": {"type": "string"}
                            },
                            "required": ["tipo", "fecha", "contenido"]
                        }
                    }
                },
                "required": ["cliente", "interacciones"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_finanzas",
            "description": "Analiza ingresos, gastos y rentabilidad. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "periodo_inicio": {"type": "string", "format": "date"},
                    "periodo_fin": {"type": "string", "format": "date"},
                    "ingresos": {"type": "array", "items": {"type": "object", "properties": {"fecha": {"type": "string"}, "monto": {"type": "number"}, "categoria": {"type": "string"}}}},
                    "gastos": {"type": "array", "items": {"type": "object", "properties": {"fecha": {"type": "string"}, "monto": {"type": "number"}, "categoria": {"type": "string"}}}},
                },
                "required": ["periodo_inicio", "periodo_fin", "ingresos", "gastos"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recomendar_precios",
            "description": "Recomienda precios óptimos para productos. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "productos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "nombre": {"type": "string"},
                                "precio_actual": {"type": "number"},
                                "precio_costo": {"type": "number"},
                                "ventas_ultimos_30d": {"type": "integer"},
                                "demanda": {"type": "string", "enum": ["alta", "media", "baja"]}
                            },
                            "required": ["id", "nombre", "precio_actual", "precio_costo", "ventas_ultimos_30d", "demanda"]
                        }
                    }
                },
                "required": ["productos"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_rrhh",
            "description": "Analiza indicadores de recursos humanos: empleados, asistencia, permisos y nomina. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "empleados": {"type": "array", "items": {"type": "object"}},
                    "asistencias": {"type": "array", "items": {"type": "object"}},
                    "permisos": {"type": "array", "items": {"type": "object"}},
                    "nominas": {"type": "array", "items": {"type": "object"}}
                },
                "required": ["empleados", "asistencias", "permisos", "nominas"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_logistica",
            "description": "Analiza pedidos, envios, intentos de entrega, rutas y costos logisticos. Devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "envios": {"type": "array", "items": {"type": "object"}},
                    "pedidos": {"type": "array", "items": {"type": "object"}},
                    "rutas": {"type": "array", "items": {"type": "object"}}
                },
                "required": ["envios", "pedidos", "rutas"]
            }
        }
    }
]

SYSTEM_PROMPT_OPERATIVO = """Eres Nova, el Motor de Inteligencia Operativa y asistente amigable de ProcessNova, un ERP para PYMES mexicanas.

TU DOBLE FUNCIÓN:
1. **Interacción conversacional normal**: Cuando el usuario hable de temas generales, respondas en español de forma natural, amigable y útil.
2. **Análisis técnico con Function Calling**: Cuando el usuario pida análisis de inventario, CRM, finanzas, RRHH, logística o recomendaciones de precios, usa las herramientas disponibles para generar resultados estructurados.

REGLAS:
- Para conversaciones normales (saludos, preguntas sobre el sistema, ayuda general): responde de forma conversacional, clara y en español.
- Para análisis técnicos: usa las funciones (function calling) disponibles para inventario, CRM, finanzas, RRHH, logística y precios.
- Si detectas stock crítico o problemas financieros, marca 'alerta' como true en tu respuesta.
- Siempre prioriza la precisión cuando uses funciones, pero mantén la naturalidad en conversaciones normales."""


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
        max_tokens=2048,
        tools=tools
    )
    
    return response.choices[0].message


def analizar_inventario_y_sugerir_compras(productos: List[Dict]) -> Dict:
    """
    Función simulada de análisis de inventario. En producción, se conectaría con modelos reales.
    """
    sugerencias = []
    alerta_general = False
    
    for producto in productos:
        # Cálculo simple de demanda mensual
        demanda_mensual = producto["ventas_ultimos_30d"]
        stock_actual = producto["stock_actual"]
        stock_minimo = producto["stock_minimo"]
        
        # Nivel de reorden: 2x demanda mensual
        nivel_reorden = int(demanda_mensual * 1.5)
        cantidad_a_comprar = 0
        alerta = False
        
        if stock_actual < stock_minimo:
            alerta = True
            alerta_general = True
            # Comprar 2x la demanda mensual para reposición
            cantidad_a_comprar = nivel_reorden
        
        sugerencias.append({
            "producto_id": producto["id"],
            "producto_nombre": producto["nombre"],
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


def analizar_cliente_crm(cliente: Dict, interacciones: List[Dict]) -> Dict:
    """
    Función simulada de análisis de CRM.
    """
    from datetime import datetime
    
    # Análisis simple de sentimiento (palabras clave)
    palabras_positivas = ["excelente", "feliz", "contento", "perfecto", "gracias", "mejor"]
    palabras_negativas = ["mal", "enojo", "problema", "defectuoso", "queja", "insatisfecho"]
    
    conteo_positivo = 0
    conteo_negativo = 0
    puntos_clave = []
    
    for interaccion in interacciones:
        contenido = interaccion["contenido"].lower()
        for palabra in palabras_positivas:
            if palabra in contenido:
                conteo_positivo += 1
        for palabra in palabras_negativas:
            if palabra in contenido:
                conteo_negativo += 1
        # Extraer puntos clave (primeras 50 caracteres de cada interacción)
        puntos_clave.append(f"[{interaccion['fecha']} - {interaccion['tipo']}] {contenido[:70]}...")
    
    if conteo_positivo > conteo_negativo:
        sentimiento = "positivo"
    elif conteo_negativo > conteo_positivo:
        sentimiento = "negativo"
    else:
        sentimiento = "neutral"
    
    return {
        "cliente_id": cliente["id"],
        "cliente_nombre": cliente["nombre"],
        "cliente_email": cliente["email"],
        "sentimiento_general": sentimiento,
        "conteo_sentimiento": {"positivo": conteo_positivo, "negativo": conteo_negativo, "neutral": max(0, len(interacciones) - conteo_positivo - conteo_negativo)},
        "total_interacciones": len(interacciones),
        "ultima_interaccion": interacciones[-1]["fecha"] if interacciones else None,
        "puntos_clave": puntos_clave[-5:],  # Últimos 5 puntos clave
        "recomendaciones": [
            "Seguimiento personalizado" if sentimiento == "positivo" else "Atención inmediata" if sentimiento == "negativo" else "Mantenimiento regular"
        ]
    }


def analizar_finanzas(periodo_inicio: str, periodo_fin: str, ingresos: List[Dict], gastos: List[Dict]) -> Dict:
    """
    Analiza finanzas del período.
    """
    total_ingresos = sum(i["monto"] for i in ingresos)
    total_gastos = sum(g["monto"] for g in gastos)
    utilidad = total_ingresos - total_gastos
    margen = (utilidad / total_ingresos * 100) if total_ingresos > 0 else 0
    
    # Categorizar gastos
    gastos_por_categoria = {}
    for gasto in gastos:
        cat = gasto["categoria"]
        if cat not in gastos_por_categoria:
            gastos_por_categoria[cat] = 0
        gastos_por_categoria[cat] += gasto["monto"]
    
    # Categorizar ingresos
    ingresos_por_categoria = {}
    for ingreso in ingresos:
        cat = ingreso["categoria"]
        if cat not in ingresos_por_categoria:
            ingresos_por_categoria[cat] = 0
        ingresos_por_categoria[cat] += ingreso["monto"]
    
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


def recomendar_precios(productos: List[Dict]) -> Dict:
    """
    Recomienda precios óptimos.
    """
    recomendaciones = []
    
    for producto in productos:
        # Margen ideal: 50%
        margen_ideal = 0.5
        precio_minimo = producto["precio_costo"] * 1.2  # 20% mínimo
        precio_sugerido = producto["precio_costo"] * (1 + margen_ideal)
        
        # Ajustar por demanda
        if producto["demanda"] == "alta":
            precio_sugerido *= 1.1  # +10%
        elif producto["demanda"] == "baja":
            precio_sugerido *= 0.9  # -10%
        
        recomendaciones.append({
            "producto_id": producto["id"],
            "producto_nombre": producto["nombre"],
            "precio_actual": float(producto["precio_actual"]),
            "precio_costo": float(producto["precio_costo"]),
            "precio_sugerido": float(round(precio_sugerido, 2)),
            "precio_minimo": float(round(precio_minimo, 2)),
            "margen_sugerido": float(round((precio_sugerido - producto["precio_costo"]) / precio_sugerido * 100, 2)),
            "justificacion": "Demanda alta, puede incrementar precio" if producto["demanda"] == "alta" else "Demanda baja, considera reducir precio" if producto["demanda"] == "baja" else "Demanda media, mantener margen ideal"
        })
    
    return {
        "total_productos": len(productos),
        "recomendaciones": recomendaciones
    }


def analizar_rrhh(empleados: List[Dict], asistencias: List[Dict], permisos: List[Dict], nominas: List[Dict]) -> Dict:
    """
    Analiza salud operativa de RRHH con datos resumidos del modulo.
    """
    activos = [e for e in empleados if e.get("status") == "active"]
    bajas = [e for e in empleados if e.get("status") in ("inactive", "terminated")]
    tardanzas = [a for a in asistencias if a.get("status") == "late"]
    ausencias = [a for a in asistencias if a.get("status") == "absent"]
    permisos_pendientes = [p for p in permisos if p.get("status") == "pending"]
    nomina_total = sum(n.get("net_salary", 0) for n in nominas)
    salario_promedio = sum(e.get("salary", 0) for e in activos) / len(activos) if activos else 0
    rotacion_riesgo = len(bajas) > max(1, len(empleados) * 0.15)
    asistencia_riesgo = (len(tardanzas) + len(ausencias)) > max(2, len(activos) * 0.2)

    recomendaciones = []
    if permisos_pendientes:
        recomendaciones.append("Revisar permisos pendientes para evitar atrasos administrativos.")
    if asistencia_riesgo:
        recomendaciones.append("Analizar patrones de ausencias y retardos por area o turno.")
    if rotacion_riesgo:
        recomendaciones.append("Revisar causas de baja y permanencia del personal.")
    if not recomendaciones:
        recomendaciones.append("Mantener seguimiento mensual de asistencia, rotacion y nomina.")

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


def analizar_logistica(envios: List[Dict], pedidos: List[Dict], rutas: List[Dict]) -> Dict:
    """
    Analiza estado operativo de logistica y entregas.
    """
    estados = {}
    for envio in envios:
        estado = envio.get("status", "sin_estado")
        estados[estado] = estados.get(estado, 0) + 1

    fallidos = [e for e in envios if e.get("status") in ("failed", "returned")]
    transito = [e for e in envios if e.get("status") in ("picked_up", "in_transit", "out_for_delivery")]
    intentos_altos = [e for e in envios if e.get("delivery_attempts", 0) >= 2]
    costo_total = sum(e.get("shipping_cost", 0) for e in envios)
    pedidos_pendientes = [p for p in pedidos if p.get("status") in ("pending", "confirmed", "processing")]
    rutas_activas = [r for r in rutas if r.get("is_active")]

    recomendaciones = []
    if fallidos:
        recomendaciones.append("Priorizar recontacto de entregas fallidas o devueltas.")
    if intentos_altos:
        recomendaciones.append("Validar direccion y telefono antes de nuevos intentos.")
    if pedidos_pendientes:
        recomendaciones.append("Revisar pedidos pendientes para programar despacho.")
    if not rutas_activas and envios:
        recomendaciones.append("Asignar rutas activas para mejorar trazabilidad.")
    if not recomendaciones:
        recomendaciones.append("Mantener monitoreo de costo por envio y tiempos de entrega.")

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
        
        if function_name == "analizar_inventario_y_sugerir_compras":
            tool_response = analizar_inventario_y_sugerir_compras(**function_args)
        elif function_name == "analizar_cliente_crm":
            tool_response = analizar_cliente_crm(**function_args)
        elif function_name == "analizar_finanzas":
            tool_response = analizar_finanzas(**function_args)
        elif function_name == "recomendar_precios":
            tool_response = recomendar_precios(**function_args)
        elif function_name == "analizar_rrhh":
            tool_response = analizar_rrhh(**function_args)
        elif function_name == "analizar_logistica":
            tool_response = analizar_logistica(**function_args)
        
        function_called = function_name
        
        if tool_response:
            conversation_history.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(tool_response, ensure_ascii=False)
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
