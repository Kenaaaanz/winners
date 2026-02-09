"""
M-Pesa URL Configuration
"""
import json
from django.urls import path
from .mpesa_views import (
    STKPushView,
    STKCallbackView,
    C2BValidationView,
    C2BConfirmationView,
    QueryTransactionView,
    TransactionHistoryView,
    mpesa_config_view,
    test_mpesa_webhook
)

# Additional M-Pesa callback views (simplified versions)
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def b2c_result_callback(request):
    """Handle B2C result callback"""
    try:
        data = json.loads(request.body)
        # Process B2C result
        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
    except:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Error'})

@csrf_exempt
def b2c_timeout_callback(request):
    """Handle B2C timeout callback"""
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

@csrf_exempt
def balance_result_callback(request):
    """Handle balance result callback"""
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

@csrf_exempt
def balance_timeout_callback(request):
    """Handle balance timeout callback"""
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

@csrf_exempt
def reversal_result_callback(request):
    """Handle reversal result callback"""
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

@csrf_exempt
def reversal_timeout_callback(request):
    """Handle reversal timeout callback"""
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

@csrf_exempt
def transaction_status_result_callback(request):
    """Handle transaction status result callback"""
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

@csrf_exempt
def transaction_status_timeout_callback(request):
    """Handle transaction status timeout callback"""
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})

urlpatterns = [
    # API Endpoints
    path('stk-push/', STKPushView.as_view(), name='mpesa_stk_push'),
    path('stk-query/', QueryTransactionView.as_view(), name='mpesa_stk_query'),
    path('transactions/', TransactionHistoryView.as_view(), name='mpesa_transactions'),
    path('config/', mpesa_config_view, name='mpesa_config'),
    
    # Webhook Callbacks
    path('stk-callback/', STKCallbackView.as_view(), name='mpesa_stk_callback'),
    path('c2b-validation/', C2BValidationView.as_view(), name='mpesa_c2b_validation'),
    path('c2b-confirmation/', C2BConfirmationView.as_view(), name='mpesa_c2b_confirmation'),
    
    # Additional Callbacks (for other M-Pesa APIs)
    path('b2c-result/', b2c_result_callback, name='mpesa_b2c_result'),
    path('b2c-timeout/', b2c_timeout_callback, name='mpesa_b2c_timeout'),
    path('balance-result/', balance_result_callback, name='mpesa_balance_result'),
    path('balance-timeout/', balance_timeout_callback, name='mpesa_balance_timeout'),
    path('reversal-result/', reversal_result_callback, name='mpesa_reversal_result'),
    path('reversal-timeout/', reversal_timeout_callback, name='mpesa_reversal_timeout'),
    path('transaction-status-result/', transaction_status_result_callback, name='mpesa_transaction_status_result'),
    path('transaction-status-timeout/', transaction_status_timeout_callback, name='mpesa_transaction_status_timeout'),
    
    # Testing
    path('test-webhook/', test_mpesa_webhook, name='test_mpesa_webhook'),
]