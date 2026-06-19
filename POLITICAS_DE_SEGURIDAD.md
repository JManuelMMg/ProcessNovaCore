# Políticas de Seguridad de ProcessNovaCore

## 1. Protección de Datos
- **Cifrado en tránsito**: Todo el tráfico debe usar HTTPS, obligatorio en producción.
- **Cifrado en reposo**: La base de datos (PostgreSQL) debe estar cifrada.
- **Claves secretas**: La `SECRET_KEY` y cualquier otra credencial deben estar en variables de entorno, NUNCA en código o repositorio.

## 2. Acceso y Permisos
- **Principio de mínimo privilegio**: Los usuarios solo pueden acceder a lo necesario.
- **Roles**:
  - `admin_central`: Acceso completo.
  - `branch_manager`: Acceso a la sucursal asignada.
  - `employee`: Acceso limitado a POS y vistas de lectura.
- **Sesiones**: Las sesiones expiran automáticamente después de 1 hora de inactividad.

## 3. Código y Desarrollo
- **Validación de entrada**: Todas las entradas del usuario deben ser validadas en el servidor.
- **SQL Injection**: Usamos ORM de Django, NO consultas SQL crudas.
- **XSS**: Las plantillas de Django escapan automáticamente la salida.
- **CSRF**: Todas las peticiones POST usan el token CSRF.

## 4. Despliegue
- **DEBUG = False**: En producción, el modo DEBUG DEBE estar DESACTIVADO.
- **ALLOWED_HOSTS**: No usar '*', especificar dominios autorizados.
- **HSTS**: Habilitado para un año.
- **Cookies seguras**: Cookies marcadas como `Secure` y `HttpOnly`.

## 5. Auditoría y Monitoreo
- **Log de auditoría**: Se usa `django-auditlog` para registrar cambios en modelos importantes.
- **Logs**: Todas las peticiones, errores y eventos importantes deben ser registrados.

## 6. Respuesta a Incidentes
- Reportar incidentes de seguridad a security@processnova.mx
- Seguir procedimientos de respuesta en caso de vulnerabilidades.

## 7. Copias de Seguridad
- Realizar copias de seguridad de la base de datos periódicamente.
- Almacenar copias de seguridad en lugar seguro, separado del servidor de producción.
