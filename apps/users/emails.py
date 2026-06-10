from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


def send_user_invitation(invitation, request):
    accept_url = request.build_absolute_uri(
        f'/users/invite/accept/{invitation.token}/'
    )
    role_label = dict(invitation._meta.get_field('role').choices).get(
        invitation.role, invitation.role
    )
    context = {
        'invitation': invitation,
        'organization': invitation.organization,
        'role_label': role_label,
        'branch': invitation.branch,
        'accept_url': accept_url,
        'expires_at': invitation.expires_at,
    }
    subject = f'Invitación a ProcessNova — {invitation.organization.name}'
    message = render_to_string('users/emails/invitation.txt', context)
    html_message = render_to_string('users/emails/invitation.html', context)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
        html_message=html_message,
        fail_silently=False,
    )
