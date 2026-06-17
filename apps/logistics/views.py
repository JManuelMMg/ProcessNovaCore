from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.permissions import permission_required, tenant_required
from .models import Shipment, Route, Carrier, Zone, Order


@login_required
@tenant_required
@permission_required('logistics')
def shipment_list(request):
    shipments = Shipment.objects.for_org(request.organization).select_related('order', 'carrier', 'route')
    return render(request, 'logistics/shipment_list.html', {'shipments': shipments})


@login_required
@tenant_required
@permission_required('logistics')
def shipment_detail(request, pk):
    shipment = get_object_or_404(Shipment.objects.for_org(request.organization).select_related('order', 'carrier', 'route', 'package'), pk=pk)
    trackings = shipment.trackings.all()
    return render(request, 'logistics/shipment_detail.html', {
        'shipment': shipment,
        'trackings': trackings
    })


@login_required
@tenant_required
@permission_required('logistics')
def route_list(request):
    routes = Route.objects.for_org(request.organization).select_related('origin')
    return render(request, 'logistics/route_list.html', {'routes': routes})


@login_required
@tenant_required
@permission_required('logistics')
def carrier_list(request):
    carriers = Carrier.objects.for_org(request.organization).filter(is_active=True)
    return render(request, 'logistics/carrier_list.html', {'carriers': carriers})


@login_required
@tenant_required
@permission_required('logistics')
def order_list(request):
    orders = Order.objects.for_org(request.organization).select_related('customer')
    return render(request, 'logistics/order_list.html', {'orders': orders})


@login_required
@tenant_required
@permission_required('logistics')
def update_shipment_status(request, pk):
    if request.method == 'POST':
        shipment = get_object_or_404(Shipment.objects.for_org(request.organization), pk=pk)
        new_status = request.POST.get('status')
        status_message = request.POST.get('status_message', '')
        
        if new_status in dict(Shipment.STATUS_CHOICES):
            shipment.status = new_status
            shipment.status_message = status_message
            
            # Registrar tracking
            from .models import ShipmentTracking
            ShipmentTracking.objects.create(
                organization=request.organization,
                shipment=shipment,
                status=new_status,
                status_message=status_message,
                tracked_by=request.user.get_full_name() or request.user.username
            )
            
            shipment.save()
            messages.success(request, 'Estado del envío actualizado.')
        return redirect('logistics:shipment_detail', pk=pk)
    return redirect('logistics:shipment_list')
