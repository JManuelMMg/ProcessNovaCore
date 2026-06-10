from django.db import migrations


def migrate_roles_and_branches(apps, schema_editor):
    Organization = apps.get_model('users', 'Organization')
    Branch = apps.get_model('users', 'Branch')
    Membership = apps.get_model('users', 'Membership')

    role_map = {
        'owner': 'admin_central',
        'manager': 'branch_manager',
        'employee': 'employee',
        'admin_central': 'admin_central',
        'branch_manager': 'branch_manager',
    }

    for membership in Membership.objects.all():
        new_role = role_map.get(membership.role, 'employee')
        if membership.role != new_role:
            membership.role = new_role
            membership.save(update_fields=['role'])

    for org in Organization.objects.all():
        if not Branch.objects.filter(organization=org).exists():
            Branch.objects.create(
                organization=org,
                name='Sucursal Principal',
                codigo_postal=org.codigo_postal,
                is_main=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_roles_branches_tenant'),
    ]

    operations = [
        migrations.RunPython(migrate_roles_and_branches, migrations.RunPython.noop),
    ]
