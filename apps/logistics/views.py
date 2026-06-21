from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Sum, Count
from core.permissions import permission_required, tenant_required
from .models import Shipment, Route, Carrier, Order, OrderItem, Vehicle
from apps.inventory.models import Product, Stock
from apps.crm.models import Customer
from apps.sales.models import Sale, SaleItem
from django.utils import timezone
from datetime import timedelta


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
def vehicle_list(request):
    vehicles = Vehicle.objects.for_org(request.organization)
    return render(request, 'logistics/vehicle_list.html', {'vehicles': vehicles})


@login_required
@tenant_required
@permission_required('logistics')
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle.objects.for_org(request.organization), pk=pk)
    return render(request, 'logistics/vehicle_detail.html', {'vehicle': vehicle})


@login_required
@tenant_required
@permission_required('logistics')
def vehicle_create(request):
    if request.method == 'POST':
        vehicle = Vehicle.objects.create(
            organization=request.organization,
            name=request.POST.get('name'),
            plate=request.POST.get('plate'),
            type=request.POST.get('type'),
            status=request.POST.get('status'),
            capacity_kg=request.POST.get('capacity_kg') or None,
            capacity_volume=request.POST.get('capacity_volume') or None,
            model=request.POST.get('model'),
            year=request.POST.get('year') or None,
            driver_name=request.POST.get('driver_name'),
            driver_phone=request.POST.get('driver_phone'),
            last_maintenance_date=request.POST.get('last_maintenance_date') or None,
            next_maintenance_date=request.POST.get('next_maintenance_date') or None,
            notes=request.POST.get('notes')
        )
        messages.success(request, 'Vehículo creado exitosamente!')
        return redirect('logistics:vehicle_detail', pk=vehicle.pk)
    return render(request, 'logistics/vehicle_form.html', {'editing': False})


@login_required
@tenant_required
@permission_required('logistics')
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(Vehicle.objects.for_org(request.organization), pk=pk)
    if request.method == 'POST':
        vehicle.name = request.POST.get('name')
        vehicle.plate = request.POST.get('plate')
        vehicle.type = request.POST.get('type')
        vehicle.status = request.POST.get('status')
        vehicle.capacity_kg = request.POST.get('capacity_kg') or None
        vehicle.capacity_volume = request.POST.get('capacity_volume') or None
        vehicle.model = request.POST.get('model')
        vehicle.year = request.POST.get('year') or None
        vehicle.driver_name = request.POST.get('driver_name')
        vehicle.driver_phone = request.POST.get('driver_phone')
        vehicle.last_maintenance_date = request.POST.get('last_maintenance_date') or None
        vehicle.next_maintenance_date = request.POST.get('next_maintenance_date') or None
        vehicle.notes = request.POST.get('notes')
        vehicle.save()
        messages.success(request, 'Vehículo actualizado exitosamente!')
        return redirect('logistics:vehicle_detail', pk=vehicle.pk)
    return render(request, 'logistics/vehicle_form.html', {'editing': True, 'vehicle': vehicle})


@login_required
@tenant_required
@permission_required('logistics')
def order_list(request):
    orders = Order.objects.for_org(request.organization).select_related('customer')
    return render(request, 'logistics/order_list.html', {'orders': orders})


@login_required
@tenant_required
@permission_required('logistics')
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.for_org(request.organization).select_related('customer'), pk=pk)
    items = order.items.select_related('product')
    return render(request, 'logistics/order_detail.html', {'order': order, 'items': items})


@login_required
@tenant_required
@permission_required('logistics')
def order_create(request):
    if request.method == 'POST':
        with transaction.atomic():
            # Crear pedido
            customer_id = request.POST.get('customer')
            customer = get_object_or_404(Customer.objects.for_org(request.organization), pk=customer_id)
            
            order = Order.objects.create(
                organization=request.organization,
                customer=customer,
                status='pending',
                date=timezone.now().date(),
                created_by=request.user
            )
            
            # Generar número de pedido
            order.number = f"ORD-{timezone.now().year}-{str(order.pk).zfill(6)}"
            order.save()
            
            # Añadir items
            product_ids = request.POST.getlist('products')
            quantities = request.POST.getlist('quantities')
            
            for product_id, qty in zip(product_ids, quantities):
                if product_id and qty:
                    product = get_object_or_404(Product.objects.for_org(request.organization), pk=product_id)
                    OrderItem.objects.create(
                        organization=request.organization,
                        order=order,
                        product=product,
                        quantity=int(qty),
                        price=product.price
                    )
            
            order.calculate_totals()
            messages.success(request, 'Pedido creado exitosamente.')
            return redirect('logistics:order_detail', pk=order.pk)
    
    customers = Customer.objects.for_org(request.organization)
    products = Product.objects.for_org(request.organization).filter(is_active=True)
    return render(request, 'logistics/order_form.html', {
        'customers': customers,
        'products': products,
        'editing': False
    })


