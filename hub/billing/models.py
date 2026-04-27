from django.db import models


class Plan(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_extra_instance_price_id = models.CharField(max_length=100, blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    extra_instance_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_instances = models.IntegerField(null=True, blank=True)
    max_members = models.IntegerField(null=True, blank=True)
    max_contacts = models.IntegerField(null=True, blank=True)
    is_unlimited = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return self.name

class OrganizationSubscription(models.Model):
    class Status(models.TextChoices):
        FREE = 'free'
        ACTIVE = 'active'
        PAST_DUE = 'past_due'
        CANCELED = 'canceled'
        TRIALING = 'trialing'

    organization = models.OneToOneField('accounts.Organization', on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    extra_instances = models.IntegerField(default=0)
    status = models.CharField(choices=Status.choices, default=Status.FREE)
    current_period_end = models.DateTimeField(null=True, blank=True)
    granted_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.organization.name} - {self.plan.name}'

    @property
    def max_instances_total(self):
        if self.plan.is_unlimited or self.plan.max_instances is None:
            return None
        return self.plan.max_instances + self.extra_instances