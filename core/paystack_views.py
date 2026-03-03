"""
Paystack Payment Views
"""
import json
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from .models import Sale, PaystackTransaction, Customer
from .paystack_service import PaystackService

logger = logging.getLogger('paystack')


@login_required
def paystack_checkout(request, sale_id):
    """
    Initialize Paystack payment for a sale
    """
    try:
        sale = get_object_or_404(Sale, id=sale_id)
        
        # Check if sale is already paid
        if sale.status == 'COMPLETED':
            messages.warning(request, 'This sale has already been paid.')
            return redirect('pos_dashboard')
        
        # Get customer email
        customer_email = sale.customer.email if sale.customer else request.user.email
        
        # Initialize Paystack transaction
        paystack_service = PaystackService()
        reference = paystack_service.generate_reference(f'SALE-{sale.invoice_number}')
        
        # Create metadata
        metadata = {
            'sale_id': sale.id,
            'invoice_number': sale.invoice_number,
            'customer_name': sale.customer.full_name if sale.customer else request.user.get_full_name(),
            'user_id': request.user.id,
        }
        
        # Initialize transaction
        init_response = paystack_service.initialize_transaction(
            email=customer_email,
            amount=float(sale.total),
            reference=reference,
            metadata=metadata
        )
        
        # Create PaystackTransaction record
        paystack_txn = PaystackTransaction.objects.create(
            sale=sale,
            reference=reference,
            access_code=init_response.get('access_code', ''),
            email=customer_email,
            amount=sale.total,
            metadata=metadata,
            gateway_response=init_response,
            authorization_url=init_response.get('authorization_url', ''),
            access_code_url=init_response.get('access_code_url', ''),
        )
        
        # Update sale with Paystack reference
        sale.paystack_reference = reference
        sale.paystack_access_code = init_response.get('access_code', '')
        sale.save()
        
        logger.info(f"Initialized Paystack payment for sale {sale.invoice_number}: {reference}")
        
        return render(request, 'paystack/checkout.html', {
            'sale': sale,
            'paystack_txn': paystack_txn,
            'public_key': settings.PAYSTACK_PUBLIC_KEY,
            'initialization_response': init_response,
        })
        
    except Exception as e:
        logger.error(f"Error initializing Paystack payment: {str(e)}")
        messages.error(request, f'Error initializing payment: {str(e)}')
        return redirect('pos_dashboard')


