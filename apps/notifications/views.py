from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.permissions import permission_required, tenant_required
from core.mail_service import send_email, fetch_inbox, is_email_configured
from .forms import ComposeEmailForm


@login_required
@tenant_required
def notification_list(request):
    return render(request, 'notifications/notification_list.html')


@login_required
@tenant_required
@permission_required('email')
def inbox(request):
    emails = []
    error = None
    if is_email_configured():
        try:
            emails = fetch_inbox(limit=30)
        except Exception as e:
            error = str(e)
    else:
        error = 'Configura EMAIL_HOST_USER y EMAIL_HOST_PASSWORD en tu archivo .env'
    return render(request, 'notifications/inbox.html', {
        'emails': emails,
        'error': error,
        'configured': is_email_configured(),
    })


@login_required
@tenant_required
@permission_required('email')
def compose(request):
    if not is_email_configured():
        messages.error(request, 'Configura tu correo en .env antes de enviar.')
        return redirect('notifications:inbox')

    if request.method == 'POST':
        form = ComposeEmailForm(request.POST)
        if form.is_valid():
            try:
                send_email(
                    to=form.cleaned_data['to'],
                    subject=form.cleaned_data['subject'],
                    body=form.cleaned_data['body'],
                )
                messages.success(request, f'Correo enviado a {form.cleaned_data["to"]}')
                return redirect('notifications:inbox')
            except Exception as e:
                messages.error(request, f'Error al enviar: {e}')
    else:
        form = ComposeEmailForm()
    return render(request, 'notifications/compose.html', {'form': form})
