class POSSystem {
    constructor() {
        this.cart = [];
        this.subtotal = 0;
        this.taxRate = 16;
        this.discount = 0;
        this.initializeEventListeners();
        this.loadCartFromSession();
    }
    
    initializeEventListeners() {
        // Product click
        $(document).on('click', '.product-card', (e) => {
            const productId = $(e.currentTarget).data('product-id');
            this.addToCart(productId);
        });
        
        // Search products
        $('#productSearch').on('input', (e) => {
            const searchTerm = $(e.target).val().toLowerCase();
            $('.product-card').each(function() {
                const productName = $(this).find('.card-title').text().toLowerCase();
                const productSku = $(this).find('.card-text small').text().toLowerCase();
                const matches = productName.includes(searchTerm) || productSku.includes(searchTerm);
                $(this).toggle(matches);
            });
        });
        
        // Category filter
        $('.category-btn').on('click', (e) => {
            const category = $(e.target).data('category');
            $('.product-card').each(function() {
                const productCategory = $(this).data('category');
                const matches = category === 'all' || productCategory === category;
                $(this).toggle(matches);
            });
        });
        
        // Cart quantity changes
        $(document).on('click', '.btn-minus', (e) => {
            const input = $(e.target).closest('.input-group').find('.quantity-input');
            const newValue = parseInt(input.val()) - 1;
            if (newValue >= 1) {
                input.val(newValue);
                this.updateCartQuantity($(e.target).closest('.cart-item').data('product-id'), newValue);
            }
        });
        
        $(document).on('click', '.btn-plus', (e) => {
            const input = $(e.target).closest('.input-group').find('.quantity-input');
            const newValue = parseInt(input.val()) + 1;
            input.val(newValue);
            this.updateCartQuantity($(e.target).closest('.cart-item').data('product-id'), newValue);
        });
        
        $(document).on('change', '.quantity-input', (e) => {
            const productId = $(e.target).closest('.cart-item').data('product-id');
            const quantity = parseInt($(e.target).val());
            if (quantity >= 1) {
                this.updateCartQuantity(productId, quantity);
            }
        });
        
        // Remove item from cart
        $(document).on('click', '.remove-item', (e) => {
            const productId = $(e.target).closest('.cart-item').data('product-id');
            this.removeFromCart(productId);
        });
        
        // Clear cart
        $('#clearCart').on('click', () => {
            this.clearCart();
        });
        
        // Payment method change
        $('#paymentMethod').on('change', (e) => {
            if ($(e.target).val() === 'MPESA') {
                $('#mpesaPhoneSection').show();
            } else {
                $('#mpesaPhoneSection').hide();
            }
        });
        
        // Process sale
        $('#processSale').on('click', () => {
            this.processSale();
        });
        
        // New customer
        $('#saveCustomer').on('click', () => {
            this.saveNewCustomer();
        });
    }
    
    async addToCart(productId, quantity = 1) {
        try {
            const response = await fetch('/pos/cart/add/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.cart = data.cart_items;
                this.updateCartDisplay();
                this.showToast('Product added to cart', 'success');
            } else {
                this.showToast(data.error, 'error');
            }
        } catch (error) {
            this.showToast('Error adding to cart', 'error');
        }
    }
    
    async updateCartQuantity(productId, quantity) {
        try {
            const response = await fetch('/pos/cart/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.cart = data.cart_items;
                this.updateCartDisplay();
            } else {
                this.showToast(data.error, 'error');
            }
        } catch (error) {
            this.showToast('Error updating cart', 'error');
        }
    }
    
    async removeFromCart(productId) {
        try {
            const response = await fetch('/pos/cart/remove/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    product_id: productId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.cart = data.cart_items;
                this.updateCartDisplay();
                this.showToast('Item removed from cart', 'success');
            } else {
                this.showToast(data.error, 'error');
            }
        } catch (error) {
            this.showToast('Error removing item', 'error');
        }
    }
    
    async clearCart() {
        try {
            const response = await fetch('/pos/cart/clear/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.cart = [];
                this.updateCartDisplay();
                this.showToast('Cart cleared', 'success');
            }
        } catch (error) {
            this.showToast('Error clearing cart', 'error');
        }
    }
    
