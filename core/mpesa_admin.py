"""
M-Pesa Admin Configuration
"""
from django.contrib import admin
from django.utils import timezone
from .models import MpesaTransaction, MpesaCallback, MpesaConfiguration

class MpesaTransactionAdmin(admin.ModelAdmin):
    """Admin configuration for MpesaTransaction"""
    
    list_display = [
        'transaction_id',
        'transaction_type',
        'amount',
        'phone_number',
        'status',
        'mpesa_receipt_number',
        'created_at',
        'user',
        'is_complete'
    ]
    
    list_filter = [
        'transaction_type',
        'status',
        'is_complete',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'transaction_id',
        'checkout_request_id',
        'merchant_request_id',
        'mpesa_receipt_number',
        'phone_number',
        'account_reference'
    ]
    
    readonly_fields = [
        'transaction_id',
        'created_at',
        'updated_at',
        'completed_at',
        'raw_request',
        'raw_response'
    ]
    
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'transaction_id',
                'transaction_type',
                'amount',
                'phone_number',
                'account_reference',
                'transaction_desc'
            )
        }),
        ('M-Pesa Response', {
            'fields': (
                'merchant_request_id',
                'checkout_request_id',
                'mpesa_receipt_number',
                'result_code',
                'result_description',
                'response_code',
                'response_description'
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'is_complete',
                'created_at',
                'updated_at',
                'completed_at'
            )
        }),
        ('Relations', {
            'fields': (
                'user',
                'sale'
            )
        }),
        ('Technical Details', {
            'fields': (
                'ip_address',
                'user_agent',
                'raw_request',
                'raw_response'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_successful', 'mark_as_failed', 'resend_notifications']
    
    def mark_as_successful(self, request, queryset):
        """Mark selected transactions as successful"""
        updated = queryset.update(
            status='SUCCESS',
            is_complete=True,
            completed_at=timezone.now()
        )
        self.message_user(request, f'{updated} transactions marked as successful.')
    mark_as_successful.short_description = "Mark selected as successful"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected transactions as failed"""
        updated = queryset.update(
            status='FAILED',
            is_complete=True,
            completed_at=timezone.now(),
            result_code=999,
            result_description='Manually marked as failed'
        )
        self.message_user(request, f'{updated} transactions marked as failed.')
    mark_as_failed.short_description = "Mark selected as failed"
    
    def resend_notifications(self, request, queryset):
        """Resend notifications for selected transactions"""
        from .mpesa_utils import MpesaUtils
        for transaction in queryset:
            if transaction.status == 'SUCCESS':
                MpesaUtils.send_payment_notification(transaction, 'SUCCESS')
        self.message_user(request, f'Notifications resent for {queryset.count()} transactions.')
    resend_notifications.short_description = "Resend notifications"

class MpesaCallbackAdmin(admin.ModelAdmin):
    """Admin configuration for MpesaCallback"""
    
    list_display = [
        'id',
        'callback_type',
        'transaction',
        'result_code',
        'is_processed',
        'received_at'
    ]
    
    list_filter = [
        'callback_type',
        'is_processed',
        'received_at'
    ]
    
    search_fields = [
        'result_description',
        'processing_notes'
    ]
    
    readonly_fields = [
        'received_at',
        'raw_data'
    ]
    
    fieldsets = (
        ('Callback Information', {
            'fields': (
                'callback_type',
                'transaction',
                'result_code',
                'result_description'
            )
        }),
        ('Processing Status', {
            'fields': (
                'is_processed',
                'processed_at',
                'processing_notes'
            )
        }),
        ('Raw Data', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('received_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_processed', 'mark_as_unprocessed']
    
    def mark_as_processed(self, request, queryset):
        """Mark selected callbacks as processed"""
        updated = queryset.update(
            is_processed=True,
            processed_at=timezone.now(),
            processing_notes='Manually marked as processed'
        )
        self.message_user(request, f'{updated} callbacks marked as processed.')
    mark_as_processed.short_description = "Mark selected as processed"
    
    def mark_as_unprocessed(self, request, queryset):
        """Mark selected callbacks as unprocessed"""
        updated = queryset.update(
            is_processed=False,
            processed_at=None,
            processing_notes=''
        )
        self.message_user(request, f'{updated} callbacks marked as unprocessed.')
    mark_as_unprocessed.short_description = "Mark selected as unprocessed"

class MpesaConfigurationAdmin(admin.ModelAdmin):
    """Admin configuration for MpesaConfiguration"""
    
    list_display = [
        'config_type',
        'shortcode',
        'is_active',
        'auto_register_urls',
        'updated_at'
    ]
    
    list_filter = [
        'config_type',
        'is_active'
    ]
    
    fieldsets = (
        ('Authentication', {
            'fields': (
                'config_type',
                'consumer_key',
                'consumer_secret',
                'shortcode',
                'passkey'
            )
        }),
        ('Initiator Details', {
            'fields': (
                'initiator_name',
                'initiator_password',
                'certificate_path'
            )
        }),
        ('Callback URLs', {
            'fields': (
                'callback_base_url',
                'stk_callback_url',
                'c2b_validation_url',
                'c2b_confirmation_url'
            )
        }),
        ('Settings', {
            'fields': (
                'is_active',
                'auto_register_urls'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    
    actions = ['activate_configuration', 'register_urls']
    
    def activate_configuration(self, request, queryset):
        """Activate selected configuration"""
        for config in queryset:
            config.is_active = True
            config.save()
        self.message_user(request, f'{queryset.count()} configuration(s) activated.')
    activate_configuration.short_description = "Activate selected configuration"
    
    def register_urls(self, request, queryset):
        """Register URLs for selected configuration"""
        from .mpesa_service import MpesaService
        
        success_count = 0
        for config in queryset:
            if config.is_active:
                try:
                    mpesa_service = MpesaService()
                    
                    # Register C2B URLs
                    if config.c2b_validation_url and config.c2b_confirmation_url:
                        result = mpesa_service.c2b_register_url(
                            validation_url=config.c2b_validation_url,
                            confirmation_url=config.c2b_confirmation_url
                        )
                        
                        if result['success']:
                            success_count += 1
                    
                except Exception as e:
                    self.message_user(request, f'Error registering URLs for {config.config_type}: {str(e)}', level='error')
        
        self.message_user(request, f'URLs registered for {success_count} configuration(s).')
    register_urls.short_description = "Register URLs for selected configuration"

# Register models
admin.site.register(MpesaTransaction, MpesaTransactionAdmin)
admin.site.register(MpesaCallback, MpesaCallbackAdmin)
admin.site.register(MpesaConfiguration, MpesaConfigurationAdmin)