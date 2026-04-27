from django.db import models
from accounts.models import Organization

class Label(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='labels')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#6366f1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'name')
        ordering = ['-created_at']


