from core.api import api
from django.contrib import admin
from django.urls import path
from billing.webhook import stripe_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/webhooks/stripe/', stripe_webhook),
    path('api/', api.urls),
]
