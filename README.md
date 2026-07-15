# ProcessNovaCore

Sistema integral de gestión empresarial para pequeñas y medianas empresas que incluye:
- Punto de Venta (POS)
- Control de Inventario
- CRM
- Finanzas
- Recursos Humanos (HR)
- Logística
- Motor de Inteligencia Artificial

## Requisitos
- Python 3.10 o superior
- PostgreSQL (se recomienda Neon Postgres para serverless)
- Docker (opcional, para despliegue)
- Render (o similar, para despliegue en la nube)

## Instalación

1. Clona el repositorio
2. Crea un entorno virtual y actívalo:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Copia las variables de entorno y configúralas:
   ```bash
   # Crea un archivo .env en la raíz
   ```
5. Aplica las migraciones:
   ```bash
   python manage.py migrate
   ```
6. Crea un superusuario:
   ```bash
   python manage.py createsuperuser
   ```
7. Ejecuta el servidor:
   ```bash
   python manage.py runserver
   ```

## Estructura del Proyecto

- `apps/`: Contiene las aplicaciones del sistema
  - `ai_engine/`: Motor de IA para análisis y recomendaciones
  - `crm/`: Gestión de relaciones con clientes
  - `finance/`: Finanzas y facturación
  - `hr/`: Gestión de recursos humanos
  - `inventory/`: Control de inventario
  - `logistics/`: Logística y pedidos
  - `notifications/`: Notificaciones
  - `sales/`: Ventas y punto de venta
  - `users/`: Usuarios, sucursales y organización
- `core/`: Funcionalidades centrales, permisos, middleware
- `config/`: Configuración de Django
- `templates/`: Plantillas HTML

## Roles y Permisos

- `admin_central`: Administrador con acceso a todo
- `branch_manager`: Encargado de sucursal, puede gestionar inventario, empleados, finanzas básicas
- `employee`: Empleado básico, puede usar POS, ver inventario, ver clientes

## Variables de Entorno

Configura estas variables en tu entorno:
- `SECRET_KEY`: Clave secreta de Django
- `DEBUG`: Establece en False en producción
- `DATABASE_URL`: URL de conexión a PostgreSQL. Para Neon usa la cadena completa con `sslmode=require&channel_binding=require`.
- `ALLOWED_HOSTS`: Hosts permitidos

## Despliegue

El proyecto está listo para desplegar en Render, usa el archivo `render.yaml` provisto.

## Contribuciones

Antes de contribuir, lee las políticas de seguridad y la guía de estilo.

## Licencia

Copyright © 2026 ProcessNova
