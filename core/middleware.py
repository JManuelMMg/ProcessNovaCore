from apps.users.models import Membership, Branch
from django.core.cache import cache
from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Middleware para agregar headers de seguridad avanzados.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Content Security Policy (CSP) - Aplicada
        csp = getattr(settings, 'SECURE_CSP', {})
        if csp:
            csp_header = '; '.join([f'{key} {value}' for key, value in csp.items()])
            response['Content-Security-Policy'] = csp_header
        
        # X-XSS-Protection (modern browsers use CSP, pero lo agregamos para compatibilidad)
        response['X-XSS-Protection'] = '1; mode=block'
        
        # X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Permissions-Policy (reemplaza Feature-Policy)
        response['Permissions-Policy'] = (
            'geolocation=(), camera=(), microphone=(), payment=(), usb=(), bluetooth=(), '
            'gyroscope=(), accelerometer=(), magnetometer=()'
        )
        
        return response


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.membership = None
        request.user_role = 'employee'
        request.branch = None

        if request.user.is_authenticated:
            # Usar cache por usuario (5 minutos)
            cache_key = f'membership_{request.user.id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                request.membership = cached_data['membership']
                request.organization = cached_data['organization']
                request.user_role = cached_data['role']
                # Solo recuperar branch de sesión o default
                branch_id = request.session.get('active_branch_id')
                if branch_id:
                    request.branch = Branch.objects.filter(
                        id=branch_id,
                        organization=request.organization,
                        is_active=True,
                    ).first()
                
                if not request.branch:
                    request.branch = cached_data.get('default_branch')
            else:
                try:
                    membership = Membership.objects.select_related(
                        'organization', 'branch'
                    ).get(user=request.user)
                    request.membership = membership
                    request.organization = membership.organization
                    request.user_role = membership.role

                    # Obtener todas las branches en una query
                    branch_id = request.session.get('active_branch_id')
                    default_branch = None
                    
                    if branch_id:
                        request.branch = Branch.objects.filter(
                            id=branch_id,
                            organization=membership.organization,
                            is_active=True,
                        ).first()
                    
                    if not request.branch:
                        request.branch = membership.branch
                    
                    if not request.branch:
                        # Una sola query para obtener la rama principal
                        default_branch = Branch.objects.filter(
                            organization=membership.organization,
                            is_active=True,
                        ).order_by('-is_main', 'id').first()
                        request.branch = default_branch

                    # Cachear por 5 minutos
                    cache.set(cache_key, {
                        'membership': membership,
                        'organization': membership.organization,
                        'role': membership.role,
                        'default_branch': request.branch,
                    }, 300)

                except Membership.DoesNotExist:
                    pass

        response = self.get_response(request)
        return response
