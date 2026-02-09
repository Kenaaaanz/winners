"""
Django signals for automatic profile creation and role assignment
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create a Profile for new users or update existing profile.
    Automatically assign 'ADMIN' role to superusers/staff.
    """
    try:
        profile = Profile.objects.get(user=instance)
    except Profile.DoesNotExist:
        profile = Profile()
    
    # Update profile
    profile.user = instance
    
    # Assign role based on user status
    if instance.is_superuser:
        profile.role = 'ADMIN'
    elif instance.is_staff:
        profile.role = 'MANAGER'
    elif not profile.role or profile.role == 'Staff':  # Default value
        profile.role = 'STAFF'
    # Otherwise keep existing role
    
    profile.save()


@receiver(post_delete, sender=Profile)
def delete_profile_user(sender, instance, **kwargs):
    """
    Allow profile deletion without error (user can be deleted separately)
    """
    pass
