from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def shipment_list(request):
    return render(request, 'logistics/shipment_list.html')


@login_required
def shipment_detail(request, pk):
    return render(request, 'logistics/shipment_detail.html')


@login_required
def vehicle_list(request):
    return render(request, 'logistics/vehicle_list.html')
