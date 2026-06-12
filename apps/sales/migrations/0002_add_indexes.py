# Generated migration - Add indexes for performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='sale',
            index=models.Index(fields=['organization', 'status', 'created_at'], name='sale_org_status_date_idx'),
        ),
        migrations.AddIndex(
            model_name='sale',
            index=models.Index(fields=['branch', 'created_at'], name='sale_branch_date_idx'),
        ),
        migrations.AddIndex(
            model_name='saleitem',
            index=models.Index(fields=['sale', 'product'], name='saleitem_sale_product_idx'),
        ),
    ]
