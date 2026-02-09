import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg, F, Q, Max
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.utils import timezone
from decimal import Decimal

from core.models import Sale, SaleItem, Product, Customer, Expense, StockTransaction
from core.reports import (
    generate_sales_report_pdf, generate_inventory_report_pdf,
    generate_financial_report_pdf, generate_customer_report_pdf
)

class ReportGenerator:
    """Base class for all report generators"""
    
    def __init__(self, start_date=None, end_date=None):
        self.start_date = start_date or timezone.now().date() - timedelta(days=30)
        self.end_date = end_date or timezone.now().date()
        self.today = timezone.now().date()
    
    def format_currency(self, amount):
        """Format amount as currency"""
        return f"KES {amount:,.2f}"
    
    def calculate_percentage(self, part, total):
        """Calculate percentage"""
        if total == 0:
            return 0
        return (part / total) * 100

class SalesReportGenerator(ReportGenerator):
    """Generate comprehensive sales reports"""
    
    def generate_detailed_report(self):
        """Generate detailed sales report"""
        sales = Sale.objects.filter(
            created_at__date__range=[self.start_date, self.end_date],
            status='COMPLETED'
        ).order_by('-created_at')
        
        report = {
            'period': f"{self.start_date} to {self.end_date}",
            'generated_at': timezone.now(),
            'summary': self._generate_summary(sales),
            'daily_breakdown': self._generate_daily_breakdown(sales),
            'payment_analysis': self._generate_payment_analysis(sales),
            'product_performance': self._generate_product_performance(),
            'customer_analysis': self._generate_customer_analysis(sales),
            'hourly_analysis': self._generate_hourly_analysis(sales),
            'trend_analysis': self._generate_trend_analysis(),
        }
        
        return report
    
    def _generate_summary(self, sales):
        """Generate sales summary"""
        summary = sales.aggregate(
            total_sales=Sum('total'),
            total_transactions=Count('id'),
            avg_sale=Avg('total'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('tax_amount'),
            total_profit=Sum(F('total') - F('subtotal') + F('discount_amount'))
        )
        
        # Calculate additional metrics
        summary['profit_margin'] = self.calculate_percentage(
            summary['total_profit'] or 0,
            summary['total_sales'] or 1
        )
        
        # Best day
        best_day = sales.annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            daily_total=Sum('total')
        ).order_by('-daily_total').first()
        
        summary['best_day'] = {
            'date': best_day['day'].date() if best_day else None,
            'amount': best_day['daily_total'] if best_day else 0
        }
        
        return summary
    
    def _generate_daily_breakdown(self, sales):
        """Generate daily sales breakdown"""
        daily_data = sales.annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            daily_total=Sum('total'),
            daily_count=Count('id'),
            daily_avg=Avg('total')
        ).order_by('day')
        
        return list(daily_data)
    
    def _generate_payment_analysis(self, sales):
        """Analyze payment methods"""
        payment_data = sales.values('payment_method').annotate(
            total=Sum('total'),
            count=Count('id'),
            avg=Avg('total')
        ).order_by('-total')
        
        analysis = []
        for payment in payment_data:
            percentage = self.calculate_percentage(
                payment['total'] or 0,
                sales.aggregate(total=Sum('total'))['total'] or 1
            )
            analysis.append({
                'method': payment['payment_method'],
                'total': payment['total'] or 0,
                'count': payment['count'] or 0,
                'avg': payment['avg'] or 0,
                'percentage': percentage
            })
        
        return analysis
    
    def _generate_product_performance(self):
        """Analyze product performance"""
        products = Product.objects.annotate(
            total_sold=Sum('saleitem__quantity'),
            total_revenue=Sum(F('saleitem__quantity') * F('saleitem__unit_price')),
            total_cost=Sum(F('saleitem__quantity') * F('cost_price')),
            total_profit=Sum((F('saleitem__unit_price') - F('cost_price')) * F('saleitem__quantity'))
        ).filter(
            saleitem__sale__created_at__date__range=[self.start_date, self.end_date],
            saleitem__sale__status='COMPLETED'
        ).distinct().order_by('-total_sold')
        
        performance = []
        for product in products:
            if product.total_sold:
                margin = self.calculate_percentage(
                    product.total_profit or 0,
                    product.total_revenue or 1
                )
                
                # Calculate turnover rate (if product still exists)
                if product.quantity > 0:
                    turnover = product.total_sold / product.quantity
                else:
                    turnover = product.total_sold  # If sold out, turnover is total sold
                
                performance.append({
                    'product_id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'category': product.category.name if product.category else 'Uncategorized',
                    'total_sold': product.total_sold or 0,
                    'total_revenue': product.total_revenue or 0,
                    'total_cost': product.total_cost or 0,
                    'total_profit': product.total_profit or 0,
                    'profit_margin': margin,
                    'turnover_rate': turnover,
                    'current_stock': product.quantity,
                    'status': 'Out of Stock' if product.quantity == 0 else 
                             'Low Stock' if product.is_low_stock else 'In Stock'
                })
        
        return performance
    
    def _generate_customer_analysis(self, sales):
        """Analyze customer behavior"""
        customers = Customer.objects.annotate(
            num_purchases=Count('sale'),
            total_spent=Sum('sale__total'),
            last_purchase=Max('sale__created_at'),
            avg_purchase=Avg('sale__total')
        ).filter(
            sale__created_at__date__range=[self.start_date, self.end_date],
            sale__status='COMPLETED'
        ).distinct().order_by('-total_spent')
        
        analysis = []
        for customer in customers:
            # Calculate customer lifetime value metrics
            days_since_last_purchase = (self.today - customer.last_purchase.date()).days if customer.last_purchase else 999
            
            analysis.append({
                'customer_id': customer.id,
                'name': customer.full_name,
                'email': customer.email,
                'phone': customer.phone,
                'membership': customer.get_membership_type_display(),
                'purchase_count': customer.num_purchases or 0,
                'total_spent': customer.total_spent or 0,
                'avg_purchase': customer.avg_purchase or 0,
                'last_purchase': customer.last_purchase,
                'days_since_last_purchase': days_since_last_purchase,
                'loyalty_points': customer.loyalty_points
            })
        
        return analysis
    
    def _generate_hourly_analysis(self, sales):
        """Analyze sales by hour"""
        hourly_data = sales.annotate(
            hour=ExtractHour('created_at')
        ).values('hour').annotate(
            total=Sum('total'),
            count=Count('id'),
            avg=Avg('total')
        ).order_by('hour')
        
        # Fill missing hours
        full_hourly_data = []
        for hour in range(0, 24):
            hour_data = next((h for h in hourly_data if h['hour'] == hour), None)
            if hour_data:
                full_hourly_data.append(hour_data)
            else:
                full_hourly_data.append({
                    'hour': hour,
                    'total': 0,
                    'count': 0,
                    'avg': 0
                })
        
        return full_hourly_data
    
    def _generate_trend_analysis(self):
        """Generate sales trend analysis"""
        # Get last 12 months of data
        twelve_months_ago = self.today - timedelta(days=365)
        
        monthly_trend = Sale.objects.filter(
            created_at__date__range=[twelve_months_ago, self.end_date],
            status='COMPLETED'
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total_sales=Sum('total'),
            total_transactions=Count('id'),
            avg_sale=Avg('total')
        ).order_by('month')
        
        # Calculate growth rates
        trend_data = list(monthly_trend)
        for i, month_data in enumerate(trend_data):
            if i > 0:
                prev_month = trend_data[i-1]
                if prev_month['total_sales'] and prev_month['total_sales'] > 0:
                    growth_rate = ((month_data['total_sales'] - prev_month['total_sales']) / 
                                   prev_month['total_sales']) * 100
                else:
                    growth_rate = 100 if month_data['total_sales'] > 0 else 0
                month_data['growth_rate'] = growth_rate
            else:
                month_data['growth_rate'] = 0
        
        return trend_data
    
    def export_to_dataframe(self):
        """Export report data to pandas DataFrame"""
        report = self.generate_detailed_report()
        
        # Create DataFrames for each section
        dfs = {}
        
        # Summary DataFrame
        summary_data = {
            'Metric': ['Total Sales', 'Total Transactions', 'Average Sale', 
                      'Total Discount', 'Total Tax', 'Total Profit', 'Profit Margin'],
            'Value': [
                self.format_currency(report['summary']['total_sales'] or 0),
                report['summary']['total_transactions'] or 0,
                self.format_currency(report['summary']['avg_sale'] or 0),
                self.format_currency(report['summary']['total_discount'] or 0),
                self.format_currency(report['summary']['total_tax'] or 0),
                self.format_currency(report['summary']['total_profit'] or 0),
                f"{report['summary']['profit_margin']:.1f}%"
            ]
        }
        dfs['Summary'] = pd.DataFrame(summary_data)
        
        # Daily Breakdown DataFrame
        daily_data = []
        for day in report['daily_breakdown']:
            daily_data.append({
                'Date': day['day'].strftime('%Y-%m-%d'),
                'Total Sales': day['daily_total'] or 0,
                'Transaction Count': day['daily_count'] or 0,
                'Average Sale': day['daily_avg'] or 0
            })
        dfs['Daily Breakdown'] = pd.DataFrame(daily_data)
        
        # Product Performance DataFrame
        product_data = []
        for product in report['product_performance']:
            product_data.append({
                'Product': product['name'],
                'SKU': product['sku'],
                'Category': product['category'],
                'Units Sold': product['total_sold'],
                'Revenue': product['total_revenue'],
                'Cost': product['total_cost'],
                'Profit': product['total_profit'],
                'Margin': f"{product['profit_margin']:.1f}%",
                'Turnover Rate': f"{product['turnover_rate']:.2f}",
                'Current Stock': product['current_stock'],
                'Status': product['status']
            })
        dfs['Product Performance'] = pd.DataFrame(product_data)
        
        return dfs

