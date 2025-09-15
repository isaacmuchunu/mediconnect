from django import forms
from django.contrib.auth import get_user_model
from .models import Referral
from patients.models import Patient
from doctors.models import DoctorProfile

User = get_user_model()

class ReferralForm(forms.ModelForm):
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': 'Select Patient'
        }),
        empty_label="Select a patient"
    )
    
    target_doctor = forms.ModelChoiceField(
        queryset=DoctorProfile.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': 'Select Specialist Doctor'
        }),
        empty_label="Select a specialist"
    )
    
    specialty = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter specialty required'
        })
    )
    
    priority = forms.ChoiceField(
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        initial='medium'
    )
    
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe the reason for referral'
        })
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional notes (optional)'
        })
    )
    
    attachments = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control'
        })
    )
    
    ambulance_required = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = Referral
        fields = ['patient', 'target_doctor', 'specialty', 'priority', 'reason', 'notes', 'attachments', 'ambulance_required']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filter doctors based on user's hospital or all if admin
            if hasattr(user, 'doctor_profile'):
                self.fields['target_doctor'].queryset = DoctorProfile.objects.exclude(id=user.doctor_profile.id)

class ReferralSearchForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Referral.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    priority = forms.ChoiceField(
        choices=[('', 'All Priorities'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    specialty = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by specialty'
        })
    )
    
    patient_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient name'
        })
    )
    
    doctor_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by doctor name'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

class ReferralResponseForm(forms.ModelForm):
    response_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Add your response notes'
        })
    )
    
    class Meta:
        model = Referral
        fields = ['response_notes']

class ReferralUpdateForm(forms.ModelForm):
    class Meta:
        model = Referral
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }