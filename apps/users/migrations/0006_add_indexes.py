# Generated migration - Add indexes for performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='membership',
            index=models.Index(fields=['user', 'organization'], name='membership_user_org_idx'),
        ),
        migrations.AddIndex(
            model_name='branch',
            index=models.Index(fields=['organization', 'is_active'], name='branch_org_active_idx'),
        ),
    ]
