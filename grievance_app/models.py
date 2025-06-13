from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from core_app.models import Department, District



class Grievance(models.Model):
    """
    Core complaint tracking system with automatic deadlines and status tracking.
    """
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        RESOLVED = 'RESOLVED', _('Resolved')
        REJECTED = 'REJECTED', _('Rejected')
        ESCALATED = 'ESCALATED', _('Escalated')
    
    class PriorityChoices(models.TextChoices):
        LOW = 'LOW', _('Low (30 days)')
        MEDIUM = 'MEDIUM', _('Medium (15 days)')
        HIGH = 'HIGH', _('High (7 days)')
        CRITICAL = 'CRITICAL', _('Critical (3 days)')
    
    class SourceChoices(models.TextChoices):
        WEB = 'WEB', _('Website')
        MOBILE = 'MOBILE', _('Mobile App')
        OFFICE = 'OFFICE', _('Office Visit')
        EMAIL = 'EMAIL', _('Email')
    
    # Core Fields
    grievance_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name=_("Grievance ID")
    )
    date_filed = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Filing Date")
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated")
    )
    
    # Complaint Details
    subject = models.CharField(
        max_length=200,
        verbose_name=_("Subject")
    )
    description = models.TextField(
        verbose_name=_("Detailed Description")
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        verbose_name=_("Responsible Department")
    )
    source = models.CharField(
        max_length=20,
        choices=SourceChoices.choices,
        verbose_name=_("Source Channel")
    )
    
    # Tracking Fields
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        verbose_name=_("Current Status")
    )
    priority = models.CharField(
        max_length=20,
        choices=PriorityChoices.choices,
        default=PriorityChoices.MEDIUM,
        verbose_name=_("Priority Level")
    )
    due_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Resolution Due Date")
    )

    # Applicant Details
    applicant_name = models.CharField(
    max_length=100,
    verbose_name=_("Applicant Name"),
    default="N/A"
    )

    applicant_address = models.TextField(
        verbose_name=_("Applicant Address"),
        help_text=_("Provide full residential address"),
        default="N/A"
    )

    contact_number = models.CharField(
    max_length=15,
    verbose_name=_("Phone Number"),
    default="0000000000"
    )

    email = models.EmailField(
        null=True,
        blank=True,
        verbose_name=_("Email Address")
    )

#for pass the grievance to coresponding collector

    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        verbose_name=_("Department District"),
        default=1  # Or set dynamically in the form
    )
        
    class Meta:
        verbose_name = _("Public Grievance")
        verbose_name_plural = _("Public Grievances")
        ordering = ['-date_filed']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['due_date']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate grievance ID and set due date on creation"""
        if not self.grievance_id:
            last_id = Grievance.objects.aggregate(models.Max('id'))['id__max'] or 0
            self.grievance_id = f"GY-{timezone.now().year}-{last_id+1:04d}"
        
        if not self.due_date:
            days_map = {
                'LOW': 30,
                'MEDIUM': 15,
                'HIGH': 7,
                'CRITICAL': 3
            }
            self.due_date = timezone.now().date() + timedelta(days=days_map[self.priority])
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if grievance is past its due date"""
        return (
            self.status not in ['RESOLVED', 'REJECTED'] 
            and timezone.now().date() > self.due_date
        )