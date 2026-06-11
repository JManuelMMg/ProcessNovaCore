"""
Vistas personalizadas de autenticación con manejo seguro de envío de emails
"""
import logging
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings

logger = logging.getLogger(__name__)


class SafePasswordResetView(PasswordResetView):
    """
    Vista personalizada de recuperación de contraseña que maneja errores de envío de email de forma segura
    """
    
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """
        Sobreescribimos el método de envío de email para manejar errores de forma segura
        """
        try:
            # Usamos el mismo código que Django, pero con fail_silently=True y registro de errores
            subject = render_to_string(subject_template_name, context)
            # Eliminar saltos de línea del asunto (requisito de RFC 2822)
            subject = "".join(subject.splitlines())
            message = render_to_string(email_template_name, context)
            
            send_mail(
                subject,
                message,
                from_email,
                [to_email],
                fail_silently=True,
                html_message=render_to_string(html_email_template_name, context) if html_email_template_name else None,
            )
            logger.info('Email de recuperación de contraseña enviado a %s', to_email)
        except Exception as e:
            logger.exception('Error al enviar email de recuperación de contraseña a %s', to_email)
            # No fallamos, seguimos mostrando el mensaje de éxito al usuario
