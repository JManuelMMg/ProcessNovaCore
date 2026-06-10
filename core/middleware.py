from apps.users.models import Membership, Branch


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.membership = None
        request.user_role = 'employee'
        request.branch = None

        if request.user.is_authenticated:
            try:
                membership = Membership.objects.select_related(
                    'organization', 'branch'
                ).get(user=request.user)
                request.membership = membership
                request.organization = membership.organization
                request.user_role = membership.role

                branch_id = request.session.get('active_branch_id')
                if branch_id:
                    request.branch = Branch.objects.filter(
                        id=branch_id,
                        organization=membership.organization,
                        is_active=True,
                    ).first()

                if not request.branch and membership.branch:
                    request.branch = membership.branch

                if not request.branch:
                    request.branch = Branch.objects.filter(
                        organization=membership.organization,
                        is_main=True,
                        is_active=True,
                    ).first()

                if not request.branch:
                    request.branch = Branch.objects.filter(
                        organization=membership.organization,
                        is_active=True,
                    ).first()

            except Membership.DoesNotExist:
                pass

        response = self.get_response(request)
        return response
