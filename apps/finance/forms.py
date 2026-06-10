from django import forms
from apps.crm.models import Customer
from .models import Invoice

INPUT = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500'


class InvoiceFromSaleForm(forms.Form):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        widget=forms.Select(attrs={'class': INPUT}),
        label='Cliente para facturar',
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['customer'].queryset = Customer.objects.for_org(organization)
