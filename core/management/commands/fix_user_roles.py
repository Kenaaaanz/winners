from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile


class Command(BaseCommand):
    help = 'Fix existing superuser and staff profiles with proper roles'

    def handle(self, *args, **options):
        updated_count = 0
        
        # Update all superusers to have ADMIN role
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            profile, created = Profile.objects.get_or_create(user=user)
            if profile.role != 'ADMIN':
                profile.role = 'ADMIN'
                profile.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Set {user.username} role to ADMIN')
                )
            else:
                self.stdout.write(f'○ {user.username} already has ADMIN role')
        
        # Update all staff users to have MANAGER role
        staff_users = User.objects.filter(is_staff=True, is_superuser=False)
        for user in staff_users:
            profile, created = Profile.objects.get_or_create(user=user)
            if profile.role != 'MANAGER':
                profile.role = 'MANAGER'
                profile.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Set {user.username} role to MANAGER')
                )
            else:
                self.stdout.write(f'○ {user.username} already has MANAGER role')
        
        # Ensure all regular users have at least STAFF role
        regular_users = User.objects.filter(is_staff=False, is_superuser=False)
        for user in regular_users:
            profile, created = Profile.objects.get_or_create(user=user)
            if not profile.role or profile.role == 'Staff':
                profile.role = 'STAFF'
                profile.save()
                updated_count += 1
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Successfully updated {updated_count} user profiles!')
            )
        else:
            self.stdout.write(self.style.WARNING('All profiles are already set correctly.'))
