from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from core.permissions import permission_required, tenant_required
from .models import Product, Stock, StockMovement, Category
from .forms import ProductForm, CategoryForm


def _products_qs(request):
    return Product.objects.for_org(request.organization)


def _stocks_qs(request):
    qs = Stock.objects.for_org(request.organization).select_related('product', 'branch')
    if request.user_role != 'admin_central' and request.branch:
        qs = qs.filter(branch=request.branch)
    return qs


@login_required
@tenant_required
@permission_required('inventory_view')
def product_list(request):
    products = _products_qs(request).select_related('category')
    return render(request, 'inventory/product_list.html', {'products': products})


@login_required
@tenant_required
@permission_required('inventory_view')
def product_detail(request, pk):
    product = get_object_or_404(_products_qs(request), pk=pk)
    stocks = product.stocks.select_related('branch').all()
    if request.user_role != 'admin_central' and request.branch:
        stocks = stocks.filter(branch=request.branch)
    movements = product.movements.select_related('stock', 'created_by').all()[:50]
    return render(request, 'inventory/product_detail.html', {
        'product': product,
        'stocks': stocks,
        'movements': movements,
    })


def _resolve_category(form, organization):
    new_name = form.cleaned_data.get('new_category_name', '').strip()
    if new_name:
        category, _ = Category.objects.get_or_create(
            organization=organization,
            name=new_name,
            defaults={'description': ''},
        )
        return category
    return form.cleaned_data.get('category')


@login_required
@tenant_required
@permission_required('inventory_create')
def category_list(request):
    categories = Category.objects.for_org(request.organization).select_related('parent')
    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
@tenant_required
@permission_required('inventory_create')
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, organization=request.organization)
        if form.is_valid():
            category = form.save(commit=False)
            category.organization = request.organization
            category.save()
            messages.success(request, f'Categoría "{category.name}" creada.')
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(organization=request.organization)
    return render(request, 'inventory/category_form.html', {'form': form})


@login_required
@tenant_required
@permission_required('inventory_create')
@require_POST
def api_create_category(request):
    data = json.loads(request.body)
    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'El nombre es requerido'}, status=400)
    category, created = Category.objects.get_or_create(
        organization=request.organization,
        name=name,
        defaults={'description': data.get('description', '')},
    )
    return JsonResponse({
        'id': category.id,
        'name': category.name,
        'created': created,
    })


@login_required
@tenant_required
@permission_required('inventory_create')
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, organization=request.organization)
        if form.is_valid():
            product = form.save(commit=False)
            product.organization = request.organization
            product.category = _resolve_category(form, request.organization)
            product.save()
            initial_stock = form.cleaned_data.get('initial_stock', 0)
            if initial_stock > 0 and request.branch:
                stock, _ = Stock.objects.get_or_create(
                    product=product,
                    branch=request.branch,
                    organization=request.organization,
                    defaults={'quantity': 0},
                )
                stock.quantity += initial_stock
                stock.save()
                qty_before = stock.quantity - initial_stock  # ya se sumó arriba
                StockMovement.objects.create(
                    product=product,
                    stock=stock,
                    type='in',
                    quantity=initial_stock,
                    quantity_before=qty_before,
                    quantity_after=stock.quantity,
                    reference='Alta de producto',
                    organization=request.organization,
                    created_by=request.user,
                )
            messages.success(request, f'Producto "{product.name}" creado correctamente.')
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm(organization=request.organization)
    categories = Category.objects.for_org(request.organization)
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'categories': categories,
    })


@login_required
@tenant_required
@permission_required('inventory_edit')
def product_edit(request, pk):
    """Editar un producto existente."""
    product = get_object_or_404(_products_qs(request), pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product, organization=request.organization)
        if form.is_valid():
            p = form.save(commit=False)
            p.category = _resolve_category(form, request.organization)
            p.save()
            messages.success(request, f'Producto "{p.name}" actualizado.')
            return redirect('inventory:product_detail', pk=p.pk)
    else:
        form = ProductForm(instance=product, organization=request.organization)
    categories = Category.objects.for_org(request.organization)
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'product': product,
        'categories': categories,
        'editing': True,
    })


