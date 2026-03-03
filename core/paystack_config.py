"""
Paystack Configuration
"""
from django.conf import settings
from decouple import config


class PaystackConfig:
    """
    Paystack configuration class
    """
    
    # Paystack API Keys
    PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='pk_test_84bee673cf72bf8dccf8468d8248811066cfef96')
    SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='sk_test_041187b838f3f830b638c8c8626c2131a089da40')
    
    # API Endpoints
    BASE_URL = 'https://api.paystack.co'
    
    # Endpoints mapping
    ENDPOINTS = {
        'initialize': '/transaction/initialize',
        'verify': '/transaction/verify',
        'list': '/transaction',
        'fetch': '/transaction/{reference}',
        'charge': '/charge',
        'create_plan': '/plan',
        'create_subscription': '/subscription',
        'fetch_customer': '/customer/{customer_code}',
        'list_customers': '/customer',
        'create_customer': '/customer',
        'update_customer': '/customer/{customer_code}',
        'whitelist_customer': '/customer/set_risk_level/{customer_id}',
        'deactivate_auth': '/authorization/deactivate',
    }
    
    # Payment status choices
    STATUS_CHOICES = {
        'success': 'Successful',
        'pending': 'Pending',
        'cancelled': 'Cancelled',
        'failed': 'Failed',
        'processing': 'Processing',
    }
    
    @staticmethod
    def get_endpoint(endpoint_name):
        """Get full endpoint URL"""
        if endpoint_name in PaystackConfig.ENDPOINTS:
            return PaystackConfig.BASE_URL + PaystackConfig.ENDPOINTS[endpoint_name]
        return None
    
    @staticmethod
    def get_public_key():
        """Get Paystack public key"""
        return PaystackConfig.PUBLIC_KEY
    
    @staticmethod
    def get_secret_key():
        """Get Paystack secret key"""
        return PaystackConfig.SECRET_KEY
    
    @staticmethod
    def get_base_url():
        """Get base URL"""
        return PaystackConfig.BASE_URL
    
    @staticmethod
    def get_headers():
        """Get headers for API requests"""
        return {
            'Authorization': f'Bearer {PaystackConfig.get_secret_key()}',
            'Content-Type': 'application/json',
        }

