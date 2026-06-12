# Generated migration - Add indexes for performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='stock',
            index=models.Index(fields=['organization', 'quantity'], name='stock_org_qty_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['organization', 'name'], name='product_org_name_idx'),
        ),
    ]
