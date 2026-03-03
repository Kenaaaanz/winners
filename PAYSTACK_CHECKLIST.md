# Paystack Integration - Complete Checklist

## Pre-Integration Checklist

- [ ] Django project is running successfully
- [ ] Database migrations are up to date
- [ ] Admin panel is accessible at `/admin/`
- [ ] You have an active Paystack account
- [ ] You have Paystack API keys ready

---

## Installation Steps

### Step 1: Environment Setup

- [ ] Add to `.env` file:
  ```
  PAYSTACK_PUBLIC_KEY=pk_test_your_key
  PAYSTACK_SECRET_KEY=sk_test_your_secret_key
  ```
- [ ] Verify `.env` file is in `.gitignore` (not committed)
- [ ] Review `.env.example` for reference

### Step 2: Code Integration

- [ ] Verify `core/paystack_config.py` exists
- [ ] Verify `core/paystack_service.py` exists
- [ ] Verify `core/paystack_views.py` exists
- [ ] Verify `core/paystack_urls.py` exists
- [ ] Verify all imports are correct

### Step 3: Database Updates

- [ ] Run: `python manage.py makemigrations`
- [ ] Verify `core/migrations/` has new PaystackTransaction migration
- [ ] Run: `python manage.py migrate`
- [ ] Check database has `core_paystacktransaction` table
- [ ] Verify `core_sale` table has new Paystack fields

### Step 4: Django Configuration

- [ ] Verify `winners/settings.py` has Paystack config
- [ ] Verify `winners/urls.py` includes paystack URLs:
  ```python
  path('api/paystack/', include('core.paystack_urls'))
  ```
- [ ] Restart Django: `python manage.py runserver`
- [ ] Check for any import errors in terminal

### Step 5: Admin Interface

- [ ] Go to `/admin/`
- [ ] Look for "Paystack transactions" in Core app
- [ ] It should be clickable
- [ ] List should be empty (no transactions yet)

### Step 6: Templates

- [ ] Verify `templates/paystack/` directory exists
- [ ] Verify `checkout.html` exists
- [ ] Verify `transaction_history.html` exists
- [ ] Verify `transaction_detail.html` exists

---

## Functional Testing Checklist

### Test 1: Create a Sale

- [ ] Navigate to POS dashboard
- [ ] Add products to cart
- [ ] Enter customer details or "Walk-in"
- [ ] Click "Checkout" or "Complete Sale"
- [ ] Sale should be created with status "PENDING"
- [ ] Check database: `Sale` record should exist

### Test 2: Initialize Paystack Payment

- [ ] After creating sale, click "Pay with Paystack"
- [ ] You should be redirected to `/api/paystack/checkout/<sale_id>/`
- [ ] Checkout page should display:
  - [ ] Order summary
  - [ ] Invoice number
  - [ ] Total amount in NGN
  - [ ] Paystack payment button
- [ ] Check database: `PaystackTransaction` record created
- [ ] Check database: `Sale.paystack_reference` is populated

### Test 3: Complete Payment

- [ ] Click "Pay with Paystack" button
- [ ] Paystack modal should appear
- [ ] Enter test email (any email)
- [ ] Click "Pay now"
- [ ] Use test card: `4111 1111 1111 1111`
- [ ] Enter any CVC: `000`
- [ ] Set future expiry date
- [ ] OTP: (auto-verified in test mode)
- [ ] Success message should appear

### Test 4: Payment Verification

- [ ] Success modal should show:
  - [ ] ✓ icon and "Payment Successful"
  - [ ] Invoice number
  - [ ] Amount paid
  - [ ] Status: "completed"
- [ ] Frontend auto-verifies via `/api/paystack/verify/<sale_id>/`
- [ ] Check database: `Sale.status` changed to "COMPLETED"
- [ ] Check database: `Sale.amount_paid` populated
- [ ] Check database: `PaystackTransaction.status` = "SUCCESS"

### Test 5: Automatic Updates

- [ ] Inventory should be reduced:
  - [ ] Check `Product.quantity` decreased
- [ ] Loyalty points should be awarded:
  - [ ] Check `Customer.loyalty_points` increased
  - [ ] Check `Sale.loyalty_points_earned`
- [ ] Sale should be finalized:
  - [ ] Check `Sale.status` = "COMPLETED"

### Test 6: Transaction History

- [ ] Navigate to `/api/paystack/transactions/`
- [ ] Your transaction should appear in list
- [ ] Should show:
  - [ ] Transaction reference
  - [ ] Amount
  - [ ] Email
  - [ ] Status badge (green for success)
  - [ ] Created date
  - [ ] View button
- [ ] Click "View" on transaction
- [ ] Should show:
  - [ ] Detailed transaction information
  - [ ] Associated sale details
  - [ ] Gateway response
  - [ ] Refund option (if applicable)

### Test 7: Admin Interface

- [ ] Go to `/admin/core/paystacktransaction/`
- [ ] Your transaction should appear
- [ ] Should show:
  - [ ] Reference
  - [ ] Amount
  - [ ] Email
  - [ ] Status
  - [ ] Created date
- [ ] Click transaction to view details
- [ ] Should show all transaction metadata
- [ ] Gateway response should be viewable as JSON

### Test 8: Failed Payment Test

