from django.db import models
from django.utils import timezone

from core_app.models import Department
from user.models import User
from grievance_app.models import Grievance


class OfficerProfile(models.Model):
    """
    Maps to table officer_officerprofile
    """
    is_hod = models.BooleanField(default=False)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)

    class Meta:
        db_table = "officer_officerprofile"

    def __str__(self):
        return f"{self.user.username} ({'HOD' if self.is_hod else 'Officer'})"


class OfficerIDTracker(models.Model):
    """
    Tracks last auto‑generated officer IDs per department
    """
    last_used = models.IntegerField(default=0)
    department = models.OneToOneField(Department, on_delete=models.CASCADE, unique=True)

    class Meta:
        db_table = "officer_officeridtracker"

    def __str__(self):
        return f"{self.department.code} – {self.last_used}"


class GrievanceAssignment(models.Model):
    assigned_at = models.DateTimeField(default=timezone.now)
    is_primary = models.BooleanField(default=False)

    assigned_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="assignments_made"
    )
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE)
    officer = models.ForeignKey(OfficerProfile, on_delete=models.CASCADE)

    class Meta:
        db_table = "officer_grievanceassignment"

    def __str__(self):
        return f"G{self.grievance_id} → Officer {self.officer_id}"


class GrievanceFlow(models.Model):
    is_completed = models.BooleanField(default=False)
    current_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    current_officer = models.ForeignKey(
        OfficerProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    grievance = models.OneToOneField(Grievance, on_delete=models.CASCADE)

    class Meta:
        db_table = "officer_grievanceflow"

    def __str__(self):
        return f"Flow for G{self.grievance_id}"


class GrievanceStatusLog(models.Model):
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(default=timezone.now)

    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE)

    class Meta:
        db_table = "officer_grievancestatuslog"

    def __str__(self):
        return f"G{self.grievance_id}: {self.old_status} → {self.new_status}"


class GrievanceTransfer(models.Model):
    reason = models.CharField(max_length=20)
    transferred_at = models.DateTimeField(default=timezone.now)

    from_department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="transfers_from"
    )
    to_department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="transfers_to"
    )
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE)
    transferred_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = "officer_grievancetransfer"

    def __str__(self):
        return (
            f"G{self.grievance_id}: {self.from_department.code} → {self.to_department.code}"
        )


class FlowStage(models.Model):
    stage_type = models.CharField(max_length=20)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    officer = models.ForeignKey(
        OfficerProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    flow = models.ForeignKey(GrievanceFlow, on_delete=models.CASCADE)

    class Meta:
        db_table = "officer_flowstage"

    def __str__(self):
        return f"{self.stage_type} – Flow {self.flow_id}"
