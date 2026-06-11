from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from .models import User, Membership, Branch, UserInvitation


INPUT_CLASS = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'


class UsernameRecoveryForm(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS}),
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('No existe ningún usuario asociado a este correo electrónico.')
        return email

    def send_username_email(self):
        import logging
        logger = logging.getLogger(__name__)
        
        email = self.cleaned_data['email']
        users = User.objects.filter(email__iexact=email)
        
        subject = 'Tu nombre de usuario en ProcessNova'
        site_url = settings.SITE_URL or 'http://localhost:8000'
        protocol = 'https' if site_url.startswith('https://') else 'http'
        domain = site_url.replace('http://', '').replace('https://', '')
        
        context = {
            'users': users,
            'protocol': protocol,
            'domain': domain,
        }
        
        message = render_to_string('registration/username_recovery_email.txt', context)
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )
            logger.info('Email de recuperación de usuario enviado a %s', email)
        except Exception as e:
            logger.exception('Error al enviar email de recuperación de usuario a %s', email)
            # No fallamos, seguimos mostrando el mensaje de éxito al usuario
            pass


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASS})


class OrganizationRegistrationForm(CustomUserCreationForm):
    organization_name = forms.CharField(max_length=255, label='Nombre de la empresa')
    rfc = forms.CharField(max_length=13, label='RFC')
    razon_social = forms.CharField(max_length=255, label='Razón social')
    regimen_fiscal = forms.CharField(max_length=100, label='Régimen fiscal', initial='612')
    codigo_postal = forms.CharField(max_length=10, label='Código postal')
    branch_name = forms.CharField(max_length=255, label='Nombre de sucursal principal', initial='Sucursal Principal')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        extra_fields = ['organization_name', 'rfc', 'razon_social', 'regimen_fiscal', 'codigo_postal', 'branch_name']
        for name in extra_fields:
            self.fields[name].widget.attrs.update({'class': INPUT_CLASS})

    def clean_rfc(self):
        rfc = self.cleaned_data.get('rfc').upper()
        # No validamos aquí para manejarlo en la vista y ofrecer opciones
        return rfc


class UserInviteForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}), label='Contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}), label='Confirmar contraseña')
    role = forms.ChoiceField(choices=Membership.ROLE_CHOICES, widget=forms.Select(attrs={'class': INPUT_CLASS}))
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(), required=False,
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
        label='Sucursal asignada'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['branch'].queryset = Branch.objects.for_org(organization).filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            raise forms.ValidationError('Las contraseñas no coinciden.')
        role = cleaned.get('role')
        if role != 'admin_central' and not cleaned.get('branch'):
            raise forms.ValidationError('Debes asignar una sucursal para este rol.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class EmailInviteForm(forms.ModelForm):
    class Meta:
        model = UserInvitation
        fields = ['email', 'first_name', 'last_name', 'role', 'branch']
        widgets = {
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'role': forms.Select(attrs={'class': INPUT_CLASS}),
            'branch': forms.Select(attrs={'class': INPUT_CLASS}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['branch'].queryset = Branch.objects.for_org(organization).filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        if role != 'admin_central' and not cleaned.get('branch'):
            raise forms.ValidationError('Debes asignar una sucursal para este rol.')
        if User.objects.filter(email=cleaned.get('email')).exists():
            raise forms.ValidationError('Ya existe un usuario con este correo.')
        return cleaned


class AcceptInviteForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASS})


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'address', 'codigo_postal', 'phone', 'is_main']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'address': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2}),
            'codigo_postal': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'phone': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'is_main': forms.CheckboxInput(attrs={'class': 'rounded'}),
        }
