from django.core.management.base import BaseCommand, CommandError

from core.email_service import send_promotional_email
from core.models import Customer


class Command(BaseCommand):
    help = 'Send a promotional email to active customers.'

    def add_arguments(self, parser):
        parser.add_argument('--subject', required=True)
        parser.add_argument('--message', required=True)
        parser.add_argument('--membership', help='Optional membership type, e.g. VIP or GOLD')

    def handle(self, *args, **options):
        customers = Customer.objects.filter(is_active=True).exclude(email='')
        if options['membership']:
            customers = customers.filter(membership_type=options['membership'])
        recipients = customers.values_list('email', flat=True)
        try:
            sent = send_promotional_email(options['subject'], options['message'], recipients)
        except Exception as error:
            raise CommandError(f'Promotion could not be sent: {error}') from error
        self.stdout.write(self.style.SUCCESS(f'Promotional email dispatched ({sent} message).'))
