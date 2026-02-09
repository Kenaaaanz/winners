from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.db.models import (
    Sum, Count, Avg, Max, F, Q, ExpressionWrapper, DecimalField,
    Case, When, Value, IntegerField
)
from django.db.models.functions import TruncDay, TruncMonth, TruncYear, ExtractHour
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta, date
import json
from decimal import Decimal
import pandas as pd
import plotly.express as px
import plotly.io as pio
from django.db.models.functions import TruncDay, TruncMonth, TruncYear, TruncWeek
from django.db.models import ExpressionWrapper, DecimalField

from core.models import (
    Sale, SaleItem, Product, Customer, Expense, StockTransaction,
    PurchaseOrder
)
from core.forms import DateRangeForm
from core.reports import (
    generate_sales_report_pdf, generate_financial_report_pdf,
    generate_customer_report_pdf, generate_inventory_report_pdf
)
from core.permissions import require_role, require_permission

@require_role('ADMIN', 'MANAGER', 'ANALYST')
@login_required
def analytics_dashboard(request):
    """Main analytics dashboard with charts"""
    # Date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    year_ago = today - timedelta(days=365)
    
    # Sales metrics
    sales_today = Sale.objects.filter(
    created_at__date=today,
    status='COMPLETED'
    ).aggregate(
        total=Sum('total'),
        count=Count('id')
    )

    # Calculate average manually
    total = sales_today['total'] or 0
    count = sales_today['count'] or 0
    sales_today['avg'] = total / count if count > 0 else 0
    
    sales_week = Sale.objects.filter(
        created_at__date__gte=week_ago,
        status='COMPLETED'
    ).aggregate(total=Sum('total'), count=Count('id'))
    
    sales_month = Sale.objects.filter(
        created_at__date__gte=month_ago,
        status='COMPLETED'
    ).aggregate(total=Sum('total'), count=Count('id'))
    
    # Customer metrics
    total_customers = Customer.objects.count()
    new_customers_week = Customer.objects.filter(
        date_joined__date__gte=week_ago
    ).count()
    
    # Inventory metrics
    total_products = Product.objects.count()
    low_stock_count = Product.objects.filter(
        quantity__lte=F('low_stock_threshold'),
        is_active=True
    ).count()
    out_of_stock_count = Product.objects.filter(quantity=0, is_active=True).count()
    
    # Profit metrics
    month_sales = Sale.objects.filter(
        created_at__date__gte=month_ago,
        status='COMPLETED'
    )
    month_profit = sum(sale.profit for sale in month_sales)
    
    # Monthly sales trend
    monthly_trend = Sale.objects.filter(
        created_at__date__gte=year_ago,
        status='COMPLETED'
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total_sales=Sum('total'),
        total_profit=Sum(ExpressionWrapper(F('total') - F('subtotal'), output_field=DecimalField())),
        transaction_count=Count('id')
    ).order_by('month')

    # Prepare data for Chart.js
    monthly_trend_list = list(monthly_trend)
    
    # Extract labels and data for charts
    monthly_labels = []
    monthly_revenue = []
    monthly_profit = []

    for item in monthly_trend_list:
        # Format month as "Jan", "Feb", etc.
        monthly_labels.append(item['month'].strftime('%b %Y'))
        monthly_revenue.append(float(item['total_sales'] or 0))
        monthly_profit.append(float(item['total_profit'] or 0))
    
    # Top products by revenue
    top_products = Product.objects.annotate(
        total_revenue=Sum(ExpressionWrapper(F('saleitem__quantity') * F('saleitem__unit_price'), output_field=DecimalField())),
        total_quantity=Sum('saleitem__quantity')
    ).filter(
        total_revenue__isnull=False
    ).order_by('-total_revenue')[:10]
    
    # Top customers
    top_customers = Customer.objects.annotate(
        num_purchases=Count('sale'),
        last_purchase_date=Max('sale__created_at')
    ).filter(
        num_purchases__gt=0
    ).order_by('-total_spent')[:10]
    
    # Payment method distribution
    payment_distribution = Sale.objects.filter(
        created_at__date__gte=month_ago,
        status='COMPLETED'
    ).values('payment_method').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('-total')

    # Payment distribution data
    payment_distribution_list = list(payment_distribution)
    payment_labels = []
    payment_data = []
    
    for item in payment_distribution_list:
        payment_labels.append(item['payment_method'])
        payment_data.append(float(item['total'] or 0))
    
    context = {
        'sales_today': sales_today,
        'sales_week': sales_week,
        'sales_month': sales_month,
        'total_customers': total_customers,
        'new_customers_week': new_customers_week,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'month_profit': month_profit,
        'monthly_trend': list(monthly_trend),
        'monthly_labels': monthly_labels,  # NEW
        'monthly_revenue': monthly_revenue,  # NEW
        'monthly_profit': monthly_profit,  # NEW
        'top_products': top_products,
        'top_customers': top_customers,
        'payment_distribution': payment_distribution,
        'payment_labels': payment_labels,  # NEW
        'payment_data': payment_data,  # NEW
    }
    
    return render(request, 'analytics/dashboard.html', context)

