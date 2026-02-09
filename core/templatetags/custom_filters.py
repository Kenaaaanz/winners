from django import template
from django.db.models import QuerySet
from django.db.models import Sum
import builtins
import json
from django.utils.safestring import mark_safe

from core.models import Product

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply value by arg - handles Decimal types"""
    try:
        from decimal import Decimal
        v = float(value) if not isinstance(value, Decimal) else float(value)
        a = float(arg) if not isinstance(arg, Decimal) else float(arg)
        return v * a
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide value by arg - handles Decimal types"""
    try:
        from decimal import Decimal
        v = float(value) if not isinstance(value, Decimal) else float(value)
        a = float(arg) if not isinstance(arg, Decimal) else float(arg)
        return v / a if a != 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def subtract(value, arg):
    """Subtract arg from value - handles Decimal types"""
    try:
        from decimal import Decimal
        v = float(value) if not isinstance(value, Decimal) else float(value)
        a = float(arg) if not isinstance(arg, Decimal) else float(arg)
        return v - a
    except (ValueError, TypeError):
        return 0

@register.filter
def sum_attribute(queryset, attribute):
    """Sum attribute of queryset"""
    return sum(getattr(item, attribute, 0) for item in queryset)

@register.filter
def filter_by_membership(queryset, membership_types):
    """Filter customers by membership types"""
    types = [t.strip() for t in membership_types.split(',')]
    return [item for item in queryset if item.membership_type in types]

@register.filter
def filter_by_active(queryset, is_active=True):
    """Filter products by active status"""
    return [item for item in queryset if getattr(item, 'is_active', False) == is_active]

@register.filter
def filter_by_low_stock(queryset, is_low=True):
    """Filter products by low stock status"""
    if is_low:
        return [item for item in queryset if getattr(item, 'is_low_stock', False)]
    return [item for item in queryset]

@register.filter
def filter_by_type(queryset, transaction_type):
    """Filter stock transactions by type"""
    return [item for item in queryset if item.transaction_type == transaction_type]

@register.filter
def filter_by_date(queryset, target_date):
    """Filter sales by date"""
    return [item for item in queryset if item.created_at.date() == target_date]

@register.filter
def filter_by_quantity(queryset, quantity):
    """Filter products by quantity"""
    return [item for item in queryset if item.quantity == quantity]

@register.filter(name='abs')
def absolute_value(value):
    """Return absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0
    
@register.filter(name='sum')
def sum_filter(queryset, field_name):
    """Sum the values of a field in a queryset or iterable.

    Uses Django's `aggregate` for QuerySets and the builtin `sum` for lists/iterables.
    """
    try:
        if isinstance(queryset, QuerySet):
            result = queryset.aggregate(total=Sum(field_name))['total']
            return result if result is not None else 0

        # For lists or other iterables, use the builtin sum to avoid recursion
        return builtins.sum(
            getattr(item, field_name, 0) for item in queryset if getattr(item, field_name) is not None
        )
    except Exception:
        return 0

@register.filter(name='sum_field')
def sum_field(queryset, field_name):
    """Alias to `sum` filter — kept for backwards compatibility."""
    return sum_filter(queryset, field_name)

@register.filter(name='map')
def map_filter(queryset, field_name):
    """Extract specific field values from a queryset/dict list."""
    result = []
    for item in queryset:
        if isinstance(item, dict):
            value = item.get(field_name)
        else:
            value = getattr(item, field_name, None)
        
        # Handle date formatting
        if field_name == 'month' and value:
            try:
                from datetime import datetime
                if isinstance(value, str):
                    value = datetime.strptime(value, '%Y-%m-%d')
                result.append(value.strftime('%b %Y'))
                continue
            except (ValueError, AttributeError):
                pass
        
        result.append(value)
    return result

@register.filter
def jsonify(value):
    """Convert value to JSON string."""
    return mark_safe(json.dumps(value, default=str))

@register.filter(name='filter_by_margin')
def filter_by_margin(products, margin_range):
    """Filter products by profit margin range."""
    try:
        min_margin, max_margin = map(float, margin_range.split('-'))
    except ValueError:
        return []
    
    filtered_products = []
    for product in products:
        # Ensure product has profit_margin attribute
        margin = getattr(product, 'profit_margin', 0)
        if min_margin <= margin < max_margin:
            filtered_products.append(product)
    return filtered_products

@register.filter(name='filter_by_membership')
def filter_by_membership(customers, membership_types):
    """
    Filter customers by membership types.
    Usage: {{ customers|filter_by_membership:"GOLD,PLATINUM,VIP" }}
    """
    if not customers:
        return []
    
    # Split the comma-separated string
    membership_list = [m.strip().upper() for m in membership_types.split(',')]
    
    # Filter the customers
    result = []
    for customer in customers:
        # Get membership_type attribute
        membership = getattr(customer, 'membership_type', None)
        if membership and membership.upper() in membership_list:
            result.append(customer)
    
    return result

@register.simple_tag
def get_product_counts():
    total = Product.objects.count()
    active = Product.objects.filter(is_active=True).count()
    return {
        'total': total,
        'active': active,
        'inactive': total - active
    }

@register.filter(name='filter_by_score')
def filter_by_score(customers, score_range):
    """Filter customers by RFM score range."""
    if not customers:
        return []
    
    try:
        if '-' in score_range:
            min_score, max_score = map(int, score_range.split('-'))
        else:
            min_score = int(score_range)
            max_score = min_score
    except ValueError:
        return []
    
    filtered_customers = []
    for customer in customers:
        # Make sure customer has rfm_score attribute
        score = getattr(customer, 'rfm_score', 0)
        if min_score <= score <= max_score:
            filtered_customers.append(customer)
    
    return filtered_customers