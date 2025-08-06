from django import forms
from user.models import User
from .models import DistrictOfficerProfile
from core_app.models import District

class DOCreateUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DOUpdateUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DistrictOfficerProfileForm(forms.ModelForm):
    class Meta:
        model = DistrictOfficerProfile
        fields = ['district', 'is_active']
        widgets = {
            'district': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if hasattr(self.request.user, 'collector_profile'):
            self.fields['district'].initial = self.request.user.collector_profile.district
            self.fields['district'].disabled = True
        elif self.request.user.user_type == 'ADMIN' or self.request.user.is_superuser:
            self.fields['district'].queryset = District.objects.all()
        else:
            self.fields['district'].disabled = True