class InventoryReportGenerator(ReportGenerator):
    """Generate inventory analysis reports"""
    
    def generate_detailed_report(self):
        """Generate detailed inventory report"""
        products = Product.objects.filter(is_active=True).order_by('category__name', 'name')
        
        report = {
            'generated_at': timezone.now(),
            'summary': self._generate_summary(products),
            'category_analysis': self._generate_category_analysis(products),
            'stock_status': self._generate_stock_status(products),
            'valuation_analysis': self._generate_valuation_analysis(products),
            'expiry_analysis': self._generate_expiry_analysis(products),
            'slow_moving': self._identify_slow_moving(products),
            'fast_moving': self._identify_fast_moving(products),
            'reorder_recommendations': self._generate_reorder_recommendations(products)
        }
        
        return report
    
    def _generate_summary(self, products):
        """Generate inventory summary"""
        total_products = products.count()
        total_valuation = sum(p.total_value for p in products)
        total_sales_value = sum(p.total_sales_value for p in products)
        
        low_stock = sum(1 for p in products if p.is_low_stock)
        out_of_stock = sum(1 for p in products if p.quantity == 0)
        healthy_stock = total_products - low_stock - out_of_stock
        
        summary = {
            'total_products': total_products,
            'total_valuation': total_valuation,
            'total_sales_value': total_sales_value,
            'avg_valuation': total_valuation / total_products if total_products > 0 else 0,
            'low_stock_count': low_stock,
            'out_of_stock_count': out_of_stock,
            'healthy_stock_count': healthy_stock,
            'percentage_low_stock': self.calculate_percentage(low_stock, total_products),
            'percentage_out_of_stock': self.calculate_percentage(out_of_stock, total_products)
        }
        
        return summary
    
    def _generate_category_analysis(self, products):
        """Analyze inventory by category"""
        category_data = {}
        
        for product in products:
            category_name = product.category.name if product.category else 'Uncategorized'
            if category_name not in category_data:
                category_data[category_name] = {
                    'product_count': 0,
                    'total_quantity': 0,
                    'total_value': 0,
                    'total_sales_value': 0,
                    'low_stock_count': 0,
                    'out_of_stock_count': 0
                }
            
            category_data[category_name]['product_count'] += 1
            category_data[category_name]['total_quantity'] += product.quantity
            category_data[category_name]['total_value'] += product.total_value
            category_data[category_name]['total_sales_value'] += product.total_sales_value
            
            if product.quantity == 0:
                category_data[category_name]['out_of_stock_count'] += 1
            elif product.is_low_stock:
                category_data[category_name]['low_stock_count'] += 1
        
        return category_data
    
    def _generate_stock_status(self, products):
        """Generate stock status analysis"""
        status_data = {
            'out_of_stock': [],
            'low_stock': [],
            'healthy_stock': []
        }
        
        for product in products:
            product_info = {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'category': product.category.name if product.category else 'Uncategorized',
                'current_stock': product.quantity,
                'low_stock_threshold': product.low_stock_threshold,
                'reorder_quantity': product.reorder_quantity,
                'stock_value': product.total_value,
                'status': 'Out of Stock' if product.quantity == 0 else 
                         'Low Stock' if product.is_low_stock else 'Healthy'
            }
            
            if product.quantity == 0:
                status_data['out_of_stock'].append(product_info)
            elif product.is_low_stock:
                status_data['low_stock'].append(product_info)
            else:
                status_data['healthy_stock'].append(product_info)
        
        return status_data
    
    def _generate_valuation_analysis(self, products):
        """Analyze inventory valuation"""
        # Sort products by value
        sorted_products = sorted(products, key=lambda x: x.total_value, reverse=True)
        
        # Calculate ABC analysis (Pareto analysis)
        total_value = sum(p.total_value for p in products)
        cumulative_value = 0
        abc_analysis = []
        
        for product in sorted_products:
            cumulative_value += product.total_value
            percentage_of_total = self.calculate_percentage(product.total_value, total_value)
            cumulative_percentage = self.calculate_percentage(cumulative_value, total_value)
            
            classification = 'A' if cumulative_percentage <= 80 else 'B' if cumulative_percentage <= 95 else 'C'
            
            abc_analysis.append({
                'product': product.name,
                'sku': product.sku,
                'quantity': product.quantity,
                'unit_cost': product.cost_price,
                'total_value': product.total_value,
                'percentage_of_total': percentage_of_total,
                'cumulative_percentage': cumulative_percentage,
                'classification': classification
            })
        
        # Summary of ABC analysis
        abc_summary = {}
        for item in abc_analysis:
            classification = item['classification']
            if classification not in abc_summary:
                abc_summary[classification] = {
                    'count': 0,
                    'total_value': 0,
                    'percentage_of_products': 0,
                    'percentage_of_value': 0
                }
            
            abc_summary[classification]['count'] += 1
            abc_summary[classification]['total_value'] += item['total_value']
        
        # Calculate percentages
        for classification in abc_summary:
            abc_summary[classification]['percentage_of_products'] = self.calculate_percentage(
                abc_summary[classification]['count'], len(products)
            )
            abc_summary[classification]['percentage_of_value'] = self.calculate_percentage(
                abc_summary[classification]['total_value'], total_value
            )
        
        return {
            'abc_analysis': abc_analysis,
            'abc_summary': abc_summary,
            'total_valuation': total_value,
            'avg_product_value': total_value / len(products) if products else 0
        }
    
    def _generate_expiry_analysis(self, products):
        """Analyze products nearing expiry"""
        thirty_days_from_now = self.today + timedelta(days=30)
        sixty_days_from_now = self.today + timedelta(days=60)
        
        expiring_soon = []
        expired = []
        
        for product in products:
            if product.expiry_date:
                days_until_expiry = (product.expiry_date - self.today).days
                
                if days_until_expiry < 0:
                    expired.append({
                        'product': product.name,
                        'sku': product.sku,
                        'expiry_date': product.expiry_date,
                        'quantity': product.quantity,
                        'stock_value': product.total_value,
                        'days_expired': abs(days_until_expiry)
                    })
                elif days_until_expiry <= 30:
                    expiring_soon.append({
                        'product': product.name,
                        'sku': product.sku,
                        'expiry_date': product.expiry_date,
                        'quantity': product.quantity,
                        'stock_value': product.total_value,
                        'days_until_expiry': days_until_expiry,
                        'urgency': 'High' if days_until_expiry <= 7 else 'Medium'
                    })
        
        # Sort by urgency
        expiring_soon.sort(key=lambda x: x['days_until_expiry'])
        
        return {
            'expiring_soon': expiring_soon,
            'expired': expired,
            'total_expiring_value': sum(item['stock_value'] for item in expiring_soon),
            'total_expired_value': sum(item['stock_value'] for item in expired)
        }
    
    def _identify_slow_moving(self, products):
        """Identify slow moving products"""
        ninety_days_ago = self.today - timedelta(days=90)
        
        slow_moving = []
        for product in products:
            # Check sales in last 90 days
            recent_sales = SaleItem.objects.filter(
                product=product,
                sale__created_at__date__gte=ninety_days_ago,
                sale__status='COMPLETED'
            ).aggregate(total_sold=Sum('quantity'))['total_sold'] or 0
            
            # Calculate turnover rate for last 90 days
            if product.quantity > 0:
                turnover_rate = recent_sales / product.quantity
            else:
                turnover_rate = 0
            
            # Consider as slow moving if no sales in 90 days or very low turnover
            if recent_sales == 0 or turnover_rate < 0.1:
                slow_moving.append({
                    'product': product.name,
                    'sku': product.sku,
                    'category': product.category.name if product.category else 'Uncategorized',
                    'current_stock': product.quantity,
                    'recent_sales': recent_sales,
                    'turnover_rate': turnover_rate,
                    'stock_value': product.total_value,
                    'last_sale_date': self._get_last_sale_date(product)
                })
        
        # Sort by stock value (most valuable slow movers first)
        slow_moving.sort(key=lambda x: x['stock_value'], reverse=True)
        
        return slow_moving
    
    def _identify_fast_moving(self, products):
        """Identify fast moving products"""
        ninety_days_ago = self.today - timedelta(days=90)
        
        fast_moving = []
        for product in products:
            # Check sales in last 90 days
            recent_sales = SaleItem.objects.filter(
                product=product,
                sale__created_at__date__gte=ninety_days_ago,
                sale__status='COMPLETED'
            ).aggregate(total_sold=Sum('quantity'))['total_sold'] or 0
            
            # Calculate turnover rate for last 90 days
            if product.quantity > 0:
                turnover_rate = recent_sales / product.quantity
            else:
                turnover_rate = recent_sales  # If sold out, consider turnover as sales
            
            # Consider as fast moving if high turnover (e.g., > 2)
            if turnover_rate > 2:
                fast_moving.append({
                    'product': product.name,
                    'sku': product.sku,
                    'category': product.category.name if product.category else 'Uncategorized',
                    'current_stock': product.quantity,
                    'recent_sales': recent_sales,
                    'turnover_rate': turnover_rate,
                    'stock_value': product.total_value,
                    'profit_margin': product.profit_margin
                })
        
        # Sort by turnover rate (highest first)
        fast_moving.sort(key=lambda x: x['turnover_rate'], reverse=True)
        
        return fast_moving[:20]  # Return top 20
    
    def _get_last_sale_date(self, product):
        """Get last sale date for a product"""
        last_sale = SaleItem.objects.filter(
            product=product,
            sale__status='COMPLETED'
        ).order_by('-sale__created_at').first()
        
        return last_sale.sale.created_at if last_sale else None
    
    def _generate_reorder_recommendations(self, products):
        """Generate reorder recommendations"""
        recommendations = []
        
        for product in products:
            if product.is_low_stock or product.quantity == 0:
                suggested_qty = max(product.reorder_quantity - product.quantity, 1)
                estimated_cost = suggested_qty * product.cost_price
                
                recommendations.append({
                    'product': product.name,
                    'sku': product.sku,
                    'supplier': product.supplier.name if product.supplier else 'Unknown',
                    'current_stock': product.quantity,
                    'reorder_point': product.low_stock_threshold,
                    'reorder_quantity': product.reorder_quantity,
                    'suggested_qty': suggested_qty,
                    'unit_cost': product.cost_price,
                    'estimated_cost': estimated_cost,
                    'urgency': 'Critical' if product.quantity == 0 else 'High' if product.quantity <= 2 else 'Medium'
                })
        
        # Sort by urgency and estimated cost
        recommendations.sort(key=lambda x: (
            0 if x['urgency'] == 'Critical' else 1 if x['urgency'] == 'High' else 2,
            -x['estimated_cost']
        ))
        
        return recommendations
    
    def export_to_dataframe(self):
        """Export inventory report to pandas DataFrame"""
        report = self.generate_detailed_report()
        
        dfs = {}
        
        # Summary DataFrame
        summary_data = {
            'Metric': ['Total Products', 'Total Valuation', 'Total Sales Value',
                      'Low Stock Items', 'Out of Stock Items', 'Healthy Stock Items',
                      'Avg. Product Value'],
            'Value': [
                report['summary']['total_products'],
                self.format_currency(report['summary']['total_valuation']),
                self.format_currency(report['summary']['total_sales_value']),
                report['summary']['low_stock_count'],
                report['summary']['out_of_stock_count'],
                report['summary']['healthy_stock_count'],
                self.format_currency(report['summary']['avg_valuation'])
            ]
        }
        dfs['Summary'] = pd.DataFrame(summary_data)
        
        # Category Analysis DataFrame
        category_data = []
        for category, data in report['category_analysis'].items():
            category_data.append({
                'Category': category,
                'Products': data['product_count'],
                'Total Quantity': data['total_quantity'],
                'Total Value': self.format_currency(data['total_value']),
                'Total Sales Value': self.format_currency(data['total_sales_value']),
                'Low Stock': data['low_stock_count'],
                'Out of Stock': data['out_of_stock_count']
            })
        dfs['Category Analysis'] = pd.DataFrame(category_data)
        
        # Stock Status DataFrame
        stock_status_data = []
        for status, products in report['stock_status'].items():
            for product in products:
                stock_status_data.append({
                    'Status': status.replace('_', ' ').title(),
                    'Product': product['name'],
                    'SKU': product['sku'],
                    'Category': product['category'],
                    'Current Stock': product['current_stock'],
                    'Low Stock Threshold': product['low_stock_threshold'],
                    'Stock Value': self.format_currency(product['stock_value'])
                })
        dfs['Stock Status'] = pd.DataFrame(stock_status_data)
        
        # Reorder Recommendations DataFrame
        reorder_data = []
        for rec in report['reorder_recommendations']:
            reorder_data.append({
                'Product': rec['product'],
                'SKU': rec['sku'],
                'Supplier': rec['supplier'],
                'Current Stock': rec['current_stock'],
                'Suggested Qty': rec['suggested_qty'],
                'Unit Cost': self.format_currency(rec['unit_cost']),
                'Estimated Cost': self.format_currency(rec['estimated_cost']),
                'Urgency': rec['urgency']
            })
        dfs['Reorder Recommendations'] = pd.DataFrame(reorder_data)
        
        return dfs

