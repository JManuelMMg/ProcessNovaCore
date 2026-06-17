from django import forms
from .models import Employee, Department, Position

INPUT = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'first_name', 'middle_name', 'last_name', 'email', 'personal_email',
            'phone', 'mobile_phone', 'position', 'department', 'hire_date',
            'birth_date', 'gender', 'marital_status', 'address', 'city', 'state',
            'zip_code', 'rfc', 'nss', 'curp', 'emergency_contact_name',
            'emergency_contact_phone', 'emergency_contact_relationship',
            'salary', 'payment_frequency', 'bank_name', 'bank_account', 'clabe',
            'status', 'notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT}),
            'middle_name': forms.TextInput(attrs={'class': INPUT}),
            'last_name': forms.TextInput(attrs={'class': INPUT}),
            'email': forms.EmailInput(attrs={'class': INPUT}),
            'personal_email': forms.EmailInput(attrs={'class': INPUT}),
            'phone': forms.TextInput(attrs={'class': INPUT}),
            'mobile_phone': forms.TextInput(attrs={'class': INPUT}),
            'position': forms.Select(attrs={'class': INPUT}),
            'department': forms.Select(attrs={'class': INPUT}),
            'hire_date': forms.DateInput(attrs={'class': INPUT, 'type': 'date'}),
            'birth_date': forms.DateInput(attrs={'class': INPUT, 'type': 'date'}),
            'gender': forms.Select(attrs={'class': INPUT}),
            'marital_status': forms.Select(attrs={'class': INPUT}),
            'address': forms.Textarea(attrs={'class': INPUT, 'rows': 2}),
            'city': forms.TextInput(attrs={'class': INPUT}),
            'state': forms.TextInput(attrs={'class': INPUT}),
            'zip_code': forms.TextInput(attrs={'class': INPUT}),
            'rfc': forms.TextInput(attrs={'class': INPUT}),
            'nss': forms.TextInput(attrs={'class': INPUT}),
            'curp': forms.TextInput(attrs={'class': INPUT}),
            'emergency_contact_name': forms.TextInput(attrs={'class': INPUT}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': INPUT}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': INPUT}),
            'salary': forms.NumberInput(attrs={'class': INPUT, 'step': '0.01'}),
            'payment_frequency': forms.Select(attrs={'class': INPUT}),
            'bank_name': forms.TextInput(attrs={'class': INPUT}),
            'bank_account': forms.TextInput(attrs={'class': INPUT}),
            'clabe': forms.TextInput(attrs={'class': INPUT}),
            'status': forms.Select(attrs={'class': INPUT}),
            'notes': forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        # Make some fields optional
        self.fields['middle_name'].required = False
        self.fields['personal_email'].required = False
        self.fields['phone'].required = False
        self.fields['mobile_phone'].required = False
        self.fields['position'].required = False
        self.fields['department'].required = False
        self.fields['birth_date'].required = False
        self.fields['gender'].required = False
        self.fields['marital_status'].required = False
        self.fields['address'].required = False
        self.fields['city'].required = False
        self.fields['state'].required = False
        self.fields['zip_code'].required = False
        self.fields['rfc'].required = False
        self.fields['nss'].required = False
        self.fields['curp'].required = False
        self.fields['emergency_contact_name'].required = False
        self.fields['emergency_contact_phone'].required = False
        self.fields['emergency_contact_relationship'].required = False
        self.fields['bank_name'].required = False
        self.fields['bank_account'].required = False
        self.fields['clabe'].required = False
        self.fields['notes'].required = False
        # Set empty labels
        self.fields['position'].empty_label = '— Seleccionar puesto —'
        self.fields['department'].empty_label = '— Seleccionar departamento —'
        self.fields['gender'].empty_label = '— Seleccionar género —'
        self.fields['marital_status'].empty_label = '— Seleccionar estado civil —'
        # Filter position and department by organization
        if organization:
            self.fields['position'].queryset = Position.objects.for_org(organization)
            self.fields['department'].queryset = Department.objects.for_org(organization)
