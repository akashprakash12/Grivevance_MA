from django.db import models
from django.utils.translation import gettext_lazy as _
from user.models import User
from core_app.models import District

class CollectorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'COLLECTOR'},
        related_name='collector_profile',
        verbose_name=_("User Account")
    )
    district = models.OneToOneField(
        District,
        on_delete=models.CASCADE,
        verbose_name=_("Administered District")
    )
    official_address = models.TextField(
        verbose_name=_("Office Address")
    )
    collector_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Collector ID")
    )
    tenure_start = models.DateField(
        verbose_name=_("Tenure Start Date")
    )
    profile_picture = models.ImageField(
        upload_to='collector_profiles/',
        null=True,
        blank=True,
        verbose_name=_("Profile Picture"),
        help_text=_("Upload a profile image for the collector.")
    )

    
    class Meta:
        verbose_name = _("Collector Profile")
        verbose_name_plural = _("Collector Profiles")
    
    def __str__(self):
        return f"Collector of {self.district}"
