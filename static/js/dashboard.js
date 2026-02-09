// Dashboard JavaScript
class DashboardManager {
    constructor() {
        this.charts = {};
        this.widgets = {};
        this.initialize();
    }
    
    initialize() {
        this.setupEventListeners();
        this.loadDashboardData();
        this.setupAutoRefresh();
        this.setupWidgetDragAndDrop();
        this.setupThemeToggle();
    }
    
    setupEventListeners() {
        // Refresh button
        $('#refreshDashboard').on('click', () => this.loadDashboardData());
        
        // Date range picker
        $('.dashboard-date-range').on('change', () => this.loadDashboardData());
        
        // Widget collapse/expand
        $('.widget-collapse-btn').on('click', function() {
            const widget = $(this).closest('.dashboard-widget');
            const content = widget.find('.widget-content');
            content.slideToggle();
            $(this).find('i').toggleClass('fa-chevron-down fa-chevron-up');
        });
        
        // Widget close
        $('.widget-close-btn').on('click', function() {
            const widget = $(this).closest('.dashboard-widget');
            widget.fadeOut(300, () => widget.remove());
        });
        
        // Export buttons
        $('.export-dashboard').on('click', function() {
            const format = $(this).data('format');
            DashboardManager.exportDashboard(format);
        });
        
        // Quick filter buttons
        $('.quick-filter').on('click', function() {
            const period = $(this).data('period');
            DashboardManager.applyQuickFilter(period);
        });
    }
    
    loadDashboardData() {
        this.showLoading();
        
        // Load dashboard stats
        $.ajax({
            url: '/api/dashboard/stats/',
            method: 'GET',
            success: (response) => this.updateDashboardStats(response),
            error: (error) => this.handleLoadError(error)
        });
        
        // Load sales chart data
        $.ajax({
            url: '/api/dashboard/sales-chart/',
            method: 'GET',
            success: (response) => this.updateSalesChart(response),
            error: (error) => console.error('Chart load error:', error)
        });
        
        // Load recent activities
        $.ajax({
            url: '/api/dashboard/recent-activities/',
            method: 'GET',
            success: (response) => this.updateRecentActivities(response),
            error: (error) => console.error('Activities load error:', error)
        });
        
        // Load notifications
        $.ajax({
            url: '/api/dashboard/notifications/',
            method: 'GET',
            success: (response) => this.updateNotifications(response),
            error: (error) => console.error('Notifications load error:', error)
        });
    }
    
    updateDashboardStats(stats) {
        // Update total sales
        $('#totalSales').text(`KES ${stats.total_sales.toLocaleString('en-KE', {minimumFractionDigits: 2})}`);
        $('#salesChange').html(`
            <i class="fas fa-arrow-${stats.sales_change >= 0 ? 'up' : 'down'}"></i>
            ${Math.abs(stats.sales_change)}%
        `).toggleClass('positive negative', stats.sales_change >= 0);
        
        // Update total customers
        $('#totalCustomers').text(stats.total_customers.toLocaleString());
        $('#customersChange').html(`
            <i class="fas fa-arrow-${stats.customers_change >= 0 ? 'up' : 'down'}"></i>
            ${Math.abs(stats.customers_change)}%
        `).toggleClass('positive negative', stats.customers_change >= 0);
        
        // Update total products
        $('#totalProducts').text(stats.total_products.toLocaleString());
        $('#productsChange').html(`
            <i class="fas fa-arrow-${stats.products_change >= 0 ? 'up' : 'down'}"></i>
            ${Math.abs(stats.products_change)}%
        `).toggleClass('positive negative', stats.products_change >= 0);
        
        // Update low stock
        $('#lowStockCount').text(stats.low_stock_count.toLocaleString());
        $('#lowStockChange').html(`
            <i class="fas fa-arrow-${stats.low_stock_change >= 0 ? 'up' : 'down'}"></i>
            ${Math.abs(stats.low_stock_change)}%
        `).toggleClass('positive negative', stats.low_stock_change <= 0);
        
        // Update today's sales
        $('#todaySales').text(`KES ${stats.today_sales.toLocaleString('en-KE', {minimumFractionDigits: 2})}`);
        $('#todayTransactions').text(`${stats.today_transactions} transactions`);
        
        // Update conversion rate
        $('#conversionRate').text(`${stats.conversion_rate.toFixed(1)}%`);
        $('#conversionChange').html(`
            <i class="fas fa-arrow-${stats.conversion_change >= 0 ? 'up' : 'down'}"></i>
            ${Math.abs(stats.conversion_change)}%
        `).toggleClass('positive negative', stats.conversion_change >= 0);
        
        // Update average transaction
        $('#avgTransaction').text(`KES ${stats.avg_transaction.toLocaleString('en-KE', {minimumFractionDigits: 2})}`);
        
        this.hideLoading();
    }
    
