from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.db.models import Sum, Count, Avg, F, Q

from .models import Sale, SaleItem, Product, Customer, Expense, StockTransaction

def generate_receipt_pdf(sale):
    """Generate PDF receipt for a sale"""
    buffer = io.BytesIO()
    
    # Create PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(3 * inch, 8 * inch),  # Small receipt size
        rightMargin=0.25 * inch,
        leftMargin=0.25 * inch,
        topMargin=0.25 * inch,
        bottomMargin=0.25 * inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=9
    )
    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold'
    )
    center_style = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=8
    )
    
    # Content
    story = []
    
    # Shop header
    story.append(Paragraph("WINNERS COSMETICS SHOP", title_style))
    story.append(Paragraph("123 Winners Avenue, Nairobi", center_style))
    story.append(Paragraph("Phone: +254 700 000 000", center_style))
    story.append(Paragraph("Email: info@winnerscosmetics.co.ke", center_style))
    story.append(Spacer(1, 0.1 * inch))
    
    # Receipt header
    story.append(Paragraph(f"INVOICE: {sale.invoice_number}", bold_style))
    story.append(Paragraph(f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M')}", normal_style))
    story.append(Paragraph(f"Cashier: {sale.cashier.get_full_name()}", normal_style))
    
    if sale.customer:
        story.append(Paragraph(f"Customer: {sale.customer.full_name}", normal_style))
    
    story.append(Spacer(1, 0.1 * inch))
    
    # Items table
    items_data = []
    items_data.append(['Item', 'Qty', 'Price', 'Total'])
    
    for item in sale.items.all():
        items_data.append([
            item.product_name[:20],  # Truncate long names
            str(item.quantity),
            f"KES {item.unit_price:.2f}",
            f"KES {item.total_price:.2f}"
        ])
    
    items_table = Table(items_data, colWidths=[1.5*inch, 0.5*inch, 0.8*inch, 0.8*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    
    story.append(items_table)
    story.append(Spacer(1, 0.1 * inch))
    
    # Totals
    story.append(Paragraph(f"Subtotal: KES {sale.subtotal:.2f}", normal_style))
    
    if sale.discount_amount > 0:
        story.append(Paragraph(f"Discount: KES {sale.discount_amount:.2f}", normal_style))
    
    story.append(Paragraph(f"Tax ({sale.tax_rate}%): KES {sale.tax_amount:.2f}", normal_style))
    story.append(Paragraph(f"Total: KES {sale.total:.2f}", bold_style))
    story.append(Paragraph(f"Paid: KES {sale.amount_paid:.2f}", normal_style))
    
    if sale.change_given > 0:
        story.append(Paragraph(f"Change: KES {sale.change_given:.2f}", normal_style))
    
    story.append(Paragraph(f"Payment: {sale.get_payment_method_display()}", normal_style))
    
    if sale.mpesa_receipt:
        story.append(Paragraph(f"M-Pesa Receipt: {sale.mpesa_receipt}", normal_style))
    
    story.append(Spacer(1, 0.2 * inch))
    
    # Footer
    story.append(Paragraph("Thank you for your purchase!", center_style))
    story.append(Paragraph("Items cannot be returned after 7 days", center_style))
    story.append(Paragraph("Receipt is required for returns", center_style))
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_sales_report_pdf(start_date, end_date):
    """Generate PDF sales report"""
    buffer = io.BytesIO()
    
    # Create PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10
    )
    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold'
    )
    right_style = ParagraphStyle(
        'Right',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontSize=10
    )
    
    # Content
    story = []
    
    # Header
    story.append(Paragraph("SALES REPORT", title_style))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", normal_style))
    story.append(Paragraph(f"Generated: {date.today()}", normal_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Get sales data
    sales = Sale.objects.filter(
        created_at__date__range=[start_date, end_date],
        status='COMPLETED'
    ).order_by('-created_at')
    
    # Summary
    story.append(Paragraph("Summary", heading_style))
    
    summary_data = sales.aggregate(
        total_sales=Sum('total'),
        total_transactions=Count('id'),
        avg_sale=Avg('total'),
        total_discount=Sum('discount_amount'),
        total_tax=Sum('tax_amount')
    )
    
    summary_items = [
        ['Total Sales:', f"KES {summary_data['total_sales'] or 0:.2f}"],
        ['Total Transactions:', str(summary_data['total_transactions'] or 0)],
        ['Average Sale:', f"KES {summary_data['avg_sale'] or 0:.2f}"],
        ['Total Discount:', f"KES {summary_data['total_discount'] or 0:.2f}"],
        ['Total Tax:', f"KES {summary_data['total_tax'] or 0:.2f}"],
    ]
    
    summary_table = Table(summary_items, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Sales by payment method
    story.append(Paragraph("Sales by Payment Method", heading_style))
    
    payment_data = sales.values('payment_method').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('-total')
    
    payment_items = [['Payment Method', 'Count', 'Amount', 'Percentage']]
    total_sales = summary_data['total_sales'] or 1
    
    for payment in payment_data:
        percentage = (payment['total'] / total_sales * 100) if total_sales > 0 else 0
        payment_items.append([
            payment['payment_method'],
            str(payment['count']),
            f"KES {payment['total']:.2f}",
            f"{percentage:.1f}%"
        ])
    
    payment_table = Table(payment_items, colWidths=[1.5*inch, 1*inch, 1.5*inch, 1*inch])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    
    story.append(payment_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Top selling products
    story.append(Paragraph("Top Selling Products", heading_style))
    
    top_products = SaleItem.objects.filter(
        sale__created_at__date__range=[start_date, end_date]
    ).values(
        'product__name', 'product__sku'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('unit_price')),
        total_profit=Sum((F('unit_price') - F('cost_price')) * F('quantity'))
    ).order_by('-total_quantity')[:10]
    
    if top_products:
        product_items = [['Product', 'SKU', 'Quantity', 'Revenue', 'Profit']]
        
        for product in top_products:
            product_items.append([
                product['product__name'][:30],
                product['product__sku'],
                str(product['total_quantity']),
                f"KES {product['total_revenue']:.2f}",
                f"KES {product['total_profit']:.2f}"
            ])
        
        product_table = Table(product_items, colWidths=[2*inch, 1*inch, 0.8*inch, 1.2*inch, 1.2*inch])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(product_table)
    else:
        story.append(Paragraph("No sales data available for this period.", normal_style))
    
    story.append(Spacer(1, 0.3 * inch))
    
    # Daily sales breakdown
    story.append(Paragraph("Daily Sales Breakdown", heading_style))
    
    daily_sales = sales.annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('day')
    
    if daily_sales:
        daily_items = [['Date', 'Transactions', 'Total Sales']]
        
        for day in daily_sales:
            daily_items.append([
                day['day'].strftime('%Y-%m-%d'),
                str(day['count']),
                f"KES {day['total']:.2f}"
            ])
        
        daily_table = Table(daily_items, colWidths=[1.5*inch, 1*inch, 1.5*inch])
        daily_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(daily_table)
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_inventory_report_pdf():
    """Generate PDF inventory report"""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=9
    )
    
    story = []
    
    # Header
    story.append(Paragraph("INVENTORY REPORT", title_style))
    story.append(Paragraph(f"Generated: {date.today()}", normal_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Inventory summary
    products = Product.objects.filter(is_active=True).order_by('category__name', 'name')
    
    total_valuation = sum(p.total_value for p in products)
    total_items = products.count()
    low_stock_count = sum(1 for p in products if p.is_low_stock)
    
    story.append(Paragraph("Inventory Summary", heading_style))
    story.append(Paragraph(f"Total Products: {total_items}", normal_style))
    story.append(Paragraph(f"Total Valuation: KES {total_valuation:.2f}", normal_style))
    story.append(Paragraph(f"Low Stock Items: {low_stock_count}", normal_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Inventory details
    story.append(Paragraph("Product Details", heading_style))
    
    # Group by category
    categories = {}
    for product in products:
        category_name = product.category.name if product.category else "Uncategorized"
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append(product)
    
    for category_name, category_products in categories.items():
        story.append(Paragraph(category_name, styles['Heading3']))
        
        table_data = [['SKU', 'Product', 'Stock', 'Cost', 'Price', 'Value', 'Status']]
        
        for product in category_products:
            status = "Low" if product.is_low_stock else "OK" if product.quantity > 0 else "Out"
            table_data.append([
                product.sku,
                product.name[:30],
                str(product.quantity),
                f"KES {product.cost_price:.2f}",
                f"KES {product.selling_price:.2f}",
                f"KES {product.total_value:.2f}",
                status
            ])
        
        table = Table(table_data, colWidths=[0.8*inch, 1.8*inch, 0.5*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.1 * inch))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_financial_report_pdf(start_date, end_date):
    """Generate PDF financial report"""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10
    )
    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    # Header
    story.append(Paragraph("FINANCIAL REPORT", title_style))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", normal_style))
    story.append(Paragraph(f"Generated: {date.today()}", normal_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Get data
    sales = Sale.objects.filter(
        created_at__date__range=[start_date, end_date],
        status='COMPLETED'
    )
    expenses = Expense.objects.filter(date__range=[start_date, end_date])
    
    # Income Statement
    story.append(Paragraph("Income Statement", heading_style))
    
    total_revenue = sales.aggregate(total=Sum('total'))['total'] or 0
    cogs = SaleItem.objects.filter(
        sale__created_at__date__range=[start_date, end_date]
    ).aggregate(
        total=Sum(F('quantity') * F('cost_price'))
    )['total'] or 0
    gross_profit = total_revenue - cogs
    
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    net_profit = gross_profit - total_expenses
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    income_data = [
        ['Revenue', f"KES {total_revenue:.2f}"],
        ['Cost of Goods Sold', f"KES {cogs:.2f}"],
        ['Gross Profit', f"KES {gross_profit:.2f}"],
        ['', ''],
        ['Operating Expenses', f"KES {total_expenses:.2f}"],
        ['Net Profit', f"KES {net_profit:.2f}"],
        ['Profit Margin', f"{profit_margin:.1f}%"],
    ]
    
    income_table = Table(income_data, colWidths=[3*inch, 2*inch])
    income_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (1, 5), (1, 5), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 5), (1, 5), 11),
        ('GRID', (0, 0), (-1, 5), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(income_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Expense breakdown
    story.append(Paragraph("Expense Breakdown", heading_style))
    
    expense_data = expenses.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    if expense_data:
        expense_items = [['Category', 'Amount', 'Percentage']]
        for expense in expense_data:
            percentage = (expense['total'] / total_expenses * 100) if total_expenses > 0 else 0
            expense_items.append([
                expense['category'],
                f"KES {expense['total']:.2f}",
                f"{percentage:.1f}%"
            ])
        
        expense_table = Table(expense_items, colWidths=[2*inch, 1.5*inch, 1*inch])
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(expense_table)
    else:
        story.append(Paragraph("No expenses recorded for this period.", normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_customer_report_pdf():
    """Generate PDF customer report"""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=9
    )
    
    story = []
    
    # Header
    story.append(Paragraph("CUSTOMER REPORT", title_style))
    story.append(Paragraph(f"Generated: {date.today()}", normal_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Customer summary
    customers = Customer.objects.all().order_by('-total_spent')
    total_customers = customers.count()
    total_spent = sum(c.total_spent for c in customers)
    avg_spent = total_spent / total_customers if total_customers > 0 else 0
    
    story.append(Paragraph("Customer Summary", heading_style))
    story.append(Paragraph(f"Total Customers: {total_customers}", normal_style))
    story.append(Paragraph(f"Total Revenue from Customers: KES {total_spent:.2f}", normal_style))
    story.append(Paragraph(f"Average Spend per Customer: KES {avg_spent:.2f}", normal_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Top customers
    story.append(Paragraph("Top 20 Customers by Spending", heading_style))
    
    top_customers = customers[:20]
    
    if top_customers:
        customer_data = [['Name', 'Phone', 'Email', 'Member Since', 'Total Spent', 'Visits']]
        
        for customer in top_customers:
            customer_data.append([
                customer.full_name[:20],
                customer.phone,
                customer.email[:20],
                customer.date_joined.strftime('%Y-%m-%d'),
                f"KES {customer.total_spent:.2f}",
                str(customer.purchase_count)
            ])
        
        customer_table = Table(customer_data, colWidths=[1.2*inch, 1*inch, 1.2*inch, 0.8*inch, 1*inch, 0.5*inch])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        story.append(customer_table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()