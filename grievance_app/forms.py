from django import forms
from .models import Grievance


class GrievanceForm(forms.ModelForm):
    class Meta:
        model=Grievance
        fields=['subject','description','department','applicant_name','applicant_address','contact_number','email','district']