from django.urls import path
from . import views

urlpatterns = [
    # POS Interface
    path('', views.pos_dashboard, name='pos_dashboard'),
    
    # Cart endpoints
    path('cart/', views.get_cart, name='get_cart'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    
    # Customer endpoints
    path('customers/create/', views.create_customer, name='create_customer'),
    
    # Sales processing and management
    path('sales/process/', views.process_sale, name='process_sale'),
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:sale_id>/receipt/', views.print_receipt, name='print_receipt'),
    path('sales/daily/', views.daily_sales_report, name='daily_sales'),
    
    # M-Pesa Integration
    path('mpesa-callback/', views.mpesa_callback, name='mpesa_callback'),
]