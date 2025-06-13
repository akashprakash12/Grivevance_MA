# user/forms.py

from django import forms
from user.models import User, PublicUserProfile

class PublicUserForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance or not self.instance.pk:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
        else:
            self.fields['password'].required = False
            self.fields['confirm_password'].required = False

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password or confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data



class PublicUserProfileForm(forms.ModelForm):
    class Meta:
        model = PublicUserProfile
        fields = ['address', 'gender', 'date_of_birth', 'thaluk', 'village', 'panchayath','district']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
