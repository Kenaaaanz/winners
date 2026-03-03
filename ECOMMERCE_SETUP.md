# Winners Cosmetics E-Commerce Setup

## Overview
A complete e-commerce system has been integrated into the Winners Cosmetics management platform, allowing customers to shop online, pay via Paystack, and receive orders delivered to their address. The system includes stock reservation to prevent overselling, full analytics integration, and admin controls to manage product visibility.

---

## Architecture

### Components
1. **Shop App** (`shop/`) - Customer-facing e-commerce interface
2. **Stock Reservation System** - Prevents overselling during pending payments
3. **Paystack Integration** - Secure online payment processing
4. **Analytics Dashboard** - E-commerce KPIs and performance metrics
5. **Delivery Management** - Customer delivery address collection and tracking

---

## Features

### 1. Customer Shopping Experience
- **Landing Page** (Site Root `/`)
  - Featured products display with hero section
  - Search functionality (by product name, description, category, brand)
  - Pagination (12 products per page)
  - Product images and stock status indicators
  - Category and brand filtering

- **Product Detail Page** (`/product/<id>/`)
  - Full product description and images
  - Stock availability with quantity selector
  - Add to cart functionality
  - Related product recommendations

- **Shopping Cart** (`/cart/`)
  - View all items with subtotal, tax, and total
  - Update quantities or remove items
  - Sticky order summary sidebar
  - Proceed to checkout button

- **Checkout** (`/checkout/`)
  - **Customer Information Section**
    - First name, last name, email, phone
  - **Delivery Address Section** (NEW)
    - Recipient name and phone
    - City and full address
    - Optional delivery instructions
  - **Order Summary**
    - Itemized product list
    - Subtotal, tax (16%), total
    - Paystack payment button

- **Order Confirmation** (`/checkout/success/`)
  - Order number and total amount
  - Delivery address confirmation
  - Delivery instructions display
  - Payment status indicator
  - Order items recap

### 2. Stock Management & Reservations
**New Model: `StockReservation`**
- **Automatic Stock Reservation** during checkout (30-minute payment window)
- **Status Tracking**:
  - `ACTIVE` - Payment pending
  - `CONFIRMED` - Payment successful, stock deducted
  - `RELEASED` - Payment failed, stock restored
  - `EXPIRED` - Reservation window closed, stock restored
- **Prevents Overselling** - Real-time stock count excludes reserved items
- **Dashboard Display** - Available stock shown considering reservations

### 3. Product Management (Admin)
**New Admin Fields** for Products:
- `show_on_shop` - Toggle product visibility on e-commerce site
- `is_featured` - Display product in featured section

**Admin Filters & List Display**:
- Filter by `show_on_shop` and `is_featured` status
- Quick toggle from admin list view

### 4. Paystack Integration
**Enhancements**:
- Initialize transactions with order metadata (delivery info, customer details)
- Webhook receiver confirms stock reservations on successful payment
- Webhook receiver releases stock on failed payments
- Customer-facing payment page with metadata
- Transaction history with reference numbers

### 5. Delivery Information Capture
**Sale Model Extensions** (`core/models.py`):
```python
delivery_name          # Recipient name
delivery_phone         # Recipient phone
delivery_address       # Full street address
delivery_city          # City/location
delivery_instructions  # Special delivery notes (optional)
```

**Admin Display**:
- All delivery fields visible in Sale admin
- Editable for order management
- Used for fulfillment and customer communication

### 6. Analytics & Reporting
**New E-Commerce KPIs** in Analytics Dashboard:
- **Online Sales Today** - Orders placed today via Paystack
- **Online Sales This Month** - Monthly online revenue and order count
- **Pending Payments** - Orders awaiting payment confirmation
- **Average Order Value** - Revenue per transaction

**Filters Applied**:
- `payment_method='PAYSTACK'`
- `cashier__isnull=True` (anonymous checkout)
- Date range filters for trending

