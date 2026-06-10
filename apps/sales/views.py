from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.utils import timezone
import json

from core.permissions import permission_required, tenant_required
from .models import Sale, SaleItem, SalesPayment
from apps.inventory.models import Product, Stock, StockMovement


def _products_qs(request):
    return Product.objects.for_org(request.organization)


def _sales_qs(request):
    qs = Sale.objects.for_org(request.organization).select_related('branch', 'created_by')
    if request.user_role != 'admin_central' and request.branch:
        qs = qs.filter(branch=request.branch)
    return qs


def _get_or_create_sale(request):
    sale_id = request.session.get('current_sale')
    if sale_id:
        sale = Sale.objects.filter(
            id=sale_id,
            organization=request.organization,
            status='draft',
        ).first()
        if sale:
            return sale
    sale = Sale.objects.create(
        organization=request.organization,
        branch=request.branch,
        created_by=request.user,
        status='draft',
    )
    request.session['current_sale'] = sale.id
    return sale


def _get_stock(product, branch):
    if not branch:
        return Stock.objects.filter(product=product).first()
    return Stock.objects.filter(product=product, branch=branch).first()


@login_required
@tenant_required
@permission_required('pos')
def pos_view(request):
    products = _products_qs(request).select_related('category')
    from apps.inventory.models import Category
    categories = Category.objects.for_org(request.organization)
    branches = []
    if request.user_role == 'admin_central':
        from apps.users.models import Branch
        branches = Branch.objects.for_org(request.organization).filter(is_active=True)
    return render(request, 'sales/pos.html', {
        'products': products,
        'categories': categories,
        'branches': branches,
        'can_create_products': request.user_role in ('admin_central', 'branch_manager'),
    })


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_add_to_cart(request):
    data = json.loads(request.body)
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    product = get_object_or_404(_products_qs(request), id=product_id)

    stock = _get_stock(product, request.branch)
    available = stock.quantity if stock else 0
    if available < quantity:
        return JsonResponse({
            'error': f'Stock insuficiente. Disponible: {available}',
            'available': available,
        }, status=400)

    sale = _get_or_create_sale(request)
    existing = sale.items.filter(product=product).first()
    if existing:
        new_qty = existing.quantity + quantity
        if available < new_qty:
            return JsonResponse({
                'error': f'Stock insuficiente. Disponible: {available}',
                'available': available,
            }, status=400)
        existing.quantity = new_qty
        existing.save()
        item = existing
    else:
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            unit_price=product.price,
            organization=request.organization,
        )
    sale.calculate_total()
    return JsonResponse({
        'item': {
            'id': item.id,
            'product_name': product.name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'subtotal': float(item.subtotal),
        }
    })


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_remove_from_cart(request):
    item_id = json.loads(request.body)['item_id']
    item = get_object_or_404(
        SaleItem.objects.filter(organization=request.organization),
        id=item_id,
    )
    sale = item.sale
    item.delete()
    sale.calculate_total()
    return JsonResponse({'success': True})


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_get_cart(request):
    sale_id = request.session.get('current_sale')
    if not sale_id:
        return JsonResponse({'items': [], 'total': 0.0})
    sale = Sale.objects.filter(
        id=sale_id, organization=request.organization, status='draft'
    ).first()
    if not sale:
        return JsonResponse({'items': [], 'total': 0.0})
    items = [{
        'id': i.id,
        'product_name': i.product.name,
        'product_id': i.product.id,
        'quantity': i.quantity,
        'unit_price': float(i.unit_price),
        'subtotal': float(i.subtotal),
    } for i in sale.items.select_related('product').all()]
    return JsonResponse({'items': items, 'total': float(sale.total)})


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_clear_cart(request):
    sale_id = request.session.get('current_sale')
    if sale_id:
        Sale.objects.filter(
            id=sale_id, organization=request.organization, status='draft'
        ).delete()
        request.session.pop('current_sale', None)
    return JsonResponse({'success': True})


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_checkout(request):
    data = json.loads(request.body)
    payment_method = data.get('payment_method', 'cash')
    amount_paid = float(data.get('amount_paid', 0))
    sale_id = request.session.get('current_sale')
    if not sale_id:
        return JsonResponse({'error': 'No hay venta activa'}, status=400)
    sale = get_object_or_404(
        Sale.objects.filter(organization=request.organization, status='draft'),
        id=sale_id,
    )
    if not sale.items.count():
        return JsonResponse({'error': 'No hay productos en la venta'}, status=400)

    for item in sale.items.select_related('product').all():
        stock = _get_stock(item.product, request.branch)
        if not stock or stock.quantity < item.quantity:
            available = stock.quantity if stock else 0
            return JsonResponse({
                'error': f'Stock insuficiente para {item.product.name}. Disponible: {available}',
            }, status=400)

    for item in sale.items.select_related('product').all():
        stock = _get_stock(item.product, request.branch)
        stock.quantity -= item.quantity
        stock.save()
        StockMovement.objects.create(
            product=item.product,
            stock=stock,
            type='out',
            quantity=item.quantity,
            reference=f'Venta #{sale.id}',
            organization=request.organization,
            created_by=request.user,
        )

    change = max(0, amount_paid - float(sale.total))
    SalesPayment.objects.create(
        sale=sale,
        amount=amount_paid,
        method=payment_method,
        organization=request.organization,
    )
    sale.status = 'paid'
    sale.paid_amount = amount_paid
    sale.change_amount = change
    sale.branch = request.branch
    sale.save()
    request.session.pop('current_sale', None)
    return JsonResponse({
        'success': True,
        'sale_id': sale.id,
        'total': float(sale.total),
        'change': change,
    })


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_scan_product(request):
    barcode = json.loads(request.body)['barcode'].strip()
    product = _products_qs(request).filter(barcode=barcode).first()
    if not product:
        product = _products_qs(request).filter(sku__iexact=barcode).first()
    if product:
        stock = _get_stock(product, request.branch)
        return JsonResponse({
            'product': {
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'sku': product.sku,
                'barcode': product.barcode,
                'stock': stock.quantity if stock else 0,
            }
        })
    return JsonResponse({'error': 'Producto no encontrado', 'barcode': barcode}, status=404)


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_switch_branch(request):
    if request.user_role != 'admin_central':
        return JsonResponse({'error': 'Sin permiso'}, status=403)
    branch_id = json.loads(request.body).get('branch_id')
    from apps.users.models import Branch
    branch = Branch.objects.filter(
        id=branch_id, organization=request.organization, is_active=True
    ).first()
    if not branch:
        return JsonResponse({'error': 'Sucursal no encontrada'}, status=404)
    request.session['active_branch_id'] = branch.id
    request.session.pop('current_sale', None)
    return JsonResponse({'success': True, 'branch_name': branch.name})


