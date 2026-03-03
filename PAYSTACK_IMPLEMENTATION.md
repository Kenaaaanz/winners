# Paystack Integration - Complete Implementation Guide

## Overview

This document provides a complete guide to implementing Paystack as the main payment gateway in your Winners POS application. The integration includes:

- ✅ Payment initialization and processing
- ✅ Transaction verification
- ✅ Webhook support for asynchronous updates
- ✅ Refund processing
- ✅ Transaction history and reporting
- ✅ Admin dashboard for transaction management
- ✅ Automatic inventory and loyalty points updates

## Files Created/Modified

### New Files Created:

1. **`core/paystack_config.py`** - Paystack configuration and constants
2. **`core/paystack_service.py`** - Paystack API service class
3. **`core/paystack_views.py`** - Views for Paystack payment handling
4. **`core/paystack_urls.py`** - URL routing for Paystack endpoints
5. **`templates/paystack/checkout.html`** - Paystack payment checkout template
6. **`templates/paystack/transaction_history.html`** - Transaction history page
7. **`templates/paystack/transaction_detail.html`** - Transaction details page
8. **`PAYSTACK_SETUP.md`** - Setup and configuration guide
9. **`.env.example`** - Example environment variables

### Modified Files:

1. **`core/models.py`** - Added PaystackTransaction model and updated Sale model
2. **`core/admin.py`** - Added PaystackTransactionAdmin and updated SaleAdmin
3. **`winners/settings.py`** - Added Paystack configuration
4. **`winners/urls.py`** - Added Paystack URL routing

## Quick Start (5 Minutes)

### 1. Get Paystack Keys

```bash
# Visit https://dashboard.paystack.com/#/settings/developers
# Copy your keys
```

### 2. Update `.env` File

```bash
PAYSTACK_PUBLIC_KEY=pk_test_your_key
PAYSTACK_SECRET_KEY=sk_test_your_key
```

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Test Payment Flow

1. Create a sale: `/pos/`
2. Click "Pay with Paystack"
3. Use test card: `4111 1111 1111 1111`

## Implementation Details

### 1. Payment Initialization Flow

```
User Creates Sale
    ↓
Clicks "Pay with Paystack"
    ↓
PaystackService.initialize_transaction()
    ↓
Creates PaystackTransaction Record
    ↓
Renders Checkout Template
    ↓
User Completes Payment in Paystack
    ↓
Frontend Calls Verify Endpoint
```

### 2. Code Integration Example

**In your POS sales view:**

```python
from core.paystack_views import paystack_checkout

# After creating sale and sale items
sale = Sale.objects.create(
    invoice_number=generate_invoice_number(),
    customer=customer,
    cashier=request.user,
    subtotal=subtotal,
    tax_amount=tax_amount,
    total=total,
    status='PENDING',
)

# Add sale items
for item_data in items:
    SaleItem.objects.create(sale=sale, **item_data)

# Redirect to Paystack checkout
return redirect('paystack:checkout', sale_id=sale.id)
```

### 3. Webhook Configuration

For **production only**:

```bash
# 1. Go to: https://dashboard.paystack.com/#/settings/developers
# 2. Find "Webhooks" section
# 3. Set webhook URL: https://your-domain.com/api/paystack/webhook/
# 4. Subscribe to: charge.success, charge.failed
```

The webhook will automatically:
- Verify payments
- Update sale status
- Reduce inventory
- Award loyalty points
- Create notifications

### 4. API Endpoints

```
POST   /api/paystack/checkout/<sale_id>/      → Initialize payment
POST   /api/paystack/verify/<sale_id>/        → Verify payment
POST   /api/paystack/webhook/                 → Webhook endpoint
GET    /api/paystack/transactions/            → Transaction history
GET    /api/paystack/transactions/<pk>/       → Transaction details
POST   /api/paystack/refund/<transaction_id>/ → Process refund
```

### 5. Admin Management

Access at `/admin/core/paystacktransaction/`:

Features:
- View all transactions
- Filter by status, date, payment status
- One-click status updates
- View gateway responses
- Process refunds

## Key Features

### Automatic Actions After Successful Payment

