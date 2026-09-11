import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Sale
from .reports import generate_receipt_pdf

logger = logging.getLogger(__name__)


def _admin_recipients():
    configured = getattr(settings, 'ADMIN_EMAILS', [])
    staff_emails = User.objects.filter(is_staff=True, is_active=True).values_list('email', flat=True)
    return sorted({email for email in list(configured) + list(staff_emails) if email})


def send_sale_completion_emails(sale):
    """Send a receipt to the customer and a completion alert to administrators once."""
    receipt_pdf = None
    if sale.customer and sale.customer.email and not sale.receipt_email_sent:
        try:
            receipt_pdf = generate_receipt_pdf(sale)
            message = EmailMessage(
                subject=f'Receipt for invoice {sale.invoice_number}',
                body=(
                    f'Hello {sale.customer.full_name},\n\n'
                    f'Thank you for your purchase. Your invoice number is {sale.invoice_number}.\n'
                    f'Total paid: KES {sale.amount_paid:.2f}.\n\n'
                    'Your receipt is attached.\n\nWinners Cosmetics'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[sale.customer.email],
            )
            message.attach(f'receipt_{sale.invoice_number}.pdf', receipt_pdf, 'application/pdf')
            message.send(fail_silently=False)
            sale.receipt_email_sent = timezone.now()
            sale.save(update_fields=['receipt_email_sent', 'updated_at'])
        except Exception:
            logger.exception('Could not send receipt email for sale %s', sale.invoice_number)

    admin_recipients = _admin_recipients()
    if admin_recipients and not sale.admin_email_sent:
        try:
            message = EmailMessage(
                subject=f'Payment completed: {sale.invoice_number}',
                body=(
                    f'Payment completed for invoice {sale.invoice_number}.\n'
                    f'Amount: KES {sale.amount_paid:.2f}\n'
                    f'Method: {sale.get_payment_method_display()}\n'
                    f'Customer: {sale.customer.full_name if sale.customer else "Walk-in customer"}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_recipients,
            )
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
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        bcc=recipients,
    )
    return message.send(fail_silently=False)