- [ ] Create another sale
- [ ] Click "Pay with Paystack"
- [ ] Use invalid card details (any invalid number)
- [ ] Should fail with error message
- [ ] Check database: `PaystackTransaction.status` = "FAILED"
- [ ] Transaction should appear in history with red status badge

### Test 9: Partial Refund

- [ ] Find a successful transaction in history
- [ ] Click "View" on that transaction
- [ ] Click "Process Refund" button
- [ ] Enter partial amount (less than full)
- [ ] Confirm refund
- [ ] Check status shows "Refund initiated successfully"
- [ ] Check database: `PaystackTransaction.status` = "REFUNDED"

### Test 10: Full Refund

- [ ] Create and complete another payment
- [ ] In admin panel go to Paystack transactions
- [ ] Select the transaction
- [ ] Click "Refund" button
- [ ] Confirm full refund
- [ ] Status should change to "REFUNDED"

---

## Production Readiness Checklist

### Security

- [ ] Remove all test keys from code
- [ ] Use environment variables for all secrets
- [ ] Verify `.env` is in `.gitignore`
- [ ] Enable HTTPS on domain
- [ ] Set `SECURE_SSL_REDIRECT=True` in settings
- [ ] Update CSRF settings for HTTPS

### Paystack Configuration

- [ ] Upgrade Paystack account (KYC verification)
- [ ] Get live API keys (pk_live_..., sk_live_...)
- [ ] Update `.env` with live keys:
  ```
  PAYSTACK_PUBLIC_KEY=pk_live_your_live_key
  PAYSTACK_SECRET_KEY=sk_live_your_live_secret_key
  ```

### Webhook Setup

- [ ] Find your public domain/IP address
- [ ] Go to https://dashboard.paystack.com/#/settings/developers
- [ ] Find "Webhooks" section
- [ ] Add webhook URL: `https://your-domain.com/api/paystack/webhook/`
- [ ] Subscribe to events:
  - [ ] `charge.success`
  - [ ] `charge.failed`
- [ ] Save webhook
- [ ] Verify webhook is active (green checkmark)

### Testing in Production

- [ ] Create test sale with small amount
- [ ] Complete payment with test card
- [ ] Verify payment appears after ~30 seconds
- [ ] Check admin panel for transaction
- [ ] Verify webhook received and processed notification
- [ ] Verify inventory was reduced
- [ ] Verify loyalty points awarded

### Monitoring & Logging

- [ ] Set up log file rotation:
  ```bash
  # Ensure logs/ directory exists
  mkdir -p logs/
  ```
- [ ] Test logging:
  ```bash
  tail -f logs/paystack.log
  ```
- [ ] Set up monitoring alerts for errors
- [ ] Create dashboard for transaction monitoring

### Database

- [ ] Create database backup before deploying
- [ ] Verify migrations ran on production
- [ ] Verify PaystackTransaction table exists
- [ ] Test queries work on production database

### Documentation

- [ ] Share setup guide with team: `PAYSTACK_SETUP.md`
- [ ] Share quick reference with developers: `PAYSTACK_QUICK_REFERENCE.md`
- [ ] Share implementation guide: `PAYSTACK_IMPLEMENTATION.md`
- [ ] Document any custom modifications made
- [ ] Create troubleshooting runbook

---

## Post-Deployment Checklist

### First Week Monitoring

- [ ] Monitor logs for errors: `tail -f logs/paystack.log`
- [ ] Check transaction success rate
- [ ] Verify all payments are processed correctly
- [ ] Test refund functionality
- [ ] Check customer support for issues
- [ ] Monitor Paystack dashboard for anomalies

### Ongoing Maintenance

- [ ] Weekly: Review error logs
- [ ] Weekly: Check transaction count and amounts
- [ ] Monthly: Review failed transactions
- [ ] Monthly: Test backup and restore procedures
- [ ] Quarterly: Update Paystack API library if needed
- [ ] Yearly: Review security settings

### Monitoring Queries

```python
# Daily transactions
from core.models import PaystackTransaction
from datetime import date
PaystackTransaction.objects.filter(created_at__date=date.today()).count()

# Today's revenue
from django.db.models import Sum
PaystackTransaction.objects.filter(
    created_at__date=date.today(),
    status='SUCCESS'
).aggregate(Sum('amount'))

# Failed transactions
PaystackTransaction.objects.filter(status='FAILED').count()

# Recent errors
# Check logs: grep ERROR logs/paystack.log | tail -20
```

---

## Support & Troubleshooting

### If Something Breaks

1. [ ] Check error logs: `tail -f logs/paystack.log`
2. [ ] Check Django debug page for traceback
3. [ ] Verify `.env` file has correct keys
4. [ ] Restart Django: `python manage.py runserver`
5. [ ] Check Paystack status: https://status.paystack.com/
6. [ ] Check database migrations: `python manage.py showmigrations`

### Key Support Contacts

- [ ] Paystack Support: https://support.paystack.com
- [ ] Paystack Community: https://community.paystack.com
- [ ] Documentation: https://paystack.com/docs

---

## Sign-Off

- [ ] **Integration Completed By**: _____________
- [ ] **Date**: _____________
- [ ] **Tested By**: _____________
- [ ] **Approved For Production By**: _____________

**All items checked?** You're ready to go! 🚀