@login_required
@require_http_methods(["POST"])
def paystack_verify(request, sale_id):
    """
    Verify Paystack payment transaction
    """
    try:
        sale = get_object_or_404(Sale, id=sale_id)
        
        if not sale.paystack_reference:
            return JsonResponse({
                'status': False,
                'message': 'No Paystack transaction found for this sale'
            })
        
        paystack_service = PaystackService()
        
        # Verify transaction
        verification_response = paystack_service.verify_transaction(sale.paystack_reference)
        
        # Get or create PaystackTransaction
        paystack_txn, created = PaystackTransaction.objects.get_or_create(
            reference=sale.paystack_reference,
            defaults={
                'sale': sale,
                'email': sale.customer.email if sale.customer else request.user.email,
                'amount': sale.total,
            }
        )
        
        # Update transaction record
        paystack_txn.gateway_response = verification_response
        paystack_txn.verified_at = timezone.now()
        
        # Check if payment was successful
        if verification_response.get('status') == 'success':
            paystack_txn.status = 'SUCCESS'
            paystack_txn.payment_status = 'success'
            paystack_txn.paid_at = timezone.now()
            
            # Get authorization details if available
            if verification_response.get('authorization'):
                auth = verification_response['authorization']
                paystack_txn.authorization_code = auth.get('authorization_code', '')
                paystack_txn.customer_code = auth.get('customer_code', '')
                sale.paystack_authorization_code = auth.get('authorization_code', '')
                sale.card_last4 = auth.get('last4', '')
            
            # Update sale
            with transaction.atomic():
                sale.status = 'COMPLETED'
                sale.amount_paid = sale.total
                sale.payment_method = 'PAYSTACK'
                
                # Calculate change
                if sale.amount_paid > sale.total:
                    sale.change_given = sale.amount_paid - sale.total
                
                # Award loyalty points
                if sale.customer:
                    loyalty_points = int(sale.total / 1000)  # 1 point per 1000 currency units
                    sale.loyalty_points_earned = loyalty_points
                    sale.customer.loyalty_points += loyalty_points
                    sale.customer.total_spent += sale.total
                    sale.customer.last_purchase = timezone.now()
                    sale.customer.save()
                
                # Stock is already deducted in process_sale, no need to deduct again
                
                sale.save()
            
            paystack_txn.save()
            
            logger.info(f"Payment verified successfully for sale {sale.invoice_number}")
            
            return JsonResponse({
                'status': True,
                'message': 'Payment verified successfully',
                'data': {
                    'sale_id': sale.id,
                    'invoice_number': sale.invoice_number,
                    'amount': float(sale.total),
                    'status': 'completed'
                }
            })
        else:
            paystack_txn.status = 'FAILED'
            paystack_txn.payment_status = verification_response.get('status', 'unknown')
            paystack_txn.save()
            
            logger.warning(f"Payment verification failed for sale {sale.invoice_number}")
            
            return JsonResponse({
                'status': False,
                'message': f"Payment failed: {verification_response.get('status', 'Unknown error')}",
                'data': {
                    'sale_id': sale.id,
                    'invoice_number': sale.invoice_number,
                }
            })
        
    except Exception as e:
        logger.error(f"Error verifying Paystack payment: {str(e)}")
        return JsonResponse({
            'status': False,
            'message': f'Error verifying payment: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """
    Paystack webhook handler
    Verify webhook signature and process payment notification
    """
    try:
        # Verify webhook signature
        paystack_secret = settings.PAYSTACK_SECRET_KEY
        
        # Get signature from header
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')
        
        # Get request body
        payload = request.body
        
        # Hash the payload with secret
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            paystack_secret.encode(),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        # Verify signature
        if signature != expected_signature:
            logger.warning("Invalid Paystack webhook signature")
            return HttpResponse(status=403)
        
        # Parse the request body
        event_data = json.loads(payload)
        
        if 'data' not in event_data or 'reference' not in event_data['data']:
            return HttpResponse(status=200)
        
        reference = event_data['data']['reference']
        event_type = event_data.get('event', '')
        
        logger.info(f"Received Paystack webhook: {event_type} for reference {reference}")
        
        try:
            paystack_txn = PaystackTransaction.objects.get(reference=reference)
            
            if event_type == 'charge.success':
                paystack_txn.status = 'SUCCESS'
                paystack_txn.payment_status = 'success'
                paystack_txn.paid_at = timezone.now()
                paystack_txn.verified_at = timezone.now()
                paystack_txn.gateway_response = event_data.get('data', {})
                
                # Update associated sale
                if paystack_txn.sale:
                    from .models import StockReservation
                    sale = paystack_txn.sale
                    sale.status = 'COMPLETED'
                    sale.amount_paid = sale.total
                    sale.payment_method = 'PAYSTACK'
                    
                    # Award loyalty points
                    if sale.customer:
                        loyalty_points = int(sale.total / 1000)
                        sale.loyalty_points_earned = loyalty_points
                        sale.customer.loyalty_points += loyalty_points
                        sale.customer.total_spent += sale.total
                        sale.customer.last_purchase = timezone.now()
                        sale.customer.save()
                    
                    # Confirm stock reservation (stock was already deducted at checkout)
                    try:
                        reservation = StockReservation.objects.get(sale=sale)
                        reservation.confirm()
                    except StockReservation.DoesNotExist:
                        # For older sales without reservations, reduce stock manually
                        for item in sale.items.all():
                            if item.product:
                                item.product.quantity -= item.quantity
                                item.product.save()
                    
                    sale.save()
                
                logger.info(f"Webhook processed successfully for {reference}")
                
            elif event_type == 'charge.failed':
                paystack_txn.status = 'FAILED'
                paystack_txn.payment_status = 'failed'
                paystack_txn.gateway_response = event_data.get('data', {})
                
                # Release stock reservation on failed payment
                if paystack_txn.sale:
                    from .models import StockReservation
                    try:
                        reservation = StockReservation.objects.get(sale=paystack_txn.sale)
                        reservation.release()
                        logger.info(f"Stock reservation released for failed payment {reference}")
                    except StockReservation.DoesNotExist:
                        pass
                
                logger.warning(f"Webhook: Payment failed for {reference}")
            
            paystack_txn.save()
            
        except PaystackTransaction.DoesNotExist:
            logger.warning(f"PaystackTransaction not found for reference: {reference}")
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error processing Paystack webhook: {str(e)}")
        return HttpResponse(status=500)


@login_required
def paystack_transaction_history(request):
    """
    Display Paystack transaction history
    """
    transactions = PaystackTransaction.objects.filter(
        sale__cashier=request.user
    ).order_by('-created_at')
    
    if request.GET.get('status'):
        transactions = transactions.filter(status=request.GET.get('status'))
    
    context = {
        'transactions': transactions,
        'total_amount': sum(t.amount for t in transactions if t.status == 'SUCCESS'),
        'status_filter': request.GET.get('status', ''),
    }
    
    return render(request, 'paystack/transaction_history.html', context)


@login_required
def paystack_transaction_detail(request, pk):
    """
    Display Paystack transaction details
    """
    paystack_txn = get_object_or_404(PaystackTransaction, pk=pk)
    
    # Check permission
    if paystack_txn.sale and paystack_txn.sale.cashier != request.user:
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to view this transaction.')
            return redirect('paystack_transaction_history')
    
    context = {
        'transaction': paystack_txn,
        'sale': paystack_txn.sale,
    }
    
    return render(request, 'paystack/transaction_detail.html', context)


@login_required
@require_http_methods(["POST"])
def paystack_refund(request, transaction_id):
    """
    Initiate a refund for a Paystack transaction
    """
    try:
        paystack_txn = get_object_or_404(PaystackTransaction, id=transaction_id)
        
        # Check permission
        if paystack_txn.sale and paystack_txn.sale.cashier != request.user:
            if not request.user.is_staff:
                return JsonResponse({
                    'status': False,
                    'message': 'You do not have permission to refund this transaction'
                })
        
        # Check if transaction can be refunded
        if paystack_txn.status != 'SUCCESS':
            return JsonResponse({
                'status': False,
                'message': 'Only successful transactions can be refunded'
            })
        
        # Get refund amount from request
        refund_amount = request.POST.get('amount', paystack_txn.amount)
        refund_amount = Decimal(refund_amount)
        
        # Initialize refund
        paystack_service = PaystackService()
        refund_response = paystack_service.refund_transaction(
            reference=paystack_txn.reference,
            amount=float(refund_amount)
        )
        
        # Update transaction record
        paystack_txn.status = 'REFUNDED'
        paystack_txn.gateway_response = refund_response
        paystack_txn.save()
        
        # Update sale
        if paystack_txn.sale:
            sale = paystack_txn.sale
            sale.status = 'REFUNDED'
            sale.amount_paid = sale.total - refund_amount
            sale.save()
            
            # Restore product quantities
            for item in sale.items.all():
                if item.product:
                    item.product.quantity += item.quantity
                    item.product.save()
        
        logger.info(f"Refund initiated successfully for {paystack_txn.reference}")
        
        return JsonResponse({
            'status': True,
            'message': 'Refund initiated successfully',
            'data': {
                'transaction_id': paystack_txn.id,
                'reference': paystack_txn.reference,
                'refund_amount': float(refund_amount),
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing Paystack refund: {str(e)}")
        return JsonResponse({
            'status': False,
            'message': f'Error processing refund: {str(e)}'
        }, status=500)
