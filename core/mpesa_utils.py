"""
M-Pesa Utility Functions and Helpers
"""
import re
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from .mpesa_config import MpesaConfig

class MpesaUtils:
    """
    Utility class for M-Pesa operations
    """
    
    @staticmethod
    def format_phone_number(phone_number):
        """
        Format Kenyan phone number to M-Pesa format (2547XXXXXXXX)
        
        Args:
            phone_number: Raw phone number string
            
        Returns:
            Formatted phone number
            
        Raises:
            ValueError: If phone number is invalid
        """
        # Remove all non-digit characters
        phone = re.sub(r'\D', '', phone_number)
        
        # Validate length
        if len(phone) < 9 or len(phone) > 12:
            raise ValueError(f"Invalid phone number length: {phone}")
        
        # Convert to 254 format
        if phone.startswith('0'):
            # Format: 07XXXXXXXX -> 2547XXXXXXXX
            if len(phone) == 10:
                return '254' + phone[1:]
            else:
                raise ValueError(f"Invalid 0-prefixed phone number: {phone}")
        elif phone.startswith('254'):
            # Format: 2547XXXXXXXX
            if len(phone) == 12:
                return phone
            else:
                raise ValueError(f"Invalid 254-prefixed phone number: {phone}")
        elif phone.startswith('7'):
            # Format: 7XXXXXXXX -> 2547XXXXXXXX
            if len(phone) == 9:
                return '254' + phone
            else:
                raise ValueError(f"Invalid 7-prefixed phone number: {phone}")
        elif phone.startswith('+254'):
            # Format: +2547XXXXXXXX -> 2547XXXXXXXX
            if len(phone) == 13:
                return phone[1:]  # Remove +
            else:
                raise ValueError(f"Invalid +254-prefixed phone number: {phone}")
        else:
            raise ValueError(f"Unknown phone number format: {phone}")
    
    @staticmethod
    def validate_amount(amount):
        """
        Validate amount for M-Pesa transaction
        
        Args:
            amount: Amount to validate
            
        Returns:
            Validated amount as integer
            
        Raises:
            ValueError: If amount is invalid
        """
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")
            if amount > 150000:
                raise ValueError("Amount exceeds M-Pesa limit of 150,000")
            
            # M-Pesa requires whole shillings for STK Push
            if not amount.is_integer():
                raise ValueError("Amount must be a whole number (no cents)")
            
            return int(amount)
        except (ValueError, TypeError):
            raise ValueError("Invalid amount format")
    
    @staticmethod
    def generate_transaction_reference(prefix='INV'):
        """
        Generate unique transaction reference
        
        Args:
            prefix: Reference prefix
            
        Returns:
            Unique reference string
        """
        from django.utils import timezone
        import random
        import string
        
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        return f"{prefix}-{timestamp}-{random_str}"
    
    @staticmethod
    def get_access_token(cache_key='mpesa_access_token'):
        """
        Get cached access token or fetch new one
        
        Args:
            cache_key: Cache key for token
            
        Returns:
            Access token string
        """
        from .mpesa_service import MpesaService
        
        # Check cache first
        token_data = cache.get(cache_key)
        if token_data and token_data.get('expires_at') > timezone.now():
            return token_data['token']
        
        # Fetch new token
        mpesa_service = MpesaService()
        try:
            token = mpesa_service.get_access_token()
            
            # Cache token for 55 minutes (tokens expire after 1 hour)
            cache.set(cache_key, {
                'token': token,
                'expires_at': timezone.now() + timedelta(minutes=55)
            }, 55 * 60)
            
            return token
        except Exception as e:
            raise Exception(f"Failed to get access token: {str(e)}")
    
    @staticmethod
    def verify_callback_signature(request_body, signature_header):
        """
        Verify M-Pesa callback signature (for security)
        
        Args:
            request_body: Raw request body
            signature_header: Signature from X-Mpesa-Signature header
            
        Returns:
            Boolean indicating if signature is valid
        """
        # This is a placeholder. In production, implement proper signature verification
        # using your secret key
        
        # For now, return True in sandbox mode
        if settings.MPESA_ENVIRONMENT == MpesaConfig.ENV_SANDBOX:
            return True
        
        # In production, you should verify the signature
        # Example implementation:
        # secret_key = settings.MPESA_CALLBACK_SECRET
        # computed_signature = hmac.new(
        #     secret_key.encode(),
        #     request_body.encode(),
        #     hashlib.sha256
        # ).hexdigest()
        # return computed_signature == signature_header
        
        return True  # TODO: Implement proper signature verification
    
    @staticmethod
    def parse_callback_data(data):
        """
        Parse callback data into structured format
        
        Args:
            data: Raw callback data
            
        Returns:
            Parsed callback data dictionary
        """
        parsed_data = {
            'type': None,
            'transaction_id': None,
            'amount': None,
            'phone_number': None,
            'result_code': None,
            'result_description': None,
            'raw_data': data
        }
        
        try:
            # Check if it's STK callback
            if 'Body' in data and 'stkCallback' in data['Body']:
                parsed_data['type'] = 'STK'
                stk_callback = data['Body']['stkCallback']
                
                parsed_data['checkout_request_id'] = stk_callback.get('CheckoutRequestID')
                parsed_data['result_code'] = stk_callback.get('ResultCode')
                parsed_data['result_description'] = stk_callback.get('ResultDesc')
                
                # Extract metadata
                if 'CallbackMetadata' in stk_callback:
                    for item in stk_callback['CallbackMetadata'].get('Item', []):
                        if item.get('Name') == 'Amount':
                            parsed_data['amount'] = item.get('Value')
                        elif item.get('Name') == 'MpesaReceiptNumber':
                            parsed_data['transaction_id'] = item.get('Value')
                        elif item.get('Name') == 'PhoneNumber':
                            parsed_data['phone_number'] = item.get('Value')
            
            # Check if it's C2B callback
            elif 'TransactionType' in data:
                parsed_data['type'] = 'C2B'
                parsed_data['transaction_id'] = data.get('TransID')
                parsed_data['amount'] = data.get('TransAmount')
                parsed_data['phone_number'] = data.get('MSISDN')
                parsed_data['result_code'] = 0  # C2B doesn't have result code
                parsed_data['result_description'] = 'C2B Payment'
            
            # Check if it's B2C callback
            elif 'Result' in data:
                parsed_data['type'] = 'B2C'
                result = data['Result']
                parsed_data['transaction_id'] = result.get('TransactionID')
                parsed_data['result_code'] = result.get('ResultCode')
                parsed_data['result_description'] = result.get('ResultDesc')
                
                # Extract result parameters
                if 'ResultParameters' in result:
                    for param in result['ResultParameters'].get('ResultParameter', []):
                        if param.get('Key') == 'TransactionAmount':
                            parsed_data['amount'] = param.get('Value')
                        elif param.get('Key') == 'ReceiverPartyPublicName':
                            parsed_data['phone_number'] = param.get('Value')
        
        except Exception as e:
            parsed_data['error'] = str(e)
        
        return parsed_data
    
    @staticmethod
    def calculate_transaction_fee(amount):
        """
        Calculate M-Pesa transaction fee
        
        Args:
            amount: Transaction amount
            
        Returns:
            Transaction fee
            
        Note: These are approximate fees, check latest M-Pesa rates
        """
        amount = float(amount)
        
        if amount <= 100:
            return 0
        elif amount <= 500:
            return 11
        elif amount <= 1000:
            return 15
        elif amount <= 1500:
            return 25
        elif amount <= 2500:
            return 30
        elif amount <= 3500:
            return 53
        elif amount <= 5000:
            return 60
        elif amount <= 7500:
            return 75
        elif amount <= 10000:
            return 85
        elif amount <= 15000:
            return 95
        elif amount <= 20000:
            return 100
        elif amount <= 35000:
            return 110
        elif amount <= 50000:
            return 120
        elif amount <= 150000:
            return 150
        else:
            return 200
    
    @staticmethod
    def get_transaction_status_message(result_code):
        """
        Get human-readable message for M-Pesa result code
        
        Args:
            result_code: M-Pesa result code
            
        Returns:
            Status message
        """
        status_messages = {
            0: "Success",
            1: "Insufficient Funds",
            2: "Less Than Minimum Transaction Value",
            3: "More Than Maximum Transaction Value",
            4: "Would Exceed Daily Transfer Limit",
            5: "Would Exceed Minimum Balance",
            6: "Unresolved Primary Party",
            7: "Unresolved Receiver Party",
            8: "Would Exceed Maximum Balance",
            11: "Debit Account Invalid",
            12: "Credit Account Invalid",
            13: "Unresolved Debit Account",
            14: "Unresolved Credit Account",
            15: "Duplicate Detected",
            17: "Internal Failure",
            20: "Unresolved Initiator",
            26: "Traffic blocking condition in place",
        }
        
        return status_messages.get(result_code, f"Unknown error (Code: {result_code})")
    
    @staticmethod
    def log_mpesa_transaction(transaction_data, response_data, user=None, sale=None):
        """
        Log M-Pesa transaction to database
        
        Args:
            transaction_data: Transaction request data
            response_data: M-Pesa response data
            user: User who initiated transaction
            sale: Related sale object
        """
        from .models import MpesaTransaction
        
        try:
            # Extract transaction details
            amount = transaction_data.get('amount')
            phone_number = transaction_data.get('phone_number')
            account_reference = transaction_data.get('account_reference')
            transaction_desc = transaction_data.get('transaction_desc')
            
            # Create transaction record
            transaction = MpesaTransaction.objects.create(
                transaction_type='STK_PUSH',
                amount=amount,
                phone_number=phone_number,
                account_reference=account_reference,
                transaction_desc=transaction_desc,
                user=user,
                sale=sale,
                raw_request=transaction_data,
                raw_response=response_data,
                ip_address=transaction_data.get('ip_address'),
                user_agent=transaction_data.get('user_agent')
            )
            
            # Update with response details
            if response_data.get('success'):
                transaction.merchant_request_id = response_data.get('merchant_request_id')
                transaction.checkout_request_id = response_data.get('checkout_request_id')
                transaction.response_code = response_data.get('response_code')
                transaction.response_description = response_data.get('response_description')
                transaction.save()
            
            return transaction
            
        except Exception as e:
            # Log error but don't break the flow
            import logging
            logger = logging.getLogger('mpesa')
            logger.error(f"Error logging M-Pesa transaction: {str(e)}")
            return None
    
    @staticmethod
    def send_payment_notification(transaction, notification_type='SUCCESS'):
        """
        Send payment notification to user
        
        Args:
            transaction: MpesaTransaction object
            notification_type: Type of notification
        """
        from .models import Notification
        
        try:
            if not transaction.user:
                return
            
            if notification_type == 'SUCCESS':
                title = 'M-Pesa Payment Successful'
                message = f'Payment of KES {transaction.amount} was successful. Receipt: {transaction.mpesa_receipt_number}'
            elif notification_type == 'FAILED':
                title = 'M-Pesa Payment Failed'
                message = f'Payment of KES {transaction.amount} failed. Reason: {transaction.result_description}'
            elif notification_type == 'PENDING':
                title = 'M-Pesa Payment Initiated'
                message = f'Payment of KES {transaction.amount} has been initiated. Check your phone to complete.'
            else:
                return
            
            Notification.objects.create(
                user=transaction.user,
                notification_type='SALE' if notification_type == 'SUCCESS' else 'SYSTEM',
                title=title,
                message=message,
                link=f'/transactions/mpesa/{transaction.transaction_id}/'
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger('mpesa')
            logger.error(f"Error sending payment notification: {str(e)}")