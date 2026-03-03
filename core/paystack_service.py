"""
Complete Paystack Service with all functionalities
"""
import requests
import json
import logging
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .paystack_config import PaystackConfig
import uuid

# Setup logging
logger = logging.getLogger('paystack')

# Development/Demo mode - set to True to work without internet
USE_MOCK_PAYMENTS = settings.DEBUG and getattr(settings, 'USE_MOCK_PAYMENTS', False)


class PaystackService:
    """
    Paystack Service for handling all Paystack operations
    """
    
    def __init__(self):
        self.secret_key = PaystackConfig.get_secret_key()
        self.public_key = PaystackConfig.get_public_key()
        self.base_url = PaystackConfig.get_base_url()
        self.headers = PaystackConfig.get_headers()
        
    def _validate_credentials(self):
        """Validate Paystack credentials"""
        if not self.secret_key or self.secret_key.startswith('sk_test_'):
            if self.secret_key == 'sk_test_your_secret_key':
                logger.error("PAYSTACK_SECRET_KEY not properly configured!")
                raise Exception("PAYSTACK_SECRET_KEY is not configured. Please set it in environment variables.")
        return True
    
    def initialize_transaction(self, email, amount, reference, metadata=None, callback_url=None):
        """
        Initialize a Paystack transaction
        
        Args:
            email (str): Customer email
            amount (float/Decimal): Amount in cents (Paystack uses kobo for NGN)
            reference (str): Unique transaction reference
            metadata (dict): Additional metadata
            callback_url (str): Custom callback URL
        
        Returns:
            dict: Transaction initialization response
        """
        self._validate_credentials()
        
        # Convert amount to kobo (cents) for NGN
        amount_in_kobo = int(float(amount) * 100)
        
        url = self.base_url + '/transaction/initialize'
        
        payload = {
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
        }
        
        if metadata:
            payload['metadata'] = metadata
        
        if callback_url:
            payload['callback_url'] = callback_url
        
        logger.info(f"Initializing Paystack transaction: Reference={reference}, Amount={amount}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                logger.info(f"Successfully initialized transaction: {reference}")
                return data.get('data', {})
            else:
                logger.warning(f"Transaction initialization failed: {data.get('message')}")
                raise Exception(f"Failed to initialize transaction: {data.get('message')}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout initializing transaction: {reference}")
            raise Exception("Request timeout")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error initializing transaction: {e.response.text}")
            raise Exception(f"HTTP Error: {e.response.text}")
        except Exception as e:
            logger.error(f"Error initializing transaction: {str(e)}")
            raise
    
    def verify_transaction(self, reference):
        """
        Verify a Paystack transaction
        
        Args:
            reference (str): Transaction reference
        
        Returns:
            dict: Transaction verification response
        """
        self._validate_credentials()
        
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        logger.info(f"Verifying Paystack transaction: {reference}")
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                logger.info(f"Successfully verified transaction: {reference}")
                return data.get('data', {})
            else:
                logger.warning(f"Transaction verification failed: {data.get('message')}")
                raise Exception(f"Failed to verify transaction: {data.get('message')}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout verifying transaction: {reference}")
            raise Exception("Request timeout")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error verifying transaction: {e.response.text}")
            raise Exception(f"HTTP Error: {e.response.text}")
        except Exception as e:
            logger.error(f"Error verifying transaction: {str(e)}")
            raise
    
    def create_customer(self, email, first_name, last_name, phone=None):
        """
        Create a Paystack customer
        
        Args:
            email (str): Customer email
            first_name (str): Customer first name
            last_name (str): Customer last name
            phone (str): Customer phone number
        
        Returns:
            dict: Customer creation response
        """
        self._validate_credentials()
        
        url = f"{self.base_url}/customer"
        
        payload = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
        }
        
        if phone:
            payload['phone'] = phone
        
        logger.info(f"Creating Paystack customer: {email}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                logger.info(f"Successfully created customer: {email}")
                return data.get('data', {})
            else:
                logger.warning(f"Customer creation failed: {data.get('message')}")
                raise Exception(f"Failed to create customer: {data.get('message')}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout creating customer: {email}")
            raise Exception("Request timeout")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error creating customer: {e.response.text}")
            raise Exception(f"HTTP Error: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            raise
    
    def get_customer(self, customer_code):
        """
        Get Paystack customer details
        
        Args:
            customer_code (str): Customer code or ID
        
        Returns:
            dict: Customer details
        """
        self._validate_credentials()
        
        url = f"{self.base_url}/customer/{customer_code}"
        
        logger.info(f"Fetching customer: {customer_code}")
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                logger.info(f"Successfully fetched customer: {customer_code}")
                return data.get('data', {})
            else:
                logger.warning(f"Customer fetch failed: {data.get('message')}")
                raise Exception(f"Failed to fetch customer: {data.get('message')}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching customer: {customer_code}")
            raise Exception("Request timeout")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error fetching customer: {e.response.text}")
            raise Exception(f"HTTP Error: {e.response.text}")
        except Exception as e:
            logger.error(f"Error fetching customer: {str(e)}")
            raise
    
    def charge_authorization(self, authorization_code, email, amount, reference, metadata=None):
        """
        Charge a customer using their authorization
        
        Args:
            authorization_code (str): Customer authorization code
            email (str): Customer email
            amount (float/Decimal): Amount in major units
            reference (str): Transaction reference
            metadata (dict): Additional metadata
        
        Returns:
            dict: Charge response
        """
        self._validate_credentials()
        
        amount_in_kobo = int(float(amount) * 100)
        
        url = f"{self.base_url}/transaction/charge_authorization"
        
        payload = {
            'authorization_code': authorization_code,
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
        }
        
        if metadata:
            payload['metadata'] = metadata
        
        logger.info(f"Charging authorization: {authorization_code}, Amount={amount}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                logger.info(f"Successfully charged authorization: {reference}")
                return data.get('data', {})
            else:
                logger.warning(f"Charge failed: {data.get('message')}")
                raise Exception(f"Failed to charge: {data.get('message')}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout charging authorization: {reference}")
            raise Exception("Request timeout")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error charging authorization: {e.response.text}")
            raise Exception(f"HTTP Error: {e.response.text}")
        except Exception as e:
            logger.error(f"Error charging authorization: {str(e)}")
            raise
    
    def refund_transaction(self, reference, amount=None):
        """
        Refund a transaction
        
        Args:
            reference (str): Transaction reference
            amount (float/Decimal): Partial refund amount (optional)
        
        Returns:
            dict: Refund response
        """
        self._validate_credentials()
        
        url = f"{self.base_url}/refund"
        
        payload = {
            'transaction': reference,
        }
        
        if amount:
            amount_in_kobo = int(float(amount) * 100)
            payload['amount'] = amount_in_kobo
        
        logger.info(f"Refunding transaction: {reference}, Amount={amount}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                logger.info(f"Successfully refunded transaction: {reference}")
                return data.get('data', {})
            else:
                logger.warning(f"Refund failed: {data.get('message')}")
                raise Exception(f"Failed to refund: {data.get('message')}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout refunding transaction: {reference}")
            raise Exception("Request timeout")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error refunding transaction: {e.response.text}")
            raise Exception(f"HTTP Error: {e.response.text}")
        except Exception as e:
            logger.error(f"Error refunding transaction: {str(e)}")
            raise
    
    def list_transactions(self, limit=50, offset=0, from_date=None, to_date=None):
        """
        List Paystack transactions
        
        Args:
            limit (int): Number of records to fetch
            offset (int): Record offset
            from_date (str): Filter from date
            to_date (str): Filter to date
        
        Returns:
            dict: List of transactions
        """
        self._validate_credentials()
        
        url = f"{self.base_url}/transaction"
        
        params = {
            'perPage': limit,
            'page': (offset // limit) + 1
        }
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        
        logger.info(f"Listing transactions: limit={limit}, offset={offset}")
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                logger.info(f"Successfully fetched transaction list")
                return data.get('data', [])
            else:
                logger.warning(f"Transaction list fetch failed: {data.get('message')}")
                raise Exception(f"Failed to fetch transactions: {data.get('message')}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching transactions")
            raise Exception("Request timeout")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error fetching transactions: {e.response.text}")
            raise Exception(f"HTTP Error: {e.response.text}")
        except Exception as e:
            logger.error(f"Error fetching transactions: {str(e)}")
            raise
    
    def generate_reference(self, prefix='TXN'):
        """
        Generate a unique transaction reference
        
        Args:
            prefix (str): Reference prefix
        
        Returns:
            str: Unique reference
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"{prefix}-{timestamp}-{unique_id}"
