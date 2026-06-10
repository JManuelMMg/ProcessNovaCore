from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse

from core.permissions import permission_required, tenant_required
from apps.sales.models import Sale
from .models import Invoice, Income, Expense, Payment
from .forms import InvoiceFromSaleForm
from . import cfdi as cfdi_service


def _invoices_qs(request):
    return Invoice.objects.for_org(request.organization).select_related('customer', 'sale')


@login_required
@tenant_required
@permission_required('finance')
def dashboard(request):
    org = request.organization
    total_invoices = Invoice.objects.for_org(org).count()
    total_income = Income.objects.for_org(org).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = Expense.objects.for_org(org).aggregate(Sum('amount'))['amount__sum'] or 0
    stamped = Invoice.objects.for_org(org).filter(cfdi_status='stamped').count()
    return render(request, 'finance/dashboard.html', {
        'total_invoices': total_invoices,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'stamped_invoices': stamped,
        'recent_invoices': _invoices_qs(request)[:5],
        'recent_incomes': Income.objects.for_org(org).order_by('-date')[:5],
        'recent_expenses': Expense.objects.for_org(org).order_by('-date')[:5],
    })


@login_required
@tenant_required
@permission_required('finance')
def invoice_list(request):
    invoices = _invoices_qs(request)
    return render(request, 'finance/invoice_list.html', {'invoices': invoices})


@login_required
@tenant_required
@permission_required('finance')
def invoice_detail(request, pk):
    invoice = get_object_or_404(_invoices_qs(request), pk=pk)
    return render(request, 'finance/invoice_detail.html', {
        'invoice': invoice,
        'payments': invoice.payments.all(),
        'items': invoice.items.select_related('product').all(),
    })


@login_required
@tenant_required
@permission_required('finance')
def invoice_stamp(request, pk):
    invoice = get_object_or_404(_invoices_qs(request), pk=pk)
    if invoice.cfdi_status == 'stamped':
        messages.info(request, 'Esta factura ya está timbrada.')
        return redirect('finance:invoice_detail', pk=pk)
    try:
        result = cfdi_service.stamp_cfdi(invoice, request.organization)
        messages.success(request, f'CFDI timbrado. UUID: {result["uuid"]}')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('finance:invoice_detail', pk=pk)


@login_required
@tenant_required
@permission_required('finance')
def invoice_download_xml(request, pk):
    invoice = get_object_or_404(_invoices_qs(request), pk=pk)
    if not invoice.xml_content:
        messages.error(request, 'La factura no tiene XML generado.')
        return redirect('finance:invoice_detail', pk=pk)
    response = HttpResponse(invoice.xml_content, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="CFDI_{invoice.number}.xml"'
    return response


@login_required
@tenant_required
@permission_required('finance')
def invoice_from_sale(request, sale_id):
    sale = get_object_or_404(
        Sale.objects.for_org(request.organization).filter(status='paid'),
        id=sale_id,
    )
    if sale.invoices.filter(cfdi_status='stamped').exists():
        messages.info(request, 'Esta venta ya tiene factura timbrada.')
        return redirect('sales:sale_detail', pk=sale_id)

    if request.method == 'POST':
        form = InvoiceFromSaleForm(request.POST, organization=request.organization)
        if form.is_valid():
            customer = form.cleaned_data['customer']
            invoice = cfdi_service.create_invoice_from_sale(
                sale, customer, request.organization
            )
            messages.success(request, f'Factura {invoice.number} creada. Puedes timbrarla ahora.')
            return redirect('finance:invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceFromSaleForm(organization=request.organization)

    return render(request, 'finance/invoice_from_sale.html', {
        'form': form,
        'sale': sale,
    })


@login_required
@tenant_required
@permission_required('finance')
def income_list(request):
    incomes = Income.objects.for_org(request.organization).select_related('customer', 'invoice')
    return render(request, 'finance/income_list.html', {'incomes': incomes})


@login_required
@tenant_required
@permission_required('finance')
def expense_list(request):
    expenses = Expense.objects.for_org(request.organization)
    return render(request, 'finance/expense_list.html', {'expenses': expenses})
