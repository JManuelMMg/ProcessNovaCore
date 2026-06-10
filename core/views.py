from pathlib import Path
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404
from django.conf import settings

from apps.users.forms import OrganizationRegistrationForm, UsernameRecoveryForm
from apps.users.models import Organization, Membership, Branch

logger = logging.getLogger(__name__)


def landing_page(request):
    return render(request, 'landing.html')


def serve_sw(request):
    sw_path = Path(settings.BASE_DIR) / 'static' / 'sw.js'
    if not sw_path.exists():
        raise Http404
    return FileResponse(open(sw_path, 'rb'), content_type='application/javascript')


def serve_manifest(request):
    manifest_path = Path(settings.BASE_DIR) / 'static' / 'manifest.json'
    if not manifest_path.exists():
        raise Http404
    return FileResponse(open(manifest_path, 'rb'), content_type='application/manifest+json')


@login_required
def dashboard(request):
    context = {}
    if request.organization:
        from apps.inventory.models import Product, Stock
        from apps.sales.models import Sale, SaleItem
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        sales_qs = Sale.objects.for_org(request.organization).filter(status='paid')
        if request.user_role != 'admin_central' and request.branch:
            sales_qs = sales_qs.filter(branch=request.branch)

        # KPIs de hoy
        sales_today_qs = sales_qs.filter(created_at__date=today)
        context['sales_today'] = sales_today_qs.count()
        context['revenue_today'] = sales_today_qs.aggregate(total=Sum('total'))['total'] or 0

        # KPIs de la semana
        sales_week_qs = sales_qs.filter(created_at__date__gte=week_start)
        context['sales_week'] = sales_week_qs.count()
        context['revenue_week'] = sales_week_qs.aggregate(total=Sum('total'))['total'] or 0

        # KPIs del mes
        sales_month_qs = sales_qs.filter(created_at__date__gte=month_start)
        context['sales_month'] = sales_month_qs.count()
        context['revenue_month'] = sales_month_qs.aggregate(total=Sum('total'))['total'] or 0

        # Inventario
        context['total_products'] = Product.objects.for_org(request.organization).count()

        # Stock bajo (≤ min_quantity)
        low_stock_qs = Stock.objects.for_org(request.organization).filter(
            quantity__lte=5
        ).select_related('product', 'branch')
        context['low_stock'] = low_stock_qs.count()
        context['low_stock_items'] = low_stock_qs[:5]

        # Top 5 productos del mes
        context['top_products'] = (
            SaleItem.objects
            .filter(sale__in=sales_month_qs)
            .values('product__name')
            .annotate(total_qty=Sum('quantity'), total_revenue=Sum('subtotal'))
            .order_by('-total_qty')[:5]
        )

    return render(request, 'dashboard.html', context)


@transaction.atomic
def register(request):
    if request.method == 'POST':
        form = OrganizationRegistrationForm(request.POST)
        if form.is_valid():
            rfc = form.cleaned_data['rfc'].upper()
            # Verificar si la organización ya existe
            existing_org = Organization.objects.filter(rfc=rfc).first()
            
            if existing_org:
                # La organización ya existe: mostrar mensaje
                messages.warning(
                    request, 
                    f"¡La organización con RFC {rfc} ya está registrada! "
                    f"Si perteneces a esta empresa, por favor contacta a un administrador de {existing_org.name} "
                    f"para que te envíe una invitación."
                )
                return render(request, 'registration/register.html', {'form': form, 'existing_org': existing_org})
            
            # La organización no existe: crearla normalmente
            try:
                org = Organization.objects.create(
                    name=form.cleaned_data['organization_name'],
                    rfc=rfc,
                    razon_social=form.cleaned_data['razon_social'],
                    regimen_fiscal=form.cleaned_data['regimen_fiscal'],
                    codigo_postal=form.cleaned_data['codigo_postal'],
                )
                branch = Branch.objects.create(
                    organization=org,
                    name=form.cleaned_data['branch_name'],
                    codigo_postal=form.cleaned_data['codigo_postal'],
                    is_main=True,
                )
                user = form.save()
                Membership.objects.create(
                    user=user,
                    organization=org,
                    role='admin_central',
                )
                login(request, user)
                messages.success(request, f'¡Bienvenido a ProcessNova! Tu empresa {org.name} ha sido creada.')
                return redirect('dashboard')
            except Exception as e:
                logger.exception('Error al crear organización/usuario en registro: %s', e)
                messages.error(request, "Ocurrió un error al crear tu cuenta. Por favor, intenta nuevamente.")
    else:
        form = OrganizationRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def username_recovery(request):
    if request.method == 'POST':
        form = UsernameRecoveryForm(request.POST)
        if form.is_valid():
            form.send_username_email()
            return redirect('username_recovery_done')
    else:
        form = UsernameRecoveryForm()
    return render(request, 'registration/username_recovery_form.html', {'form': form})


def username_recovery_done(request):
    return render(request, 'registration/username_recovery_done.html')
