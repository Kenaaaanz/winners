from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

class DashboardWidget(models.Model):
    """User-customizable dashboard widgets"""
    WIDGET_TYPES = [
        ('SALES_CHART', 'Sales Chart'),
        ('REVENUE_CARD', 'Revenue Card'),
        ('TOP_PRODUCTS', 'Top Products'),
        ('RECENT_SALES', 'Recent Sales'),
        ('LOW_STOCK', 'Low Stock Alert'),
        ('CUSTOMER_METRICS', 'Customer Metrics'),
        ('PROFIT_CHART', 'Profit Chart'),
        ('INVENTORY_VALUE', 'Inventory Value'),
    ]
    
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    widget_type = models.CharField(max_length=50, choices=WIDGET_TYPES)
    title = models.CharField(max_length=100)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4)  # In grid columns (1-12)
    height = models.IntegerField(default=4)  # In grid rows
    settings = models.JSONField(default=dict)  # Widget-specific settings
    is_visible = models.BooleanField(default=True)
    refresh_interval = models.IntegerField(default=300)  # Seconds
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'widget_type']
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"{self.user.username}'s {self.get_widget_type_display()}"

class SavedReport(models.Model):
    """User-saved reports"""
    REPORT_TYPES = [
        ('SALES', 'Sales Report'),
        ('PRODUCT', 'Product Performance'),
        ('CUSTOMER', 'Customer Analysis'),
        ('INVENTORY', 'Inventory Report'),
        ('FINANCIAL', 'Financial Report'),
        ('CUSTOM', 'Custom Report'),
    ]
    
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parameters = models.JSONField(default=dict)  # Report parameters/filters
    columns = models.JSONField(default=list)  # Selected columns
    sorting = models.JSONField(default=dict)  # Sorting preferences
    chart_config = models.JSONField(default=dict, blank=True)  # Chart configuration
    is_shared = models.BooleanField(default=False)
    shared_with = models.ManyToManyField('auth.User', related_name='shared_reports', blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    run_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"
    
    def mark_run(self):
        self.last_run = timezone.now()
        self.run_count += 1
        self.save()

class ReportSchedule(models.Model):
    """Scheduled report generation"""
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]
    
    OUTPUT_FORMATS = [
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
        ('HTML', 'HTML'),
    ]
    
    name = models.CharField(max_length=200)
    report = models.ForeignKey(SavedReport, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    output_format = models.CharField(max_length=10, choices=OUTPUT_FORMATS, default='PDF')
    recipients = models.TextField(help_text="Comma-separated email addresses")
    next_run = models.DateTimeField()
    last_run = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['next_run']
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"
    
    def calculate_next_run(self):
        from datetime import timedelta
        
        now = timezone.now()
        if self.frequency == 'DAILY':
            next_run = now + timedelta(days=1)
        elif self.frequency == 'WEEKLY':
            next_run = now + timedelta(weeks=1)
        elif self.frequency == 'MONTHLY':
            # Add approximately one month
            next_run = now + timedelta(days=30)
        elif self.frequency == 'QUARTERLY':
            next_run = now + timedelta(days=90)
        elif self.frequency == 'YEARLY':
            next_run = now + timedelta(days=365)
        else:
            next_run = now + timedelta(days=1)
        
        return next_run.replace(hour=9, minute=0, second=0, microsecond=0)

class BusinessMetric(models.Model):
    """Key business metrics tracking"""
    METRIC_TYPES = [
        ('REVENUE', 'Revenue'),
        ('PROFIT', 'Profit'),
        ('TRANSACTIONS', 'Transactions'),
        ('AVG_TICKET', 'Average Ticket Size'),
        ('CONVERSION', 'Conversion Rate'),
        ('CUSTOMER_COUNT', 'Customer Count'),
        ('LOYALTY', 'Loyalty Points'),
        ('INVENTORY_TURNOVER', 'Inventory Turnover'),
        ('GROSS_MARGIN', 'Gross Margin'),
        ('NET_MARGIN', 'Net Margin'),
    ]
    
    PERIOD_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    period_date = models.DateField()
    value = models.DecimalField(max_digits=12, decimal_places=2)
    target = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    previous_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    growth = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Percentage
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['metric_type', 'period', 'period_date']
        ordering = ['-period_date', 'metric_type']
        indexes = [
            models.Index(fields=['metric_type', 'period_date']),
            models.Index(fields=['period', 'period_date']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.period_date} ({self.period})"
    
    @property
    def achievement_percentage(self):
        if self.target and self.target > 0:
            return (self.value / self.target) * 100
        return None

class KPI(models.Model):
    """Key Performance Indicators"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    metric = models.CharField(max_length=100)  # Field or calculation
    target = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50)  # KES, %, units, etc.
    frequency = models.CharField(max_length=20, choices=BusinessMetric.PERIOD_CHOICES)
    department = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    weight = models.IntegerField(default=1)  # Importance weight (1-10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['department', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.department})"
    
    @property
    def current_value(self):
        # Get latest metric value
        latest = BusinessMetric.objects.filter(
            metric_type=self.metric,
            period=self.frequency
        ).order_by('-period_date').first()
        
        return latest.value if latest else Decimal('0')

class Forecast(models.Model):
    """Business forecasts"""
    FORECAST_TYPES = [
        ('SALES', 'Sales'),
        ('DEMAND', 'Demand'),
        ('REVENUE', 'Revenue'),
        ('INVENTORY', 'Inventory'),
        ('EXPENSES', 'Expenses'),
    ]
    
    MODEL_CHOICES = [
        ('MOVING_AVERAGE', 'Moving Average'),
        ('EXPONENTIAL_SMOOTHING', 'Exponential Smoothing'),
        ('ARIMA', 'ARIMA'),
        ('LINEAR_REGRESSION', 'Linear Regression'),
        ('SEASONAL', 'Seasonal'),
    ]
    
    forecast_type = models.CharField(max_length=20, choices=FORECAST_TYPES)
    model = models.CharField(max_length=30, choices=MODEL_CHOICES)
    period = models.CharField(max_length=20, choices=BusinessMetric.PERIOD_CHOICES)
    forecast_date = models.DateField()
    forecast_value = models.DecimalField(max_digits=12, decimal_places=2)
    confidence_interval_lower = models.DecimalField(max_digits=12, decimal_places=2)
    confidence_interval_upper = models.DecimalField(max_digits=12, decimal_places=2)
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Percentage
    parameters = models.JSONField(default=dict)  #Model-specific parameters
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['forecast_type', 'period', 'forecast_date']
        ordering = ['forecast_type', '-forecast_date']
    
    def __str__(self):
        return f"{self.get_forecast_type_display()} Forecast for {self.forecast_date}"
    
    @property
    def confidence_range(self):
        return self.confidence_interval_upper - self.confidence_interval_lower

class AnalyticsCache(models.Model):
    """Cache for expensive analytics queries"""
    cache_key = models.CharField(max_length=500, unique=True)
    data = models.JSONField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['cache_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return self.cache_key
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

class UserDashboardPreference(models.Model):
    """User preferences for analytics dashboard"""
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    theme = models.CharField(max_length=20, default='light', choices=[
        ('LIGHT', 'Light'),
        ('DARK', 'Dark'),
        ('AUTO', 'Auto'),
    ])
    default_period = models.CharField(max_length=20, default='month', choices=[
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
    ])
    refresh_interval = models.IntegerField(default=300)  # Seconds
    show_animations = models.BooleanField(default=True)
    show_tooltips = models.BooleanField(default=True)
    default_currency = models.CharField(max_length=10, default='KES')
    number_format = models.CharField(max_length=50, default='en-KE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Dashboard Preferences"