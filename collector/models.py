from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from user.models import User
from core_app.models import District


class CollectorProfile(models.Model):
    # ────────────────────────────────
    # Core relations
    # ────────────────────────────────
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'COLLECTOR'},
        related_name='collector_profile',
        verbose_name=_("User Account"),
    )

    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        verbose_name=_("Administered District"),
    )

    # ────────────────────────────────
    # Identity and tenure
    # ────────────────────────────────
    collector_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Collector ID"),
    )

    tenure_start = models.DateField(verbose_name=_("Tenure Start Date"))
    tenure_end   = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Tenure End Date"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active Collector"),
        help_text=_("Only one active collector per district."),
    )

    # ────────────────────────────────
    # Profile & notes
    # ────────────────────────────────
    official_address = models.TextField(verbose_name=_("Office Address"))

    handover_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Handover Notes"),
        help_text=_("Optional remarks during handover."),
    )

    profile_picture = models.ImageField(
        upload_to='collector_profiles/',
        null=True,
        blank=True,
        verbose_name=_("Profile Picture"),
        help_text=_("Upload a profile image for the collector."),
    )

    # ────────────────────────────────
    # Audit timestamps
    # ────────────────────────────────
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    # ────────────────────────────────
    # Meta & string
    # ────────────────────────────────
    class Meta:
        verbose_name = _("Collector Profile")
        verbose_name_plural = _("Collector Profiles")
        constraints = [
            # Ensure ONE active collector per district
            models.UniqueConstraint(
                fields=['district'],
                condition=models.Q(is_active=True),
                name='unique_active_collector_per_district',
            )
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Handovered"
        return f"Collector of {self.district} ({status})"