@require_role('ADMIN', 'MANAGER', 'ANALYST')
@login_required
def sales_report(request):
    """Detailed sales report"""
    form = DateRangeForm(request.GET or None)
    
    # Default date range: current month
    today = timezone.now().date()
    start_date = request.GET.get('start_date') or today.replace(day=1)
    end_date = request.GET.get('end_date') or today
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get sales data
    sales = Sale.objects.filter(
        created_at__date__range=[start_date, end_date],
        status='COMPLETED'
    ).order_by('-created_at')
    
    # Calculate totals
    summary = sales.aggregate(
        total_sales=Sum('total'),
        total_transactions=Count('id'),
        avg_sale=Avg('total'),
        total_discount=Sum('discount_amount'),
        total_tax=Sum('tax_amount')
    )
    
    # Daily breakdown
    daily_sales = sales.annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        daily_total=Sum('total'),
        daily_count=Count('id')
    ).order_by('day')
    
    # Payment method breakdown
    payment_breakdown = sales.values('payment_method').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('-total')
    
    # Top selling products
    top_products = SaleItem.objects.filter(
        sale__created_at__date__range=[start_date, end_date]
    ).values(
        'product__name', 'product__sku'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum(ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField())),
        total_profit=Sum(ExpressionWrapper((F('unit_price') - F('cost_price')) * F('quantity'), output_field=DecimalField()))
    ).order_by('-total_quantity')[:20]
    
    context = {
        'form': form,
        'sales': sales,
        'summary': summary,
        'daily_sales': daily_sales,
        'payment_breakdown': payment_breakdown,
        'top_products': top_products,
        'start_date': start_date,
        'end_date': end_date,
        'max_total_quantity': max([p['total_quantity'] for p in top_products], default=0),
    }
    
    return render(request, 'analytics/sales_report.html', context)

