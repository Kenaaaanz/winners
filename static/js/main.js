// Main JavaScript file for Winners Cosmetics System

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
    
    // Format currency inputs
    $('.currency-input').on('blur', function() {
        var value = parseFloat($(this).val());
        if (!isNaN(value)) {
            $(this).val(value.toFixed(2));
        }
    });
    
    // Confirm on delete actions
    $('.confirm-delete').on('click', function() {
        return confirm('Are you sure you want to delete this item? This action cannot be undone.');
    });
    
    // Toggle sidebar on mobile
    $('#sidebarToggle').on('click', function() {
        $('.sidebar').toggleClass('collapsed');
    });
    
    // Update cart count in navbar
    function updateCartCount() {
        $.ajax({
            url: '/api/cart/count/',
            method: 'GET',
            success: function(response) {
                $('#cartCount').text(response.count);
            }
        });
    }
    
    // Auto-refresh dashboard every 30 seconds
    if ($('#dashboard').length) {
        setInterval(function() {
            $.ajax({
                url: '/api/dashboard/stats/',
                method: 'GET',
                success: function(response) {
                    // Update stats on dashboard
                    $('#totalSales').text('KES ' + response.total_sales.toFixed(2));
                    $('#todaySales').text('KES ' + response.today_sales.toFixed(2));
                    $('#totalCustomers').text(response.total_customers);
                    $('#lowStockCount').text(response.low_stock_count);
                }
            });
        }, 30000);
    }
    
    // Search functionality
    $('#globalSearch').on('keyup', function() {
        var searchTerm = $(this).val().toLowerCase();
        if (searchTerm.length > 2) {
            $.ajax({
                url: '/api/search/',
                method: 'GET',
                data: { q: searchTerm },
                success: function(response) {
                    // Display search results
                    displaySearchResults(response);
                }
            });
        }
    });
    
    // Print functionality
    $('.print-btn').on('click', function() {
        window.print();
    });
    
    // Export functionality
    $('.export-btn').on('click', function() {
        var format = $(this).data('format');
        var url = $(this).data('url');
        
        if (format === 'pdf') {
            window.open(url, '_blank');
        } else if (format === 'csv') {
            window.location.href = url;
        } else if (format === 'excel') {
            window.location.href = url;
        }
    });
    
    // Date range picker
    if ($('.date-range-picker').length) {
        flatpickr('.date-range-picker', {
            mode: 'range',
            dateFormat: 'Y-m-d',
            maxDate: 'today'
        });
    }
    
    // Single date picker
    if ($('.date-picker').length) {
        flatpickr('.date-picker', {
            dateFormat: 'Y-m-d',
            maxDate: 'today'
        });
    }
    
    // Initialize DataTables
    if ($('.data-table').length) {
        $('.data-table').DataTable({
            pageLength: 25,
            responsive: true,
            order: [[0, 'desc']],
            language: {
                search: 'Search:',
                lengthMenu: 'Show _MENU_ entries',
                info: 'Showing _START_ to _END_ of _TOTAL_ entries',
                paginate: {
                    first: 'First',
                    last: 'Last',
                    next: 'Next',
                    previous: 'Previous'
                }
            }
        });
    }
    
    // Chart colors
    const chartColors = {
        primary: '#6c5ce7',
        secondary: '#a29bfe',
        success: '#00b894',
        danger: '#d63031',
        warning: '#fdcb6e',
        info: '#0984e3',
        dark: '#2d3436',
        light: '#dfe6e9'
    };
    
    // Toast notification function
    window.showToast = function(message, type = 'info') {
        const toast = $(`
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `);
        
        // Add to container
        const container = $('#toastContainer');
        if (!container.length) {
            $('body').append('<div id="toastContainer" class="toast-container position-fixed bottom-0 end-0 p-3"></div>');
        }
        $('#toastContainer').append(toast);
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast[0]);
        bsToast.show();
        
        // Remove after hidden
        toast.on('hidden.bs.toast', function () {
            $(this).remove();
        });
    };
    
    // Get CSRF token function
    window.getCSRFToken = function() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };
    
    // Format currency
    window.formatCurrency = function(amount) {
        return new Intl.NumberFormat('en-KE', {
            style: 'currency',
            currency: 'KES',
            minimumFractionDigits: 2
        }).format(amount);
    };
    
    // Format date
    window.formatDate = function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-KE', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };
    
    // Format date time
    window.formatDateTime = function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-KE', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };
    
    // Calculate percentage
    window.calculatePercentage = function(part, total) {
        if (total === 0) return 0;
        return (part / total) * 100;
    };
    
    // Calculate profit margin
    window.calculateProfitMargin = function(cost, price) {
        if (cost === 0) return 0;
        return ((price - cost) / cost) * 100;
    };
});

// Global error handler
window.onerror = function(message, source, lineno, colno, error) {
    console.error('Global error:', message, error);
    return false;
};

// AJAX setup
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type)) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
        }
    },
    error: function(xhr, status, error) {
        console.error('AJAX Error:', status, error);
        showToast('An error occurred. Please try again.', 'error');
    }
});