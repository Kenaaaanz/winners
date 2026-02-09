/**
 * M-Pesa Integration JavaScript
 */

class MpesaIntegration {
    constructor() {
        this.baseUrl = '/api/mpesa/';
        this.config = null;
        this.initialize();
    }
    
    async initialize() {
        // Load M-Pesa configuration
        await this.loadConfig();
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    async loadConfig() {
        try {
            const response = await fetch(this.baseUrl + 'config/');
            this.config = await response.json();
            console.log('M-Pesa config loaded:', this.config);
        } catch (error) {
            console.error('Failed to load M-Pesa config:', error);
        }
    }
    
    setupEventListeners() {
        // STK Push form submission
        const stkForm = document.getElementById('mpesaStkForm');
        if (stkForm) {
            stkForm.addEventListener('submit', (e) => this.handleStkSubmit(e));
        }
        
        // Phone number formatting
        const phoneInputs = document.querySelectorAll('.mpesa-phone-input');
        phoneInputs.forEach(input => {
            input.addEventListener('blur', (e) => this.formatPhoneNumber(e.target));
        });
        
        // Amount validation
        const amountInputs = document.querySelectorAll('.mpesa-amount-input');
        amountInputs.forEach(input => {
            input.addEventListener('blur', (e) => this.validateAmount(e.target));
        });
    }
    
    formatPhoneNumber(input) {
        let phone = input.value.trim();
        
        // Remove all non-digit characters
        phone = phone.replace(/\D/g, '');
        
        // Format to Kenyan standard
        if (phone.startsWith('0') && phone.length === 10) {
            phone = '254' + phone.substring(1);
        } else if (phone.startsWith('7') && phone.length === 9) {
            phone = '254' + phone;
        } else if (phone.startsWith('254') && phone.length === 12) {
            // Already formatted
        } else if (phone.startsWith('+254') && phone.length === 13) {
            phone = phone.substring(1);
        }
        
        input.value = phone;
        return phone;
    }
    
    validateAmount(input) {
        let amount = parseFloat(input.value);
        
        if (isNaN(amount) || amount <= 0) {
            this.showError(input, 'Amount must be greater than 0');
            return false;
        }
        
        if (amount > this.config?.max_amount || 150000) {
            this.showError(input, `Amount cannot exceed KES ${this.config?.max_amount || 150,000}`);
            return false;
        }
        
        // M-Pesa requires whole shillings
        if (!Number.isInteger(amount)) {
            this.showError(input, 'Amount must be a whole number (no cents)');
            return false;
        }
        
        this.clearError(input);
        return true;
    }
    
    async handleStkSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        
        // Get form values
        const phoneNumber = formData.get('phone_number');
        const amount = formData.get('amount');
        const accountReference = formData.get('account_reference') || 'INV-' + Date.now();
        const transactionDesc = formData.get('transaction_desc') || 'Payment for goods/services';
        
        // Validate inputs
        if (!this.validatePhoneNumber(phoneNumber)) {
            this.showToast('Please enter a valid Kenyan phone number', 'error');
            return;
        }
        
        if (!this.validateAmount(amount)) {
            this.showToast('Please enter a valid amount', 'error');
            return;
        }
        
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        submitBtn.disabled = true;
        
        try {
            // Initiate STK Push
            const result = await this.initiateStkPush({
                phone_number: phoneNumber,
                amount: amount,
                account_reference: accountReference,
                transaction_desc: transactionDesc
            });
            
            if (result.success) {
                this.showToast('Payment initiated! Check your phone to complete.', 'success');
                
                // Start polling for status
                this.pollTransactionStatus(result.checkout_request_id, result.transaction_id);
                
                // Reset form
                form.reset();
                
                // If there's a success callback, execute it
                if (typeof window.onMpesaSuccess === 'function') {
                    window.onMpesaSuccess(result);
                }
            } else {
                this.showToast(result.error || 'Payment initiation failed', 'error');
            }
            
        } catch (error) {
            console.error('STK Push error:', error);
            this.showToast('An error occurred. Please try again.', 'error');
        } finally {
            // Reset button state
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    }
    
    async initiateStkPush(paymentData) {
        const response = await fetch(this.baseUrl + 'stk-push/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify(paymentData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async pollTransactionStatus(checkoutRequestId, transactionId) {
        // Create status container if it doesn't exist
        let statusContainer = document.getElementById('mpesa-status-container');
        if (!statusContainer) {
            statusContainer = document.createElement('div');
            statusContainer.id = 'mpesa-status-container';
            statusContainer.className = 'mt-3';
            document.querySelector('#mpesaStkForm').parentNode.appendChild(statusContainer);
        }
        
        // Show initial status
        statusContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-spinner fa-spin"></i>
                Waiting for payment confirmation...
                <div class="mt-2">
                    <small>Transaction ID: ${transactionId}</small>
                </div>
            </div>
        `;
        
        // Poll for status every 5 seconds
        let pollCount = 0;
        const maxPolls = 60; // 5 minutes
        
        const pollInterval = setInterval(async () => {
            pollCount++;
            
            if (pollCount > maxPolls) {
                clearInterval(pollInterval);
                statusContainer.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-clock"></i>
                        Payment timeout. Please check your M-Pesa messages.
                    </div>
                `;
                return;
            }
            
            try {
                const response = await fetch(this.baseUrl + 'stk-query/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({
                        transaction_id: checkoutRequestId
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    
                    if (result.success && result.result_code === 0) {
                        // Payment successful
                        clearInterval(pollInterval);
                        statusContainer.innerHTML = `
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle"></i>
                                Payment confirmed successfully!
                                <div class="mt-2">
                                    <small>Transaction completed successfully</small>
                                </div>
                            </div>
                        `;
                        
                        // Refresh page or update UI as needed
                        setTimeout(() => {
                            if (typeof window.onPaymentComplete === 'function') {
                                window.onPaymentComplete(result);
                            }
                        }, 2000);
                        
                    } else if (result.success && result.result_code !== 0) {
                        // Payment failed
                        clearInterval(pollInterval);
                        statusContainer.innerHTML = `
                            <div class="alert alert-danger">
                                <i class="fas fa-times-circle"></i>
                                Payment failed: ${result.result_desc}
                            </div>
                        `;
                    }
                    // If still pending, continue polling
                }
            } catch (error) {
                console.error('Status poll error:', error);
            }
        }, 5000);
        
