# models.py

from django.db import models

class IDTracker(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Example: 'officer', 'department'
    last_used = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} - {self.last_used}"
