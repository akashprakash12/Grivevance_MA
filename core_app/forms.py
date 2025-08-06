from django import forms
from .models import Department, District


class DeptForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'district']  # assume these are the fields

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Remove 'district' field for collector to avoid validation error
        if request and hasattr(request.user, "collector_profile"):
            self.fields.pop('district')
        elif request and hasattr(request.user, "district_officer_profile"):
            self.fields.pop('district')

class DistrictForm(forms.ModelForm):
    """
    Simple form for creating/updating a District.
    """

    class Meta:
        model = District
        fields = ['code', 'name']
