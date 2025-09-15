from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
import re

from .models import (
    DoctorProfile, Hospital, Specialty, Availability, 
    DoctorReview, EmergencyContact
)


class DoctorRegistrationForm(forms.ModelForm):
    """Form for doctor registration"""
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput(), min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    
    # Terms and conditions
    agree_to_terms = forms.BooleanField(
        required=True,
        error_messages={"required": "You must agree to the terms and conditions"}
    )

    class Meta:
        model = DoctorProfile
        fields = [
            'first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth',
            'license_number', 'license_state', 'license_expiry_date', 'npi_number',
            'phone', 'office_address', 'city', 'state', 'zip_code',
            'medical_school', 'graduation_year', 'residency_program',
            'primary_specialty', 'primary_hospital', 'bio', 'years_of_experience',
            'languages_spoken', 'profile_photo'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'license_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 2000}),
            'office_address': forms.Textarea(attrs={'rows': 3}),
            'years_of_experience': forms.NumberInput(attrs={'min': 0, 'max': 60}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['primary_specialty'].queryset = Specialty.objects.filter(is_active=True)
        self.fields['primary_hospital'].queryset = Hospital.objects.filter(is_active=True)

        # Add CSS classes for styling
        for field_name, field in self.fields.items():
            if field_name not in ['agree_to_terms']:
                field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = True

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_license_number(self):
        license_number = self.cleaned_data['license_number']
        if DoctorProfile.objects.filter(license_number=license_number).exists():
            raise ValidationError("A doctor with this license number is already registered.")
        return license_number

    def clean_npi_number(self):
        npi_number = self.cleaned_data['npi_number']
        if not re.match(r'^\d{10}$', npi_number):
            raise ValidationError("NPI number must be exactly 10 digits.")
        if DoctorProfile.objects.filter(npi_number=npi_number).exists():
            raise ValidationError("A doctor with this NPI number is already registered.")
        return npi_number

    def clean_license_expiry_date(self):
        expiry_date = self.cleaned_data['license_expiry_date']
        if expiry_date <= date.today():
            raise ValidationError("License expiry date must be in the future.")
        return expiry_date

    def clean_date_of_birth(self):
        birth_date = self.cleaned_data['date_of_birth']
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        if age < 22:
            raise ValidationError("Doctor must be at least 22 years old.")
        if age > 100:
            raise ValidationError("Please enter a valid birth date.")
        return birth_date

    def clean_graduation_year(self):
        graduation_year = self.cleaned_data['graduation_year']
        current_year = date.today().year
        
        if graduation_year < 1950:
            raise ValidationError("Graduation year seems too old.")
        if graduation_year > current_year:
            raise ValidationError("Graduation year cannot be in the future.")
        return graduation_year

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords do not match.")

        return cleaned_data


class DoctorProfileUpdateForm(forms.ModelForm):
    """Form for updating doctor profile"""

    class Meta:
        model = DoctorProfile
        fields = [
            'first_name', 'last_name', 'middle_name', 'gender',
            'phone', 'emergency_phone', 'office_address', 'city', 'state', 'zip_code',
            'bio', 'years_of_experience', 'languages_spoken', 'profile_photo',
            'board_certifications', 'fellowship_programs',
            'primary_hospital', 'specialties', 'affiliated_hospitals',
            'consultation_fee', 'accepts_insurance', 'telehealth_available',
            'emergency_availability', 'accepts_referrals', 'max_patients_per_day'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 2000}),
            'office_address': forms.Textarea(attrs={'rows': 3}),
            'board_certifications': forms.Textarea(attrs={'rows': 2}),
            'fellowship_programs': forms.Textarea(attrs={'rows': 2}),
            'years_of_experience': forms.NumberInput(attrs={'min': 0, 'max': 60}),
            'consultation_fee': forms.NumberInput(attrs={'min': 0, 'step': 0.01}),
            'max_patients_per_day': forms.NumberInput(attrs={'min': 1, 'max': 100}),
            'specialties': forms.CheckboxSelectMultiple(),
            'affiliated_hospitals': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['specialties'].queryset = Specialty.objects.filter(is_active=True)
        self.fields['affiliated_hospitals'].queryset = Hospital.objects.filter(is_active=True)
        self.fields['primary_hospital'].queryset = Hospital.objects.filter(is_active=True)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            if field_name not in ['specialties', 'affiliated_hospitals']:
                field.widget.attrs['class'] = 'form-control'


class DoctorSearchForm(forms.Form):
    """Form for searching doctors"""
    q = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by name, specialty, or hospital',
            'class': 'form-control'
        })
    )
    specialty = forms.ModelChoiceField(
        queryset=Specialty.objects.filter(is_active=True),
        required=False,
        empty_label="All Specialties",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'City, State, or ZIP',
            'class': 'form-control'
        })
    )
    hospital = forms.ModelChoiceField(
        queryset=Hospital.objects.filter(is_active=True),
        required=False,
        empty_label="All Hospitals",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    min_rating = forms.ChoiceField(
        choices=[
            ('', 'Any Rating'),
            ('3.0', '3+ Stars'),
            ('4.0', '4+ Stars'),
            ('4.5', '4.5+ Stars'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    gender = forms.ChoiceField(
        choices=[('', 'Any Gender')] + DoctorProfile.GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    accepts_insurance = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    telehealth = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    emergency_available = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('name', 'Name'),
            ('rating', 'Rating'),
            ('experience', 'Experience'),
            ('location', 'Location'),
        ],
        required=False,
        initial='name',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class AvailabilityForm(forms.ModelForm):
    """Form for creating/updating availability slots"""

    class Meta:
        model = Availability
        fields = [
            'date', 'start_time', 'end_time', 'slot_duration',
            'max_patients', 'location', 'appointment_type', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'slot_duration': forms.NumberInput(attrs={'min': 15, 'max': 120, 'step': 15, 'class': 'form-control'}),
            'max_patients': forms.NumberInput(attrs={'min': 1, 'max': 20, 'class': 'form-control'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'appointment_type': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs['min'] = date.today().strftime('%Y-%m-%d')

    def clean_date(self):
        d = self.cleaned_data.get("date")
        if d and d < timezone.now().date():
            raise ValidationError("Availability date cannot be in the past.")
        return d

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time and start_time >= end_time:
            raise ValidationError("End time must be after start time.")
        
        return cleaned_data


class DoctorReviewForm(forms.ModelForm):
    """Form for submitting a doctor review."""
    class Meta:
        model = DoctorReview
        fields = [
            'reviewer_name', 'reviewer_email', 'rating', 'review_title', 'review_text',
            'bedside_manner_rating', 'communication_rating', 'expertise_rating',
            'visit_date', 'would_recommend'
        ]
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'review_text': forms.Textarea(attrs={'rows': 4}),
            'bedside_manner_rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'communication_rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'expertise_rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'visit_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

class EmergencyContactForm(forms.ModelForm):
    """Form for doctor's emergency contact."""
    class Meta:
        model = EmergencyContact
        fields = ['name', 'relationship', 'phone', 'email', 'is_primary']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'relationship': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'