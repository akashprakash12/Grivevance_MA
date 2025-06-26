from django import forms
from django.forms.widgets import ClearableFileInput
from user.models import User
from .models import CollectorProfile


# ─────────────────────────────────────────────
#  Collector •  User‑creation form
# ─────────────────────────────────────────────
class CollectorCreateUserForm(forms.ModelForm):
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "password"]
        widgets = {
            "first_name":  forms.TextInput(attrs={"class": "form-control"}),
            "last_name":   forms.TextInput(attrs={"class": "form-control"}),
            "email":       forms.EmailInput(attrs={"class": "form-control"}),
            "phone":       forms.TextInput(attrs={"class": "form-control"}),
            "password":    forms.PasswordInput(attrs={"class": "form-control"}),
        }

    # make password + confirm mandatory
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].required = True
        self.fields["confirm_password"].required = True

    # ensure the two passwords match
    def clean(self):
        cleaned = super().clean()
        pwd, cpwd = cleaned.get("password"), cleaned.get("confirm_password")
        if pwd and cpwd and pwd != cpwd:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned


# ─────────────────────────────────────────────
#  Collector •  User‑update form (no password)
# ─────────────────────────────────────────────
class CollectorUpdateUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "email":      forms.EmailInput(attrs={"class": "form-control"}),
            "phone":      forms.TextInput(attrs={"class": "form-control"}),
        }


# ─────────────────────────────────────────────
#  Collector •  Profile form  (create/update)
# ─────────────────────────────────────────────
class CollectorProfileForm(forms.ModelForm):
    class Meta:
        model = CollectorProfile
        fields = ["district", "official_address", "tenure_start", "profile_picture"]
        widgets = {
            "district":          forms.Select(attrs={"class": "form-control"}),
            "official_address":  forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tenure_start":      forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            # ← uses Django’s default ClearableFileInput
            "profile_picture": forms.FileInput(),  # Simple FileInput (no path display)
        }
