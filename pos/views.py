from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from decimal import Decimal
import json
import uuid
from datetime import datetime

from core.models import Product, Customer, Sale, SaleItem, StockTransaction, Category, Notification
from core.forms import SaleForm
# Mpesa gateway implementation lives in the top-level `core` package
from core.mpesa_service import MpesaService as MpesaGateway
from core.reports import generate_receipt_pdf
from core.permissions import require_role

@require_role('ADMIN', 'STAFF', 'CASHIER')
@login_required
def pos_dashboard(request):
    """Main POS interface"""
    products = Product.objects.filter(is_active=True).order_by('name')
    categories = Category.objects.filter(product__is_active=True).distinct().order_by('name')
    
    # Get active cart from session
    cart = request.session.get('pos_cart', [])
    cart_total = sum(item['total_price'] for item in cart)
    
    customers = Customer.objects.filter(is_active=True).order_by('first_name')
    
    context = {
        'products': products,
        'categories': categories,
        'cart': cart,
        'cart_total': cart_total,
        'customers': customers,
        'payment_methods': Sale.PAYMENT_METHODS,
    }
    return render(request, 'pos/dashboard.html', context)

@login_required
def get_cart(request):
    """Get current cart from session"""
    cart = request.session.get('pos_cart', [])
    return JsonResponse({
        'success': True,
        'cart': cart,
        'cart_count': len(cart),
        'subtotal': sum(item['total_price'] for item in cart)
    })

