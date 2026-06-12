from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.permissions import permission_required, tenant_required
from .models import Customer, Segment, Interaction, Lead, Opportunity, Campaign
from .forms import CustomerForm, SegmentForm, InteractionForm, LeadForm, OpportunityForm, CampaignForm


@login_required
@tenant_required
@permission_required('crm')
def customer_list(request):
    # Cachear listado de clientes por 10 minutos
    from django.core.cache import cache
    cache_key = f'customers_list_{request.organization.id}'
    customers = cache.get(cache_key)
    if not customers:
        customers = list(Customer.objects.for_org(request.organization).prefetch_related('sales', 'interactions'))
        cache.set(cache_key, customers, 600)
    return render(request, 'crm/customer_list.html', {'customers': customers})


@login_required
@tenant_required
@permission_required('crm')
def customer_detail(request, pk):
    customer = get_object_or_404(Customer.objects.for_org(request.organization), pk=pk)
    interactions = customer.interactions.select_related('created_by')
    sales = customer.sales.filter(status='paid').select_related('branch')
    return render(request, 'crm/customer_detail.html', {
        'customer': customer,
        'interactions': interactions,
        'sales': sales
    })


@login_required
@tenant_required
@permission_required('crm')
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST, organization=request.organization)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.organization = request.organization
            customer.save()
            messages.success(request, 'Cliente creado exitosamente.')
            return redirect('crm:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(organization=request.organization)
    return render(request, 'crm/customer_form.html', {'form': form, 'title': 'Nuevo Cliente'})


@login_required
@tenant_required
@permission_required('crm')
def customer_edit(request, pk):
    customer = get_object_or_404(Customer.objects.for_org(request.organization), pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer, organization=request.organization)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado exitosamente.')
            return redirect('crm:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer, organization=request.organization)
    return render(request, 'crm/customer_form.html', {'form': form, 'title': 'Editar Cliente'})


@login_required
@tenant_required
@permission_required('crm')
def customer_delete(request, pk):
    customer = get_object_or_404(Customer.objects.for_org(request.organization), pk=pk)
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Cliente eliminado exitosamente.')
        return redirect('crm:customer_list')
    return render(request, 'confirm_delete.html', {'object': customer, 'title': 'Eliminar Cliente'})


@login_required
@tenant_required
@permission_required('crm')
def segment_list(request):
    segments = Segment.objects.for_org(request.organization).prefetch_related('customers')
    return render(request, 'crm/segment_list.html', {'segments': segments})


@login_required
@tenant_required
@permission_required('crm')
def segment_create(request):
    if request.method == 'POST':
        form = SegmentForm(request.POST)
        if form.is_valid():
            segment = form.save(commit=False)
            segment.organization = request.organization
            segment.save()
            messages.success(request, 'Segmento creado exitosamente.')
            return redirect('crm:segment_list')
    else:
        form = SegmentForm()
    return render(request, 'crm/segment_form.html', {'form': form, 'title': 'Nuevo Segmento'})


@login_required
@tenant_required
@permission_required('crm')
def interaction_list(request):
    interactions = Interaction.objects.for_org(request.organization).select_related('customer', 'lead', 'created_by')
    return render(request, 'crm/interaction_list.html', {'interactions': interactions})


@login_required
@tenant_required
@permission_required('crm')
def interaction_create(request):
    if request.method == 'POST':
        form = InteractionForm(request.POST, organization=request.organization)
        if form.is_valid():
            interaction = form.save(commit=False)
            interaction.organization = request.organization
            interaction.created_by = request.user
            interaction.save()
            messages.success(request, 'Interacción registrada exitosamente.')
            return redirect('crm:interaction_list')
    else:
        form = InteractionForm(organization=request.organization)
    return render(request, 'crm/interaction_form.html', {'form': form, 'title': 'Nueva Interacción'})


@login_required
@tenant_required
@permission_required('crm')
def lead_list(request):
    leads = Lead.objects.for_org(request.organization).select_related('assigned_to', 'created_by')
    return render(request, 'crm/lead_list.html', {'leads': leads})


@login_required
@tenant_required
@permission_required('crm')
def lead_create(request):
    if request.method == 'POST':
        form = LeadForm(request.POST, organization=request.organization)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.organization = request.organization
            lead.created_by = request.user
            lead.save()
            messages.success(request, 'Lead creado exitosamente.')
            return redirect('crm:lead_list')
    else:
        form = LeadForm(organization=request.organization)
    return render(request, 'crm/lead_form.html', {'form': form, 'title': 'Nuevo Lead'})


@login_required
@tenant_required
@permission_required('crm')
def lead_detail(request, pk):
    lead = get_object_or_404(Lead.objects.for_org(request.organization), pk=pk)
    interactions = lead.interactions.select_related('created_by')
    opportunities = lead.opportunities.select_related('customer')
    return render(request, 'crm/lead_detail.html', {
        'lead': lead,
        'interactions': interactions,
        'opportunities': opportunities
    })


@login_required
@tenant_required
@permission_required('crm')
def opportunity_list(request):
    opportunities = Opportunity.objects.for_org(request.organization).select_related('customer', 'assigned_to', 'created_by')
    return render(request, 'crm/opportunity_list.html', {'opportunities': opportunities})


@login_required
@tenant_required
@permission_required('crm')
def opportunity_create(request):
    if request.method == 'POST':
        form = OpportunityForm(request.POST, organization=request.organization)
        if form.is_valid():
            opportunity = form.save(commit=False)
            opportunity.organization = request.organization
            opportunity.created_by = request.user
            opportunity.save()
            messages.success(request, 'Oportunidad creada exitosamente.')
            return redirect('crm:opportunity_list')
    else:
        form = OpportunityForm(organization=request.organization)
    return render(request, 'crm/opportunity_form.html', {'form': form, 'title': 'Nueva Oportunidad'})


@login_required
@tenant_required
@permission_required('crm')
def campaign_list(request):
    campaigns = Campaign.objects.for_org(request.organization).prefetch_related('target_audience')
    return render(request, 'crm/campaign_list.html', {'campaigns': campaigns})


@login_required
@tenant_required
@permission_required('crm')
def campaign_create(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST, organization=request.organization)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.organization = request.organization
            campaign.created_by = request.user
            campaign.save()
            form.save_m2m()
            messages.success(request, 'Campaña creada exitosamente.')
            return redirect('crm:campaign_list')
    else:
        form = CampaignForm(organization=request.organization)
    return render(request, 'crm/campaign_form.html', {'form': form, 'title': 'Nueva Campaña'})