```python
# 1. Sale Status Update
sale.status = 'COMPLETED'

# 2. Inventory Reduction
for item in sale.items.all():
    product.quantity -= item.quantity
    product.save()

# 3. Loyalty Points Award
if customer:
    points = int(sale.total / 1000)
    customer.loyalty_points += points
    customer.total_spent += sale.total
    customer.save()

# 4. Transaction Recording
PaystackTransaction.objects.create(...)
```

### Error Handling

```python
try:
    response = paystack_service.initialize_transaction(...)
except Exception as e:
    logger.error(f"Paystack error: {str(e)}")
    messages.error(request, "Payment initialization failed")
```

## Testing Paystack Integration

### Test Cards

| Card Type | Number | CVV | Expiry |
|---|---|---|---|
| Visa | 4111 1111 1111 1111 | 000 | Any future |
| Mastercard | 5399 8350 8350 8350 | 000 | Any future |
| Verve | 5061 0200 0000 0000000 | 000 | Any future |

### Test Flow

1. **Create a Test Sale**
   ```bash
   # From POS dashboard
   Add products and create sale
   Click "Pay with Paystack"
   ```

2. **Complete Test Payment**
   ```
   Use test card from above
   Enter any email
   Complete payment
   ```

3. **Verify Payment**
   ```
   Check sale status (should be COMPLETED)
   Check inventory (should be reduced)
   Check loyalty points (should be awarded)
   ```

4. **Check Admin**
   ```
   Visit /admin/core/paystacktransaction/
   Verify transaction appears
   ```

### Common Test Cases

- ✅ Successful payment
- ✅ Failed payment (use invalid CVV)
- ✅ Webhook notification
- ✅ Transaction refund
- ✅ Multiple payments for same customer
- ✅ Partial refunds

## Production Checklist

- [ ] Upgrade to Paystack live keys
- [ ] Set up webhook URL
- [ ] Enable HTTPS (required for webhooks)
- [ ] Set `DEBUG=False` in settings
- [ ] Set `SECURE_SSL_REDIRECT=True`
- [ ] Test complete payment flow
- [ ] Test webhook signature verification
- [ ] Configure email notifications
- [ ] Set up monitoring/logging
- [ ] Create backup procedures
- [ ] Document troubleshooting steps

## Troubleshooting

### Common Issues & Solutions

**Issue: "PAYSTACK_SECRET_KEY not configured"**
```bash
# Solution: Update .env file
PAYSTACK_SECRET_KEY=sk_test_your_actual_key
# Restart: python manage.py runserver
```

**Issue: Webhook not receiving notifications**
```bash
# Check:
1. Webhook URL is publicly accessible
2. CSRF protection is commented out (it is in paystack_views.py)
3. Paystack dashboard has correct webhook URL
4. Your domain is not in DEBUG mode
```

**Issue: Payment initializes but doesn't redirect properly**
```bash
# Check:
1. Paystack public key is correct
2. Amount > 0
3. Email is valid
4. JavaScript console for errors
```

**Issue: Transaction not appearing in history**
```bash
# Check:
1. Sale was created successfully
2. Database migration ran (python manage.py migrate)
3. Check logs: tail -f logs/paystack.log
4. Check admin for PaystackTransaction records
```

## Monitoring & Maintenance

### Enable Logging

Already configured in `settings.py`:

```python
'paystack': {
    'handlers': ['file', 'console'],
    'level': 'INFO',
    'propagate': True,
}
```

View logs:
```bash
tail -f logs/paystack.log
```

### Monitoring API Response Times

```python
import time
from core.paystack_service import PaystackService

paystack = PaystackService()
start = time.time()
response = paystack.initialize_transaction(...)
duration = time.time() - start
print(f"API call took {duration:.2f}s")
```

### Health Check

```python
# In a management command or scheduled task
from core.paystack_service import PaystackService

try:
    paystack = PaystackService()
    # Try to get access token
    paystack._validate_credentials()
    print("✅ Paystack API is accessible")
except Exception as e:
    print(f"❌ Paystack API error: {str(e)}")
```

## Advanced Usage

### 1. Recurring Payments

