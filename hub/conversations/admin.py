from django.contrib import admin
from .models import Conversation, Contact, Message

admin.site.register(Contact)
admin.site.register(Conversation)
admin.site.register(Message)

