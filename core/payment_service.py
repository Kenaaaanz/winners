import logging

from django.db import transaction
from django.utils import timezone

from .email_service import send_sale_completion_emails

logger = logging.getLogger(__name__)


def complete_paystack_sale(sale, verification_response):
    """Apply a verified Paystack payment exactly once, then notify by email."""
    if verification_response.get('status') != 'success':
        return False

    with transaction.atomic():
        sale_locked = type(sale).objects.select_for_update().get(pk=sale.pk)
        already_completed = sale_locked.status == 'COMPLETED'

        if not already_completed:
            from .models import StockReservation

            sale_locked.status = 'COMPLETED'
            sale_locked.amount_paid = sale_locked.total
            sale_locked.payment_method = 'PAYSTACK'

            if verification_response.get('authorization'):
                authorization = verification_response['authorization']
                sale_locked.paystack_authorization_code = authorization.get('authorization_code', '')
                sale_locked.card_last4 = authorization.get('last4', '')

            if sale_locked.customer:
                loyalty_points = int(sale_locked.total / 1000)
                sale_locked.loyalty_points_earned = loyalty_points
                sale_locked.customer.loyalty_points += loyalty_points
                sale_locked.customer.total_spent += sale_locked.total
                sale_locked.customer.last_purchase = timezone.now()
                sale_locked.customer.save(update_fields=[
                    'loyalty_points', 'total_spent', 'last_purchase'
                ])

            sale_locked.save()

            try:
                reservation = StockReservation.objects.select_for_update().get(sale=sale_locked)
                reservation.confirm()
            except StockReservation.DoesNotExist:
                pass

    send_sale_completion_emails(sale_locked)
    logger.info('Paystack sale completed: %s', sale_locked.invoice_number)
    return True
