# Paystack Integration Setup Guide

This guide will help you set up and integrate Paystack as the main payment gateway in your Winners application.

## Prerequisites

- Django application installed and running
- Paystack account (https://paystack.com)
- Paystack API keys (Public and Secret keys)

## Step 1: Get Paystack API Keys

1. Visit https://dashboard.paystack.com/#/settings/developers
2. Copy your Public Key (starts with `pk_`)
3. Copy your Secret Key (starts with `sk_`)

### Test Keys (for development):
- They are provided automatically when you create your account
- They start with `pk_test_` and `sk_test_`

### Live Keys (for production):
- Available after your account is verified
- They start with `pk_live_` and `sk_live_`

## Step 2: Configure Environment Variables

Create or update your `.env` file with the following variables:

```env
# Paystack Configuration
PAYSTACK_PUBLIC_KEY=pk_test_your_public_key_here
PAYSTACK_SECRET_KEY=sk_test_your_secret_key_here

# Keep existing configurations
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=your_mpesa_key
MPESA_CONSUMER_SECRET=your_mpesa_secret
MPESA_SHORTCODE=174379
MPESA_PASSKEY=bfb279f9ba9b9d47157394d9e0e75aeae70e6a23
BASE_URL=http://localhost:8000
```

## Step 3: Run Migrations

Create a migration file for the new PaystackTransaction model:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Step 4: Update Your POS/Sales Views

To integrate Paystack payment into your sales flow, update your sale completion view:

```python
from django.shortcuts import redirect
from core.paystack_views import paystack_checkout

# After creating a sale, redirect to Paystack checkout
return redirect('paystack:checkout', sale_id=sale.id)
```

## Step 5: Configure Webhook (Important for Production)

1. Go to https://dashboard.paystack.com/#/settings/developers
2. Click on "webhooks" tab
3. Add your webhook URL: `https://your-domain.com/api/paystack/webhook/`
4. Select all events you want to listen to (at minimum: `charge.success`, `charge.failed`)

The webhook handler will:
- Verify the payment
- Update the sale status
- Award loyalty points
- Reduce inventory
- Send notifications

## Available Paystack Views

### Checkout View
- **URL**: `/api/paystack/checkout/<sale_id>/`
- **Method**: GET
- **Description**: Initialize Paystack payment for a sale
- **Response**: Renders checkout page with payment form

### Verify View
- **URL**: `/api/paystack/verify/<sale_id>/`
- **Method**: POST
- **Description**: Verify payment after customer completes transaction
- **Response**: JSON with verification status

### Webhook View
- **URL**: `/api/paystack/webhook/`
- **Method**: POST
- **Description**: Receives payment notifications from Paystack
- **Note**: CSRF protection is disabled for this endpoint

### Transaction History
- **URL**: `/api/paystack/transactions/`
- **Method**: GET
- **Description**: View all Paystack transactions
- **Features**: Filter by status, view detailed info

### Transaction Detail
- **URL**: `/api/paystack/transactions/<transaction_id>/`
- **Method**: GET
- **Description**: View individual transaction details

### Refund
- **URL**: `/api/paystack/refund/<transaction_id>/`
- **Method**: POST
- **Description**: Process refund for a transaction
- **Parameters**: `amount` (optional, defaults to full amount)

## Usage Examples

### 1. Initiating a Payment

```python
from core.paystack_service import PaystackService
from core.models import Sale, PaystackTransaction

# Get your sale
sale = Sale.objects.get(id=1)

# Initialize Paystack payment
paystack_service = PaystackService()
reference = paystack_service.generate_reference(f'SALE-{sale.invoice_number}')

metadata = {
    'sale_id': sale.id,
    'invoice_number': sale.invoice_number,
}

# Initialize transaction
response = paystack_service.initialize_transaction(
    email=sale.customer.email,
    amount=float(sale.total),
    reference=reference,
    metadata=metadata
)

# Create PaystackTransaction record
paystack_txn = PaystackTransaction.objects.create(
    sale=sale,
    reference=reference,
    access_code=response.get('access_code'),
    email=sale.customer.email,
    amount=sale.total,
    authorization_url=response.get('authorization_url'),
)

# Redirect to checkout
# The checkout template will use response['authorization_url']
```

### 2. Verifying a Payment

```python
from core.paystack_service import PaystackService

paystack_service = PaystackService()

# Verify transaction
verification = paystack_service.verify_transaction('TXN-20240101120000-ABC123')

if verification.get('status') == 'success':
    # Payment is successful
    sale.status = 'COMPLETED'
    sale.save()
else:
    # Payment failed
    print(f"Payment failed: {verification}")
```

### 3. Creating a Customer

```python
from core.paystack_service import PaystackService

paystack_service = PaystackService()

customer = paystack_service.create_customer(
    email='customer@example.com',
    first_name='John',
    last_name='Doe',
    phone='+234801234567'
)

# Save customer code for future recurring payments
customer_code = customer['customer_code']
```

### 4. Charging with Authorization

```python
from core.paystack_service import PaystackService

paystack_service = PaystackService()

# Charge a customer with saved authorization (for recurring payments)
response = paystack_service.charge_authorization(
    authorization_code='AUTH_YOUR_CODE',
    email='customer@example.com',
    amount=50000,  # in Naira
    reference='RECURRING-001'
)
```

### 5. Processing a Refund

```python
from core.paystack_service import PaystackService
from core.models import PaystackTransaction

paystack_service = PaystackService()
paystack_txn = PaystackTransaction.objects.get(id=1)

# Full refund
response = paystack_service.refund_transaction(paystack_txn.reference)

# Partial refund
response = paystack_service.refund_transaction(
    paystack_txn.reference,
    amount=25000  # Refund 25,000 Naira
)
```

## Important Notes

1. **Amount Format**: Paystack uses Kobo (smallest unit) for Nigerian Naira
   - 1 Naira = 100 Kobo
   - The service automatically converts amounts
   - Store amounts in your database as Naira (not Kobo)

2. **Email Verification**: Customer must provide valid email for payment

3. **Webhook Security**: Always verify webhook signatures:
   ```python
   import hmac
   import hashlib
   
   signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
   secret = settings.PAYSTACK_SECRET_KEY
   
   expected_sig = hmac.new(
       secret.encode(), 
       request.body, 
       hashlib.sha512
   ).hexdigest()
   
   if signature != expected_sig:
       # Invalid webhook - reject it
   ```

4. **Recurring Payments**: Save the `authorization_code` from successful payments to enable:
   - Automatic billing
   - One-click checkout
   - Subscription payments

5. **Error Handling**: Always wrap Paystack service calls in try-except:
   ```python
   try:
       response = paystack_service.initialize_transaction(...)
   except Exception as e:
       logger.error(f"Paystack error: {str(e)}")
       messages.error(request, "Payment processing error")
   ```

## Troubleshooting

### Issue: "PAYSTACK_SECRET_KEY not configured"
- **Solution**: Ensure `PAYSTACK_SECRET_KEY` is set in your `.env` file
- Restart your Django application: `python manage.py runserver`

### Issue: Payments not processing
- Check that your Paystack account is verified
- Verify webhook is properly configured
- Check logs: `tail -f logs/paystack.log`

### Issue: "Invalid webhook signature"
- Ensure `PAYSTACK_SECRET_KEY` matches your dashboard
- Webhook URL must be publicly accessible
- Check for any URL encoding issues

### Issue: Amounts not displaying correctly
- Remember: Database stores Naira, Paystack API uses Kobo
- Service handles conversion automatically
- Check `PaystackTransaction.amount` vs `PaystackService` initialization

## Testing Checklist

- [ ] Environment variables configured
- [ ] Migrations run successfully
- [ ] Can create a sale
- [ ] Can initiate Paystack payment
- [ ] Can complete payment with test card
- [ ] Can verify payment
- [ ] Sale status updates to COMPLETED
- [ ] Stock reduces automatically
- [ ] Loyalty points awarded
- [ ] Can view transaction history
- [ ] Can view transaction details
- [ ] Can process refund
- [ ] Webhook receives notifications (production only)

## Test Card Numbers

Use these cards to test your Paystack integration:

| Card Number | Expiry | CVC | Description |
|---|---|---|---|
| 4111 1111 1111 1111 | Any future date | Any 3 digits | Visa |
| 5399 8350 8350 8350 | Any future date | Any 3 digits | Mastercard |
| 3782 822463 10005 | Any future date | Any 3 digits | Amex |

## Production Deployment

1. **Get Live Keys**:
   - Submit KYC information on Paystack dashboard
   - Wait for verification (usually 24-48 hours)
   - Retrieve live keys

2. **Update Environment**:
   ```env
   PAYSTACK_PUBLIC_KEY=pk_live_your_live_public_key
   PAYSTACK_SECRET_KEY=sk_live_your_live_secret_key
   DEBUG=False
   ```

3. **Update Webhook**:
   - Change webhook URL to production domain
   - Test with live transaction

4. **Security**:
   - Use HTTPS only
   - Set `SECURE_SSL_REDIRECT=True`
   - Enable CSRF protection
   - Validate all inputs

## Support & Documentation

- **Paystack Documentation**: https://paystack.com/docs
- **API Reference**: https://paystack.com/docs/api/
- **Paystack Support**: https://support.paystack.com

## License

This integration is part of the Winners application and follows the same license.
