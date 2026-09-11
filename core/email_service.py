import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Sale
from .reports import generate_receipt_pdf

logger = logging.getLogger(__name__)


def _admin_recipients():
    configured = getattr(settings, 'ADMIN_EMAILS', [])
    try:
        staff_emails = User.objects.filter(is_staff=True, is_active=True).values_list('email', flat=True)
    except Exception:
        logger.exception('Could not load staff email recipients')
        staff_emails = []
    return sorted({email for email in list(configured) + list(staff_emails) if email})


def send_sale_completion_emails(sale):
    """Send branded receipts and admin alerts without affecting payment completion."""
    receipt_pdf = None
    if sale.customer and sale.customer.email and not sale.receipt_email_sent:
        try:
            receipt_pdf = generate_receipt_pdf(sale)
            context = {'sale': sale, 'customer': sale.customer}
            message = EmailMultiAlternatives(
                subject=f'Receipt for invoice {sale.invoice_number}',
                body=render_to_string('emails/receipt.txt', context),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[sale.customer.email],
            )
            message.attach_alternative(render_to_string('emails/receipt.html', context), 'text/html')
            message.attach(f'receipt_{sale.invoice_number}.pdf', receipt_pdf, 'application/pdf')
            message.send(fail_silently=False)
            sale.receipt_email_sent = timezone.now()
            sale.save(update_fields=['receipt_email_sent', 'updated_at'])
        except Exception:
            logger.exception('Could not send receipt email for sale %s', sale.invoice_number)

    admin_recipients = _admin_recipients()
    if admin_recipients and not sale.admin_email_sent:
        try:
            context = {'sale': sale, 'customer': sale.customer}
            message = EmailMultiAlternatives(
                subject=f'Payment completed: {sale.invoice_number}',
                body=render_to_string('emails/admin_payment.txt', context),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_recipients,
            )
            message.attach_alternative(render_to_string('emails/admin_payment.html', context), 'text/html')
            if receipt_pdf is None:
                receipt_pdf = generate_receipt_pdf(sale)
            message.attach(f'receipt_{sale.invoice_number}.pdf', receipt_pdf, 'application/pdf')
            message.send(fail_silently=False)
            sale.admin_email_sent = timezone.now()
            sale.save(update_fields=['admin_email_sent', 'updated_at'])
        except Exception:
            logger.exception('Could not send admin payment email for sale %s', sale.invoice_number)


def send_promotional_email(subject, body, recipients):
    """Send a plain-text promotional email to a validated customer audience."""
    recipients = sorted({email for email in recipients if email})
    if not recipients:
        return 0
    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            bcc=recipients,
        )
        message.attach_alternative(
            f'''<html><body style="margin:0;background:#fcf9f7;color:#2c2c2c;font-family:Arial,sans-serif;">
            <div style="max-width:640px;margin:32px auto;background:#fff;border:1px solid #ead9b2;">
            <div style="padding:26px 30px;background:#2c2c2c;color:#f7e7ce;font-family:Georgia,serif;font-size:28px;">Winners Cosmetics</div>
            <div style="padding:32px;line-height:1.7;"><h1 style="font-family:Georgia,serif;color:#8b4c61;">{subject}</h1>
            <p style="white-space:pre-line;color:#666;">{body}</p></div></div></body></html>''',
            'text/html',
        )
        return message.send(fail_silently=False)
    except Exception:
        logger.exception('Could not send promotional email')
        return 0
