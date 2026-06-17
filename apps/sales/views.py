from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import json

from core.permissions import permission_required, tenant_required
from .models import Sale, SaleItem, SalesPayment
from apps.inventory.models import Product, Stock, StockMovement
from apps.crm.models import Customer

WHOLESALE_DISCOUNT_RATE = Decimal('0.10')
VALID_SALE_TYPES = {'pos', 'wholesale'}
PAYMENT_METHOD_ALIASES = {
    'card': 'card_debit',
    'debit': 'card_debit',
    'credit': 'card_credit',
}


def _products_qs(request):
    return Product.objects.for_org(request.organization).filter(is_active=True)


def _sales_qs(request):
    qs = Sale.objects.for_org(request.organization).select_related('branch', 'created_by', 'customer')
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
    # Bug 7 fix: branch can be None if admin hasn't selected branch
    sale = Sale.objects.create(
        organization=request.organization,
        branch=request.branch,  # can be None for admin without active branch
        created_by=request.user,
        status='draft',
    )
    request.session['current_sale'] = sale.id
    return sale


def _get_stock(product, branch):
    if not branch:
        return Stock.objects.filter(product=product).first()
    return Stock.objects.filter(product=product, branch=branch).first()


def _parse_positive_int(value, default=1):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, value)


def _parse_money(value, default='0'):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _normalize_sale_type(value):
    return value if value in VALID_SALE_TYPES else 'pos'


def _unit_price_for(product, sale_type):
    price = product.price
    if sale_type == 'wholesale':
        price = price * (Decimal('1') - WHOLESALE_DISCOUNT_RATE)
    return price.quantize(Decimal('0.01'))


def _tax_rate_for(product):
    return product.tax_rate if product.is_taxable else Decimal('0')


def _serialize_cart(sale):
    items = [{
        'id': i.id,
        'product_name': i.product.name,
        'product_id': i.product.id,
        'quantity': i.quantity,
        'unit_price': float(i.unit_price),
        'subtotal': float(i.subtotal),
        'tax_amount': float(i.tax_amount),
        'total': float(i.total),
    } for i in sale.items.select_related('product').all()]
    return {
        'items': items,
        'subtotal': float(sale.subtotal),
        'tax': float(sale.tax),
        'total': float(sale.total),
    }


