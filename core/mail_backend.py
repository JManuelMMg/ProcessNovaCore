"""
Email backend que intenta enviar por SMTP pero si falla (firewall, red, etc.)
lo registra en consola sin romper la aplicación.
"""
import logging
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)


class FallbackEmailBackend(EmailBackend):
    """
    Backend SMTP con fallback silencioso.
    Si no puede conectar (firewall, ISP, etc.), loguea el error
    y muestra el email en consola en vez de lanzar excepción.
    """

    def send_messages(self, email_messages):
        try:
            return super().send_messages(email_messages)
        except Exception as e:
            logger.warning(f'No se pudo enviar email por SMTP: {e}')
            logger.info('--- EMAIL (no enviado) ---')
            for msg in email_messages:
                logger.info(f'De: {msg.from_email}')
                logger.info(f'Para: {msg.recipients()}')
                logger.info(f'Asunto: {msg.subject}')
                logger.info(f'Cuerpo: {msg.body[:200]}...')
                logger.info('--- FIN EMAIL ---')
            return 0