class CustomerReportGenerator(ReportGenerator):
    """Generate customer analysis reports"""
    
    def generate_detailed_report(self):
        """Generate detailed customer report"""
        customers = Customer.objects.filter(is_active=True).order_by('-date_joined')
        
        report = {
            'generated_at': timezone.now(),
            'summary': self._generate_summary(customers),
            'demographic_analysis': self._generate_demographic_analysis(customers),
            'rfm_analysis': self._generate_rfm_analysis(customers),
            'segmentation': self._generate_segmentation(customers),
            'loyalty_analysis': self._generate_loyalty_analysis(customers),
            'acquisition_analysis': self._generate_acquisition_analysis(customers),
            'churn_analysis': self._generate_churn_analysis(customers),
            'top_customers': self._identify_top_customers(customers)
        }
        
        return report
    
    def _generate_summary(self, customers):
        """Generate customer summary"""
        total_customers = customers.count()
        
        # Calculate active customers (purchased in last 90 days)
        ninety_days_ago = self.today - timedelta(days=90)
        active_customers = customers.filter(
            sale__created_at__date__gte=ninety_days_ago,
            sale__status='COMPLETED'
        ).distinct().count()
        
        # Calculate new customers (joined in last 30 days)
        thirty_days_ago = self.today - timedelta(days=30)
        new_customers = customers.filter(
            date_joined__date__gte=thirty_days_ago
        ).count()
        
        # Calculate total revenue from customers
        total_revenue = customers.aggregate(total=Sum('total_spent'))['total'] or 0
        
        # Calculate average customer value
        avg_customer_value = total_revenue / total_customers if total_customers > 0 else 0
        
        summary = {
            'total_customers': total_customers,
            'active_customers': active_customers,
            'new_customers': new_customers,
            'inactive_customers': total_customers - active_customers,
            'total_revenue': total_revenue,
            'avg_customer_value': avg_customer_value,
            'active_percentage': self.calculate_percentage(active_customers, total_customers),
            'new_customer_percentage': self.calculate_percentage(new_customers, total_customers)
        }
        
        return summary
    
    def _generate_demographic_analysis(self, customers):
        """Analyze customer demographics"""
        demographic_data = {
            'gender': {'M': 0, 'F': 0, 'O': 0, 'Unknown': 0},
            'membership': {},
            'city': {},
            'age_groups': {
                'Under 18': 0,
                '18-25': 0,
                '26-35': 0,
                '36-45': 0,
                '46-55': 0,
                '56+': 0,
                'Unknown': 0
            }
        }
        
        for customer in customers:
            # Gender analysis
            gender = customer.gender if customer.gender else 'Unknown'
            demographic_data['gender'][gender] = demographic_data['gender'].get(gender, 0) + 1
            
            # Membership analysis
            membership = customer.get_membership_type_display()
            demographic_data['membership'][membership] = demographic_data['membership'].get(membership, 0) + 1
            
            # City analysis
            city = customer.city if customer.city else 'Unknown'
            demographic_data['city'][city] = demographic_data['city'].get(city, 0) + 1
            
            # Age group analysis
            if customer.date_of_birth:
                age = self.today.year - customer.date_of_birth.year
                if age < 18:
                    demographic_data['age_groups']['Under 18'] += 1
                elif age <= 25:
                    demographic_data['age_groups']['18-25'] += 1
                elif age <= 35:
                    demographic_data['age_groups']['26-35'] += 1
                elif age <= 45:
                    demographic_data['age_groups']['36-45'] += 1
                elif age <= 55:
                    demographic_data['age_groups']['46-55'] += 1
                else:
                    demographic_data['age_groups']['56+'] += 1
            else:
                demographic_data['age_groups']['Unknown'] += 1
        
        # Calculate percentages
        for category in demographic_data:
            if isinstance(demographic_data[category], dict):
                total = sum(demographic_data[category].values())
                if total > 0:
                    for key in demographic_data[category]:
                        demographic_data[category][f'{key}_percentage'] = self.calculate_percentage(
                            demographic_data[category][key], total
                        )
        
        return demographic_data
    
    def _generate_rfm_analysis(self, customers):
        """Generate RFM (Recency, Frequency, Monetary) analysis"""
        rfm_data = []
        
        for customer in customers:
            # Get customer's purchase history
            purchases = Sale.objects.filter(
                customer=customer,
                status='COMPLETED'
            ).order_by('-created_at')
            
            # Recency (days since last purchase)
            last_purchase = purchases.first()
            recency = (self.today - last_purchase.created_at.date()).days if last_purchase else 999
            
            # Frequency (number of purchases)
            frequency = purchases.count()
            
            # Monetary (total spent)
            monetary = customer.total_spent or 0
            
            # Calculate RFM scores (1-5, 5 being best)
            recency_score = self._calculate_rfm_score(recency, 'recency')
            frequency_score = self._calculate_rfm_score(frequency, 'frequency')
            monetary_score = self._calculate_rfm_score(monetary, 'monetary')
            
            total_rfm_score = recency_score + frequency_score + monetary_score
            rfm_segment = f"{recency_score}{frequency_score}{monetary_score}"
            
            rfm_data.append({
                'customer_id': customer.id,
                'name': customer.full_name,
                'email': customer.email,
                'phone': customer.phone,
                'recency': recency,
                'frequency': frequency,
                'monetary': monetary,
                'recency_score': recency_score,
                'frequency_score': frequency_score,
                'monetary_score': monetary_score,
                'total_score': total_rfm_score,
                'rfm_segment': rfm_segment,
                'segment_name': self._get_rfm_segment_name(rfm_segment)
            })
        
        # Sort by total RFM score (highest first)
        rfm_data.sort(key=lambda x: x['total_score'], reverse=True)
        
        return rfm_data
    
    def _calculate_rfm_score(self, value, metric):
        """Calculate RFM score (1-5) based on metric"""
        if metric == 'recency':
            # Lower recency is better (more recent)
            if value <= 30: return 5
            elif value <= 60: return 4
            elif value <= 90: return 3
            elif value <= 180: return 2
            else: return 1
        elif metric == 'frequency':
            # Higher frequency is better
            if value >= 20: return 5
            elif value >= 10: return 4
            elif value >= 5: return 3
            elif value >= 2: return 2
            else: return 1
        elif metric == 'monetary':
            # Higher monetary is better
            if value >= 50000: return 5
            elif value >= 20000: return 4
            elif value >= 10000: return 3
            elif value >= 5000: return 2
            else: return 1
    
    def _get_rfm_segment_name(self, rfm_segment):
        """Get segment name from RFM segment code"""
        segment_map = {
            '555': 'Champions', '554': 'Champions', '545': 'Champions', '544': 'Champions',
            '455': 'Loyal Customers', '454': 'Loyal Customers', '445': 'Loyal Customers',
            '355': 'Potential Loyalists', '354': 'Potential Loyalists', '345': 'Potential Loyalists',
            '255': 'Recent Customers', '254': 'Recent Customers', '245': 'Recent Customers',
            '155': 'Promising', '154': 'Promising', '145': 'Promising',
            '111': 'Lost', '112': 'Lost', '113': 'Lost', '114': 'Lost', '115': 'Lost',
            '211': 'Hibernating', '212': 'Hibernating', '213': 'Hibernating',
            '311': 'At Risk', '312': 'At Risk', '313': 'At Risk',
            '411': 'Cannot Lose', '412': 'Cannot Lose', '413': 'Cannot Lose',
            '511': 'About to Sleep', '512': 'About to Sleep', '513': 'About to Sleep'
        }
        
        return segment_map.get(rfm_segment, 'Need Attention')
    
    def _generate_segmentation(self, customers):
        """Generate customer segmentation"""
        rfm_data = self._generate_rfm_analysis(customers)
        
        segments = {}
        for customer in rfm_data:
            segment = customer['segment_name']
            if segment not in segments:
                segments[segment] = {
                    'count': 0,
                    'total_revenue': 0,
                    'avg_recency': 0,
                    'avg_frequency': 0,
                    'avg_monetary': 0,
                    'customers': []
                }
            
            segments[segment]['count'] += 1
            segments[segment]['total_revenue'] += customer['monetary']
            segments[segment]['customers'].append(customer['name'])
        
        # Calculate averages
        for segment in segments:
            if segments[segment]['count'] > 0:
                segments[segment]['avg_revenue'] = segments[segment]['total_revenue'] / segments[segment]['count']
                segments[segment]['percentage'] = self.calculate_percentage(
                    segments[segment]['count'], len(customers)
                )
        
        return segments
    
    def _generate_loyalty_analysis(self, customers):
        """Analyze customer loyalty program"""
        loyalty_data = {
            'membership_levels': {},
            'points_distribution': {
                '0-100': 0,
                '101-500': 0,
                '501-1000': 0,
                '1001-5000': 0,
                '5000+': 0
            },
            'points_redemption': 0,
            'points_earned_last_month': 0
        }
        
        # Calculate points earned in last 30 days
        thirty_days_ago = self.today - timedelta(days=30)
        recent_sales = Sale.objects.filter(
            created_at__date__gte=thirty_days_ago,
            status='COMPLETED',
            customer__isnull=False
        )
        
        loyalty_data['points_earned_last_month'] = recent_sales.aggregate(
            total=Sum('loyalty_points_earned')
        )['total'] or 0
        
        loyalty_data['points_redemption'] = recent_sales.aggregate(
            total=Sum('loyalty_points_used')
        )['total'] or 0
        
        # Analyze membership levels
        for customer in customers:
            membership = customer.get_membership_type_display()
            if membership not in loyalty_data['membership_levels']:
                loyalty_data['membership_levels'][membership] = {
                    'count': 0,
                    'avg_points': 0,
                    'total_points': 0
                }
            
            loyalty_data['membership_levels'][membership]['count'] += 1
            loyalty_data['membership_levels'][membership]['total_points'] += customer.loyalty_points
            
            # Points distribution
            points = customer.loyalty_points
            if points <= 100:
                loyalty_data['points_distribution']['0-100'] += 1
            elif points <= 500:
                loyalty_data['points_distribution']['101-500'] += 1
            elif points <= 1000:
                loyalty_data['points_distribution']['501-1000'] += 1
            elif points <= 5000:
                loyalty_data['points_distribution']['1001-5000'] += 1
            else:
                loyalty_data['points_distribution']['5000+'] += 1
        
        # Calculate averages
        for membership in loyalty_data['membership_levels']:
            level = loyalty_data['membership_levels'][membership]
            if level['count'] > 0:
                level['avg_points'] = level['total_points'] / level['count']
        
        return loyalty_data
    
    def _generate_acquisition_analysis(self, customers):
        """Analyze customer acquisition"""
        # Group by month of acquisition
        acquisition_data = customers.annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            new_customers=Count('id'),
            total_revenue=Sum('total_spent')
        ).order_by('month')
        
        # Calculate acquisition cost (simplified - you'd need marketing data)
        # For now, we'll calculate average revenue per new customer by month
        acquisition_summary = []
        for data in acquisition_data:
            avg_revenue_per_customer = data['total_revenue'] / data['new_customers'] if data['new_customers'] > 0 else 0
            
            acquisition_summary.append({
                'month': data['month'].strftime('%Y-%m'),
                'new_customers': data['new_customers'],
                'total_revenue': data['total_revenue'] or 0,
                'avg_revenue_per_customer': avg_revenue_per_customer,
                'estimated_acquisition_cost': avg_revenue_per_customer * 0.3  # 30% as example
            })
        
        return acquisition_summary
    
    def _generate_churn_analysis(self, customers):
        """Analyze customer churn"""
        churn_data = {
            'at_risk': [],
            'churned': [],
            'loyal': [],
            'churn_rate': 0,
            'retention_rate': 0
        }
        
        # Define churned as no purchase in last 180 days
        # At risk as no purchase in last 90 days but within 180 days
        # Loyal as purchased in last 90 days
        
        for customer in customers:
            last_purchase = Sale.objects.filter(
                customer=customer,
                status='COMPLETED'
            ).order_by('-created_at').first()
            
            if last_purchase:
                days_since_last_purchase = (self.today - last_purchase.created_at.date()).days
                
                if days_since_last_purchase <= 90:
                    churn_data['loyal'].append({
                        'customer': customer.full_name,
                        'last_purchase': last_purchase.created_at.date(),
                        'days_since_purchase': days_since_last_purchase,
                        'total_spent': customer.total_spent
                    })
                elif days_since_last_purchase <= 180:
                    churn_data['at_risk'].append({
                        'customer': customer.full_name,
                        'last_purchase': last_purchase.created_at.date(),
                        'days_since_purchase': days_since_last_purchase,
                        'total_spent': customer.total_spent
                    })
                else:
                    churn_data['churned'].append({
                        'customer': customer.full_name,
                        'last_purchase': last_purchase.created_at.date(),
                        'days_since_purchase': days_since_last_purchase,
                        'total_spent': customer.total_spent
                    })
            else:
                # Customer never purchased
                churn_data['churned'].append({
                    'customer': customer.full_name,
                    'last_purchase': None,
                    'days_since_purchase': 999,
                    'total_spent': 0
                })
        
        # Calculate churn and retention rates
        total_customers = len(customers)
        churned_customers = len(churn_data['churned'])
        
        if total_customers > 0:
            churn_data['churn_rate'] = self.calculate_percentage(churned_customers, total_customers)
            churn_data['retention_rate'] = 100 - churn_data['churn_rate']
        
        return churn_data
    
    def _identify_top_customers(self, customers, limit=20):
        """Identify top customers by revenue"""
        top_customers = sorted(
            customers,
            key=lambda x: x.total_spent or 0,
            reverse=True
        )[:limit]
        
        detailed_top_customers = []
        for customer in top_customers:
            # Get customer's purchase details
            purchases = Sale.objects.filter(
                customer=customer,
                status='COMPLETED'
            )
            
            # Calculate additional metrics
            purchase_count = purchases.count()
            avg_purchase = customer.total_spent / purchase_count if purchase_count > 0 else 0
            
            # Get favorite products
            favorite_products = SaleItem.objects.filter(
                sale__customer=customer
            ).values('product__name').annotate(
                total_quantity=Sum('quantity')
            ).order_by('-total_quantity')[:3]
            
            detailed_top_customers.append({
                'rank': len(detailed_top_customers) + 1,
                'customer': customer.full_name,
                'email': customer.email,
                'phone': customer.phone,
                'membership': customer.get_membership_type_display(),
                'total_spent': customer.total_spent or 0,
                'purchase_count': purchase_count,
                'avg_purchase': avg_purchase,
                'loyalty_points': customer.loyalty_points,
                'last_purchase': purchases.order_by('-created_at').first().created_at if purchases.exists() else None,
                'favorite_products': [p['product__name'] for p in favorite_products if p['product__name']]
            })
        
        return detailed_top_customers
    
    def export_to_dataframe(self):
        """Export customer report to pandas DataFrame"""
        report = self.generate_detailed_report()
        
        dfs = {}
        
        # Summary DataFrame
        summary_data = {
            'Metric': ['Total Customers', 'Active Customers', 'New Customers (30 days)',
                      'Inactive Customers', 'Total Revenue', 'Average Customer Value',
                      'Active Percentage', 'Churn Rate'],
            'Value': [
                report['summary']['total_customers'],
                report['summary']['active_customers'],
                report['summary']['new_customers'],
                report['summary']['inactive_customers'],
                self.format_currency(report['summary']['total_revenue']),
                self.format_currency(report['summary']['avg_customer_value']),
                f"{report['summary']['active_percentage']:.1f}%",
                f"{report['churn_analysis']['churn_rate']:.1f}%"
            ]
        }
        dfs['Summary'] = pd.DataFrame(summary_data)
        
        # RFM Analysis DataFrame
        rfm_data = []
        for customer in report['rfm_analysis']:
            rfm_data.append({
                'Customer': customer['name'],
                'Email': customer['email'],
                'Recency': customer['recency'],
                'Frequency': customer['frequency'],
                'Monetary': self.format_currency(customer['monetary']),
                'RFM Score': customer['total_score'],
                'Segment': customer['segment_name']
            })
        dfs['RFM Analysis'] = pd.DataFrame(rfm_data)
        
        # Top Customers DataFrame
        top_customers_data = []
        for customer in report['top_customers']:
            top_customers_data.append({
                'Rank': customer['rank'],
                'Customer': customer['customer'],
                'Total Spent': self.format_currency(customer['total_spent']),
                'Purchases': customer['purchase_count'],
                'Avg. Purchase': self.format_currency(customer['avg_purchase']),
                'Membership': customer['membership'],
                'Loyalty Points': customer['loyalty_points'],
                'Last Purchase': customer['last_purchase'].strftime('%Y-%m-%d') if customer['last_purchase'] else 'Never',
                'Favorite Products': ', '.join(customer['favorite_products'])
            })
        dfs['Top Customers'] = pd.DataFrame(top_customers_data)
        
        # Segmentation DataFrame
        segmentation_data = []
        for segment, data in report['segmentation'].items():
            segmentation_data.append({
                'Segment': segment,
                'Customers': data['count'],
                'Percentage': f"{data.get('percentage', 0):.1f}%",
                'Total Revenue': self.format_currency(data['total_revenue']),
                'Avg. Revenue': self.format_currency(data.get('avg_revenue', 0))
            })
        dfs['Segmentation'] = pd.DataFrame(segmentation_data)
        
        return dfs