from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

ROLE_ADMIN = 'admin_central'
ROLE_BRANCH_MANAGER = 'branch_manager'
ROLE_EMPLOYEE = 'employee'

ROLE_LABELS = {
    ROLE_ADMIN: 'Administrador Central',
    ROLE_BRANCH_MANAGER: 'Encargado de Sucursal',
    ROLE_EMPLOYEE: 'Empleado',
}

MODULE_PERMISSIONS = {
    'dashboard': [ROLE_ADMIN, ROLE_BRANCH_MANAGER, ROLE_EMPLOYEE],
    'pos': [ROLE_ADMIN, ROLE_BRANCH_MANAGER, ROLE_EMPLOYEE],
    'inventory_view': [ROLE_ADMIN, ROLE_BRANCH_MANAGER, ROLE_EMPLOYEE],
    'inventory_create': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
    'inventory_edit': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
    'sales_history': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
    'crm': [ROLE_ADMIN, ROLE_BRANCH_MANAGER, ROLE_EMPLOYEE],
    'finance': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
    'hr': [ROLE_ADMIN],
    'hr_view': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
    'hr_create': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
    'hr_edit': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
    'logistics': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
    'ai': [ROLE_ADMIN, ROLE_BRANCH_MANAGER, ROLE_EMPLOYEE],
    'users_manage': [ROLE_ADMIN],
    'branches_manage': [ROLE_ADMIN],
    'email': [ROLE_ADMIN, ROLE_BRANCH_MANAGER],
}


def get_user_role(user):
    if user.is_superuser:
        return ROLE_ADMIN
    try:
        return user.membership.role
    except Exception:
        return ROLE_EMPLOYEE


def has_permission(user, module):
    if user.is_superuser:
        return True
    role = get_user_role(user)
    return role in MODULE_PERMISSIONS.get(module, [])


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            role = get_user_role(request.user)
            if request.user.is_superuser or role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'No tienes permiso para acceder a esta sección.')
            return redirect('dashboard')
        return wrapper
    return decorator


def permission_required(module):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if not has_permission(request.user, module):
                messages.error(request, 'No tienes permiso para acceder a esta sección.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def tenant_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.organization:
            messages.error(request, 'Tu cuenta no está vinculada a una organización.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
