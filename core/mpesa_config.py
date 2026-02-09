"""
M-Pesa Configuration and Constants
"""
from django.conf import settings

class MpesaConfig:
    """
    M-Pesa Configuration class
    """
    
    # Environments
    ENV_SANDBOX = 'sandbox'
    ENV_PRODUCTION = 'production'
    
    # URLs
    SANDBOX_BASE_URL = 'https://sandbox.safaricom.co.ke'
    PRODUCTION_BASE_URL = 'https://api.safaricom.co.ke'
    
    # Endpoints
    ENDPOINTS = {
        'oauth': '/oauth/v1/generate?grant_type=client_credentials',
        'stk_push': '/mpesa/stkpush/v1/processrequest',
        'stk_query': '/mpesa/stkpushquery/v1/query',
        'c2b_register': '/mpesa/c2b/v1/registerurl',
        'c2b_simulate': '/mpesa/c2b/v1/simulate',
        'b2c': '/mpesa/b2c/v1/paymentrequest',
        'transaction_status': '/mpesa/transactionstatus/v1/query',
        'account_balance': '/mpesa/accountbalance/v1/query',
        'reversal': '/mpesa/reversal/v1/request'
    }
    
    @classmethod
    def get_base_url(cls):
        """Get base URL based on environment"""
        if settings.MPESA_ENVIRONMENT == cls.ENV_PRODUCTION:
            return cls.PRODUCTION_BASE_URL
        return cls.SANDBOX_BASE_URL
    
    @classmethod
    def get_endpoint(cls, endpoint_name):
        """Get complete endpoint URL"""
        return cls.get_base_url() + cls.ENDPOINTS.get(endpoint_name, '')
    
    @classmethod
    def get_shortcode(cls):
        """Get shortcode based on environment"""
        if settings.MPESA_ENVIRONMENT == cls.ENV_PRODUCTION:
            return settings.MPESA_SHORTCODE
        return '174379'  # Sandbox test shortcode
    
    @classmethod
    def get_passkey(cls):
        """Get passkey based on environment"""
        if settings.MPESA_ENVIRONMENT == cls.ENV_PRODUCTION:
            return settings.MPESA_PASSKEY
        return 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'