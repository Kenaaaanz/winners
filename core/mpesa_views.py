"""
M-Pesa API Views and Webhook Handlers
"""
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.mpesa_config import MpesaConfig

from .mpesa_models import  MpesaTransaction, MpesaCallback
from .models import Sale, Notification
from .mpesa_service import MpesaService
from .serializers import MpesaTransactionSerializer

# Setup logger
logger = logging.getLogger('mpesa')

class MpesaAPIView(APIView):
    """
    Base M-Pesa API View
    """
    permission_classes = [IsAuthenticated]
    
    def get_mpesa_service(self):
        return MpesaService()
    
    def log_transaction(self, transaction_data, response_data):
        """Log transaction details"""
        logger.info(f"Transaction: {transaction_data}")
        logger.info(f"Response: {response_data}")

@method_decorator(csrf_exempt, name='dispatch')
class MpesaWebhookView(View):
    """
    Base M-Pesa Webhook View
    """
    
    def parse_request(self, request):
        """Parse incoming request"""
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook request")
            return None

class STKPushView(MpesaAPIView):
    """
    Initiate STK Push Payment
    """
    
    def post(self, request):
        try:
            data = request.data
            
            # Validate required fields
            required_fields = ['phone_number', 'amount', 'account_reference', 'transaction_desc']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {'error': f'Missing required field: {field}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get M-Pesa service
            mpesa_service = self.get_mpesa_service()
            
            # Validate and format phone number
            try:
                phone_number = mpesa_service.validate_phone_number(data['phone_number'])
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Format amount
            try:
                amount = mpesa_service.format_amount(data['amount'])
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create transaction record
            transaction = MpesaTransaction.objects.create(
                transaction_type='STK_PUSH',
                amount=amount,
                phone_number=phone_number,
                account_reference=data['account_reference'],
                transaction_desc=data['transaction_desc'],
                user=request.user,
                raw_request=data,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Initiate STK Push
            result = mpesa_service.stk_push(
                phone_number=phone_number,
                amount=amount,
                account_reference=data['account_reference'],
                transaction_desc=data['transaction_desc']
            )
            
            # Update transaction with response
            transaction.raw_response = result
            transaction.merchant_request_id = result.get('data', {}).get('MerchantRequestID', '')
            transaction.checkout_request_id = result.get('checkout_request_id', '')
            transaction.response_code = result.get('response_code', '')
            transaction.response_description = result.get('response_description', '')
            
            if result['success']:
                transaction.save()
                self.log_transaction(data, result)
                
                return Response({
                    'success': True,
                    'transaction_id': transaction.transaction_id,
                    'checkout_request_id': transaction.checkout_request_id,
                    'merchant_request_id': transaction.merchant_request_id,
                    'customer_message': result.get('customer_message'),
                    'message': 'STK Push initiated successfully. Check your phone to complete payment.'
                }, status=status.HTTP_200_OK)
            else:
                transaction.status = 'FAILED'
                transaction.result_description = result.get('error', 'STK Push failed')
                transaction.save()
                
                return Response({
                    'success': False,
                    'error': result.get('error', 'STK Push failed'),
                    'transaction_id': transaction.transaction_id
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"STK Push error: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class STKCallbackView(MpesaWebhookView):
    """
    Handle STK Push Callback from M-Pesa
    """
    
    @csrf_exempt
    def post(self, request):
        try:
            # Parse callback data
            callback_data = self.parse_request(request)
            if not callback_data:
                return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid JSON'})
            
            logger.info(f"STK Callback received: {callback_data}")
            
            # Save callback for auditing
            callback = MpesaCallback.objects.create(
                callback_type='STK',
                raw_data=callback_data
            )
            
            # Extract callback metadata
            body = callback_data.get('Body', {})
            stk_callback = body.get('stkCallback', {})
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            
            # Extract transaction details
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            
            # Update callback with extracted data
            callback.result_code = result_code
            callback.result_description = result_desc
            callback.save()
            
            # Find transaction
            try:
                transaction = MpesaTransaction.objects.get(
                    checkout_request_id=checkout_request_id,
                    status='PENDING'
                )
                callback.transaction = transaction
                callback.save()
            except MpesaTransaction.DoesNotExist:
                logger.error(f"Transaction not found for CheckoutRequestID: {checkout_request_id}")
                return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Transaction not found'})
            
            # Process based on result code
            if result_code == 0:
                # Success
                self.handle_successful_payment(transaction, callback_metadata)
                callback.is_processed = True
                callback.processed_at = timezone.now()
                callback.save()
                
                return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
            else:
                # Failed
                self.handle_failed_payment(transaction, result_code, result_desc)
                callback.is_processed = True
                callback.processed_at = timezone.now()
                callback.save()
                
                return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
                
        except Exception as e:
            logger.error(f"STK Callback processing error: {str(e)}", exc_info=True)
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Processing error'})
    
    def handle_successful_payment(self, transaction, callback_metadata):
        """Handle successful payment"""
        try:
            # Extract payment details from metadata
            amount = None
            receipt_number = None
            phone_number = None
            transaction_date = None
            
            if callback_metadata and 'Item' in callback_metadata:
                for item in callback_metadata['Item']:
                    if item.get('Name') == 'Amount':
                        amount = item.get('Value')
                    elif item.get('Name') == 'MpesaReceiptNumber':
                        receipt_number = item.get('Value')
                    elif item.get('Name') == 'PhoneNumber':
                        phone_number = item.get('Value')
                    elif item.get('Name') == 'TransactionDate':
                        transaction_date = item.get('Value')
            
            # Update transaction
            transaction.mpesa_receipt_number = receipt_number
            transaction.result_code = 0
            transaction.result_description = 'Payment successful'
            transaction.mark_success(
                receipt_number=receipt_number,
                result_code=0,
                result_desc='Payment successful'
            )
            
            # Update sale if exists
            self.update_sale_payment(transaction, amount, receipt_number)
            
            # Create notification
            self.create_notification(
                user=transaction.user,
                title='M-Pesa Payment Successful',
                message=f'Payment of KES {amount} received. Receipt: {receipt_number}',
                notification_type='SALE'
            )
            
            logger.info(f"Payment successful for transaction {transaction.transaction_id}")
            
        except Exception as e:
            logger.error(f"Error handling successful payment: {str(e)}")
    
    def handle_failed_payment(self, transaction, result_code, result_desc):
        """Handle failed payment"""
        try:
            # Update transaction
            transaction.result_code = result_code
            transaction.result_description = result_desc
            transaction.mark_failed(
                result_code=result_code,
                result_desc=result_desc
            )
            
            # Create notification
            self.create_notification(
                user=transaction.user,
                title='M-Pesa Payment Failed',
                message=f'Payment failed: {result_desc}',
                notification_type='SYSTEM'
            )
            
            logger.info(f"Payment failed for transaction {transaction.transaction_id}")
            
        except Exception as e:
            logger.error(f"Error handling failed payment: {str(e)}")
    
    def update_sale_payment(self, transaction, amount, receipt_number):
        """Update sale with payment details"""
        try:
            if transaction.sale:
                sale = transaction.sale
                sale.mpesa_receipt = receipt_number
                sale.status = 'COMPLETED'
                sale.save()
                
                # Update customer loyalty points
                if sale.customer:
                    points_earned = int(float(amount) / 100)  # 1 point per 100 KSH
                    sale.customer.loyalty_points += points_earned
                    sale.customer.total_spent += float(amount)
                    sale.customer.last_purchase = timezone.now()
                    sale.customer.save()
                    
        except Exception as e:
            logger.error(f"Error updating sale: {str(e)}")
    
    def create_notification(self, user, title, message, notification_type):
        """Create notification for user"""
        try:
            if user:
                Notification.objects.create(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    link=f'/pos/sales/{user.id}/' if user else ''
                )
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")

class C2BValidationView(MpesaWebhookView):
    """
    Handle C2B Validation Callback
    """
    
    @csrf_exempt
    def post(self, request):
        try:
            callback_data = self.parse_request(request)
            if not callback_data:
                return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid JSON'})
            
            logger.info(f"C2B Validation received: {callback_data}")
            
            # Save callback
            callback = MpesaCallback.objects.create(
                callback_type='C2B',
                raw_data=callback_data
            )
            
            # Validate transaction (you can add business logic here)
            # For now, accept all transactions
            response = {
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
            
            callback.is_processed = True
            callback.processed_at = timezone.now()
            callback.save()
            
            return JsonResponse(response)
            
        except Exception as e:
            logger.error(f"C2B Validation error: {str(e)}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Processing error'})

class C2BConfirmationView(MpesaWebhookView):
    """
    Handle C2B Confirmation Callback
    """
    
    @csrf_exempt
    def post(self, request):
        try:
            callback_data = self.parse_request(request)
            if not callback_data:
                return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid JSON'})
            
            logger.info(f"C2B Confirmation received: {callback_data}")
            
            # Save callback
            callback = MpesaCallback.objects.create(
                callback_type='C2B',
                raw_data=callback_data
            )
            
            # Process confirmed transaction
            self.process_c2b_transaction(callback_data)
            
            callback.is_processed = True
            callback.processed_at = timezone.now()
            callback.save()
            
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
            
        except Exception as e:
            logger.error(f"C2B Confirmation error: {str(e)}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Processing error'})
    
    def process_c2b_transaction(self, callback_data):
        """Process C2B transaction"""
        try:
            # Extract transaction details
            transaction_type = callback_data.get('TransactionType')
            trans_id = callback_data.get('TransID')
            trans_time = callback_data.get('TransTime')
            trans_amount = callback_data.get('TransAmount')
            business_shortcode = callback_data.get('BusinessShortCode')
            bill_ref_number = callback_data.get('BillRefNumber')
            invoice_number = callback_data.get('InvoiceNumber')
            org_account_balance = callback_data.get('OrgAccountBalance')
            third_party_trans_id = callback_data.get('ThirdPartyTransID')
            msisdn = callback_data.get('MSISDN')
            first_name = callback_data.get('FirstName')
            middle_name = callback_data.get('MiddleName')
            last_name = callback_data.get('LastName')
            
            # Create transaction record
            transaction = MpesaTransaction.objects.create(
                transaction_type='C2B',
                amount=trans_amount,
                phone_number=msisdn,
                account_reference=bill_ref_number or invoice_number or 'C2B Payment',
                transaction_desc=f'C2B {transaction_type}',
                mpesa_receipt_number=trans_id,
                status='SUCCESS',
                is_complete=True,
                completed_at=timezone.now(),
                raw_request=callback_data,
                raw_response={'processed': True}
            )
            
            # Create notification
            Notification.objects.create(
                notification_type='SALE',
                title='C2B Payment Received',
                message=f'C2B payment of KES {trans_amount} received from {first_name} {last_name}',
                link=''
            )
            
            logger.info(f"C2B transaction processed: {trans_id}")
            
        except Exception as e:
            logger.error(f"Error processing C2B transaction: {str(e)}")

class QueryTransactionView(MpesaAPIView):
    """
    Query transaction status
    """
    
    def post(self, request):
        try:
            data = request.data
            
            if 'transaction_id' not in data:
                return Response(
                    {'error': 'Missing transaction_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            mpesa_service = self.get_mpesa_service()
            
            result = mpesa_service.stk_query(data['transaction_id'])
            
            if result['success']:
                return Response({
                    'success': True,
                    'result_code': result.get('result_code'),
                    'result_desc': result.get('result_desc'),
                    'data': result.get('data')
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Query failed')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Query transaction error: {str(e)}")
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TransactionHistoryView(MpesaAPIView):
    """
    Get transaction history
    """
    
    def get(self, request):
        try:
            # Get filter parameters
            days = int(request.GET.get('days', 7))
            status_filter = request.GET.get('status')
            transaction_type = request.GET.get('type')
            
            # Calculate date range
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Build query
            transactions = MpesaTransaction.objects.filter(
                created_at__range=[start_date, end_date]
            )
            
            if status_filter:
                transactions = transactions.filter(status=status_filter)
            
            if transaction_type:
                transactions = transactions.filter(transaction_type=transaction_type)
            
            # Paginate
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            start = (page - 1) * page_size
            end = start + page_size
            
            paginated_transactions = transactions[start:end]
            
            # Serialize
            serializer = MpesaTransactionSerializer(paginated_transactions, many=True)
            
            return Response({
                'success': True,
                'transactions': serializer.data,
                'total': transactions.count(),
                'page': page,
                'page_size': page_size,
                'total_pages': (transactions.count() + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Transaction history error: {str(e)}")
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@require_GET
@login_required
def mpesa_config_view(request):
    """Get M-Pesa configuration (for frontend)"""
    config = {
        'environment': settings.MPESA_ENVIRONMENT,
        'shortcode': MpesaConfig.get_shortcode() if hasattr(settings, 'MPESA_SHORTCODE') else '',
        'is_test_mode': settings.MPESA_ENVIRONMENT == 'sandbox',
        'max_amount': 150000,
        'min_amount': 1,
        'currency': 'KES'
    }
    return JsonResponse(config)

@csrf_exempt
@require_POST
def test_mpesa_webhook(request):
    """Test endpoint for M-Pesa webhooks"""
    try:
        data = json.loads(request.body)
        logger.info(f"Test webhook received: {data}")
        
        # Simulate processing delay
        import time
        time.sleep(1)
        
        return JsonResponse({
            'success': True,
            'message': 'Webhook received successfully',
            'received_at': timezone.now().isoformat(),
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)