```python
from core.paystack_service import PaystackService

paystack = PaystackService()

# Charge saved authorization (requires previous successful payment)
response = paystack.charge_authorization(
    authorization_code='AUTH_ABC123',
    email='customer@example.com',
    amount=50000,  # Naira
    reference='RECURRING-JAN-2024'
)
```

### 2. Create Paystack Customers

```python
from core.paystack_service import PaystackService

paystack = PaystackService()

customer = paystack.create_customer(
    email='john@example.com',
    first_name='John',
    last_name='Doe',
    phone='+2348012345678'
)

# Save customer code for future transactions
customer_code = customer['customer_code']
# Store in database
```

### 3. List Transactions (for reconciliation)

```python
from core.paystack_service import PaystackService
from datetime import datetime, timedelta

paystack = PaystackService()

# Get transactions from last 7 days
seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

transactions = paystack.list_transactions(
    limit=100,
    from_date=seven_days_ago
)

for txn in transactions:
    print(f"{txn['reference']}: {txn['amount']} - {txn['status']}")
```

### 4. Custom Metadata

```python
from core.paystack_service import PaystackService

paystack = PaystackService()

metadata = {
    'sale_id': 12345,
    'customer_id': 98765,
    'invoice_number': 'INV-202401001',
    'location': 'Victoria Island, Lagos',
    'cashier': 'John Doe',
    'custom_field': 'any_value'
}

response = paystack.initialize_transaction(
    email='customer@example.com',
    amount=50000,
    reference='SALE-20240101-ABC123',
    metadata=metadata
)
```

## Security Best Practices

1. **API Keys**
   - Never commit `.env` file to version control
   - Use different keys for dev/staging/production
   - Rotate keys regularly

2. **HTTPS**
   - Always use HTTPS in production
   - Enable `SECURE_SSL_REDIRECT=True`
   - Use security headers

3. **Webhook Verification**
   ```python
   # Always verify webhook signature
   import hmac
   import hashlib
   
   signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
   payload = request.body
   secret = settings.PAYSTACK_SECRET_KEY
   
   expected = hmac.new(
       secret.encode(),
       payload,
       hashlib.sha512
   ).hexdigest()
   
   if signature != expected:
       return HttpResponse(status=403)
   ```

4. **Amount Validation**
   ```python
   # Validate amount range
   if amount < 100 or amount > 50000000:  # Kobo
       raise ValidationError("Amount out of range")
   ```

5. **Email Validation**
   ```python
   from django.core.validators import EmailValidator
   
   validator = EmailValidator()
   try:
       validator(email)
   except ValidationError:
       raise Exception("Invalid email address")
   ```

## Database Queries

### Get Total Revenue from Paystack

```python
from django.db.models import Sum
from core.models import PaystackTransaction

total = PaystackTransaction.objects.filter(
    status='SUCCESS'
).aggregate(
    total=Sum('amount')
)['total'] or 0

print(f"Total Paystack Revenue: ₦{total}")
```

### Get Today's Transactions

```python
from datetime import date
from core.models import PaystackTransaction

today_txns = PaystackTransaction.objects.filter(
    created_at__date=date.today(),
    status='SUCCESS'
)

print(f"Today's transactions: {today_txns.count()}")
print(f"Today's revenue: ₦{sum(t.amount for t in today_txns)}")
```

### Failed Transactions Report

```python
from core.models import PaystackTransaction

failed = PaystackTransaction.objects.filter(
    status='FAILED'
).order_by('-created_at')[:10]

for txn in failed:
    print(f"{txn.reference}: {txn.payment_status}")
```

## Support & Resources

- **Paystack Documentation**: https://paystack.com/docs
- **API Endpoint Reference**: https://paystack.com/docs/api/transaction/
- **Integration Examples**: https://github.com/PaystackHQ/paystack-integration-samples
- **Paystack Community**: https://community.paystack.com

## Summary

Your Paystack integration includes:

✅ Complete payment processing API  
✅ Secure webhook handling  
✅ Automatic inventory management  
✅ Loyalty points integration  
✅ Transaction history & reporting  
✅ Refund processing  
✅ Admin dashboard  
✅ Comprehensive error handling  
✅ Production-ready logging  

You're now ready to process payments and grow your business! 🚀