@require_role('ADMIN', 'MANAGER', 'ANALYST')
@login_required
def product_performance(request):
    """Product performance analysis"""
    products = Product.objects.annotate(
        total_sold=Sum('saleitem__quantity'),
        total_revenue=Sum(ExpressionWrapper(F('saleitem__quantity') * F('saleitem__unit_price'), output_field=DecimalField())),
        total_cost=Sum(ExpressionWrapper(F('saleitem__quantity') * F('cost_price'), output_field=DecimalField())),
        profit=Sum(ExpressionWrapper((F('saleitem__unit_price') - F('cost_price')) * F('saleitem__quantity'), output_field=DecimalField()))
    ).filter(total_sold__isnull=False).order_by('-total_revenue')
    
    # Create result list with calculated metrics
    result_products = []
    for product in products:
        # Create a simple object to hold product data and calculated metrics
        class ProductStats:
            pass
        
        product_stats = ProductStats()
        # Copy product attributes
        for attr in ['id', 'name', 'sku', 'cost_price', 'selling_price', 'quantity', 'low_stock_threshold']:
            setattr(product_stats, attr, getattr(product, attr))
        
        # Copy annotated fields
        for attr in ['total_sold', 'total_revenue', 'total_cost', 'profit']:
            setattr(product_stats, attr, getattr(product, attr))
        
        # Calculate additional metrics
        if product.total_sold and product.total_sold > 0:
            product_stats.avg_selling_price = product.total_revenue / product.total_sold
            product_stats.calc_profit_margin = (product.profit / product.total_revenue * 100) if product.total_revenue > 0 else 0
            product_stats.turnover_rate = product.total_sold / product.quantity if product.quantity > 0 else 0
        else:
            product_stats.avg_selling_price = 0
            product_stats.calc_profit_margin = 0
            product_stats.turnover_rate = 0
        
        product_stats.product_obj = product
        result_products.append(product_stats)
    
    # Filter by performance
    performance_filter = request.GET.get('performance')
    if performance_filter == 'high_profit':
        result_products = [p for p in result_products if p.calc_profit_margin > 50]
    elif performance_filter == 'low_profit':
        result_products = [p for p in result_products if p.calc_profit_margin < 20]
    elif performance_filter == 'high_turnover':
        result_products = [p for p in result_products if p.turnover_rate > 2]
    elif performance_filter == 'low_turnover':
        result_products = [p for p in result_products if p.turnover_rate < 0.5]
    
    context = {
        'products': result_products,
        'total_count': len(result_products),
        'total_revenue': sum(p.total_revenue for p in result_products if p.total_revenue),
        'total_profit': sum(p.profit for p in result_products if p.profit),
    }
    
    return render(request, 'analytics/product_performance.html', context)

@require_role('ADMIN', 'MANAGER', 'ANALYST')
@login_required
def customer_insights(request):
    """Customer analytics and insights"""
    # RFM Analysis
    today = timezone.now().date()
    
    customers = Customer.objects.annotate(
        recency=ExpressionWrapper(
            Value(today) - TruncDay(Max('sale__created_at')),
            output_field=IntegerField()
        ),
        frequency=Count('sale'),
        monetary=Sum('sale__total')
    ).filter(frequency__gt=0).order_by('-monetary')
    
    # Calculate RFM scores
    for customer in customers:
        # Recency score (1-5, 5 is most recent)
        if customer.recency <= 30:  # Last 30 days
            customer.recency_score = 5
        elif customer.recency <= 60:  # 31-60 days
            customer.recency_score = 4
        elif customer.recency <= 90:  # 61-90 days
            customer.recency_score = 3
        elif customer.recency <= 180:  # 91-180 days
            customer.recency_score = 2
        else:  # More than 180 days
            customer.recency_score = 1
        
        # Frequency score (1-5, 5 is most frequent)
        if customer.frequency >= 20:
            customer.frequency_score = 5
        elif customer.frequency >= 10:
            customer.frequency_score = 4
        elif customer.frequency >= 5:
            customer.frequency_score = 3
        elif customer.frequency >= 2:
            customer.frequency_score = 2
        else:
            customer.frequency_score = 1
        
        # Monetary score (1-5, 5 is highest spending)
        if customer.monetary >= 50000:
            customer.monetary_score = 5
        elif customer.monetary >= 20000:
            customer.monetary_score = 4
        elif customer.monetary >= 10000:
            customer.monetary_score = 3
        elif customer.monetary >= 5000:
            customer.monetary_score = 2
        else:
            customer.monetary_score = 1
        
        # Overall RFM score
        customer.rfm_score = customer.recency_score + customer.frequency_score + customer.monetary_score
        customer.rfm_segment = (
            f"{customer.recency_score}{customer.frequency_score}{customer.monetary_score}"
        )
    
    # Customer segmentation
    segments = {
        'Champions': [c for c in customers if c.rfm_score >= 13],
        'Loyal Customers': [c for c in customers if 10 <= c.rfm_score <= 12],
        'Potential Loyalists': [c for c in customers if 7 <= c.rfm_score <= 9],
        'Recent Customers': [c for c in customers if c.recency_score >= 4],
        'At Risk': [c for c in customers if c.recency_score <= 2 and c.frequency_score >= 3],
        'Lost Customers': [c for c in customers if c.recency_score == 1],
    }
    
    context = {
        'customers': customers,
        'segments': segments,
        'total_customers': customers.count(),
        'avg_rfm_score': sum(c.rfm_score for c in customers) / len(customers) if customers else 0,
    }
    
    return render(request, 'analytics/customer_insights.html', context)

