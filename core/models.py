from django.db import models


class TenantQuerySet(models.QuerySet):
    def for_org(self, organization):
        if organization is None:
            return self.none()
        return self.filter(organization=organization)

    def for_branch(self, organization, branch=None, role='employee'):
        qs = self.for_org(organization)
        if branch and role != 'admin_central' and hasattr(self.model, 'branch'):
            qs = qs.filter(branch=branch)
        return qs


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_org(self, organization):
        return self.get_queryset().for_org(organization)

    def for_branch(self, organization, branch=None, role='employee'):
        return self.get_queryset().for_branch(organization, branch, role)


class TenantAwareModel(models.Model):
    organization = models.ForeignKey(
        'users.Organization',
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )

    objects = TenantManager()

    class Meta:
        abstract = True
