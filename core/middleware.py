from apps.users.models import Membership, Branch
from django.core.cache import cache


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
