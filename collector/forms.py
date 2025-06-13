from django import forms
from user.models import User
from .models import CollectorProfile


# =============================
# Collector User Create Form
# =============================
class CollectorCreateUserForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label="Confirm Password")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # All fields are required for new user creation
        self.fields['password'].required = True
        self.fields['confirm_password'].required = True

    def clean(self):
        # Ensure password and confirm password match
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


# =============================
# Collector User Update Form
# (No password field)
# =============================
class CollectorUpdateUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No password fields shown during update


# =============================
# Collector Profile Form
# (Used in both create and update)
# =============================
class CollectorProfileForm(forms.ModelForm):
    class Meta:
        model = CollectorProfile
        fields = ['district', 'official_address', 'tenure_start', 'profile_picture']

