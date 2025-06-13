from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from core_app.models import District  # Add this import at the top
from django.db import transaction
from datetime import datetime
# models.py (add above the User model)

class IDTracker(models.Model):
    name = models.CharField(max_length=50, unique=True)
    last_used = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} - {self.last_used}"

class User(AbstractUser):
    class UserTypes(models.TextChoices):
        ADMIN = 'ADMIN', _('System Administrator')
        COLLECTOR = 'COLLECTOR', _('District Collector')
        OFFICER = 'OFFICER', _('Department Officer')
        PUBLIC = 'PUBLIC', _('Public User')

    user_type = models.CharField(
        max_length=10,
        choices=UserTypes.choices,
        verbose_name=_("User Type"),
        help_text=_("Determines the user's role and permissions in the system")
    )
    phone = models.CharField(max_length=15, null=True, blank=True)

    class Meta:
        verbose_name = _("System User")
        verbose_name_plural = _("System Users")
        ordering = ['username']
        indexes = [
            models.Index(fields=['user_type']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk and not self.username and self.user_type == 'PUBLIC':
            with transaction.atomic():
                tracker, _ = IDTracker.objects.select_for_update().get_or_create(name="public_user")
                tracker.last_used += 1
                tracker.save()

                current_year = datetime.now().year
                self.username = f"GPL{current_year}{tracker.last_used:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

class PublicUserProfile(models.Model):
    """
    Profile model for public users (user_type='PUBLIC').
    Stores personal and location details.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'PUBLIC'},
        related_name='public_profile',
        verbose_name=_("User Account")
    )

    address = models.TextField(verbose_name=_("Address"))
    gender = models.CharField(
        max_length=10,
        choices=[
            ('MALE', 'Male'),
            ('FEMALE', 'Female'),
            ('OTHER', 'Other')
        ],
        verbose_name=_("Gender")
    )
    date_of_birth = models.DateField(verbose_name=_("Date of Birth"))

    thaluk = models.CharField(max_length=100, verbose_name=_("Thaluk"))
    village = models.CharField(max_length=100, verbose_name=_("Village"))
    panchayath = models.CharField(max_length=100, verbose_name=_("Panchayath"))

    district = models.ForeignKey(
    District,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name="District"
)


    class Meta:
        verbose_name = _("Public User Profile")
        verbose_name_plural = _("Public User Profiles")

    def __str__(self):
        return f"Public Profile of {self.user.get_full_name() or self.user.username}"