from django.urls import path
from . import views

urlpatterns = [
    # Analytics Dashboard
    path('', views.analytics_dashboard, name='analytics_dashboard'),
    
    # Reports
    path('sales/', views.sales_report, name='sales_report'),
    path('products/', views.product_performance, name='product_performance'),
    path('customers/', views.customer_insights, name='customer_insights'),
    path('inventory/', views.inventory_report, name='inventory_report'),
    path('financial/', views.financial_report, name='financial_report'),
    path('custom/', views.custom_report, name='custom_report'),
    
    # Data Export
    path('export/pdf/', views.export_report_pdf, name='export_report_pdf'),
    path('chart-data/', views.sales_chart_data, name='sales_chart_data'),
]