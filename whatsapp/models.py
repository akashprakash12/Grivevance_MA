from django.db import models
from django.utils import timezone

class WhatsAppMessage(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    sender = models.CharField(max_length=20)
    message = models.TextField()

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "WhatsApp Message"
        verbose_name_plural = "WhatsApp Messages"

    def __str__(self):
        return f"Message from {self.sender} at {self.timestamp}"