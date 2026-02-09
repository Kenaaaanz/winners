from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, F, Q
from django.core.paginator import Paginator
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.forms import inlineformset_factory
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import datetime, timedelta
import csv

from core.models import Product, StockTransaction, PurchaseOrder, PurchaseOrderItem, Supplier
from core.forms import ProductForm, PurchaseOrderForm
from core.reports import generate_inventory_report_pdf
from core.permissions import require_role

# Define the formset early so it can be used in class-based views
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    fields=('product', 'quantity', 'unit_cost'),
    extra=1,
    can_delete=True
)

@require_role('ADMIN', 'MANAGER')
@login_required
def product_list(request):
    """List all products"""
    products = Product.objects.all().order_by('name')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(barcode__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        products = products.filter(category__id=category)
    
    # Filter by brand
    brand = request.GET.get('brand')
    if brand:
        products = products.filter(brand__id=brand)
    
    # Filter by stock status
    stock_status = request.GET.get('stock_status')
    if stock_status == 'low':
        products = products.filter(quantity__lte=F('low_stock_threshold'))
    elif stock_status == 'out':
        products = products.filter(quantity=0)
    elif stock_status == 'in':
        products = products.filter(quantity__gt=0)
    
    # Pagination
    paginator = Paginator(products, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories and brands for filters
    from core.models import Category, Brand
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'categories': categories,
        'brands': brands,
        'stock_status': stock_status,
        'category_id': int(category) if category else None,
        'brand_id': int(brand) if brand else None,
    }
    
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_detail(request, pk):
    """View product details"""
    product = get_object_or_404(Product, pk=pk)
    
    # Get stock transactions
    transactions = StockTransaction.objects.filter(
        product=product
    ).order_by('-created_at')[:20]
    
    # Get sales history
    sales_history = product.saleitem_set.select_related('sale').order_by('-sale__created_at')[:20]
    
    context = {
        'product': product,
        'transactions': transactions,
        'sales_history': sales_history,
    }
    
    return render(request, 'inventory/product_detail.html', context)

@login_required
def product_create(request):
    """Create new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            
            messages.success(request, 'Product created successfully!')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm()
    
    context = {'form': form}
    return render(request, 'inventory/product_form.html', context)
@require_role('ADMIN', 'MANAGER')
@login_required
def product_update(request, pk):
    """Update product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    
    context = {'form': form, 'product': product}
    return render(request, 'inventory/product_form.html', context)

@login_required
def stock_transactions(request):
    """View stock transaction history"""
    transactions = StockTransaction.objects.all().order_by('-created_at')
    
    # Filter by date
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        transactions = transactions.filter(
            created_at__date__range=[start_date, end_date]
        )
    
    # Filter by transaction type
    transaction_type = request.GET.get('transaction_type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Filter by product
    product_id = request.GET.get('product')
    if product_id:
        transactions = transactions.filter(product__id=product_id)
    
    # Pagination
    paginator = Paginator(transactions, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get products for filter
    products = Product.objects.all().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'transaction_types': StockTransaction.TRANSACTION_TYPES,
        'products': products,
        'start_date': start_date,
        'end_date': end_date,
        'transaction_type': transaction_type,
        'product_id': product_id,
    }
    
    return render(request, 'inventory/stock_transactions.html', context)

@login_required
def low_stock_report(request):
    """View low stock products"""
    low_stock_products = Product.objects.filter(
        quantity__lte=F('low_stock_threshold'),
        is_active=True
    ).order_by('quantity')
    
    # Calculate total value of low stock items
    total_value = sum(product.total_value for product in low_stock_products)
    
    context = {
        'products': low_stock_products,
        'total_count': low_stock_products.count(),
        'total_value': total_value,
    }
    
    return render(request, 'inventory/low_stock.html', context)

@require_role('ADMIN', 'MANAGER')
@login_required
def purchase_order_list(request):
    """List purchase orders"""
    orders = PurchaseOrder.objects.all().order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    # Filter by supplier
    supplier = request.GET.get('supplier')
    if supplier:
        orders = orders.filter(supplier__id=supplier)
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get suppliers for filter
    suppliers = Supplier.objects.all()
    
    context = {
        'page_obj': page_obj,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
        'suppliers': suppliers,
        'status': status,
        'supplier_id': int(supplier) if supplier else None,
    }
    
    return render(request, 'inventory/purchase_order_list.html', context)

@login_required
def purchase_order_detail(request, pk):
    """View purchase order details"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    context = {
        'order': order,
        'items': order.items.all(),
    }
    
    return render(request, 'inventory/purchase_order_detail.html', context)

@login_required
def export_inventory_csv(request):
    """Export inventory to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_{}.csv"'.format(
        datetime.now().strftime('%Y%m%d')
    )
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'SKU', 'Product Name', 'Category', 'Brand', 'Current Stock',
        'Cost Price', 'Selling Price', 'Total Value', 'Low Stock Threshold',
        'Reorder Quantity', 'Expiry Date', 'Supplier'
    ])
    
    # Write data
    products = Product.objects.all().order_by('category__name', 'name')
    for product in products:
        writer.writerow([
            product.sku,
            product.name,
            product.category.name if product.category else '',
            product.brand.name if product.brand else '',
            product.quantity,
            product.cost_price,
            product.selling_price,
            product.total_value,
            product.low_stock_threshold,
            product.reorder_quantity,
            product.expiry_date.strftime('%Y-%m-%d') if product.expiry_date else '',
            product.supplier.name if product.supplier else '',
        ])
    
    return response


class PurchaseOrderListView(ListView):
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_list.html'  # Make sure this is correct
    context_object_name = 'purchase_orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('supplier')
        
        # Apply filters
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(supplier__name__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-order_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add counts for stats
        queryset = self.get_queryset()
        context['total_orders'] = PurchaseOrder.objects.count()
        context['pending_count'] = PurchaseOrder.objects.filter(status='PENDING').count()
        context['approved_count'] = PurchaseOrder.objects.filter(status='APPROVED').count()
        context['received_count'] = PurchaseOrder.objects.filter(status='RECEIVED').count()
        
        return context

class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'inventory/purchase_order_form.html'
    success_url = reverse_lazy('purchase_order_list')
    
    def dispatch(self, request, *args, **kwargs):
        """Apply role-based access control"""
        if not hasattr(request.user, 'profile') or request.user.profile.role not in ['ADMIN', 'MANAGER']:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['formset'] = PurchaseOrderItemFormSet(self.request.POST)
        else:
            context['formset'] = PurchaseOrderItemFormSet()
        
        # Add recent orders for sidebar
        context['recent_orders'] = PurchaseOrder.objects.order_by('-created_at')[:5]
        
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            response = super().form_valid(form)
            formset.instance = self.object
            formset.save()
            messages.success(self.request, 'Purchase order created successfully!')
            return response
        else:
            return self.form_invalid(form)

class PurchaseOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'inventory/purchase_order_form.html'
    success_url = reverse_lazy('purchase_order_list')
    
    def dispatch(self, request, *args, **kwargs):
        """Apply role-based access control"""
        if not hasattr(request.user, 'profile') or request.user.profile.role not in ['ADMIN', 'MANAGER']:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['formset'] = PurchaseOrderItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['formset'] = PurchaseOrderItemFormSet(instance=self.object)
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            response = super().form_valid(form)
            formset.instance = self.object
            formset.save()
            messages.success(self.request, 'Purchase order updated successfully!')
            return response
        else:
            return self.form_invalid(form)