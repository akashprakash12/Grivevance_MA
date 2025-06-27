# user/forms.py

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from user.models import User, PublicUserProfile

class PublicUserForm(forms.ModelForm):
  
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
          
        }
       

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
     

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")
            try:
                validate_password(password, self.instance)
            except ValidationError as e:
                self.add_error('password', e)
        
        return cleaned_data


class PublicUserProfileForm(forms.ModelForm):
    class Meta:
        model = PublicUserProfile
        fields = ['address', 'gender', 'date_of_birth', 'district', 'thaluk', 'village', 'panchayath']
        widgets = {
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'district': forms.Select(attrs={'class': 'form-select'}),
            'thaluk': forms.TextInput(attrs={'class': 'form-control'}),
            'village': forms.TextInput(attrs={'class': 'form-control'}),
            'panchayath': forms.TextInput(attrs={'class': 'form-control'}),
        }