from django import forms
from .models import Product, Category

INPUT = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Ej: Bebidas, Electrónica...'}),
            'description': forms.Textarea(attrs={'class': INPUT, 'rows': 2}),
            'parent': forms.Select(attrs={'class': INPUT}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = '— Sin categoría padre —'
        if organization:
            self.fields['parent'].queryset = Category.objects.for_org(organization)


class ProductForm(forms.ModelForm):
    initial_stock = forms.IntegerField(
        min_value=0, initial=0, required=False,
        label='Stock inicial en sucursal'
    )
    new_category_name = forms.CharField(
        max_length=255, required=False,
        label='O crear categoría nueva',
        widget=forms.TextInput(attrs={
            'class': INPUT,
            'placeholder': 'Escribe el nombre de una categoría nueva',
            'id': 'new-category-name',
        }),
    )

    class Meta:
        model = Product
        fields = ['name', 'sku', 'barcode', 'description', 'price', 'cost', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT}),
            'sku': forms.TextInput(attrs={'class': INPUT}),
            'barcode': forms.TextInput(attrs={'class': INPUT, 'id': 'barcode-field'}),
            'description': forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': INPUT, 'step': '0.01'}),
            'cost': forms.NumberInput(attrs={'class': INPUT, 'step': '0.01'}),
            'category': forms.Select(attrs={'class': INPUT, 'id': 'id_category'}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields['category'].required = False
        self.fields['category'].empty_label = '— Seleccionar categoría —'
        if organization:
            self.fields['category'].queryset = Category.objects.for_org(organization)
        for field in self.fields.values():
            if hasattr(field.widget, 'attrs') and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = INPUT

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        new_name = cleaned.get('new_category_name', '').strip()
        if not category and not new_name:
            pass  # categoría opcional
        elif new_name and category:
            raise forms.ValidationError(
                'Selecciona una categoría existente O escribe una nueva, no ambas.'
            )
        return cleaned


class QuickProductForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1, initial=1)

    class Meta:
        model = Product
        fields = ['name', 'sku', 'barcode', 'price', 'cost']
