import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from django.conf import settings


def _decode_header(value):
    if not value:
        return ''
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)


def is_email_configured():
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def send_email(to, subject, body, html_body=None):
    if not is_email_configured():
        raise ValueError('Correo no configurado. Agrega EMAIL_HOST_USER y EMAIL_HOST_PASSWORD en .env')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = settings.DEFAULT_FROM_EMAIL
    msg['To'] = to
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    if html_body:
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        if settings.EMAIL_USE_TLS:
            server.starttls()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.sendmail(settings.EMAIL_HOST_USER, [to], msg.as_string())
    return True


def fetch_inbox(limit=20):
    if not is_email_configured():
        raise ValueError('Correo no configurado')

    mail = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
    mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
    mail.select('INBOX')

    _, data = mail.search(None, 'ALL')
    ids = data[0].split()
    ids = ids[-limit:] if len(ids) > limit else ids
    ids.reverse()

    messages = []
    for msg_id in ids:
        _, msg_data = mail.fetch(msg_id, '(RFC822)')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain' and not part.get('Content-Disposition'):
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    break
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='replace')

        messages.append({
            'id': msg_id.decode(),
            'from': _decode_header(msg.get('From', '')),
            'subject': _decode_header(msg.get('Subject', '(Sin asunto)')),
            'date': msg.get('Date', ''),
            'body': body[:2000],
        })

    mail.logout()
    return messages
