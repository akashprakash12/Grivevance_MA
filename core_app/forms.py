from django import forms
from .models import Department, District

class DeptForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'district']

class DistrictForm(forms.ModelForm):
    class Meta:
        model = District
        fields = ['code','name']