**Dashboard Display**:
- Dedicated E-Commerce Performance card
- Metrics: Daily/monthly orders, revenue, pending payments
- Average order value calculation

---

## User Flows

### Customer Journey
1. **Browse Shop** → Visit `/` (site root)
2. **Search/Filter** → Use search bar or pagination
3. **View Product** → Click product card for details
4. **Add to Cart** → Select quantity and click "Add to Cart"
5. **Checkout** → Review cart, enter delivery info
6. **Pay** → Redirect to Paystack payment page
7. **Confirm** → Return to success page with order details

### Admin Journey
1. **Toggle Products** → Admin → Products → Edit `show_on_shop` / `is_featured`
2. **Monitor Sales** → Analytics → E-Commerce Performance card
3. **View Orders** → Admin → Sales → Filter by `payment_method='PAYSTACK'`
4. **Process Delivery** → Click order, view delivery address, mark as shipped
5. **Track Stock** → Inventory → Monitor reservations and actual stock

---

## URL Routes

### Customer Routes
| Route | View | Purpose |
|-------|------|---------|
| `/` | `shop.index` | Shop landing page with search/pagination |
| `/product/<id>/` | `shop.product_detail` | Product detail page |
| `/cart/` | `shop.view_cart` | Shopping cart |
| `/cart/add/` | `shop.add_to_cart` (POST) | Add to cart (AJAX) |
| `/checkout/` | `shop.checkout` | Checkout form and Paystack init |
| `/checkout/success/` | `shop.checkout_success` | Order confirmation |

### Admin Routes (Dashboard)
| Route | View | Purpose |
|-------|------|---------|
| `/app/` | `core.dashboard` | Admin dashboard |
| `/analytics/` | `analytics.analytics_dashboard` | Analytics with e-commerce KPIs |
| `/pos/` | `pos.pos_dashboard` | POS interface (login required) |
| `/login/` | Django auth | Staff/admin login |

### API Routes
| Route | Purpose |
|-------|---------|
| `/api/paystack/webhook/` | Paystack webhook receiver |
| `/api/paystack/verify/<sale_id>/` | Payment verification |

---

## Database Models

### StockReservation (NEW)
```python
product          : ForeignKey(Product)
sale             : OneToOneField(Sale)
quantity         : Integer
status           : Choice(ACTIVE, CONFIRMED, RELEASED, EXPIRED)
created_at       : DateTime
expires_at       : DateTime (30 minutes from creation)
confirmed_at     : DateTime (on successful payment)
released_at      : DateTime (on failure or expiration)
```

### Sale (EXTENDED)
**New Fields**:
- `delivery_name`          : CharField (recipient name)
- `delivery_phone`         : CharField (recipient phone)
- `delivery_address`       : TextField (full address)
- `delivery_city`          : CharField (city)
- `delivery_instructions`  : TextField (optional notes)

### Product (EXTENDED)
**New Fields**:
- `show_on_shop` : BooleanField (default=False) - Visibility toggle
- `is_featured`  : BooleanField (default=False) - Featured section display

---

## Settings Configuration

### Required Environment Variables
```env
PAYSTACK_PUBLIC_KEY=pk_live_xxxx        # Paystack public key
PAYSTACK_SECRET_KEY=sk_live_xxxx        # Paystack secret key
```

### Installed Apps (settings.py)
```python
INSTALLED_APPS = [
    ...
    'shop',              # NEW
    'core',
    'pos',
    'inventory',
    'analytics',
    ...
]
```

### URL Configuration (winners/urls.py)
```python
urlpatterns = [
    path('', include('shop.urls')),       # Shop at site root (NEW)
    path('app/', include('core.urls')),   # Core moved under /app/
    path('pos/', include('pos.urls')),    # POS at /pos/
    path('login/', auth_views.LoginView.as_view(...)), # Short login route
    ...
]
```

---

## Templates

