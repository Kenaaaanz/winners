import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timedelta
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from core.models import Product, Sale, SaleItem, Customer, PaystackTransaction, StockReservation
from core.paystack_service import PaystackService


def index(request):
    """Shop index with search and pagination"""
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)
    
    # Filter products
    products = Product.objects.filter(is_active=True, show_on_shop=True)
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(brand__name__icontains=query)
        )
    
    # Get featured separately
    featured = products.filter(is_featured=True)[:8]
    
    # Pagination
    paginator = Paginator(products.order_by('-is_featured', 'name'), 12)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj,
        'featured': featured,
        'query': query,
        'total_results': products.count(),
    }
    return render(request, 'shop/index.html', context)


def product_detail(request, pk):
    """Product detail page"""
    product = get_object_or_404(Product, pk=pk, is_active=True, show_on_shop=True)
    
    # Get available stock (total - reserved)
    active_reservations = StockReservation.objects.filter(
        product=product,
        status__in=['ACTIVE', 'CONFIRMED']
    ).count() if hasattr(product, 'reservations') else 0
    available_stock = max(0, product.quantity - active_reservations)
    
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'available_stock': available_stock,
    })


def _get_cart(request):
    return request.session.get('shop_cart', [])


def _get_available_stock(product_id):
    """Get available stock considering reservations"""
    try:
        product = Product.objects.get(id=product_id)
        active_reservations = StockReservation.objects.filter(
            product=product,
            status__in=['ACTIVE', 'CONFIRMED']
        ).aggregate(total=Count('id'))['total'] or 0
        return max(0, product.quantity - active_reservations)
    except Product.DoesNotExist:
        return 0


def view_cart(request):
    """View shopping cart"""
    cart = _get_cart(request)
    
    # Recalculate availability
    for item in cart:
        item['available'] = _get_available_stock(item['product_id'])
    
    subtotal = sum(Decimal(str(i['total_price'])) for i in cart) if cart else Decimal('0')
    tax_rate = Decimal('16')
    tax = (subtotal * tax_rate) / Decimal('100')
    total = subtotal + tax
    
    return render(request, 'shop/cart.html', {
        'cart': cart,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
    })


def add_to_cart(request):
    """Add product to cart with stock check"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))

            product = get_object_or_404(Product, id=product_id, is_active=True, show_on_shop=True)
            
            # Check available stock (including reservations)
            available = _get_available_stock(product_id)
            if available < quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {available} items available'
                })

            cart = _get_cart(request)

            for item in cart:
                if item['product_id'] == product_id:
                    item['quantity'] += quantity
                    item['total_price'] = float(Decimal(str(item['unit_price'])) * item['quantity'])
                    break
            else:
                cart.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_sku': product.sku,
                    'quantity': quantity,
                    'unit_price': float(product.selling_price),
                    'total_price': float(product.selling_price * quantity),
                })

            request.session['shop_cart'] = cart
            request.session.modified = True

            return JsonResponse({'success': True, 'cart_count': len(cart)})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


def checkout(request):
    """Checkout with delivery info and stock reservation"""
    cart = _get_cart(request)
    if not cart:
        return redirect('shop:index')

    subtotal = sum(Decimal(str(i['total_price'])) for i in cart)
    tax_rate = Decimal('16')
    tax_amount = (subtotal * tax_rate) / Decimal('100')
    total = subtotal + tax_amount

    if request.method == 'POST':
        from django.db import transaction as db_transaction
        
        data = request.POST
        email = data.get('email')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        phone = data.get('phone', '')
        delivery_name = data.get('delivery_name', '')
        delivery_phone = data.get('delivery_phone', '')
        delivery_address = data.get('delivery_address', '')
        delivery_city = data.get('delivery_city', '')
        delivery_instructions = data.get('delivery_instructions', '')

        try:
            with db_transaction.atomic():
                # Get or create customer
                customer = None
                if email:
                    customer, _ = Customer.objects.get_or_create(email=email, defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'phone': phone,
                    })

                # Create sale
                sale = Sale.objects.create(
                    customer=customer,
                    cashier=None,
                    subtotal=subtotal,
                    discount_amount=Decimal('0'),
                    discount_percentage=Decimal('0'),
                    tax_amount=tax_amount,
                    tax_rate=tax_rate,
                    total=total,
                    amount_paid=Decimal('0'),
                    payment_method='PAYSTACK',
                    status='PENDING',
                    delivery_name=delivery_name,
                    delivery_phone=delivery_phone,
                    delivery_address=delivery_address,
                    delivery_city=delivery_city,
                    delivery_instructions=delivery_instructions,
                )

                # Create sale items and reservations
                for item in cart:
                    product = Product.objects.get(id=item['product_id'])
                    
                    # Reserve stock (deduct from available quantity)
                    reservation = StockReservation.objects.create(
                        product=product,
                        sale=sale,
                        quantity=item['quantity'],
                        status='ACTIVE',
                        expires_at=timezone.now() + timedelta(minutes=30)  # 30 min payment window
                    )
                    
                    # Temporarily reduce stock for this reservation
                    product.quantity -= item['quantity']
                    product.save()
                    
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

                # Initialize Paystack
                paystack = PaystackService()
                reference = paystack.generate_reference(f'SHOP-{sale.invoice_number}')
                metadata = {
                    'sale_id': sale.id,
                    'invoice_number': sale.invoice_number,
                    'customer_email': email,
                    'delivery': {
                        'name': delivery_name,
                        'phone': delivery_phone,
                        'address': delivery_address,
                        'city': delivery_city,
                        'instructions': delivery_instructions,
                    }
                }

                init = paystack.initialize_transaction(
                    email=email or settings.DEFAULT_FROM_EMAIL,
                    amount=float(total),
                    reference=reference,
                    metadata=metadata
                )

                # Create Paystack transaction record
                PaystackTransaction.objects.create(
                    sale=sale,
                    reference=reference,
                    access_code=init.get('access_code', ''),
                    email=email or settings.DEFAULT_FROM_EMAIL,
                    amount=total,
                    metadata=metadata,
                    gateway_response=init,
                    authorization_url=init.get('authorization_url', ''),
                    access_code_url=init.get('access_code_url', ''),
                )

                # Store sale ID for success page
                request.session['last_shop_sale'] = sale.id
                
                # Clear cart
                if 'shop_cart' in request.session:
                    del request.session['shop_cart']
                
                # Get redirect URL
                redirect_url = init.get('authorization_url') or init.get('data', {}).get('authorization_url')
                if redirect_url:
                    return redirect(redirect_url)

                return render(request, 'shop/checkout.html', {
                    'sale': sale,
                    'init': init,
                    'public_key': settings.PAYSTACK_PUBLIC_KEY
                })

        except Exception as e:
            # Rollback any reservations if error
            return render(request, 'shop/checkout.html', {
                'cart': cart,
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'total': total,
                'error': f'Checkout error: {str(e)}'
            })

    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'total': total,
    })


def checkout_success(request):
    """Show order confirmation"""
    sale_id = request.session.get('last_shop_sale')
    sale = None
    if sale_id:
        try:
            sale = Sale.objects.get(id=sale_id)
        except Sale.DoesNotExist:
            sale = None

    return render(request, 'shop/success.html', {'sale': sale})

@require_POST
def newsletter_signup(request):
    email = request.POST.get('email')
    if email:
        # Add your newsletter signup logic here
        # e.g., save to database, send to email service, etc.
        messages.success(request, 'Thank you for subscribing to our newsletter!')
    else:
        messages.error(request, 'Please provide a valid email address.')
    return redirect(request.META.get('HTTP_REFERER', 'shop:index'))
