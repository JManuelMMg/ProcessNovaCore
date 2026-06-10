from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Customer, Segment, Interaction


@login_required
def customer_list(request):
    customers = Customer.objects.all()
    return render(request, 'crm/customer_list.html', {'customers': customers})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    interactions = customer.interactions.all()
    return render(request, 'crm/customer_detail.html', {
        'customer': customer,
        'interactions': interactions
    })


@login_required
def customer_create(request):
    return render(request, 'crm/customer_form.html')


@login_required
def segment_list(request):
    segments = Segment.objects.all()
    return render(request, 'crm/segment_list.html', {'segments': segments})


@login_required
def interaction_list(request):
    interactions = Interaction.objects.select_related('customer', 'created_by').all()
    return render(request, 'crm/interaction_list.html', {'interactions': interactions})
