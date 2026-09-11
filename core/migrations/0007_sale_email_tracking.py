from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_customer_customer_id_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='admin_email_sent',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sale',
            name='receipt_email_sent',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
