import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_stockreservation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='customer_id',
            field=models.CharField(default=uuid.uuid4, max_length=36, unique=True),
        ),
    ]