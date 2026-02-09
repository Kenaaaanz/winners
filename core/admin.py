from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    Profile, Category, Brand, Supplier, Product, Customer,
    Sale, SaleItem, StockTransaction, PurchaseOrder, PurchaseOrderItem,
    Expense, Notification
)

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile',)
    
    def get_role(self, instance):
        return instance.profile.role
    get_role.short_description = 'Role'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'brand', 'quantity', 'selling_price', 'is_active')
    list_filter = ('category', 'brand', 'product_type', 'is_active')
    search_fields = ('sku', 'name', 'barcode')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('sku', 'barcode', 'name', 'description', 'category', 'brand', 'product_type', 'image')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price')
        }),
        ('Inventory', {
            'fields': ('quantity', 'low_stock_threshold', 'reorder_quantity', 'expiry_date', 'batch_number', 'supplier')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('product_name', 'product_sku', 'unit_price', 'cost_price', 'total_price')

class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'total', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('invoice_number', 'customer__first_name', 'customer__last_name', 'mpesa_receipt')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    inlines = [SaleItemInline]
    fieldsets = (
        ('Sale Information', {
            'fields': ('invoice_number', 'customer', 'cashier', 'notes')
        }),
        ('Totals', {
            'fields': ('subtotal', 'discount_amount', 'discount_percentage', 'tax_amount', 'tax_rate', 'total')
        }),
        ('Payment', {
            'fields': ('payment_method', 'amount_paid', 'change_given', 'mpesa_receipt', 'mpesa_transaction_id', 'mpesa_phone')
        }),
        ('Loyalty', {
            'fields': ('loyalty_points_used', 'loyalty_points_earned')
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'updated_at')
        }),
    )

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'membership_type', 'total_spent', 'date_joined')
    list_filter = ('membership_type', 'is_active', 'date_joined')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    readonly_fields = ('customer_id', 'date_joined', 'last_purchase')
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'gender', 'date_of_birth')
        }),
        ('Address', {
            'fields': ('address', 'city')
        }),
        ('Membership', {
            'fields': ('membership_type', 'loyalty_points', 'total_spent', 'preferred_payment')
        }),
        ('Additional', {
            'fields': ('notes', 'is_active', 'customer_id', 'date_joined', 'last_purchase')
        }),
    )

class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction_type', 'quantity', 'previous_quantity', 'new_quantity', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('product__name', 'reference', 'notes')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'order_date', 'expected_date', 'status', 'total_amount')
    list_filter = ('status', 'order_date', 'supplier')
    search_fields = ('po_number', 'supplier__name', 'notes')
    readonly_fields = ('po_number', 'created_at', 'updated_at')
    inlines = [PurchaseOrderItemInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('po_number', 'supplier', 'order_date', 'expected_date', 'notes')
        }),
        ('Financial', {
            'fields': ('total_amount',)
        }),
        ('Status', {
            'fields': ('status', 'created_by', 'created_at', 'updated_at')
        }),
    )

# Register all models
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Supplier)
admin.site.register(Product, ProductAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Sale, SaleAdmin)
admin.site.register(StockTransaction, StockTransactionAdmin)
admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
admin.site.register(Expense)
admin.site.register(Notification)

# Customize admin site
admin.site.site_header = "Winners Cosmetics Management System"
admin.site.site_title = "Winners Cosmetics Admin"
admin.site.index_title = "Welcome to Winners Cosmetics Administration"