from django.contrib import admin
from .models import WhatsAppMessage

@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'sender', 'message')
    search_fields = ('sender', 'message')
    list_filter = ('timestamp',)
    date_hierarchy = 'timestamp'