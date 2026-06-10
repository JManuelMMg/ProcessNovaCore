from core.permissions import has_permission, ROLE_LABELS, get_user_role, MODULE_PERMISSIONS


def tenant_context(request):
    if not request.user.is_authenticated:
        return {}

    role = get_user_role(request.user)
    can = {module: has_permission(request.user, module) for module in MODULE_PERMISSIONS}

    return {
        'current_organization': getattr(request, 'organization', None),
        'current_branch': getattr(request, 'branch', None),
        'user_role': role,
        'user_role_label': ROLE_LABELS.get(role, role),
        'can': can,
    }
