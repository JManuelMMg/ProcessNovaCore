# Generated migration - Add indexes for performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['organization', 'email'], name='customer_org_email_idx'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['organization', 'created_at'], name='customer_org_date_idx'),
        ),
    ]