    async processSale() {
        if (this.cart.length === 0) {
            this.showToast('Cart is empty', 'error');
            return;
        }
        
        const customerId = $('#customerSelect').val();
        const paymentMethod = $('#paymentMethod').val();
        const mpesaPhone = $('#mpesaPhone').val();
        const amountPaid = parseFloat($('#amountPaid').val()) || this.calculateTotal();
        const notes = $('#saleNotes').val();
        
        if (paymentMethod === 'MPESA' && !mpesaPhone) {
            this.showToast('Please enter M-Pesa phone number', 'error');
            return;
        }
        
        const saleData = {
            customer_id: customerId || null,
            payment_method: paymentMethod,
            mpesa_phone: mpesaPhone,
            amount_paid: amountPaid,
            notes: notes,
            subtotal: this.subtotal,
            tax_rate: this.taxRate,
            discount_amount: this.discount,
            items: this.cart
        };
        
        try {
            const response = await fetch('/pos/process-sale/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(saleData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Sale processed successfully!', 'success');
                
                if (data.mpesa) {
                    this.showToast('M-Pesa payment initiated. Check your phone.', 'info');
                }
                
                // Clear cart and reset form
                this.clearCart();
                $('#customerSelect').val('');
                $('#paymentMethod').val('CASH');
                $('#mpesaPhone').val('');
                $('#amountPaid').val('');
                $('#saleNotes').val('');
                $('#mpesaPhoneSection').hide();
                
                // Open receipt in new tab if needed
                if (data.sale_id) {
                    setTimeout(() => {
                        window.open(`/pos/sales/${data.sale_id}/receipt/`, '_blank');
                    }, 1000);
                }
            } else {
                this.showToast(data.error, 'error');
            }
        } catch (error) {
            this.showToast('Error processing sale', 'error');
        }
    }
    
    async saveNewCustomer() {
        const form = $('#newCustomerForm');
        const formData = new FormData(form[0]);
        const data = Object.fromEntries(formData);
        
        try {
            const response = await fetch('/customers/new/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Add new customer to select
                const option = new Option(
                    `${data.first_name} ${data.last_name} (${data.phone})`,
                    result.customer_id
                );
                $('#customerSelect').append(option).val(result.customer_id);
                
                // Close modal
                $('#newCustomerModal').modal('hide');
                form[0].reset();
                
                this.showToast('Customer saved successfully', 'success');
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            this.showToast('Error saving customer', 'error');
        }
    }
    
    updateCartDisplay() {
        const cartItemsContainer = $('#cartItems');
        const cartCount = $('#cartCount');
        const subtotalEl = $('#subtotal');
        const taxEl = $('#tax');
        const totalEl = $('#total');
        
        // Update cart items
        if (this.cart.length === 0) {
            cartItemsContainer.html('<p class="text-muted text-center">Cart is empty</p>');
        } else {
            let cartHTML = '';
            this.cart.forEach(item => {
                cartHTML += `
                    <div class="cart-item" data-product-id="${item.product_id}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">${item.product_name}</h6>
                                <small class="text-muted">KES ${item.unit_price} each</small>
                            </div>
                            <span class="text-success">KES ${item.total_price}</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2">
                            <div class="input-group input-group-sm" style="width: 120px;">
                                <button class="btn btn-outline-secondary btn-minus" type="button">
                                    <i class="fas fa-minus"></i>
                                </button>
                                <input type="number" class="form-control text-center quantity-input" 
                                       value="${item.quantity}" min="1" max="100">
                                <button class="btn btn-outline-secondary btn-plus" type="button">
                                    <i class="fas fa-plus"></i>
                                </button>
                            </div>
                            <button class="btn btn-sm btn-outline-danger remove-item">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                `;
            });
            cartItemsContainer.html(cartHTML);
        }
        
        // Calculate totals
        this.subtotal = this.cart.reduce((sum, item) => sum + item.total_price, 0);
        const tax = (this.subtotal * this.taxRate) / 100;
        const total = this.subtotal + tax - this.discount;
        
        // Update UI
        cartCount.text(this.cart.length);
        subtotalEl.text(`KES ${this.subtotal.toFixed(2)}`);
        taxEl.text(`KES ${tax.toFixed(2)}`);
        totalEl.text(`KES ${total.toFixed(2)}`);
        
        // Update amount paid field
        $('#amountPaid').val(total.toFixed(2));
        
        // Save cart to session
        this.saveCartToSession();
    }
    
    calculateTotal() {
        const tax = (this.subtotal * this.taxRate) / 100;
        return this.subtotal + tax - this.discount;
    }
    
    loadCartFromSession() {
        // Cart is loaded from Django template initially
        this.cart = JSON.parse('{{ cart|safe }}' || '[]');
        this.updateCartDisplay();
    }
    
    saveCartToSession() {
        // Cart is automatically saved via Django session
    }
    
    getCSRFToken() {
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
    }
    
    showToast(message, type = 'info') {
        // Create toast element
        const toast = $(`
            <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
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
    }
}

// Initialize POS system when page loads
function initializePOS() {
    window.posSystem = new POSSystem();
}