@login_required
@tenant_required
@permission_required('pos')
@ensure_csrf_cookie
def pos_view(request):
    products = _products_qs(request).select_related('category')
    from apps.inventory.models import Category
    categories = Category.objects.for_org(request.organization)
    customers = Customer.objects.for_org(request.organization)
    branches = []
    if request.user_role == 'admin_central':
        from apps.users.models import Branch
        branches = Branch.objects.for_org(request.organization).filter(is_active=True)
    return render(request, 'sales/pos.html', {
        'products': products,
        'categories': categories,
        'customers': customers,
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
    quantity = _parse_positive_int(data.get('quantity', 1))
    sale_type = _normalize_sale_type(data.get('sale_type', 'pos'))
    product = get_object_or_404(_products_qs(request), id=product_id)

    if not request.branch:
        return JsonResponse({
            'error': 'No hay una sucursal activa seleccionada. Por favor, selecciona una sucursal antes de agregar productos.',
        }, status=400)

    stock = _get_stock(product, request.branch)
    available = stock.quantity if stock else 0
    if available < quantity:
        return JsonResponse({
            'error': f'Stock insuficiente. Disponible: {available}',
            'available': available,
        }, status=400)

    sale = _get_or_create_sale(request)
    existing = sale.items.filter(product=product).first()
    unit_price = _unit_price_for(product, sale_type)
    if existing:
        new_qty = existing.quantity + quantity
        if available < new_qty:
            return JsonResponse({
                'error': f'Stock insuficiente. Disponible: {available}',
                'available': available,
            }, status=400)
        existing.quantity = new_qty
        existing.unit_price = unit_price
        existing.tax_rate = _tax_rate_for(product)
        existing.save()
        item = existing
    else:
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            tax_rate=_tax_rate_for(product),
            organization=request.organization,
        )
    sale.type = sale_type
    sale.calculate_total()
    return JsonResponse({
        'item': {
            'id': item.id,
            'product_name': product.name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'subtotal': float(item.subtotal),
        },
        'cart': _serialize_cart(sale),
    })


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_update_item_quantity(request):
    data = json.loads(request.body)
    item_id = data.get('item_id')
    delta = int(data.get('delta', 0))
    item = get_object_or_404(
        SaleItem.objects.filter(organization=request.organization),
        id=item_id,
    )

    if not request.branch:
        return JsonResponse({
            'error': 'No hay una sucursal activa seleccionada.',
        }, status=400)

    stock = _get_stock(item.product, request.branch)
    available = stock.quantity if stock else 0
    new_qty = item.quantity + delta

    if new_qty <= 0:
        item.delete()
        sale = item.sale
        sale.calculate_total()
        return JsonResponse({'success': True})

    if available < new_qty:
        return JsonResponse({
            'error': f'Stock insuficiente. Disponible: {available}',
            'available': available,
        }, status=400)

    item.quantity = new_qty
    item.save()
    sale = item.sale
    sale.calculate_total()
    return JsonResponse({'success': True})


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
@require_GET
def api_get_cart(request):
    sale_id = request.session.get('current_sale')
    if not sale_id:
        return JsonResponse({'items': [], 'total': 0.0})
    sale = Sale.objects.filter(
        id=sale_id, organization=request.organization, status='draft'
    ).first()
    if not sale:
        return JsonResponse({'items': [], 'total': 0.0})
    return JsonResponse(_serialize_cart(sale))


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
@transaction.atomic
def api_checkout(request):
    data = json.loads(request.body)
    payment_method = PAYMENT_METHOD_ALIASES.get(data.get('payment_method'), data.get('payment_method', 'cash'))
    amount_paid = _parse_money(data.get('amount_paid', 0))
    sale_type = _normalize_sale_type(data.get('sale_type', 'pos'))
    customer_id = data.get('customer_id')
    sale_id = request.session.get('current_sale')
    if not sale_id:
        return JsonResponse({'error': 'No hay venta activa'}, status=400)
    if not request.branch:
        return JsonResponse({'error': 'No hay una sucursal activa seleccionada. Por favor, selecciona una sucursal primero.'}, status=400)
    sale = get_object_or_404(
        Sale.objects.filter(organization=request.organization, status='draft'),
        id=sale_id,
    )
    if not sale.items.count():
        return JsonResponse({'error': 'No hay productos en la venta'}, status=400)
    sale.calculate_total()
    if amount_paid <= 0:
        amount_paid = sale.total
    if amount_paid < sale.total:
        return JsonResponse({
            'error': f'Pago insuficiente. Faltan ${float(sale.total - amount_paid):.2f}',
        }, status=400)

    for item in sale.items.select_related('product').all():
        stock = _get_stock(item.product, request.branch)
        if not stock or stock.quantity < item.quantity:
            available = stock.quantity if stock else 0
            return JsonResponse({
                'error': f'Stock insuficiente para {item.product.name}. Disponible: {available}',
            }, status=400)

    for item in sale.items.select_related('product').all():
        stock = _get_stock(item.product, request.branch)
        qty_before = stock.quantity
        stock.quantity -= item.quantity
        stock.save()
        StockMovement.objects.create(
            product=item.product,
            stock=stock,
            type='out',
            quantity=item.quantity,
            quantity_before=qty_before,
            quantity_after=stock.quantity,
            reference=f'Venta #{sale.id}',
            organization=request.organization,
            created_by=request.user,
        )

    change = max(Decimal('0'), amount_paid - sale.total)
    SalesPayment.objects.create(
        sale=sale,
        amount=amount_paid,
        method=payment_method,
        organization=request.organization,
    )
    sale.status = 'paid'
    sale.paid_amount = amount_paid
    sale.change_amount = change
    sale.type = sale_type
    if customer_id:
        sale.customer = Customer.objects.for_org(request.organization).filter(id=customer_id).first()
    sale.branch = request.branch
    sale.save()
    request.session.pop('current_sale', None)
    return JsonResponse({
        'success': True,
        'sale_id': sale.id,
        'sale_number': sale.number,
        'total': float(sale.total),
        'amount_paid': float(amount_paid),
        'change': float(change),
        'cart_cleared': True,
    })


@login_required
@tenant_required
@permission_required('pos')
@require_POST
def api_scan_product(request):
    barcode = json.loads(request.body).get('barcode', '').strip()
    if not barcode:
        return JsonResponse({'error': 'Código vacío'}, status=400)
    product = _products_qs(request).filter(
        Q(barcode__iexact=barcode) | Q(sku__iexact=barcode)
    ).first()
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
                'retail_price': float(product.price),
                'wholesale_price': float(_unit_price_for(product, 'wholesale')),
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
                    unit_price=_unit_price_for(product, sale_data.get('sale_type', 'pos')),
                    tax_rate=_tax_rate_for(product),
                    organization=request.organization,
                )
                qty_before = stock.quantity
                stock.quantity -= qty
                stock.save()
                StockMovement.objects.create(
                    product=product,
                    stock=stock,
                    type='out',
                    quantity=qty,
                    quantity_before=qty_before,
                    quantity_after=stock.quantity,
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
    from django.core.paginator import Paginator
    from datetime import date

    sales = _sales_qs(request).filter(status='paid').prefetch_related('items__product')

    # Date filters
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    if date_from:
        try:
            from_dt = date.fromisoformat(date_from)
            sales = sales.filter(created_at__date__gte=from_dt)
        except ValueError:
            pass
    if date_to:
        try:
            to_dt = date.fromisoformat(date_to)
            sales = sales.filter(created_at__date__lte=to_dt)
        except ValueError:
            pass

    # Export CSV
    if request.GET.get('export') == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="ventas.csv"'
        response.write('\ufeff')  # BOM for Excel
        writer = csv.writer(response)
        writer.writerow(['#', 'Fecha', 'Cliente', 'Sucursal', 'Total', 'Método pago', 'Cajero'])
        for s in sales.select_related('customer', 'branch', 'created_by'):
            payment = s.payments.first()
            writer.writerow([
                s.number,
                s.created_at.strftime('%d/%m/%Y %H:%M'),
                s.customer.name if s.customer else '—',
                s.branch.name if s.branch else '—',
                float(s.total),
                payment.get_method_display() if payment else '—',
                s.created_by.get_full_name() or s.created_by.username if s.created_by else '—',
            ])
        return response

    paginator = Paginator(sales, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'sales/sale_list.html', {
        'sales': page_obj,
        'page_obj': page_obj,
        'date_from': date_from or '',
        'date_to': date_to or '',
    })


@login_required
@tenant_required
@permission_required('sales_history')
def sale_detail(request, pk):
    sale = get_object_or_404(_sales_qs(request), pk=pk)
    items = sale.items.select_related('product').all()
    payments = sale.payments.all()
    refunds = sale.refunds.all()
    can_cancel = request.user_role == 'admin_central' and sale.status == 'paid'
    return render(request, 'sales/sale_detail.html', {
        'sale': sale,
        'items': items,
        'payments': payments,
        'refunds': refunds,
        'can_cancel': can_cancel,
    })


@login_required
@tenant_required
@permission_required('users_manage')
def sale_cancel(request, pk):
    """Cancel a paid sale (admin only)."""
    if request.method != 'POST':
        return redirect('sales:sale_detail', pk=pk)
    sale = get_object_or_404(
        Sale.objects.for_org(request.organization).filter(status='paid'),
        pk=pk,
    )
    # Revert stock
    for item in sale.items.select_related('product').all():
        stock = _get_stock(item.product, sale.branch)
        if stock:
            qty_before = stock.quantity
            stock.quantity += item.quantity
            stock.save()
            StockMovement.objects.create(
                product=item.product,
                stock=stock,
                type='return',
                quantity=item.quantity,
                quantity_before=qty_before,
                quantity_after=stock.quantity,
                reference=f'Cancelación venta #{sale.number}',
                organization=request.organization,
                created_by=request.user,
            )
    sale.status = 'cancelled'
    sale.save()
    messages.success(request, f'Venta {sale.number} cancelada y stock revertido.')
    return redirect('sales:sale_list')
