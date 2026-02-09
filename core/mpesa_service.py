"""
Complete M-Pesa Service with all functionalities
"""
import requests
import base64
import json
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from .mpesa_config import MpesaConfig
from urllib.parse import urlparse

# Setup logging
logger = logging.getLogger('mpesa')

class MpesaService:
    """
    M-Pesa Service for handling all M-Pesa operations
    """
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = MpesaConfig.get_base_url()
        self.environment = settings.MPESA_ENVIRONMENT
        
    def get_access_token(self):
        """
        Get M-Pesa OAuth access token
        Returns: access_token or None
        """
        url = MpesaConfig.get_endpoint('oauth')
        
        # Create Base64 encoded string
        auth_string = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        # Log credential check (without exposing actual credentials)
        logger.info(f"Attempting to get access token from: {url}")
        logger.info(f"Using environment: {self.environment}")
        
        if not self.consumer_key or self.consumer_key == '':
            logger.error("MPESA_CONSUMER_KEY not configured!")
            raise Exception("MPESA_CONSUMER_KEY is not configured")
        if not self.consumer_secret or self.consumer_secret == '':
            logger.error("MPESA_CONSUMER_SECRET not configured!")
            raise Exception("MPESA_CONSUMER_SECRET is not configured")
        
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Cache-Control': 'no-cache'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'access_token' in data:
                logger.info("Successfully obtained M-Pesa access token")
                return data['access_token']
            else:
                logger.error(f"Failed to get access token: {data}")
                raise Exception(f"Failed to get access token: {data}")
                
        except requests.exceptions.Timeout:
            logger.error("Timeout occurred while getting access token")
            raise Exception("Timeout occurred while getting access token")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error getting access token: {str(e)}")
            logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to authenticate with M-Pesa (HTTP {e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting access token: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from M-Pesa OAuth endpoint")
            raise Exception("Invalid JSON response from M-Pesa OAuth endpoint")
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            raise Exception(f"Error getting access token: {str(e)}")
    
    def generate_password(self, shortcode=None, passkey=None):
        """
        Generate password for STK Push
        """
        if not shortcode:
            shortcode = MpesaConfig.get_shortcode()
        if not passkey:
            passkey = MpesaConfig.get_passkey()
            
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{shortcode}{passkey}{timestamp}".encode()
        ).decode()
        
        return password, timestamp
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc, callback_url=None):
        """
        Initiate STK Push (Lipa na M-Pesa Online)
        
        Args:
            phone_number: Customer phone number (format: 2547XXXXXXXX)
            amount: Amount to charge
            account_reference: Reference number (invoice number)
            transaction_desc: Transaction description
            callback_url: Callback URL for payment confirmation
            
        Returns: dict with response data
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("Failed to get access token")
            
            url = MpesaConfig.get_endpoint('stk_push')
            
            shortcode = MpesaConfig.get_shortcode()
            passkey = MpesaConfig.get_passkey()
            password, timestamp = self.generate_password(shortcode, passkey)
            
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif phone_number.startswith('+254'):
                phone_number = phone_number[1:]
            elif not phone_number.startswith('254'):
                phone_number = '254' + phone_number
            
            # Use default callback URL if not provided
            if not callback_url:
                callback_url = f"{settings.BASE_URL}/api/mpesa/stk-callback/"

            # Validate callback URL: M-Pesa requires a publicly reachable HTTPS URL
            try:
                parsed_cb = urlparse(callback_url)
                if parsed_cb.scheme.lower() != 'https':
                    logger.error(f"Invalid callback URL scheme: {callback_url}")
                    raise ValueError(
                        "Invalid CallBackURL: M-Pesa requires a publicly accessible HTTPS callback URL. "
                        "Set `BASE_URL` to an https URL (eg. via ngrok) or pass a valid `callback_url`.")

                # Disallow localhost/loopback
                hostname = parsed_cb.hostname or ''
                if hostname.startswith('localhost') or hostname.startswith('127.') or hostname == '::1':
                    logger.error(f"Callback URL resolves to localhost/loopback: {callback_url}")
                    raise ValueError(
                        "Invalid CallBackURL: Callback URL must be publicly accessible (not localhost). "
                        "Use a tunneling service like ngrok or set BASE_URL to a public https endpoint.")
            except ValueError:
                # Re-raise our ValueErrors
                raise
            except Exception:
                # If urlparse failed unexpectedly, raise a helpful error
                logger.error(f"Failed to parse callback URL: {callback_url}")
                raise ValueError("Invalid CallBackURL: unable to parse provided callback URL")
            
            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": callback_url,
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"STK Push Request Payload: {json.dumps(payload, indent=2)}")
            logger.info(f"STK Push URL: {url}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"STK Push Response Status: {response.status_code}")
            logger.info(f"STK Push Response Body: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            # Validate response
            if data.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'data': data,
                    'checkout_request_id': data.get('CheckoutRequestID'),
                    'merchant_request_id': data.get('MerchantRequestID'),
                    'customer_message': data.get('CustomerMessage'),
                    'response_code': data.get('ResponseCode'),
                    'response_description': data.get('ResponseDescription')
                }
            else:
                return {
                    'success': False,
                    'error': data.get('ResponseDescription', 'STK Push failed'),
                    'response_code': data.get('ResponseCode'),
                    'response_description': data.get('ResponseDescription')
                }
                
        except requests.exceptions.Timeout:
            logger.error("Timeout occurred during STK Push")
            raise Exception("Timeout occurred during STK Push")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error during STK Push: {str(e)}")
            logger.error(f"Response text: {e.response.text}")
            raise Exception(f"M-Pesa API Error (HTTP {e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during STK Push: {str(e)}")
            raise Exception(f"Network error during STK Push: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from M-Pesa STK Push")
        except Exception as e:
            raise Exception(f"Error during STK Push: {str(e)}")
    
    def stk_query(self, checkout_request_id):
        """
        Query STK Push transaction status
        
        Args:
            checkout_request_id: Checkout Request ID from STK Push
            
        Returns: dict with transaction status
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("Failed to get access token")
            
            url = MpesaConfig.get_endpoint('stk_query')
            
            shortcode = MpesaConfig.get_shortcode()
            passkey = MpesaConfig.get_passkey()
            password, timestamp = self.generate_password(shortcode, passkey)
            
            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data,
                'result_code': data.get('ResultCode'),
                'result_desc': data.get('ResultDesc')
            }
            
        except requests.exceptions.Timeout:
            raise Exception("Timeout occurred during STK Query")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during STK Query: {str(e)}")
        except Exception as e:
            raise Exception(f"Error during STK Query: {str(e)}")
    
    def c2b_register_url(self, validation_url, confirmation_url, response_type="Completed"):
        """
        Register C2B URLs
        
        Args:
            validation_url: URL for validation
            confirmation_url: URL for confirmation
            response_type: Response type (Completed or Cancelled)
            
        Returns: dict with registration status
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("Failed to get access token")
            
            url = MpesaConfig.get_endpoint('c2b_register')
            
            shortcode = MpesaConfig.get_shortcode()
            
            payload = {
                "ShortCode": shortcode,
                "ResponseType": response_type,
                "ConfirmationURL": confirmation_url,
                "ValidationURL": validation_url
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data,
                'response_code': data.get('ResponseCode'),
                'response_description': data.get('ResponseDescription')
            }
            
        except Exception as e:
            raise Exception(f"Error registering C2B URLs: {str(e)}")
    
    def c2b_simulate(self, phone_number, amount, command_id="CustomerPayBillOnline", bill_ref_number=None):
        """
        Simulate C2B transaction (for testing)
        
        Args:
            phone_number: Customer phone number
            amount: Amount to pay
            command_id: Command ID
            bill_ref_number: Bill reference number
            
        Returns: dict with simulation result
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("Failed to get access token")
            
            url = MpesaConfig.get_endpoint('c2b_simulate')
            
            shortcode = MpesaConfig.get_shortcode()
            
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            
            payload = {
                "ShortCode": shortcode,
                "CommandID": command_id,
                "Amount": amount,
                "Msisdn": phone_number,
                "BillRefNumber": bill_ref_number or f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data,
                'response_code': data.get('ResponseCode'),
                'response_description': data.get('ResponseDescription')
            }
            
        except Exception as e:
            raise Exception(f"Error simulating C2B transaction: {str(e)}")
    
    def b2c_payment(self, phone_number, amount, command_id="BusinessPayment", remarks="Salary payment", occassion=""):
        """
        Initiate B2C payment
        
        Args:
            phone_number: Customer phone number
            amount: Amount to pay
            command_id: Command ID
            remarks: Payment remarks
            occassion: Occassion
            
        Returns: dict with payment result
        """
        try:
            # Validate required configuration
            initiator_name = settings.MPESA_INITIATOR_NAME
            if not initiator_name or initiator_name == '':
                raise ValueError("MPESA_INITIATOR_NAME is not configured. Please set it in your environment variables.")
            
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("Failed to get access token")
            
            url = MpesaConfig.get_endpoint('b2c')
            
            shortcode = MpesaConfig.get_shortcode()
            security_credential = self.get_security_credential()
            
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            
            payload = {
                "InitiatorName": initiator_name,
                "SecurityCredential": security_credential,
                "CommandID": command_id,
                "Amount": amount,
                "PartyA": shortcode,
                "PartyB": phone_number,
                "Remarks": remarks,
                "QueueTimeOutURL": f"{settings.BASE_URL}/api/mpesa/b2c-timeout/",
                "ResultURL": f"{settings.BASE_URL}/api/mpesa/b2c-result/",
                "Occassion": occassion
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data,
                'response_code': data.get('ResponseCode'),
                'response_description': data.get('ResponseDescription')
            }
            
        except Exception as e:
            raise Exception(f"Error initiating B2C payment: {str(e)}")
    
    def transaction_status(self, transaction_id, identifier_type=1, remarks="Transaction status query", occassion=""):
        """
        Query transaction status
        
        Args:
            transaction_id: M-Pesa transaction ID
            identifier_type: Identifier type (1=MSISDN, 2=Till, 4=Shortcode)
            remarks: Query remarks
            occassion: Occassion
            
        Returns: dict with transaction status
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("Failed to get access token")
            
            url = MpesaConfig.get_endpoint('transaction_status')
            
            shortcode = MpesaConfig.get_shortcode()
            initiator_name = settings.MPESA_INITIATOR_NAME
            security_credential = self.get_security_credential()
            
            payload = {
                "Initiator": initiator_name,
                "SecurityCredential": security_credential,
                "CommandID": "TransactionStatusQuery",
                "TransactionID": transaction_id,
                "PartyA": shortcode,
                "IdentifierType": identifier_type,
                "ResultURL": f"{settings.BASE_URL}/api/mpesa/transaction-status-result/",
                "QueueTimeOutURL": f"{settings.BASE_URL}/api/mpesa/transaction-status-timeout/",
                "Remarks": remarks,
                "Occassion": occassion
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data,
                'response_code': data.get('ResponseCode'),
                'response_description': data.get('ResponseDescription')
            }
            
        except Exception as e:
            raise Exception(f"Error querying transaction status: {str(e)}")
    
    def account_balance(self, identifier_type=4, remarks="Account balance query"):
        """
        Query account balance
        
        Args:
            identifier_type: Identifier type (1=MSISDN, 2=Till, 4=Shortcode)
            remarks: Query remarks
            
        Returns: dict with account balance
        """
        try:
            # Validate required configuration
            initiator_name = settings.MPESA_INITIATOR_NAME
            if not initiator_name or initiator_name == '':
                raise ValueError("MPESA_INITIATOR_NAME is not configured. Please set it in your environment variables.")
            
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("Failed to get access token")
            
            url = MpesaConfig.get_endpoint('account_balance')
            
            shortcode = MpesaConfig.get_shortcode()
            security_credential = self.get_security_credential()
            
            payload = {
                "Initiator": initiator_name,
                "SecurityCredential": security_credential,
                "CommandID": "AccountBalance",
                "PartyA": shortcode,
                "IdentifierType": identifier_type,
                "Remarks": remarks,
                "QueueTimeOutURL": f"{settings.BASE_URL}/api/mpesa/balance-timeout/",
                "ResultURL": f"{settings.BASE_URL}/api/mpesa/balance-result/"
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data,
                'response_code': data.get('ResponseCode'),
                'response_description': data.get('ResponseDescription')
            }
            
        except Exception as e:
            raise Exception(f"Error querying account balance: {str(e)}")
    
    def reversal(self, transaction_id, amount, receiver_party, remarks="Transaction reversal", occassion=""):
        """
        Initiate transaction reversal
        
        Args:
            transaction_id: Original transaction ID
            amount: Amount to reverse
            receiver_party: Receiver party (original sender)
            remarks: Reversal remarks
            occassion: Occassion
            
        Returns: dict with reversal result
        """
        try:
            # Validate required configuration
            initiator_name = settings.MPESA_INITIATOR_NAME
            if not initiator_name or initiator_name == '':
                raise ValueError("MPESA_INITIATOR_NAME is not configured. Please set it in your environment variables.")
            
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("Failed to get access token")
            
            url = MpesaConfig.get_endpoint('reversal')
            
            shortcode = MpesaConfig.get_shortcode()
            security_credential = self.get_security_credential()
            
            payload = {
                "Initiator": initiator_name,
                "SecurityCredential": security_credential,
                "CommandID": "TransactionReversal",
                "TransactionID": transaction_id,
                "Amount": amount,
                "ReceiverParty": receiver_party,
                "RecieverIdentifierType": "11",  # MSISDN
                "ResultURL": f"{settings.BASE_URL}/api/mpesa/reversal-result/",
                "QueueTimeOutURL": f"{settings.BASE_URL}/api/mpesa/reversal-timeout/",
                "Remarks": remarks,
                "Occassion": occassion
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data,
                'response_code': data.get('ResponseCode'),
                'response_description': data.get('ResponseDescription')
            }
            
        except Exception as e:
            raise Exception(f"Error initiating reversal: {str(e)}")
    
    def get_security_credential(self):
        """
        Get security credential (encrypted initiator password)
        For production, this should be stored securely
        """
        import os
        import base64
        
        # Validate configuration
        initiator_password = settings.MPESA_INITIATOR_PASSWORD
        if not initiator_password or initiator_password == '':
            raise ValueError("MPESA_INITIATOR_PASSWORD is not configured. Please set it in your environment variables.")
        
        if self.environment == MpesaConfig.ENV_PRODUCTION:
            # For production, validate certificate path
            cert_path = settings.MPESA_CERTIFICATE_PATH
            if not cert_path or cert_path == '':
                raise ValueError("MPESA_CERTIFICATE_PATH must be configured for production environment.")
            
            if not os.path.exists(cert_path):
                raise FileNotFoundError(f"M-Pesa certificate file not found at: {cert_path}")
            
            try:
                with open(cert_path, 'rb') as cert_file:
                    cert_data = cert_file.read()
            except IOError as e:
                raise IOError(f"Failed to read M-Pesa certificate: {str(e)}")
            
            # Use certificate to encrypt (simplified version)
            # In real implementation, use proper RSA encryption
            return base64.b64encode(initiator_password.encode()).decode()
        else:
            # For sandbox, use base64 encoding
            return base64.b64encode(initiator_password.encode()).decode()
    
    def validate_phone_number(self, phone_number):
        """
        Validate and format Kenyan phone number
        
        Args:
            phone_number: Raw phone number
            
        Returns: Formatted phone number or raises exception
        """
        # Remove any non-digit characters
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        if len(phone_number) < 9 or len(phone_number) > 12:
            raise ValueError("Invalid phone number length")
        
        # Handle different formats
        if phone_number.startswith('0'):
            # Format: 07XXXXXXXX
            if len(phone_number) == 10:
                return '254' + phone_number[1:]
            else:
                raise ValueError("Invalid phone number format")
        elif phone_number.startswith('254'):
            # Format: 2547XXXXXXXX
            if len(phone_number) == 12:
                return phone_number
            else:
                raise ValueError("Invalid phone number format")
        elif phone_number.startswith('7'):
            # Format: 7XXXXXXXX
            if len(phone_number) == 9:
                return '254' + phone_number
            else:
                raise ValueError("Invalid phone number format")
        else:
            raise ValueError("Invalid phone number format")
    
    def format_amount(self, amount):
        """
        Format amount for M-Pesa
        """
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")
            if amount > 150000:  # M-Pesa limit
                raise ValueError("Amount exceeds M-Pesa limit of 150,000")
            return int(amount)
        except ValueError:
            raise ValueError("Invalid amount")