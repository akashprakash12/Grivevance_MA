from django import forms
from django.core.exceptions import ValidationError
import os
from .models import Grievance
from core_app.models import Department, District

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class GrievanceForm(forms.ModelForm):
    documents = MultipleFileField(
        required=False,
        help_text='Upload supporting documents (max 10MB each)'
    )

    class Meta:
        model = Grievance
        fields = ['subject', 'description', 'department', 'applicant_name', 
                 'applicant_address', 'contact_number', 'email', 'district']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief title of your complaint'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'district': forms.Select(attrs={'class': 'form-select'}),
            'applicant_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10-digit mobile number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your@email.com'
            }),
            'applicant_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Your complete address including postal code'
            }),
        }

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if not contact_number.isdigit():
            raise forms.ValidationError("Phone number should contain only digits.")
        if len(contact_number) < 10:
            raise forms.ValidationError("Phone number should be at least 10 digits.")
        return contact_number

    def clean_documents(self):
        documents = self.cleaned_data.get('documents') or []
        if not isinstance(documents, list):
            documents = [documents]
            
        allowed_extensions = [
            '.jpg', '.jpeg', '.png', '.gif',  # Images
            '.mp4', '.avi', '.mov',  # Videos
            '.mp3', '.wav',  # Audio
            '.pdf', '.doc', '.docx'  # Documents
        ]
        max_size = 10 * 1024 * 1024  # 10MB in bytes

        for document in documents:
            if document:  # Check if document exists (might be None if not required)
                ext = os.path.splitext(document.name)[1].lower()
                if ext not in allowed_extensions:
                    raise ValidationError(
                        f"Unsupported file type: {ext}. Allowed types: {', '.join(allowed_extensions)}"
                    )
                if document.size > max_size:
                    raise ValidationError(
                        f"File {document.name} exceeds 10MB limit."
                    )
        return documents

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        instance = kwargs.get('instance')
        if instance:
            # If editing an existing instance
            self.fields['district'].initial = instance.district
            self.fields['department'].queryset = Department.objects.filter(district=instance.district)
        else:
            # For new instances
            self.fields['department'].queryset = Department.objects.none()

        # Handle AJAX department loading
        if 'district' in self.data:
            try:
                district_code = self.data.get('district')
                self.fields['department'].queryset = Department.objects.filter(
                    district__code=district_code
                ).order_by('name')
            except (ValueError, TypeError):
                pass