@login_required
@tenant_required
@permission_required('inventory_view')
def stock_list(request):
    stocks = _stocks_qs(request)
    return render(request, 'inventory/stock_list.html', {'stocks': stocks})


@login_required
@tenant_required
@permission_required('inventory_create')
def stock_intake(request):
    products = _products_qs(request).filter(is_active=True).order_by('name')
    return render(request, 'inventory/stock_intake.html', {
        'products': products
    })


@login_required
@tenant_required
@permission_required('inventory_view')
def movement_list(request):
    movements = StockMovement.objects.for_org(request.organization).select_related(
        'product', 'stock', 'created_by'
    )
    if request.user_role != 'admin_central' and request.branch:
        movements = movements.filter(stock__branch=request.branch)
    return render(request, 'inventory/movement_list.html', {'movements': movements[:100]})


@login_required
@tenant_required
@permission_required('inventory_create')
@require_POST
def api_quick_create(request):
    data = json.loads(request.body)
    barcode = data.get('barcode', '').strip()
    name = data.get('name', '').strip()
    price = data.get('price', 0)
    quantity = int(data.get('quantity', 1))
    sku = data.get('sku', '').strip() or barcode

    if not barcode or not name:
        return JsonResponse({'error': 'Código de barras y nombre son requeridos'}, status=400)

    existing = _products_qs(request).filter(barcode=barcode).first()
    if existing:
        return JsonResponse({
            'product': {
                'id': existing.id,
                'name': existing.name,
                'price': float(existing.price),
                'sku': existing.sku,
                'barcode': existing.barcode,
            },
            'created': False,
        })

    product = Product.objects.create(
        organization=request.organization,
        name=name,
        sku=sku,
        barcode=barcode,
        price=price,
        cost=data.get('cost') or None,
    )

    if request.branch and quantity > 0:
        stock, _ = Stock.objects.get_or_create(
            product=product,
            branch=request.branch,
            organization=request.organization,
            defaults={'quantity': 0},
        )
        stock.quantity += quantity
        stock.save()
        qty_before = stock.quantity - quantity
        StockMovement.objects.create(
            product=product,
            stock=stock,
            type='in',
            quantity=quantity,
            quantity_before=qty_before,
            quantity_after=stock.quantity,
            reference='Alta rápida por escaneo',
            organization=request.organization,
            created_by=request.user,
        )

    return JsonResponse({
        'product': {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'sku': product.sku,
            'barcode': product.barcode,
        },
        'created': True,
    })


@login_required
@tenant_required
@permission_required('inventory_create')
@require_POST
def api_add_stock(request):
    data = json.loads(request.body)
    barcode = data.get('barcode', '').strip()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    product = None
    if product_id:
        product = _products_qs(request).filter(pk=product_id).first()
    elif barcode:
        product = _products_qs(request).filter(barcode=barcode).first()
        if not product:
            product = _products_qs(request).filter(sku__iexact=barcode).first()
    if not product:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    if not request.branch:
        return JsonResponse({'error': 'No hay sucursal activa'}, status=400)

    stock, _ = Stock.objects.get_or_create(
        product=product,
        branch=request.branch,
        organization=request.organization,
        defaults={'quantity': 0},
    )
    stock.quantity += quantity
    stock.save()
    qty_before = stock.quantity - quantity  # ya se sumó arriba
    StockMovement.objects.create(
        product=product,
        stock=stock,
        type='in',
        quantity=quantity,
        quantity_before=qty_before,
        quantity_after=stock.quantity,
        reference='Entrada por escaneo',
        organization=request.organization,
        created_by=request.user,
    )
    return JsonResponse({
        'success': True,
        'product_name': product.name,
        'new_quantity': stock.quantity,
    })
