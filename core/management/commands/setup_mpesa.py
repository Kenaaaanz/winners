"""
Management command to setup M-Pesa configuration
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import MpesaConfiguration
from core.mpesa_service import MpesaService

class Command(BaseCommand):
    help = 'Setup M-Pesa configuration and register URLs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--environment',
            choices=['sandbox', 'production'],
            default='sandbox',
            help='Environment to setup (sandbox or production)'
        )
        parser.add_argument(
            '--register-urls',
            action='store_true',
            help='Register C2B URLs after setup'
        )
    
    def handle(self, *args, **options):
        environment = options['environment']
        register_urls = options['register_urls']
        
        self.stdout.write(f"Setting up M-Pesa {environment} configuration...")
        
        # Get configuration from settings
        config_type = environment.upper()
        
        # Check if configuration already exists
        if MpesaConfiguration.objects.filter(config_type=config_type).exists():
            self.stdout.write(self.style.WARNING(
                f"{config_type} configuration already exists. Updating..."
            ))
            config = MpesaConfiguration.objects.get(config_type=config_type)
        else:
            config = MpesaConfiguration(config_type=config_type)
        
        # Set configuration values from settings
        config.consumer_key = settings.MPESA_CONSUMER_KEY
        config.consumer_secret = settings.MPESA_CONSUMER_SECRET
        config.shortcode = settings.MPESA_SHORTCODE if hasattr(settings, 'MPESA_SHORTCODE') else ''
        config.passkey = settings.MPESA_PASSKEY if hasattr(settings, 'MPESA_PASSKEY') else ''
        config.initiator_name = settings.MPESA_INITIATOR_NAME if hasattr(settings, 'MPESA_INITIATOR_NAME') else ''
        config.initiator_password = settings.MPESA_INITIATOR_PASSWORD if hasattr(settings, 'MPESA_INITIATOR_PASSWORD') else ''
        
        # Set callback URLs
        base_url = settings.BASE_URL
        config.callback_base_url = base_url
        config.stk_callback_url = f"{base_url}/api/mpesa/stk-callback/"
        config.c2b_validation_url = f"{base_url}/api/mpesa/c2b-validation/"
        config.c2b_confirmation_url = f"{base_url}/api/mpesa/c2b-confirmation/"
        
        # Set as active if it matches current environment
        config.is_active = (settings.MPESA_ENVIRONMENT == environment)
        config.auto_register_urls = True
        
        config.save()
        
        self.stdout.write(self.style.SUCCESS(
            f"{config_type} configuration saved successfully!"
        ))
        
        # Register URLs if requested
        if register_urls and config.is_active:
            self.stdout.write("Registering C2B URLs...")
            try:
                mpesa_service = MpesaService()
                result = mpesa_service.c2b_register_url(
                    validation_url=config.c2b_validation_url,
                    confirmation_url=config.c2b_confirmation_url
                )
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS(
                        "C2B URLs registered successfully!"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f"Failed to register URLs: {result.get('error', 'Unknown error')}"
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error registering URLs: {str(e)}"))
        
        # Display configuration summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("M-Pesa Configuration Summary")
        self.stdout.write("="*50)
        self.stdout.write(f"Environment: {config_type}")
        self.stdout.write(f"Shortcode: {config.shortcode}")
        self.stdout.write(f"Active: {'Yes' if config.is_active else 'No'}")
        self.stdout.write(f"STK Callback: {config.stk_callback_url}")
        self.stdout.write(f"C2B Validation: {config.c2b_validation_url}")
        self.stdout.write(f"C2B Confirmation: {config.c2b_confirmation_url}")
        self.stdout.write("="*50)