        // Stop polling after 5 minutes
        setTimeout(() => {
            clearInterval(pollInterval);
            if (statusContainer.querySelector('.alert-info')) {
                statusContainer.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-clock"></i>
                        Status check timeout. Please check transaction history.
                    </div>
                `;
            }
        }, 300000); // 5 minutes
    }
    
    validatePhoneNumber(phone) {
        const phoneRegex = /^(?:254|\+254|0)?(7\d{8})$/;
        return phoneRegex.test(phone);
    }
    
    getCsrfToken() {
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
    
    showError(input, message) {
        this.clearError(input);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        input.classList.add('is-invalid');
        input.parentNode.appendChild(errorDiv);
    }
    
    clearError(input) {
        input.classList.remove('is-invalid');
        const errorDiv = input.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        const container = document.getElementById('toastContainer') || this.createToastContainer();
        container.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }
    
    // Utility function to calculate transaction fee
    calculateTransactionFee(amount) {
        // Simplified fee calculation based on M-Pesa rates
        const fees = [
            { max: 100, fee: 0 },
            { max: 500, fee: 11 },
            { max: 1000, fee: 15 },
            { max: 1500, fee: 25 },
            { max: 2500, fee: 30 },
            { max: 3500, fee: 53 },
            { max: 5000, fee: 60 },
            { max: 7500, fee: 75 },
            { max: 10000, fee: 85 },
            { max: 15000, fee: 95 },
            { max: 20000, fee: 100 },
            { max: 35000, fee: 110 },
            { max: 50000, fee: 120 },
            { max: 150000, fee: 150 }
        ];
        
        for (const tier of fees) {
            if (amount <= tier.max) {
                return tier.fee;
            }
        }
        
        return 200; // Default for amounts over 150,000
    }
    
    // Format amount with commas
    formatAmount(amount) {
        return new Intl.NumberFormat('en-KE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }
}

// Initialize M-Pesa integration when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mpesa = new MpesaIntegration();
});

// Global functions for callbacks
window.onMpesaSuccess = function(result) {
    console.log('M-Pesa payment initiated:', result);
    // Override this function in your page to handle success
};

window.onPaymentComplete = function(result) {
    console.log('M-Pesa payment completed:', result);
    // Override this function in your page to handle completion
    // Example: Refresh the page or update cart
    // window.location.reload();
};