@login_required
@tenant_required
@permission_required('pos')
@require_GET
def api_products_cache(request):
    products = []
    for p in _products_qs(request).select_related('category'):
        stock = _get_stock(p, request.branch)
        products.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'barcode': p.barcode or '',
            'price': float(p.price),
            'category_id': p.category_id,
            'stock': stock.quantity if stock else 0,
        })
    return JsonResponse({
        'products': products,
        'branch_id': request.branch.id if request.branch else None,
        'branch_name': request.branch.name if request.branch else None,
        'cached_at': timezone.now().isoformat(),
    })


@login_required
@tenant_required
@permission_required('pos')
@require_POST
@transaction.atomic
def api_sync_offline(request):
    data = json.loads(request.body)
    sales_data = data.get('sales', [])
    results = []

    for sale_data in sales_data:
        offline_id = sale_data.get('offline_id')
        try:
            sale = Sale.objects.create(
                organization=request.organization,
                branch=request.branch,
                created_by=request.user,
                status='paid',
                paid_amount=sale_data.get('amount_paid', 0),
                change_amount=sale_data.get('change', 0),
            )
            for item_data in sale_data.get('items', []):
                product = get_object_or_404(_products_qs(request), id=item_data['product_id'])
                qty = int(item_data['quantity'])
                stock = _get_stock(product, request.branch)
                if not stock or stock.quantity < qty:
                    raise ValueError(f'Stock insuficiente para {product.name}')
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=qty,
                    unit_price=product.price,
                    organization=request.organization,
                )
                stock.quantity -= qty
                stock.save()
                StockMovement.objects.create(
                    product=product,
                    stock=stock,
                    type='out',
                    quantity=qty,
                    reference=f'Venta offline #{sale.id}',
                    organization=request.organization,
                    created_by=request.user,
                )
            sale.calculate_total()
            SalesPayment.objects.create(
                sale=sale,
                amount=sale_data.get('amount_paid', float(sale.total)),
                method=sale_data.get('payment_method', 'cash'),
                organization=request.organization,
            )
            results.append({'offline_id': offline_id, 'sale_id': sale.id, 'success': True})
        except Exception as e:
            results.append({'offline_id': offline_id, 'success': False, 'error': str(e)})

    return JsonResponse({'results': results})


@login_required
@tenant_required
@permission_required('sales_history')
def sale_list(request):
    sales = _sales_qs(request).filter(status='paid')[:100]
    return render(request, 'sales/sale_list.html', {'sales': sales})


@login_required
@tenant_required
@permission_required('sales_history')
def sale_detail(request, pk):
    sale = get_object_or_404(_sales_qs(request), pk=pk)
    items = sale.items.select_related('product').all()
    payments = sale.payments.all()
    return render(request, 'sales/sale_detail.html', {
        'sale': sale,
        'items': items,
        'payments': payments,
    })
