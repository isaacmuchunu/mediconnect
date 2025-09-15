from django import forms
from django.utils import timezone
from .models import Appointment
from referrals.models import Referral

class AppointmentForm(forms.ModelForm):
    appointment_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'min': timezone.now().date().isoformat()
            }
        ),
        label='Appointment Date'
    )
    
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={
                'type': 'time',
                'class': 'form-control'
            }
        ),
        label='Appointment Time'
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes or special requirements...'
            }
        ),
        required=False,
        label='Notes'
    )
    
    class Meta:
        model = Appointment
        fields = ['status']
        widgets = {
            'status': forms.Select(
                attrs={'class': 'form-control'}
            )
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].initial = 'scheduled'
        
    def clean_appointment_date(self):
        date = self.cleaned_data['appointment_date']
        if date < timezone.now().date():
            raise forms.ValidationError("Appointment date cannot be in the past.")
        return date

class AppointmentSearchForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        ),
        label='From Date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        ),
        label='To Date'
    )
    
    patient_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Search by patient name...'
            }
        ),
        label='Patient Name'
    )

class RescheduleAppointmentForm(forms.ModelForm):
    new_appointment_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'min': timezone.now().date().isoformat()
            }
        ),
        label='New Appointment Date'
    )
    
    new_appointment_time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={
                'type': 'time',
                'class': 'form-control'
            }
        ),
        label='New Appointment Time'
    )
    
    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for rescheduling...'
            }
        ),
        label='Reason for Rescheduling'
    )
    
    class Meta:
        model = Appointment
        fields = []
    
    def clean_new_appointment_date(self):
        date = self.cleaned_data['new_appointment_date']
        if date < timezone.now().date():
            raise forms.ValidationError("New appointment date cannot be in the past.")
        return date