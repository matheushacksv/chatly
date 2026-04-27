from django.db import models
from accounts.models import Organization
from labels.models import Label


class Contact(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    labels = models.ManyToManyField(Label, blank=True, related_name='contacts')
    pipedrive_person_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'phone')

    def __str__(self):
        return self.name

class ContactAnnotation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='contact_annotations')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='annotations')
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pinned', '-created_at']

    def __str__(self):
        return f'{self.contact} - anotação'