@require_role('ADMIN', 'MANAGER', 'ANALYST')
@login_required
def financial_report(request):
    """Financial performance report"""
    form = DateRangeForm(request.GET or None)
    
    # Default date range: current month
    today = timezone.now().date()
    start_date = request.GET.get('start_date') or today.replace(day=1)
    end_date = request.GET.get('end_date') or today
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Sales revenue
    sales = Sale.objects.filter(
        created_at__date__range=[start_date, end_date],
        status='COMPLETED'
    )
    
    total_revenue = sales.aggregate(total=Sum('total'))['total'] or 0
    total_profit = sum(sale.profit for sale in sales)
    
    # Expenses
    expenses = Expense.objects.filter(
        date__range=[start_date, end_date]
    )
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # Cost of Goods Sold (COGS)
    cogs = SaleItem.objects.filter(
        sale__created_at__date__range=[start_date, end_date],
        sale__status='COMPLETED'
    ).aggregate(
        total=Sum(ExpressionWrapper(F('quantity') * F('cost_price'), output_field=DecimalField()))
    )['total'] or 0
    
    # Gross profit
    gross_profit = total_revenue - cogs
    
    # Net profit
    net_profit = gross_profit - total_expenses
    
    # Expense breakdown
    expense_breakdown = expenses.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Profit margin
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'total_expenses': total_expenses,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'expense_breakdown': expense_breakdown,
        'profit_margin': profit_margin,
        'sales_count': sales.count(),
        'expenses_count': expenses.count(),
    }
    
    return render(request, 'analytics/financial_report.html', context)

@require_role('ADMIN', 'MANAGER', 'ANALYST')
@login_required
def inventory_report(request):
    """Inventory analysis report"""
    # Inventory valuation
    total_valuation = sum(p.total_value for p in Product.objects.filter(is_active=True))
    total_sales_value = sum(p.total_sales_value for p in Product.objects.filter(is_active=True))
    
    # Stock status
    low_stock = Product.objects.filter(
        quantity__lte=F('low_stock_threshold'),
        is_active=True
    )
    out_of_stock = Product.objects.filter(quantity=0, is_active=True)
    healthy_stock = Product.objects.filter(
        quantity__gt=F('low_stock_threshold'),
        is_active=True
    )
    
    # Expiring soon (within 30 days)
    thirty_days_from_now = timezone.now().date() + timedelta(days=30)
    expiring_soon = Product.objects.filter(
        expiry_date__lte=thirty_days_from_now,
        expiry_date__gte=timezone.now().date(),
        is_active=True
    )
    
    # Slow moving items (no sales in last 90 days)
    ninety_days_ago = timezone.now() - timedelta(days=90)
    slow_moving = Product.objects.annotate(
        last_sale_date=Max('saleitem__sale__created_at')
    ).filter(
        last_sale_date__lt=ninety_days_ago,
        is_active=True
    ) | Product.objects.annotate(
        last_sale_date=Max('saleitem__sale__created_at')
    ).filter(
        last_sale_date__isnull=True,
        is_active=True
    )
    
    # Fast moving items (high turnover)
    fast_moving = Product.objects.annotate(
        turnover_rate=ExpressionWrapper(
            Sum('saleitem__quantity') / F('quantity'),
            output_field=DecimalField()
        )
    ).filter(
        turnover_rate__gt=1,
        is_active=True
    ).order_by('-turnover_rate')[:20]
    
    context = {
        'total_valuation': total_valuation,
        'total_sales_value': total_sales_value,
        'low_stock_count': low_stock.count(),
        'out_of_stock_count': out_of_stock.count(),
        'healthy_stock_count': healthy_stock.count(),
        'expiring_soon_count': expiring_soon.count(),
        'slow_moving_count': slow_moving.count(),
        'low_stock_products': low_stock,
        'out_of_stock_products': out_of_stock,
        'expiring_soon_products': expiring_soon,
        'slow_moving_products': slow_moving[:20],
        'fast_moving_products': fast_moving,
    }
    
    return render(request, 'analytics/inventory_report.html', context)

