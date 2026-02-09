"""
Role-based access control system for the Winners platform
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import Group
from . models import Profile


# Define role hierarchy and permissions
ROLE_PERMISSIONS = {
    'ADMIN': ['POS', 'INVENTORY', 'ANALYTICS', 'CUSTOMERS', 'SALES', 'MPESA', 'SETTINGS'],
    'MANAGER': ['INVENTORY', 'ANALYTICS', 'CUSTOMERS', 'SALES', 'MPESA', 'REPORTS', 'REPORTS_ANALYTICS'],
    'STAFF': ['POS', 'CUSTOMERS', 'SALES'],
    'CASHIER': ['POS', 'SALES'],
    'ANALYST': ['ANALYTICS', 'REPORTS', 'REPORTS_ANALYTICS'],
}

# App to permission mapping
APP_PERMISSIONS = {
    'pos': 'POS',
    'inventory': 'INVENTORY',
    'analytics': 'ANALYTICS',
    'core': ['CUSTOMERS', 'SALES'],  # Multiple permissions
    'mpesa': 'MPESA',
    'admin': 'ADMIN',
}


def get_user_role(user):
    """Get user's role from Profile"""
    try:
        profile = Profile.objects.get(user=user)
        return profile.role
    except Profile.DoesNotExist:
        return 'STAFF'  # Default role


def user_has_permission(user, permission):
    """Check if user has specific permission"""
    role = get_user_role(user)
    user_permissions = ROLE_PERMISSIONS.get(role, [])
    
    if isinstance(user_permissions, list):
        return permission in user_permissions
    return permission == user_permissions


def user_has_role(user, *roles):
    """Check if user has one of the specified roles"""
    user_role = get_user_role(user)
    return user_role in roles


def require_role(*allowed_roles):
    """
    Decorator to restrict view access by role.
    Usage: @require_role('MANAGER', 'ADMIN')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user_role = get_user_role(request.user)
            
            if user_role not in allowed_roles:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': f'Access denied. Required role(s): {", ".join(allowed_roles)}'
                    }, status=403)
                return HttpResponseForbidden(
                    f'Access denied. You need to be a {" or ".join(allowed_roles)} to access this.'
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_permission(*permissions):
    """
    Decorator to restrict view access by permission.
    Usage: @require_permission('ANALYTICS', 'REPORTS')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            has_access = False
            
            for permission in permissions:
                if user_has_permission(request.user, permission):
                    has_access = True
                    break
            
            if not has_access:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': f'Access denied. Required permission(s): {", ".join(permissions)}'
                    }, status=403)
                return HttpResponseForbidden(
                    f'Access denied. You do not have permission to access this.'
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class RoleRequiredMiddleware:
    """
    Middleware to enforce app-level access control based on user roles
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check app-level access control
        if request.user.is_authenticated:
            # Skip role checking for superusers and staff (they have built-in Django permissions)
            if request.user.is_superuser or request.user.is_staff:
                response = self.get_response(request)
                return response
            
            path = request.path
            
            # Extract app name from path
            path_parts = path.strip('/').split('/')
            if path_parts:
                app_name = path_parts[0]
                
                # Get required permission for this app
                required_permission = APP_PERMISSIONS.get(app_name)
                
                if required_permission:
                    # Handle both single permissions and multiple permissions
                    if isinstance(required_permission, list):
                        has_access = any(
                            user_has_permission(request.user, perm)
                            for perm in required_permission
                        )
                    else:
                        has_access = user_has_permission(request.user, required_permission)
                    
                    if not has_access:
                        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False,
                                'error': 'Access denied. You do not have permission to access this app.'
                            }, status=403)
                        
                        # Redirect to dashboard with error message
                        from django.contrib import messages
                        messages.error(request, f'You do not have permission to access {app_name}.')
                        return redirect(reverse('dashboard'))
        
        response = self.get_response(request)
        return response


def create_default_roles():
    """
    Create default roles/groups in the system.
    Call this once during initial setup or in a migration.
    """
    roles = ['ADMIN', 'MANAGER', 'STAFF', 'CASHIER', 'ANALYST']
    
    for role in roles:
        Group.objects.get_or_create(name=role)
