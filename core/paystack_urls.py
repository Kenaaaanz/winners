"""
Paystack URLs
"""
from django.urls import path
from . import paystack_views

app_name = 'paystack'

urlpatterns = [
    # Checkout and verification
    path('checkout/<int:sale_id>/', paystack_views.paystack_checkout, name='checkout'),
    path('verify/<int:sale_id>/', paystack_views.paystack_verify, name='verify'),
    
    # Webhook
    path('webhook/', paystack_views.paystack_webhook, name='webhook'),
    
    # History and details
    path('transactions/', paystack_views.paystack_transaction_history, name='transaction_history'),
    path('transactions/<int:pk>/', paystack_views.paystack_transaction_detail, name='transaction_detail'),
    
    # Refund
    path('refund/<int:transaction_id>/', paystack_views.paystack_refund, name='refund'),
]