@login_required
def custom_report(request):
    """Custom report generator"""
    form = DateRangeForm(request.GET or None)
    
    report_type = request.GET.get('report_type', 'sales')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    context = {
        'form': form,
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'report_types': [
            ('sales', 'Sales Report'),
            ('products', 'Product Performance'),
            ('customers', 'Customer Analysis'),
            ('inventory', 'Inventory Report'),
            ('financial', 'Financial Report'),
        ]
    }
    
    if start_date and end_date:
        # Generate report based on type
        if report_type == 'sales':
            return sales_report(request)
        elif report_type == 'products':
            return product_performance(request)
        elif report_type == 'customers':
            return customer_insights(request)
        elif report_type == 'inventory':
            return inventory_report(request)
        elif report_type == 'financial':
            return financial_report(request)
    
    return render(request, 'analytics/custom_report.html', context)

@login_required
def export_report_pdf(request):
    """Export report as PDF"""
    report_type = request.GET.get('report_type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not all([report_type, start_date, end_date]):
        return HttpResponse('Missing parameters', status=400)
    
    if report_type == 'sales':
        pdf = generate_sales_report_pdf(start_date, end_date)
        filename = f'sales_report_{start_date}_to_{end_date}.pdf'
    elif report_type == 'inventory':
        pdf = generate_inventory_report_pdf()
        filename = f'inventory_report_{date.today()}.pdf'
    elif report_type == 'financial':
        pdf = generate_financial_report_pdf(start_date, end_date)
        filename = f'financial_report_{start_date}_to_{end_date}.pdf'
    elif report_type == 'customers':
        pdf = generate_customer_report_pdf()
        filename = f'customer_report_{date.today()}.pdf'
    else:
        return HttpResponse('Invalid report type', status=400)
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def sales_chart_data(request):
    """Return sales chart data as JSON"""
    period = request.GET.get('period', 'week')
    
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
        sales_data = Sale.objects.filter(
            created_at__date__range=[start_date, today],
            status='COMPLETED'
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            total=Sum('total')
        ).order_by('day')
        
        data = {
            'labels': [d['day'].strftime('%a') for d in sales_data],
            'datasets': [{
                'label': 'Daily Sales',
                'data': [float(d['total']) for d in sales_data],
                'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                'borderColor': 'rgba(54, 162, 235, 1)',
            }]
        }
        
    elif period == 'month':
        start_date = today - timedelta(days=30)
        sales_data = Sale.objects.filter(
            created_at__date__range=[start_date, today],
            status='COMPLETED'
        ).annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            total=Sum('total')
        ).order_by('week')
        
        data = {
            'labels': [f"Week {d['week'].isocalendar()[1]}" for d in sales_data],
            'datasets': [{
                'label': 'Weekly Sales',
                'data': [float(d['total']) for d in sales_data],
                'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                'borderColor': 'rgba(255, 99, 132, 1)',
            }]
        }
    
    return JsonResponse(data)