@login_required
@tenant_required
@permission_required('logistics')
def order_fulfill(request, pk):
    order = get_object_or_404(Order.objects.for_org(request.organization), pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            # Crear venta desde el pedido
            sale = Sale.objects.create(
                organization=request.organization,
                branch=request.branch,
                customer=order.customer,
                order=order,
                created_by=request.user,
                status='paid',
                type='wholesale'
            )
            
            # Copiar items del pedido a la venta y actualizar stock
            for item in order.items.all():
                stock = Stock.objects.filter(product=item.product, branch=request.branch).first()
                if stock:
                    stock.quantity -= item.quantity
                    stock.save()
                    
                    from apps.inventory.models import StockMovement
                    StockMovement.objects.create(
                        organization=request.organization,
                        product=item.product,
                        stock=stock,
                        type='out',
                        quantity=item.quantity,
                        quantity_before=stock.quantity + item.quantity,
                        quantity_after=stock.quantity,
                        reference=f"Venta por pedido {order.number}",
                        created_by=request.user
                    )
                
                SaleItem.objects.create(
                    organization=request.organization,
                    sale=sale,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.price,
                    tax_rate=item.tax_rate
                )
            
            sale.calculate_total()
            order.status = 'shipped'
            order.save()
            
            messages.success(request, f'Pedido surtido exitosamente! Venta creada: {sale.number}')
            return redirect('sales:sale_detail', pk=sale.pk)
    return render(request, 'logistics/order_confirm_fulfill.html', {'order': order})


@login_required
@tenant_required
@permission_required('logistics')
def logistics_analytics(request):
    """Logistics analytics view."""
    today = timezone.localdate()
    start_month = today - timedelta(days=30)

    shipments = Shipment.objects.for_org(request.organization).filter(created_at__date__gte=start_month)
    total_shipments = shipments.count()
    delivered_shipments = shipments.filter(status='delivered').count()
    failed_shipments = shipments.filter(status__in=['failed', 'returned']).count()
    in_transit_shipments = shipments.filter(status__in=['picked_up', 'in_transit', 'out_for_delivery']).count()
    total_shipping_cost = shipments.aggregate(Sum('shipping_cost'))['shipping_cost__sum'] or 0

    orders = Order.objects.for_org(request.organization).filter(created_at__date__gte=start_month)
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()

    return render(request, 'logistics/analytics.html', {
        'total_shipments': total_shipments,
        'delivered_shipments': delivered_shipments,
        'failed_shipments': failed_shipments,
        'in_transit_shipments': in_transit_shipments,
        'total_shipping_cost': float(total_shipping_cost),
        'total_orders': total_orders,
        'pending_orders': pending_orders
    })


@login_required
@tenant_required
@permission_required('logistics')
@require_GET
def api_logistics_stats(request):
    """Logistics analytics API endpoint."""
    today = timezone.localdate()
    start_month = today - timedelta(days=30)

    shipments = Shipment.objects.for_org(request.organization).filter(created_at__date__gte=start_month)
    total_shipments = shipments.count()
    delivered_shipments = shipments.filter(status='delivered').count()
    failed_shipments = shipments.filter(status__in=['failed', 'returned']).count()
    in_transit_shipments = shipments.filter(status__in=['picked_up', 'in_transit', 'out_for_delivery']).count()
    total_shipping_cost = shipments.aggregate(Sum('shipping_cost'))['shipping_cost__sum'] or 0

    orders = Order.objects.for_org(request.organization).filter(created_at__date__gte=start_month)
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()

    return JsonResponse({
        'total_shipments': total_shipments,
        'delivered_shipments': delivered_shipments,
        'failed_shipments': failed_shipments,
        'in_transit_shipments': in_transit_shipments,
        'total_shipping_cost': float(total_shipping_cost),
        'total_orders': total_orders,
        'pending_orders': pending_orders
    })
