# Role-Based Access Control Setup Guide

## Overview
Your Winners platform now has a comprehensive role-based access control system that restricts app access based on user roles.

## Available Roles

| Role | Permissions | Access |
|------|------------|--------|
| **ADMIN** | All apps | Full access to all features |
| **MANAGER** | Inventory, Analytics, Customers, Sales, M-Pesa, Reports | Management & analysis features |
| **STAFF** | POS, Customers, Sales | Sales operations |
| **CASHIER** | POS, Sales | POS operations only |
| **ANALYST** | Analytics, Reports | Reporting & analysis only |

## App Access Mapping

- **POS** → Requires: ADMIN, STAFF, or CASHIER
- **INVENTORY** → Requires: ADMIN or MANAGER
- **ANALYTICS** → Requires: ADMIN, MANAGER, or ANALYST
- **CORE (Customers/Sales)** → Requires: ADMIN, MANAGER, STAFF, or CASHIER
- **MPESA** → Requires: ADMIN or MANAGER

## Setup Instructions

### 1. Create Default Roles
Run this command once to set up the role/group system:

```bash
python manage.py setup_roles
```

Output will show:
```
✓ Created role: ADMIN
✓ Created role: MANAGER
✓ Created role: STAFF
✓ Created role: CASHIER
✓ Created role: ANALYST

✓ Successfully created 5 new roles!

Role Permissions:
------------------------------------------------------------
ADMIN           → POS, INVENTORY, ANALYTICS, CUSTOMERS, SALES, MPESA, SETTINGS
MANAGER         → INVENTORY, ANALYTICS, CUSTOMERS, SALES, MPESA, REPORTS
STAFF           → POS, CUSTOMERS, SALES
CASHIER         → POS, SALES
ANALYST         → ANALYTICS, REPORTS
```

### 2. Assign Roles to Users

You can assign roles to users via Django admin or programmatically:

#### Via Django Admin:
1. Go to `/admin/core/profile/`
2. Edit a user's profile
3. Set their **Role** field to one of: ADMIN, MANAGER, STAFF, CASHIER, or ANALYST
4. Save

#### Programmatically:
```python
from core.models import Profile
from django.contrib.auth.models import User

user = User.objects.get(username='john_doe')
profile = Profile.objects.get(user=user)
profile.role = 'CASHIER'  # or 'STAFF', 'MANAGER', 'ANALYST', 'ADMIN'
profile.save()
```

### 3. Default Role Assignment

If a user doesn't have a profile or role assigned, they default to **STAFF** role. Update this in [core/permissions.py](core/permissions.py) line 82:

```python
def get_user_role(user):
    try:
        profile = Profile.objects.get(user=user)
        return profile.role
    except Profile.DoesNotExist:
        return 'STAFF'  # Change this default if needed
```

## How It Works

### Access Control Layers

#### 1. **Middleware-Level Control** (App-wide)
The `RoleRequiredMiddleware` checks every request to an app and verifies the user has access before the view even loads.

#### 2. **View-Level Control** (Specific views)
Individual views use the `@require_role()` decorator for granular control:

```python
# Analytics views - Manager and Analyst only
@require_role('ADMIN', 'MANAGER', 'ANALYST')
@login_required
def analytics_dashboard(request):
    ...

# POS views - Staff and Cashier only
@require_role('ADMIN', 'STAFF', 'CASHIER')
@login_required
def pos_dashboard(request):
    ...
```

### Behavior

**When Access is Denied:**
- Web requests → Redirect to dashboard with error message
- AJAX requests → Return JSON error response (status 403)

**Error Messages:**
```json
{
    "success": false,
    "error": "Access denied. You do not have permission to access this app."
}
```

## Usage Examples

### Check User Permissions Programmatically

```python
from core.permissions import user_has_role, user_has_permission, get_user_role

# Get user's role
role = get_user_role(request.user)  # Returns: 'STAFF', 'MANAGER', etc.

# Check if user has specific role
if user_has_role(request.user, 'MANAGER'):
    # Allow manager-specific action
    pass

# Check if user has permission
if user_has_permission(request.user, 'ANALYTICS'):
    # Allow analytics access
    pass
```

### Add Role Protection to New Views

```python
from core.permissions import require_role

@require_role('MANAGER', 'ADMIN')  # Only managers and admins
@login_required
def new_report_view(request):
    ...

# Multiple roles allowed
@require_role('STAFF', 'CASHIER', 'ADMIN')  # Staff, cashiers, and admins
@login_required
def inventory_check_view(request):
    ...
```

## Currently Protected Views

### Analytics (Manager/Analyst only)
- Analytics Dashboard
- Sales Report
- Product Performance
- Customer Insights
- Financial Report
- Inventory Report

### Inventory (Manager only)
- Product List
- Product Create/Update
- Purchase Orders

### POS (Staff/Cashier only)
- POS Dashboard
- All cart operations
- Sales processing

## Creating New Roles

To add new roles, edit `ROLE_PERMISSIONS` in [core/permissions.py](core/permissions.py):

```python
ROLE_PERMISSIONS = {
    'ADMIN': ['POS', 'INVENTORY', 'ANALYTICS', ...],
    'MANAGER': ['INVENTORY', 'ANALYTICS', ...],
    'STAFF': ['POS', 'CUSTOMERS', 'SALES'],
    'YOUR_NEW_ROLE': ['POS', 'ANALYTICS'],  # Add here
    ...
}
```

Then run setup again:
```bash
python manage.py setup_roles
```

## Password/Access Protection

Currently, access control is based on user roles in the Profile model. To implement separate passwords for different features:

1. **Option 1: Use Session-Based Feature Flags**
   - Create a separate authentication flow in your frontend
   - Store feature access in session upon verification

2. **Option 2: Use Two-Factor Authentication**
   - Install: `pip install django-otp`
   - Set up per-app MFA requirements

3. **Option 3: Add a Feature Access Table**
   - Create a model: `FeatureAccess(user, feature, password_hash)`
   - Check during middleware execution

Let me know if you'd like me to implement option 2 or 3!

## Troubleshooting

### User can't access anything
- Check if user has a Profile record
- Verify Profile.role is set to a valid role
- Default role is 'STAFF' if not assigned

### "Access denied" but should have access
- Check ROLE_PERMISSIONS mapping in permissions.py
- Verify user's profile role matches required roles
- Check APP_PERMISSIONS for app configuration

### Role changes not taking effect immediately
- Roles are read on each request (no caching)
- Changes should be immediate
- Clear browser cache if issues persist
