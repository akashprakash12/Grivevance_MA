from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from core_app.models import District



class DistrictOfficerIDTracker(models.Model):
    """
    Keeps track of the last sequential number issued for each district.
    """
    district    = models.OneToOneField(District, on_delete=models.CASCADE)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "district_officer_id_tracker"

    def __str__(self):
        return f"{self.district.code}: {self.last_number}"

class DistrictOfficerProfile(models.Model):
    officer_id     = models.CharField(max_length=12, unique=True)
    user           = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    district       = models.OneToOneField(District, on_delete=models.CASCADE, null=False, blank=False)  # ← strict one-to-one
    is_active      = models.BooleanField(default=True)
    assigned_on    = models.DateField(auto_now_add=True)
    is_first_login = models.BooleanField(default=True)

    class Meta:
        db_table  = "district_officer_profile"
        ordering  = ["-assigned_on"]

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{self.officer_id} – {full_name}"
