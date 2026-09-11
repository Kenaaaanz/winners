# Email setup

The system uses Django email. It defaults to the console backend locally, so messages are printed in the terminal until SMTP is configured.

Set these environment variables in the deployment environment (or local `.env`):

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-sender@example.com
EMAIL_HOST_PASSWORD=your-smtp-password
DEFAULT_FROM_EMAIL=your-sender@example.com
ADMIN_EMAILS=admin@example.com,manager@example.com
```

`EMAIL_HOST_PASSWORD` should be an SMTP/app password, not a personal email account password. Keep it out of source control.

## Automatic messages

After a successful Paystack or M-Pesa payment:

- The customer receives a PDF receipt when a customer email exists.
- Configured admins and active staff users with email addresses receive a payment alert with the PDF receipt.
- Receipt and admin alert timestamps are stored on the sale, so payment retries do not send duplicates.

Run the migration before deploying:

```text
python manage.py migrate
```

## Promotional emails

Promotions are sent only to active customers with email addresses. Use the management command from a protected deployment shell:

```text
python manage.py send_promotion --subject "Weekend offer" --message "Enjoy 10% off this weekend." 
python manage.py send_promotion --membership VIP --subject "VIP offer" --message "Your VIP offer is ready."
```

The command sends recipients as BCC so customer addresses are not exposed to one another. Test first with the console backend or a staging SMTP account.
