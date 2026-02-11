from django.db import migrations
from decouple import config

def create_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    
    username = config('DJANGO_SUPERUSER_USERNAME', default='Kenani')
    email = config('DJANGO_SUPERUSER_EMAIL', default='gichabakenani@gmail.com')
    password = config('DJANGO_SUPERUSER_PASSWORD', default='Onsare@4427')
    
    if password and not User.objects.filter(username=username).exists():
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_superuser),
    ]