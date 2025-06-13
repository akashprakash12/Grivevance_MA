from django.db import models
from django.utils.translation import gettext_lazy as _
from user.models import User
from core_app.models import Department

class OfficerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'OFFICER'},
        related_name='officer_profile',
        verbose_name=_("User Account")
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Assigned Department")
    )
    is_hod = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['department'],
                condition=models.Q(is_hod=True),
                name='unique_hod_per_department'
            )
        ]

    def __str__(self):
        return f"{self.user.username} ({'HOD' if self.is_hod else 'Officer'})"

class OfficerIDTracker(models.Model):
    department = models.OneToOneField(Department, on_delete=models.CASCADE)
    last_used = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.department.code} - {self.last_used}"
