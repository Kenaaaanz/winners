from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid

class InventorySettings(models.Model):
    """Store-level inventory settings"""
    low_stock_threshold_default = models.IntegerField(default=10)
    reorder_quantity_default = models.IntegerField(default=25)
    enable_expiry_tracking = models.BooleanField(default=True)
    expiry_warning_days = models.IntegerField(default=30)
    enable_barcode_scanning = models.BooleanField(default=True)
    auto_generate_barcode = models.BooleanField(default=False)
    barcode_prefix = models.CharField(max_length=10, default='BEAU')
    enable_batch_tracking = models.BooleanField(default=True)
    default_supplier = models.ForeignKey('core.Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    inventory_count_frequency = models.CharField(
        max_length=20,
        choices=[
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly'),
            ('QUARTERLY', 'Quarterly')
        ],
        default='MONTHLY'
    )
    
    class Meta:
        verbose_name_plural = "Inventory Settings"
    
    def __str__(self):
        return "Inventory Settings"

class ProductLocation(models.Model):
    """Physical location of products in store"""
    name = models.CharField(max_length=100)
    aisle = models.CharField(max_length=50, blank=True)
    shelf = models.CharField(max_length=50, blank=True)
    position = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    capacity = models.IntegerField(default=0)
    current_occupancy = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['aisle', 'shelf', 'position']
    
    def __str__(self):
        return f"{self.aisle} - {self.shelf} - {self.position}"
    
    @property
    def occupancy_percentage(self):
        if self.capacity > 0:
            return (self.current_occupancy / self.capacity) * 100
        return 0

class StockTake(models.Model):
    """Physical stock count"""
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ADJUSTED', 'Adjusted'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    reference = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    date = models.DateField(default=timezone.now)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    location = models.ForeignKey(ProductLocation, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey('core.Category', on_delete=models.SET_NULL, null=True, blank=True)
    counted_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    verified_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_stocktakes')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Stock Take {self.reference}"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"ST-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def items_count(self):
        return self.items.count()
    
    @property
    def variance_value(self):
        total = Decimal('0')
        for item in self.items.all():
            total += item.variance_value
        return total

class StockTakeItem(models.Model):
    """Individual items in stock take"""
    stock_take = models.ForeignKey(StockTake, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('core.Product', on_delete=models.CASCADE)
    expected_quantity = models.IntegerField()
    counted_quantity = models.IntegerField()
    variance = models.IntegerField(default=0)  # counted - expected
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['stock_take', 'product']
    
    def __str__(self):
        return f"{self.product.name} - Expected: {self.expected_quantity}, Counted: {self.counted_quantity}"
    
    def save(self, *args, **kwargs):
        self.variance = self.counted_quantity - self.expected_quantity
        super().save(*args, **kwargs)
    
    @property
    def variance_value(self):
        return abs(self.variance) * self.product.cost_price
    
    @property
    def variance_percentage(self):
        if self.expected_quantity > 0:
            return (abs(self.variance) / self.expected_quantity) * 100
        return 100 if self.variance != 0 else 0

class ReorderRecommendation(models.Model):
    """System-generated reorder recommendations"""
    PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]
    
    product = models.ForeignKey('core.Product', on_delete=models.CASCADE)
    current_stock = models.IntegerField()
    recommended_quantity = models.IntegerField()
    reason = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', '-generated_at']
    
    def __str__(self):
        return f"Reorder for {self.product.name} - {self.priority}"
    
    @property
    def days_of_supply(self):
        # Calculate based on average daily sales
        from datetime import timedelta
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_sales = self.product.saleitem_set.filter(
            sale__created_at__gte=thirty_days_ago
        ).aggregate(
            avg_daily=models.Avg('quantity')
        )['avg_daily'] or 0
        
        if daily_sales > 0:
            return self.current_stock / daily_sales
        return float('inf')

class InventoryAlert(models.Model):
    """System inventory alerts"""
    TYPE_CHOICES = [
        ('LOW_STOCK', 'Low Stock'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('EXPIRING_SOON', 'Expiring Soon'),
        ('EXPIRED', 'Expired'),
        ('OVERSTOCK', 'Overstock'),
        ('SLOW_MOVING', 'Slow Moving'),
        ('STOCK_TAKE', 'Stock Take Required'),
    ]
    
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    product = models.ForeignKey('core.Product', on_delete=models.CASCADE)
    message = models.TextField()
    data = models.JSONField(default=dict)  # Additional alert data
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-severity', '-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.product.name}"
    
    @property
    def age_in_days(self):
        return (timezone.now() - self.created_at).days

class InventoryAuditLog(models.Model):
    """Audit log for inventory changes"""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('ADJUST', 'Adjust'),
        ('TRANSFER', 'Transfer'),
        ('COUNT', 'Count'),
    ]
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    changes = models.JSONField()  # Stores field changes
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} {self.model_name} #{self.object_id} by {self.user}"