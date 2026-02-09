from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from core.permissions import ROLE_PERMISSIONS


class Command(BaseCommand):
    help = 'Create default user roles and permissions'

    def handle(self, *args, **options):
        created_roles = []
        
        for role_name in ROLE_PERMISSIONS.keys():
            group, created = Group.objects.get_or_create(name=role_name)
            if created:
                created_roles.append(role_name)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created role: {role_name}')
                )
            else:
                self.stdout.write(f'○ Role already exists: {role_name}')
        
        if created_roles:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Successfully created {len(created_roles)} new roles!')
            )
        else:
            self.stdout.write(self.style.WARNING('All roles already exist.'))
        
        # Display role permissions
        self.stdout.write(self.style.SUCCESS('\nRole Permissions:'))
        self.stdout.write('-' * 60)
        for role, permissions in ROLE_PERMISSIONS.items():
            perms_str = ', '.join(permissions)
            self.stdout.write(f'{role:15} → {perms_str}')
