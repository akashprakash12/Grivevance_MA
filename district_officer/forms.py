from django import forms
from user.models import User
from .models import DistrictOfficerProfile
from core_app.models import District


class DOCreateUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}),
        }


class DOUpdateUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}),
        }


class DistrictOfficerProfileForm(forms.ModelForm):
    class Meta:
        model = DistrictOfficerProfile
        fields = ['district', 'is_active', 'profile_picture', 'official_address']
        widgets = {
            'district': forms.Select(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'official_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request:
            user = self.request.user
            if hasattr(user, 'collector_profile'):
                self.fields['district'].initial = user.collector_profile.district
                self.fields['district'].disabled = True
            elif user.user_type == 'ADMIN' or user.is_superuser:
                self.fields['district'].queryset = District.objects.all()
            else:
                self.fields['district'].disabled = True