@login_required
@csrf_exempt
def add_to_cart(request):
    """Add product to POS cart"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            
            product = get_object_or_404(Product, id=product_id, is_active=True)
            
            # Check stock availability
            if product.quantity < quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {product.quantity} units available in stock'
                })
            
            # Get or initialize cart
            cart = request.session.get('pos_cart', [])
            
            # Check if product already in cart
            for item in cart:
                if item['product_id'] == product_id:
                    item['quantity'] += quantity
                    item['total_price'] = item['quantity'] * item['unit_price']
                    break
            else:
                # Add new item
                cart.append({
                    'product_id': product_id,
                    'product_name': product.name,
                    'product_sku': product.sku,
                    'quantity': quantity,
                    'unit_price': float(product.selling_price),
                    'total_price': float(product.selling_price * quantity)
                })
            
            # Update session
            request.session['pos_cart'] = cart
            request.session.modified = True
            
            # Calculate totals
            subtotal = sum(item['total_price'] for item in cart)
            
            return JsonResponse({
                'success': True,
                'cart_count': len(cart),
                'subtotal': subtotal,
                'cart_items': cart
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@csrf_exempt
def update_cart_item(request):
    """Update cart item quantity"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            
            cart = request.session.get('pos_cart', [])
            
            for item in cart:
                if item['product_id'] == product_id:
                    if quantity <= 0:
                        cart.remove(item)
                    else:
                        # Check stock
                        product = Product.objects.get(id=product_id)
                        if product.quantity < quantity:
                            return JsonResponse({
                                'success': False,
                                'error': f'Only {product.quantity} units available'
                            })
                        
                        item['quantity'] = quantity
                        item['total_price'] = item['quantity'] * item['unit_price']
                    break
            
            request.session['pos_cart'] = cart
            request.session.modified = True
            
            subtotal = sum(item['total_price'] for item in cart)
            
            return JsonResponse({
                'success': True,
                'cart_count': len(cart),
                'subtotal': subtotal,
                'cart_items': cart
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@csrf_exempt
def remove_from_cart(request):
    """Remove item from cart"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            cart = request.session.get('pos_cart', [])
            cart = [item for item in cart if item['product_id'] != product_id]
            
            request.session['pos_cart'] = cart
            request.session.modified = True
            
            subtotal = sum(item['total_price'] for item in cart)
            
            return JsonResponse({
                'success': True,
                'cart_count': len(cart),
                'subtotal': subtotal,
                'cart_items': cart
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@csrf_exempt
def clear_cart(request):
    """Clear entire cart"""
    if 'pos_cart' in request.session:
        del request.session['pos_cart']
    
    return JsonResponse({'success': True, 'cart_count': 0, 'subtotal': 0})

@login_required
@csrf_exempt
def process_sale(request):
    """Process the sale transaction"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            with transaction.atomic():
                # Get cart from session
                cart = request.session.get('pos_cart', [])
                if not cart:
                    return JsonResponse({'success': False, 'error': 'Cart is empty'})
                
                # Calculate totals - convert all to Decimal
                subtotal = Decimal(str(sum(item['total_price'] for item in cart)))
                discount_amount = Decimal(data.get('discount_amount', 0))
                tax_rate = Decimal(data.get('tax_rate', 16))
                tax_amount = (subtotal * tax_rate) / Decimal(100)
                total = subtotal + tax_amount - discount_amount
                
                # Create sale
                sale = Sale.objects.create(
                    customer_id=data.get('customer_id'),
                    cashier=request.user,
                    subtotal=subtotal,
                    discount_amount=discount_amount,
                    discount_percentage=Decimal(data.get('discount_percentage', 0)),
                    tax_amount=tax_amount,
                    tax_rate=tax_rate,
                    total=total,
                    payment_method=data.get('payment_method', 'CASH'),
                    status='PENDING' if data.get('payment_method') == 'MPESA' else 'COMPLETED',
                    notes=data.get('notes', ''),
                    amount_paid=Decimal(str(data.get('amount_paid', total))),
                    change_given=Decimal(str(data.get('change_given', 0)))
                )
                
                # Add sale items and update stock
                for item in cart:
                    product = Product.objects.get(id=item['product_id'])
                    
                    # Check stock again
                    if product.quantity < item['quantity']:
                        sale.status = 'CANCELLED'
                        sale.save()
                        return JsonResponse({
                            'success': False,
                            'error': f'Insufficient stock for {product.name}'
                        })
                    
                    # Create sale item
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        product_name=product.name,
                        product_sku=product.sku,
                        quantity=item['quantity'],
                        unit_price=Decimal(str(item['unit_price'])),
                        cost_price=product.cost_price,
                        total_price=Decimal(str(item['total_price']))
                    )
                    
                    # Update product stock
                    old_quantity = product.quantity
                    product.quantity -= item['quantity']
                    product.save()
                    
                    # Create stock transaction
                    StockTransaction.objects.create(
                        product=product,
                        transaction_type='SALE',
                        quantity=item['quantity'],
                        previous_quantity=old_quantity,
                        new_quantity=product.quantity,
                        reference=sale.invoice_number,
                        notes=f'Sale #{sale.invoice_number}',
                        created_by=request.user
                    )
                
                # Process M-Pesa payment if selected
                if data.get('payment_method') == 'MPESA' and data.get('mpesa_phone'):
                    mpesa = MpesaGateway()
                    result = mpesa.stk_push(
                        phone_number=data['mpesa_phone'],
                        amount=float(total),
                        account_reference=sale.invoice_number,
                        transaction_desc=f"Payment for invoice {sale.invoice_number}"
                    )
                    
                    if result and result.get('ResponseCode') == '0':
                        sale.mpesa_transaction_id = result.get('CheckoutRequestID')
                        sale.mpesa_phone = data['mpesa_phone']
                        sale.save()
                        
                        return JsonResponse({
                            'success': True,
                            'sale_id': sale.id,
                            'invoice_number': sale.invoice_number,
                            'mpesa_checkout_id': result.get('CheckoutRequestID'),
                            'mpesa': True,
                            'message': 'M-Pesa payment initiated. Check your phone.'
                        })
                    else:
                        sale.status = 'CANCELLED'
                        sale.save()
                        return JsonResponse({
                            'success': False,
                            'error': 'M-Pesa payment failed. Please try another method.'
                        })
                
                # Update customer if exists
                if sale.customer:
                    sale.customer.total_spent += total
                    sale.customer.last_purchase = timezone.now()
                    
                    # Calculate loyalty points (1 point per 100 KSH)
                    points_earned = int(total / 100)
                    sale.loyalty_points_earned = points_earned
                    sale.customer.loyalty_points += points_earned
                    
                    sale.customer.save()
                    sale.save()
                
                # Clear cart
                if 'pos_cart' in request.session:
                    del request.session['pos_cart']
                
                return JsonResponse({
                    'success': True,
                    'sale_id': sale.id,
                    'invoice_number': sale.invoice_number,
                    'total': float(total),
                    'mpesa': False
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def sale_list(request):
    """List all sales"""
    today = timezone.now().date()
    sales = Sale.objects.all().order_by('-created_at')
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        sales = sales.filter(
            created_at__date__range=[start_date, end_date]
        )
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        sales = sales.filter(status=status)
    
    # Filter by payment method
    payment_method = request.GET.get('payment_method')
    if payment_method:
        sales = sales.filter(payment_method=payment_method)
    
    # Pagination
    paginator = Paginator(sales, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals
    total_sales = sales.filter(status='COMPLETED').aggregate(
        total_amount=Sum('total'),
        total_count=Count('id')
    )
    
    context = {
        'page_obj': page_obj,
        'total_amount': total_sales['total_amount'] or 0,
        'total_count': total_sales['total_count'] or 0,
        'status_choices': Sale.STATUS_CHOICES,
        'payment_methods': Sale.PAYMENT_METHODS,
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
        'payment_method': payment_method,
        'today': today,
    }
    
    return render(request, 'pos/sale_list.html', context)

@login_required
def sale_detail(request, pk):
    """View sale details"""
    sale = get_object_or_404(Sale, pk=pk)
    
    context = {
        'sale': sale,
        'items': sale.items.all(),
    }
    
    return render(request, 'pos/sale_detail.html', context)

@login_required
def print_receipt(request, sale_id):
    """Print receipt for a sale"""
    sale = get_object_or_404(Sale, id=sale_id)
    
    # Generate PDF receipt
    pdf = generate_receipt_pdf(sale)
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="receipt_{sale.invoice_number}.pdf"'
    return response

@login_required
def daily_sales_report(request):
    """Daily sales summary"""
    today = timezone.now().date()
    
    # Get today's sales
    sales = Sale.objects.filter(
        created_at__date=today,
        status='COMPLETED'
    )
    
    # Calculate summary by payment method
    payment_summary = sales.values('payment_method').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('-total')
    
    # Calculate hourly sales
    hourly_sales = []
    for hour in range(9, 18):  # 9 AM to 6 PM
        hour_sales = sales.filter(
            created_at__hour=hour
        ).aggregate(total=Sum('total'))['total'] or 0
        hourly_sales.append({
            'hour': f'{hour}:00',
            'sales': float(hour_sales)
        })
    
    # Top selling products today
    top_products_today = Product.objects.filter(
        saleitem__sale__created_at__date=today
    ).annotate(
        quantity_sold=Sum('saleitem__quantity')
    ).filter(quantity_sold__gt=0).order_by('-quantity_sold')[:10]
    
    context = {
        'today': today,
        'total_sales': sales.aggregate(total=Sum('total'))['total'] or 0,
        'total_transactions': sales.count(),
        'payment_summary': payment_summary,
        'hourly_sales': hourly_sales,
        'top_products_today': top_products_today,
    }
    
    return render(request, 'pos/daily_sales.html', context)

@login_required
@csrf_exempt
def create_customer(request):
    """Create a new customer via AJAX from POS dashboard"""
    if request.method == 'POST':
        try:
            # Handle both JSON and FormData
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
            
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            phone = data.get('phone', '').strip()
            email = data.get('email', '').strip()
            address = data.get('address', '').strip()
            
            # Validation
            if not first_name or not last_name or not phone:
                return JsonResponse({
                    'success': False,
                    'error': 'First name, last name, and phone are required'
                })
            
            # Check if phone already exists
            if Customer.objects.filter(phone=phone).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Customer with phone {phone} already exists'
                })
            
            # Create customer
            customer = Customer.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email if email else None,
                address=address if address else None,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Customer created successfully',
                'customer': {
                    'id': customer.id,
                    'full_name': customer.full_name,
                    'phone': customer.phone
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa callback"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Extract transaction details
            checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
            result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
            result_desc = data.get('Body', {}).get('stkCallback', {}).get('ResultDesc')
            
            if result_code == 0:
                # Payment successful
                callback_metadata = data['Body']['stkCallback']['CallbackMetadata']['Item']
                
                amount = None
                mpesa_receipt = None
                phone = None
                
                for item in callback_metadata:
                    if item['Name'] == 'Amount':
                        amount = item['Value']
                    elif item['Name'] == 'MpesaReceiptNumber':
                        mpesa_receipt = item['Value']
                    elif item['Name'] == 'PhoneNumber':
                        phone = item['Value']
                
                # Update sale
                try:
                    sale = Sale.objects.get(
                        mpesa_transaction_id=checkout_request_id,
                        status='PENDING'
                    )
                    sale.status = 'COMPLETED'
                    sale.mpesa_receipt = mpesa_receipt
                    sale.mpesa_phone = phone
                    sale.save()
                    
                    # Send notification
                    Notification.objects.create(
                        user=sale.cashier,
                        notification_type='SALE',
                        title='M-Pesa Payment Successful',
                        message=f'Payment of KES {amount} received for invoice #{sale.invoice_number}',
                        link=f'/pos/sale/{sale.id}/'
                    )
                    
                except Sale.DoesNotExist:
                    pass
            
            else:
                # Payment failed
                try:
                    sale = Sale.objects.get(mpesa_transaction_id=checkout_request_id)
                    sale.status = 'CANCELLED'
                    sale.save()
                    
                    Notification.objects.create(
                        user=sale.cashier,
                        notification_type='SYSTEM',
                        title='M-Pesa Payment Failed',
                        message=f'Payment failed: {result_desc}',
                        link=f'/pos/sale/{sale.id}/'
                    )
                    
                except Sale.DoesNotExist:
                    pass
            
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
            
        except Exception as e:
            return JsonResponse({'ResultCode': 1, 'ResultDesc': str(e)})
    
    return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid request'})