### Shop Templates (Bootstrap 5 styled)
- `shop/index.html` - Landing page with featured & search
- `shop/product_detail.html` - Product details with add-to-cart
- `shop/cart.html` - Shopping cart view
- `shop/checkout.html` - Checkout form with delivery info
- `shop/success.html` - Order confirmation with details

### Analytics Template (Extended)
- `analytics/dashboard.html` - Added E-Commerce Performance card

---

## Stock Reservation Flow

### On Checkout (Immediate)
1. Customer submits checkout form
2. Create `Sale` object (status='PENDING')
3. Create `SaleItem` objects for each product
4. Create `StockReservation(status='ACTIVE', expires_at=now+30min)`
5. **Temporarily deduct stock** from `Product.quantity`
6. Initialize Paystack transaction
7. Redirect customer to payment page

### On Payment Success (Webhook)
1. Paystack sends `charge.success` webhook
2. Find associated `StockReservation`
3. Call `reservation.confirm()` → status='CONFIRMED'
4. Mark `Sale` as 'COMPLETED'
5. Stock remains deducted (final)
6. Award customer loyalty points
7. Send confirmation email

### On Payment Failure (Webhook)
1. Paystack sends `charge.failed` webhook
2. Find associated `StockReservation`
3. Call `reservation.release()` → status='RELEASED'
4. **Restore stock** to `Product.quantity`
5. Delete/mark `Sale` as failed
6. Stock is available for other customers

### On Reservation Expiration (Manual Cleanup)
- Background task or admin action
- Check `StockReservation` with `status='ACTIVE'` and `expires_at < now`
- Release stock and mark as 'EXPIRED'

---

## Payment Security

- **Paystack Widget** - PCI-DSS compliant hosted checkout
- **HTTPS Only** - All transactions over secure connection
- **Webhook Signature Validation** - Verify Paystack sender
- **Reference Numbering** - Unique transaction IDs prevent duplicates
- **Amount Validation** - Confirm payment amount matches order total

---

## Testing Checklist

- [ ] Visit `/` → See shop homepage with featured products
- [ ] Search for product by name/category/brand
- [ ] Pagination works (navigate pages)
- [ ] Click featured product → View product detail
- [ ] Add product to cart
- [ ] Update quantity in cart
- [ ] Proceed to checkout → Enter contact & delivery info
- [ ] Submit checkout → Redirected to Paystack
- [ ] Admin can toggle `show_on_shop` on products
- [ ] Analytics dashboard shows e-commerce KPIs
- [ ] Stock reservation prevents overselling
- [ ] Successful payment confirms order
- [ ] Failed payment releases reserved stock

---

## Future Enhancements

1. **Email Notifications**
   - Order confirmation email with tracking link
   - Payment success/failure notifications
   - Delivery status updates

2. **Customer Accounts** (Optional)
   - User registration for tracked order history
   - Saved addresses for repeat checkout
   - Loyalty program integration

3. **Shipping Integration**
   - Real carrier APIs (DHL, FedEx)
   - Automated tracking number generation
   - Delivery status webhooks

4. **Inventory Intelligence**
   - Low-stock alerts
   - Automatic reorder recommendations
   - Seasonal demand forecasting

5. **Advanced Analytics**
   - Customer lifetime value (LTV)
   - Conversion funnel analysis
   - Product performance heatmaps
   - Abandoned cart recovery

6. **Marketing Automation**
   - Email campaigns (new products, sales)
   - SMS notifications (order status)
   - Coupon/discount system

---

## Support & Maintenance

### Logs Location
- Application logs: `logs/winners.log`
- Error logs: `logs/error.log`

### Admin Resources
- Django Admin: `/admin/`
- Analytics: `/analytics/`
- Sales Management: `/admin/core/sale/`
- Product Management: `/admin/core/product/`
- Stock Reservations: `/admin/core/stockreservation/`

### Key Contacts
- Paystack Support: https://paystack.com/support
- Django Documentation: https://docs.djangoproject.com/
