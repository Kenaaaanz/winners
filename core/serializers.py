"""
Serializers for M-Pesa models
"""
from rest_framework import serializers
from .mpesa_models import MpesaTransaction, MpesaCallback

class MpesaTransactionSerializer(serializers.ModelSerializer):
    """Serializer for M-Pesa transactions"""
    
    user_name = serializers.SerializerMethodField()
    sale_invoice = serializers.SerializerMethodField()
    formatted_amount = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    formatted_completed_date = serializers.SerializerMethodField()
    
    class Meta:
        model = MpesaTransaction
        fields = [
            'transaction_id',
            'transaction_type',
            'amount',
            'formatted_amount',
            'phone_number',
            'account_reference',
            'transaction_desc',
            'status',
            'mpesa_receipt_number',
            'result_code',
            'result_description',
            'response_code',
            'response_description',
            'is_complete',
            'user_name',
            'sale_invoice',
            'created_at',
            'formatted_date',
            'completed_at',
            'formatted_completed_date',
        ]
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'
    
    def get_sale_invoice(self, obj):
        return obj.sale.invoice_number if obj.sale else None
    
    def get_formatted_amount(self, obj):
        return f"KES {obj.amount:,.2f}"
    
    def get_formatted_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S') if obj.created_at else None
    
    def get_formatted_completed_date(self, obj):
        return obj.completed_at.strftime('%Y-%m-%d %H:%M:%S') if obj.completed_at else None

class MpesaCallbackSerializer(serializers.ModelSerializer):
    """Serializer for M-Pesa callbacks"""
    
    formatted_date = serializers.SerializerMethodField()
    transaction_info = serializers.SerializerMethodField()
    
    class Meta:
        model = MpesaCallback
        fields = [
            'id',
            'callback_type',
            'transaction_info',
            'result_code',
            'result_description',
            'is_processed',
            'processed_at',
            'processing_notes',
            'received_at',
            'formatted_date',
        ]
    
    def get_formatted_date(self, obj):
        return obj.received_at.strftime('%Y-%m-%d %H:%M:%S') if obj.received_at else None
    
    def get_transaction_info(self, obj):
        if obj.transaction:
            return {
                'transaction_id': obj.transaction.transaction_id,
                'amount': str(obj.transaction.amount),
                'phone_number': obj.transaction.phone_number,
            }
        return None

class STKPushRequestSerializer(serializers.Serializer):
    """Serializer for STK Push requests"""
    
    phone_number = serializers.CharField(max_length=15, required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=1)
    account_reference = serializers.CharField(max_length=50, required=True)
    transaction_desc = serializers.CharField(max_length=100, required=True)
    
    def validate_phone_number(self, value):
        """Validate Kenyan phone number"""
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, value))
        
        if len(phone) < 9 or len(phone) > 12:
            raise serializers.ValidationError("Invalid phone number length")
        
        # Convert to standard format (2547XXXXXXXX)
        if phone.startswith('0'):
            if len(phone) == 10:
                return '254' + phone[1:]
            else:
                raise serializers.ValidationError("Invalid phone number format")
        elif phone.startswith('254'):
            if len(phone) == 12:
                return phone
            else:
                raise serializers.ValidationError("Invalid phone number format")
        elif phone.startswith('7'):
            if len(phone) == 9:
                return '254' + phone
            else:
                raise serializers.ValidationError("Invalid phone number format")
        else:
            raise serializers.ValidationError("Invalid phone number format")
    
    def validate_amount(self, value):
        """Validate amount"""
        if value > 150000:
            raise serializers.ValidationError("Amount exceeds M-Pesa limit of 150,000")
        return value

class B2CPaymentSerializer(serializers.Serializer):
    """Serializer for B2C payments"""
    
    phone_number = serializers.CharField(max_length=15, required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=1)
    remarks = serializers.CharField(max_length=100, required=True)
    occassion = serializers.CharField(max_length=100, required=False, allow_blank=True)
    command_id = serializers.ChoiceField(
        choices=[
            ('BusinessPayment', 'Business Payment'),
            ('SalaryPayment', 'Salary Payment'),
            ('PromotionPayment', 'Promotion Payment')
        ],
        default='BusinessPayment'
    )

class TransactionQuerySerializer(serializers.Serializer):
    """Serializer for transaction queries"""
    
    transaction_id = serializers.CharField(max_length=50, required=True)
    query_type = serializers.ChoiceField(
        choices=[
            ('stk', 'STK Push'),
            ('status', 'Transaction Status'),
            ('reversal', 'Reversal')
        ],
        default='stk'
    )

class MpesaWebhookSerializer(serializers.Serializer):
    """Serializer for M-Pesa webhook data"""
    
    # Common fields
    TransactionType = serializers.CharField(required=False)
    TransID = serializers.CharField(required=False)
    TransTime = serializers.CharField(required=False)
    TransAmount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    BusinessShortCode = serializers.CharField(required=False)
    BillRefNumber = serializers.CharField(required=False, allow_blank=True)
    InvoiceNumber = serializers.CharField(required=False, allow_blank=True)
    OrgAccountBalance = serializers.CharField(required=False, allow_blank=True)
    ThirdPartyTransID = serializers.CharField(required=False, allow_blank=True)
    MSISDN = serializers.CharField(required=False)
    FirstName = serializers.CharField(required=False, allow_blank=True)
    MiddleName = serializers.CharField(required=False, allow_blank=True)
    LastName = serializers.CharField(required=False, allow_blank=True)
    
    # STK Push specific
    Body = serializers.DictField(required=False)
    stkCallback = serializers.DictField(required=False)
    CallbackMetadata = serializers.DictField(required=False)
    ResultCode = serializers.IntegerField(required=False)
    ResultDesc = serializers.CharField(required=False, allow_blank=True)
    CheckoutRequestID = serializers.CharField(required=False, allow_blank=True)
    
    def to_internal_value(self, data):
        """Handle different webhook formats"""
        # Check if it's an STK callback
        if 'Body' in data and 'stkCallback' in data['Body']:
            return super().to_internal_value(data)
        # Check if it's C2B
        elif 'TransactionType' in data:
            return super().to_internal_value(data)
        # Default to original data
        else:
            return data