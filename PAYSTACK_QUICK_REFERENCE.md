# Paystack Integration - Quick Reference Guide

## ⚡ 5-Minute Setup

### 1. Get API Keys
```
Visit: https://dashboard.paystack.com/#/settings/developers
Copy: Public Key (pk_test...)
Copy: Secret Key (sk_test...)
```

### 2. Update .env
```bash
PAYSTACK_PUBLIC_KEY=pk_test_your_key
PAYSTACK_SECRET_KEY=sk_test_your_key
```

### 3. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Test It
```
Go to: /pos/
Create a sale
Click "Pay with Paystack"
Use test card: 4111 1111 1111 1111
```

## 📚 Common Tasks

### Initialize a Payment
```python
from core.paystack_service import PaystackService

paystack = PaystackService()
response = paystack.initialize_transaction(
    email='customer@example.com',
    amount=50000.00,  # In Naira
    reference='SALE-12345'
)
# Response contains: access_code, authorization_url
```

### Verify Payment
```python
from core.paystack_service import PaystackService

paystack = PaystackService()
result = paystack.verify_transaction('SALE-12345')
if result.get('status') == 'success':
    # Update sale to COMPLETED
    sale.status = 'COMPLETED'
    sale.save()
```

### Refund Payment
```python
from core.paystack_service import PaystackService

paystack = PaystackService()
# Full refund
paystack.refund_transaction('SALE-12345')

# Partial refund
paystack.refund_transaction('SALE-12345', amount=25000)
```

### Create Customer
```python
from core.paystack_service import PaystackService

paystack = PaystackService()
customer = paystack.create_customer(
    email='john@example.com',
    first_name='John',
    last_name='Doe',
    phone='+234801234567'
)
customer_code = customer['customer_code']  # Save for recurring payments
```

### Charge Saved Authorization
```python
from core.paystack_service import PaystackService

paystack = PaystackService()
result = paystack.charge_authorization(
    authorization_code='AUTH_ABC123',
    email='john@example.com',
    amount=50000,
    reference='RECURRING-001'
)
```

## 🎯 API Endpoints

```
GET    /api/paystack/checkout/<sale_id>/
POST   /api/paystack/verify/<sale_id>/
POST   /api/paystack/webhook/
GET    /api/paystack/transactions/
GET    /api/paystack/transactions/<pk>/
POST   /api/paystack/refund/<transaction_id>/
```

## 🧪 Test Data

### Test Cards
```
Visa:       4111 1111 1111 1111
Mastercard: 5399 8350 8350 8350
CVV:        000 (any)
Expiry:     Any future date
```

### Test Amounts
```
Any amount: Works normally
```

## 📊 Check Transactions

### In Django Admin
```
https://your-domain.com/admin/core/paystacktransaction/
```

### In Code
```python
from core.models import PaystackTransaction

# All successful transactions
txns = PaystackTransaction.objects.filter(status='SUCCESS')

# Today's transactions
from datetime import date
today = PaystackTransaction.objects.filter(created_at__date=date.today())

# Total revenue
from django.db.models import Sum
total = PaystackTransaction.objects.filter(
    status='SUCCESS'
).aggregate(Sum('amount'))['amount__sum']
```

## ⚙️ Configuration

### Settings
- **Public Key**: `settings.PAYSTACK_PUBLIC_KEY`
- **Secret Key**: `settings.PAYSTACK_SECRET_KEY`
- **Base URL**: `paystack.com`
- **Logger**: `logging.getLogger('paystack')`

### Error Logging
```bash
# View errors
tail -f logs/paystack.log

# All levels logged:
# - INFO: Successful operations
# - WARNING: Failed operations
# - ERROR: Exceptions
```

## 🔍 Debugging

### Check Credentials
```python
from core.paystack_service import PaystackService
paystack = PaystackService()
paystack._validate_credentials()  # Raises exception if invalid
```

### Track Payment
```python
from core.models import PaystackTransaction

txn = PaystackTransaction.objects.get(reference='SALE-12345')
print(f"Status: {txn.status}")
print(f"Amount: {txn.amount}")
print(f"Response: {txn.gateway_response}")
```

### View Webhook Response
```python
from core.models import PaystackTransaction
import json

txn = PaystackTransaction.objects.get(reference='SALE-12345')
print(json.dumps(txn.gateway_response, indent=2))
```

## 🚨 Common Errors & Fixes

```
Error: "PAYSTACK_SECRET_KEY not configured!"
Fix: Update .env and restart Django

Error: "Invalid webhook signature"
Fix: Check webhook URL is accessible and secret key matches

Error: "Payment initializes but doesn't process"
Fix: Check Paystack public key is correct

Error: "Amount not displaying correctly"
Fix: Remember: Database = Naira, Paystack API = Kobo (auto-converted)
```

## 📱 Frontend Integration

### Paystack Modal (from checkout.html)
```javascript
PaystackPop.setup({
    key: '{{ public_key }}',
    email: '{{ email }}',
    amount: {{ amount|floatformat:0 }} * 100,  // Convert to kobo
    ref: '{{ reference }}',
    onClose: function() { alert('Payment closed'); },
    onSuccess: function(res) { verifyPayment(); }
});
handler.openIframe();
```

### Verify Payment
```javascript
fetch('/api/paystack/verify/{{ sale_id }}/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    }
}).then(r => r.json()).then(data => {
    if (data.status) {
        // Payment successful
        console.log('Payment verified!');
    }
});
```

## 🔐 Production Checklist

```
[ ] Use live keys (pk_live_..., sk_live_...)
[ ] Set DEBUG=False
[ ] Enable HTTPS
[ ] Configure webhook in dashboard
[ ] Test webhook with live transaction
[ ] Set up SSL certificates
[ ] Monitor logs
[ ] Enable backups
[ ] Test error scenarios
[ ] Create runbooks
```

## 📖 Documentation Files

- **Setup**: `PAYSTACK_SETUP.md`
- **Implementation**: `PAYSTACK_IMPLEMENTATION.md`
- **File Summary**: `PAYSTACK_FILES_SUMMARY.md`
- **This Guide**: `PAYSTACK_QUICK_REFERENCE.md`

## 🆘 Getting Help

1. **Check logs**: `tail -f logs/paystack.log`
2. **Django admin**: `/admin/core/paystacktransaction/`
3. **Code comments**: Check `core/paystack_*.py` files
4. **Paystack docs**: https://paystack.com/docs
5. **Community**: https://community.paystack.com

## 📞 Quick Support

**Paystack API Status**
```python
from core.paystack_service import PaystackService
paystack = PaystackService()
try:
    paystack._validate_credentials()
    print("✅ Paystack API: OK")
except:
    print("❌ Paystack API: ERROR")
```

**Database Status**
```python
from core.models import PaystackTransaction
count = PaystackTransaction.objects.count()
print(f"✅ Total transactions: {count}")
```

**Recent Errors**
```bash
grep ERROR logs/paystack.log | tail -20
```

---

For detailed information, see the main documentation files:
- `PAYSTACK_SETUP.md` - Complete setup guide
- `PAYSTACK_IMPLEMENTATION.md` - Detailed implementation
- `PAYSTACK_FILES_SUMMARY.md` - File reference
