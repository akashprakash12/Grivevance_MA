from sys import flags
from django.db import models
from django.conf import settings
from collector.models import CollectorProfile
from core_app.models import District


class DistrictOfficerIDTracker(models.Model):
    district = models.OneToOneField(District, on_delete=models.CASCADE)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "district_officer_id_tracker"

    def __str__(self):
        return f"{self.district.code}: {self.last_number}"


class DistrictOfficerProfile(models.Model):
    officer_id = models.CharField(max_length=12, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="district_officer_profile")
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    assigned_on = models.DateField(auto_now_add=True)
    is_first_login = models.BooleanField(default=True)
    profile_picture = models.ImageField(
        upload_to='DO_profiles/',
        null=True,
        blank=True,
        verbose_name="Profile Picture",
        help_text="Upload a profile image for the district officer.",
    )
    official_address = models.TextField(verbose_name="Office Address", default="NA")
    created_by = models.ForeignKey(
            CollectorProfile,
            on_delete=models.PROTECT,
            null=False,
            blank=False,
    )
    class Meta:
            db_table = "district_officer_profile"
            ordering = ["-assigned_on"]
            

    def __str__(self):
        full_name = self.user.get_full_name().strip() or self.user.username
        return f"{self.officer_id} – {full_name}"