    updateSalesChart(chartData) {
        const ctx = document.getElementById('salesChart')?.getContext('2d');
        if (!ctx) return;
        
        if (this.charts.salesChart) {
            this.charts.salesChart.destroy();
        }
        
        this.charts.salesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Revenue (KES)',
                    data: chartData.revenue,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Transactions',
                    data: chartData.transactions,
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46, 204, 113, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Sales Performance'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Revenue (KES)'
                        },
                        ticks: {
                            callback: function(value) {
                                return 'KES ' + value.toLocaleString();
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Transaction Count'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }
    
    updateRecentActivities(activities) {
        const container = $('#recentActivities');
        if (!container.length || !activities) return;
        
        let html = '';
        activities.forEach(activity => {
            html += `
                <div class="activity-item">
                    <div class="activity-icon bg-${activity.type}">
                        <i class="fas fa-${activity.icon}"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">${activity.title}</div>
                        <div class="activity-description">${activity.description}</div>
                        <div class="activity-time">${activity.time}</div>
                    </div>
                </div>
            `;
        });
        
        container.html(html || '<div class="text-muted text-center py-3">No recent activities</div>');
    }
    
    updateNotifications(notifications) {
        const container = $('#dashboardNotifications');
        const badge = $('#notificationBadge');
        
        if (!container.length || !notifications) return;
        
        let html = '';
        let unreadCount = 0;
        
        notifications.forEach(notification => {
            if (!notification.read) unreadCount++;
            
            html += `
                <div class="notification-item ${notification.read ? '' : 'unread'}">
                    <div class="notification-icon">
                        <i class="fas fa-${notification.icon}"></i>
                    </div>
                    <div class="notification-content">
                        <div class="notification-title">${notification.title}</div>
                        <div class="notification-message">${notification.message}</div>
                        <div class="notification-time">${notification.time}</div>
                    </div>
                    ${!notification.read ? '<div class="notification-dot"></div>' : ''}
                </div>
            `;
        });
        
        container.html(html || '<div class="text-muted text-center py-3">No notifications</div>');
        badge.text(unreadCount).toggle(unreadCount > 0);
    }
    
    showLoading() {
        $('.dashboard-loading').show();
        $('.dashboard-content').addClass('loading');
    }
    
    hideLoading() {
        $('.dashboard-loading').hide();
        $('.dashboard-content').removeClass('loading');
    }
    
    handleLoadError(error) {
        console.error('Dashboard load error:', error);
        this.hideLoading();
        
        // Show error message
        showToast('Failed to load dashboard data. Please try again.', 'error');
    }
    
    setupAutoRefresh() {
        // Auto-refresh every 2 minutes
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.loadDashboardData();
            }
        }, 120000);
    }
    
    setupWidgetDragAndDrop() {
        // Only enable on desktop
        if (window.innerWidth < 768) return;
        
        $('.dashboard-widget').draggable({
            handle: '.widget-header',
            containment: '.dashboard-grid',
            stack: '.dashboard-widget',
            revert: 'invalid',
            cursor: 'move'
        });
        
        $('.dashboard-grid').droppable({
            accept: '.dashboard-widget',
            drop: function(event, ui) {
                const widget = ui.draggable;
                const grid = $(this);
                
                // Update widget position in localStorage
                DashboardManager.saveWidgetPosition(widget.attr('id'));
            }
        });
    }
    
    setupThemeToggle() {
        $('#themeToggle').on('click', function() {
            const isDark = $('body').hasClass('dark-theme');
            
            if (isDark) {
                $('body').removeClass('dark-theme');
                localStorage.setItem('dashboard-theme', 'light');
                $(this).html('<i class="fas fa-moon"></i>');
            } else {
                $('body').addClass('dark-theme');
                localStorage.setItem('dashboard-theme', 'dark');
                $(this).html('<i class="fas fa-sun"></i>');
            }
            
            // Update charts for theme
            DashboardManager.updateChartsForTheme();
        });
        
        // Load saved theme
        const savedTheme = localStorage.getItem('dashboard-theme');
        if (savedTheme === 'dark') {
            $('body').addClass('dark-theme');
            $('#themeToggle').html('<i class="fas fa-sun"></i>');
        }
    }
    
    static exportDashboard(format) {
        switch(format) {
            case 'pdf':
                window.open('/api/dashboard/export/pdf/', '_blank');
                break;
            case 'excel':
                window.location.href = '/api/dashboard/export/excel/';
                break;
            case 'csv':
                window.location.href = '/api/dashboard/export/csv/';
                break;
        }
    }
    
    static applyQuickFilter(period) {
        const now = new Date();
        let startDate, endDate;
        
        switch(period) {
            case 'today':
                startDate = endDate = now.toISOString().split('T')[0];
                break;
            case 'week':
                startDate = new Date(now.setDate(now.getDate() - 7)).toISOString().split('T')[0];
                endDate = new Date().toISOString().split('T')[0];
                break;
            case 'month':
                startDate = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
                endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0];
                break;
            case 'year':
                startDate = new Date(now.getFullYear(), 0, 1).toISOString().split('T')[0];
                endDate = new Date(now.getFullYear(), 11, 31).toISOString().split('T')[0];
                break;
        }
        
        $('input[name="start_date"]').val(startDate);
        $('input[name="end_date"]').val(endDate);
        
        // Trigger form submit
        $('.dashboard-filter-form').submit();
    }
    
    static saveWidgetPosition(widgetId) {
        const positions = JSON.parse(localStorage.getItem('widget-positions') || '{}');
        positions[widgetId] = new Date().toISOString();
        localStorage.setItem('widget-positions', JSON.stringify(positions));
    }
    
    static updateChartsForTheme() {
        const isDark = $('body').hasClass('dark-theme');
        const textColor = isDark ? '#ecf0f1' : '#2c3e50';
        const gridColor = isDark ? '#7f8c8d' : '#dee2e6';
        
        // Update all charts
        Object.values(window.dashboardManager?.charts || {}).forEach(chart => {
            if (chart.options?.scales) {
                Object.values(chart.options.scales).forEach(scale => {
                    if (scale.ticks) {
                        scale.ticks.color = textColor;
                    }
                    if (scale.grid) {
                        scale.grid.color = gridColor;
                    }
                });
                
                if (chart.options.plugins?.legend?.labels) {
                    chart.options.plugins.legend.labels.color = textColor;
                }
            }
            chart.update();
        });
    }
}

// Initialize dashboard when page loads
$(document).ready(function() {
    window.dashboardManager = new DashboardManager();
    
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Initialize popovers
    $('[data-toggle="popover"]').popover();
    
    // Real-time updates via WebSocket (if available)
    if (typeof WebSocket !== 'undefined') {
        DashboardManager.setupWebSocket();
    }
});