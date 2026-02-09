from datetime import datetime, timedelta
from decimal import Decimal
import random
import string

def generate_invoice_number():
    """Generate unique invoice number"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"INV-{date_str}-{random_str}"

def generate_sku(name):
    """Generate SKU from product name"""
    name_parts = name.upper().split()[:3]
    sku_parts = []
    for part in name_parts:
        if len(part) > 2:
            sku_parts.append(part[:2])
        else:
            sku_parts.append(part)
    
    random_str = ''.join(random.choices(string.digits, k=4))
    return f"{'-'.join(sku_parts)}-{random_str}"

def calculate_profit(cost_price, selling_price, quantity=1):
    """Calculate profit for given quantity"""
    profit_per_unit = selling_price - cost_price
    return profit_per_unit * quantity

def calculate_margin(cost_price, selling_price):
    """Calculate profit margin percentage"""
    if cost_price == 0:
        return Decimal('0')
    return ((selling_price - cost_price) / cost_price) * 100

def get_date_range(period='month'):
    """Get start and end dates for given period"""
    today = datetime.now().date()
    
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = today.replace(day=1)
        # Get last day of month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    else:
        # Default to current month
        start_date = today.replace(day=1)
        end_date = today
    
    return start_date, end_date

def format_currency(amount):
    """Format amount as currency"""
    return f"KES {amount:,.2f}"

def validate_phone(phone):
    """Validate Kenyan phone number"""
    import re
    pattern = r'^(\+?254|0)[17]\d{8}$'
    return re.match(pattern, phone) is not None

def send_sms_notification(phone, message):
    """Send SMS notification (stub - integrate with SMS gateway)"""
    # This is a stub. Integrate with your SMS gateway
    print(f"SMS to {phone}: {message}")
    return True

def send_email_notification(email, subject, message):
    """Send email notification"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False