from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta, date
import json
from decimal import Decimal

from .models import (
    Profile, Customer, Product, Sale, SaleItem, StockTransaction,
    PurchaseOrder, Expense, Notification
)
from .forms import (
    UserRegistrationForm, ProfileUpdateForm, CustomerForm,
    ProductForm, ExpenseForm, DateRangeForm
)
from .reports import generate_sales_report_pdf, generate_inventory_report_pdf

def is_manager(user):
    return user.groups.filter(name='Manager').exists() or user.is_superuser

def is_cashier(user):
    return user.groups.filter(name='Cashier').exists() or user.is_superuser

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid():
            u_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        u_form = ProfileUpdateForm(instance=request.user.profile)
    
    # Get user notifications
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:10]
    
    context = {
        'u_form': u_form,
        'notifications': notifications,
    }
    return render(request, 'core/profile.html', context)

@login_required
def dashboard(request):
    # Get today's date
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Get statistics
    total_sales_today = Sale.objects.filter(
        created_at__date=today,
        status='COMPLETED'
    ).aggregate(total=Sum('total'))['total'] or 0
    
    total_sales_week = Sale.objects.filter(
        created_at__date__gte=week_ago,
        status='COMPLETED'
    ).aggregate(total=Sum('total'))['total'] or 0
    
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    
    # Get low stock products
    low_stock_products = Product.objects.filter(
        quantity__lte=F('low_stock_threshold'),
        is_active=True
    )[:5]
    
    # Get recent sales
    recent_sales = Sale.objects.filter(
        status='COMPLETED'
    ).order_by('-created_at')[:10]
    
    # Get sales chart data
    sales_data = []
    for i in range(7):
        day = today - timedelta(days=i)
        day_sales = Sale.objects.filter(
            created_at__date=day,
            status='COMPLETED'
        ).aggregate(total=Sum('total'))['total'] or 0
        sales_data.append({
            'day': day.strftime('%a'),
            'sales': float(day_sales)
        })
    sales_data.reverse()
    
    # Get top products
    top_products = Product.objects.annotate(
        total_sold=Sum('saleitem__quantity')
    ).filter(total_sold__gt=0).order_by('-total_sold')[:5]
    
    context = {
        'total_sales_today': total_sales_today,
        'total_sales_week': total_sales_week,
        'total_customers': total_customers,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'recent_sales': recent_sales,
        'sales_data': sales_data,
        'top_products': top_products,
    }
    
    return render(request, 'core/dashboard.html', context)

# Customer Views
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'core/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.all().order_by('-date_joined')
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        # Filter by membership type
        membership = self.request.GET.get('membership', '')
        if membership:
            queryset = queryset.filter(membership_type=membership)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['membership_types'] = Customer.MEMBERSHIP_TYPES
        return context

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'core/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        # Get customer's purchase history
        purchases = Sale.objects.filter(
            customer=customer,
            status='COMPLETED'
        ).order_by('-created_at')[:20]
        
        # Calculate statistics
        total_purchases = purchases.count()
        total_spent = purchases.aggregate(total=Sum('total'))['total'] or 0
        
        context.update({
            'purchases': purchases,
            'total_purchases': total_purchases,
            'total_spent': total_spent,
        })
        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'
    success_url = reverse_lazy('customer_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer created successfully!')
        return super().form_valid(form)

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('customer_detail', kwargs={'pk': self.object.pk})

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})

@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})