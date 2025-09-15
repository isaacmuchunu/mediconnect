from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import date, timedelta
import re

from .models import (
    Patient, MedicalHistory, ConsentForm, ConsentCategory, MedicalCondition,
    PatientCondition, Medication, PatientMedication, Allergy, VitalSigns,
    DataSharingAgreement, PatientDocument, HealthcareProvider,
    PatientProviderRelationship, EmergencyContact, InsurancePolicy,
    PatientNote, PatientPreferences, ComplianceReport
)

User = get_user_model()

class BaseModelForm(forms.ModelForm):
    """Base form with common functionality"""
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Add CSS classes for styling
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.DateTimeInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'datetime-local'})
            elif isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})

class PatientRegistrationForm(BaseModelForm):
    """Comprehensive patient registration form"""
    
    # Password fields for user creation
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('Password must be at least 8 characters long')
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('Enter the same password as before, for verification')
    )
    
    # Terms and conditions
    accept_terms = forms.BooleanField(
        label=_('I accept the Terms and Conditions'),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    privacy_policy = forms.BooleanField(
        label=_('I have read and agree to the Privacy Policy'),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Patient
        fields = [
            'patient_id', 'first_name', 'middle_name', 'last_name', 'preferred_name',
            'date_of_birth', 'gender', 'marital_status', 'phone_primary', 'phone_secondary',
            'email', 'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country', 'emergency_contact_1_name', 'emergency_contact_1_phone',
            'emergency_contact_1_relationship', 'emergency_contact_2_name', 'emergency_contact_2_phone',
            'emergency_contact_2_relationship', 'blood_type', 'preferred_language', 'religion'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'marital_status': forms.Select(attrs={'class': 'form-select'}),
            'blood_type': forms.Select(attrs={'class': 'form-select'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state_province': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_patient_id(self):
        """Validate patient ID format and uniqueness"""
        patient_id = self.cleaned_data.get('patient_id')
        if patient_id:
            # Check format (example: PAT-2024-001234)
            pattern = r'^PAT-\d{4}-\d{6}$'
            if not re.match(pattern, patient_id):
                raise ValidationError(_('Patient ID must be in format PAT-YYYY-XXXXXX'))
            
            # Check uniqueness
            if Patient.objects.filter(patient_id=patient_id).exists():
                raise ValidationError(_('This Patient ID already exists'))
        
        return patient_id
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if email and Patient.objects.filter(email=email).exists():
            raise ValidationError(_('A patient with this email already exists'))
        return email
    
    def clean_phone_primary(self):
        """Validate and format phone number"""
        phone = self.cleaned_data.get('phone_primary')
        if phone:
            # Remove formatting characters
            cleaned_phone = re.sub(r'[^\d+]', '', phone)
            if len(cleaned_phone) < 10:
                raise ValidationError(_('Phone number must be at least 10 digits'))
        return phone
    
    def clean_date_of_birth(self):
        """Validate birth date"""
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > date.today():
                raise ValidationError(_('Birth date cannot be in the future'))
            if dob < date.today() - timedelta(days=120*365):
                raise ValidationError(_('Birth date seems unrealistic'))
        return dob
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(_('Passwords do not match'))
        
        # Validate emergency contacts
        ec1_name = cleaned_data.get('emergency_contact_1_name')
        ec1_phone = cleaned_data.get('emergency_contact_1_phone')
        
        if ec1_name and not ec1_phone:
            raise ValidationError(_('Emergency contact 1 phone number is required'))
        if ec1_phone and not ec1_name:
            raise ValidationError(_('Emergency contact 1 name is required'))
        
        return cleaned_data

class PatientUpdateForm(BaseModelForm):
    """Form for updating existing patient information"""
    
    class Meta:
        model = Patient
        fields = [
            'first_name', 'middle_name', 'last_name', 'preferred_name',
            'phone_primary', 'phone_secondary', 'email', 'address_line1',
            'address_line2', 'city', 'state_province', 'postal_code', 'country',
            'emergency_contact_1_name', 'emergency_contact_1_phone', 'emergency_contact_1_relationship',
            'emergency_contact_2_name', 'emergency_contact_2_phone', 'emergency_contact_2_relationship',
            'preferred_language', 'religion'
        ]
        widgets = {
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state_province': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
        }

class MedicalHistoryForm(BaseModelForm):
    """Comprehensive medical history form"""
    
    class Meta:
        model = MedicalHistory
        fields = [
            'allergies', 'allergy_severity', 'chronic_conditions', 'past_illnesses',
            'mental_health_history', 'current_medications', 'medication_allergies',
            'surgeries', 'surgical_complications', 'family_history', 'genetic_conditions',
            'smoking_status', 'alcohol_consumption', 'exercise_frequency', 'diet_restrictions',
            'additional_notes'
        ]
        widgets = {
            'allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 
                                             'placeholder': _('List all known allergies, reactions, and triggers')}),
            'chronic_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'past_illnesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'mental_health_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'current_medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                        'placeholder': _('Include medication name, dosage, and frequency')}),
            'medication_allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'surgeries': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                             'placeholder': _('Include date, procedure, and location')}),
            'surgical_complications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'family_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'genetic_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'smoking_status': forms.Select(attrs={'class': 'form-select'}),
            'alcohol_consumption': forms.Select(attrs={'class': 'form-select'}),
            'exercise_frequency': forms.TextInput(attrs={'class': 'form-control',
                                                        'placeholder': _('e.g., 3 times per week')}),
            'diet_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'additional_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def save(self, commit=True):
        """Save with current user tracking"""
        instance = super().save(commit=False)
        if self.request and self.request.user:
            instance.last_updated_by = self.request.user
        if commit:
            instance.save()
        return instance

class ConsentForm(BaseModelForm):
    """Digital consent form"""
    
    digital_signature = forms.CharField(
        label=_('Digital Signature'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Type your full name to sign')}),
        help_text=_('By typing your name, you provide digital consent')
    )
    
    acknowledge_terms = forms.BooleanField(
        label=_('I acknowledge that I have read and understood the terms'),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = ConsentForm
        fields = ['category', 'consent_given', 'consent_text', 'signature_method']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'consent_given': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'consent_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'readonly': True}),
            'signature_method': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_digital_signature(self):
        """Validate digital signature matches patient name"""
        signature = self.cleaned_data.get('digital_signature')
        if signature and hasattr(self, 'instance') and self.instance.patient:
            patient_name = self.instance.patient.full_name.lower()
            if signature.lower().strip() != patient_name:
                raise ValidationError(_('Digital signature must match your full name exactly'))
        return signature
    
    def clean(self):
        """Validate consent is actually given"""
        cleaned_data = super().clean()
        consent_given = cleaned_data.get('consent_given')
        acknowledge_terms = cleaned_data.get('acknowledge_terms')
        
        if not consent_given:
            raise ValidationError(_('You must provide consent to proceed'))
        
        if not acknowledge_terms:
            raise ValidationError(_('You must acknowledge the terms to proceed'))
        
        return cleaned_data

class PatientConditionForm(BaseModelForm):
    """Form for adding/editing patient medical conditions"""
    
    condition_search = forms.CharField(
        label=_('Search Condition'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Start typing to search conditions...'),
            'data-toggle': 'autocomplete'
        }),
        help_text=_('Search for a condition or add a custom one')
    )
    
    class Meta:
        model = PatientCondition
        fields = ['condition', 'diagnosed_date', 'severity', 'status', 'notes']
        widgets = {
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'diagnosed_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit conditions to active ones
        self.fields['condition'].queryset = MedicalCondition.objects.filter(is_active=True)
    
    def clean_diagnosed_date(self):
        """Validate diagnosis date"""
        diagnosed_date = self.cleaned_data.get('diagnosed_date')
        if diagnosed_date and diagnosed_date > date.today():
            raise ValidationError(_('Diagnosis date cannot be in the future'))
        return diagnosed_date

class PatientMedicationForm(BaseModelForm):
    """Form for patient medications"""
    
    medication_search = forms.CharField(
        label=_('Search Medication'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Start typing medication name...'),
            'data-toggle': 'autocomplete'
        })
    )
    
    class Meta:
        model = PatientMedication
        fields = [
            'medication', 'dosage', 'frequency', 'route', 'start_date', 
            'end_date', 'status', 'indication', 'instructions'
        ]
        widgets = {
            'medication': forms.Select(attrs={'class': 'form-select'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 
                                           'placeholder': _('e.g., 10mg, 2 tablets')}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 
                                              'placeholder': _('e.g., twice daily, every 8 hours')}),
            'route': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'indication': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['medication'].queryset = Medication.objects.filter(is_active=True)
        self.fields['end_date'].required = False
    
    def clean(self):
        """Validate date logic"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        status = cleaned_data.get('status')
        
        if start_date and start_date > date.today():
            raise ValidationError(_('Start date cannot be in the future'))
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError(_('End date cannot be before start date'))
        
        if status == 'completed' and not end_date:
            raise ValidationError(_('End date is required for completed medications'))
        
        return cleaned_data

class AllergyForm(BaseModelForm):
    """Form for patient allergies"""
    
    class Meta:
        model = Allergy
        fields = [
            'allergen_type', 'allergen_name', 'severity', 'symptoms',
            'onset_date', 'last_reaction_date', 'verification_method', 'notes'
        ]
        widgets = {
            'allergen_type': forms.Select(attrs={'class': 'form-select'}),
            'allergen_name': forms.TextInput(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                            'placeholder': _('Describe the allergic reaction symptoms')}),
            'onset_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'last_reaction_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'verification_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        """Validate allergy dates"""
        cleaned_data = super().clean()
        onset_date = cleaned_data.get('onset_date')
        last_reaction_date = cleaned_data.get('last_reaction_date')
        
        if onset_date and onset_date > date.today():
            raise ValidationError(_('Onset date cannot be in the future'))
        
        if last_reaction_date and last_reaction_date > date.today():
            raise ValidationError(_('Last reaction date cannot be in the future'))
        
        if onset_date and last_reaction_date and last_reaction_date < onset_date:
            raise ValidationError(_('Last reaction date cannot be before onset date'))
        
        return cleaned_data

class VitalSignsForm(BaseModelForm):
    """Form for recording vital signs"""
    
    class Meta:
        model = VitalSigns
        fields = [
            'height_cm', 'weight_kg', 'systolic_bp', 'diastolic_bp',
            'heart_rate', 'temperature_c', 'respiratory_rate', 'oxygen_saturation',
            'measurement_date', 'notes'
        ]
        widgets = {
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1',
                                                'placeholder': _('Height in centimeters')}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1',
                                                'placeholder': _('Weight in kilograms')}),
            'systolic_bp': forms.NumberInput(attrs={'class': 'form-control',
                                                  'placeholder': _('Systolic pressure')}),
            'diastolic_bp': forms.NumberInput(attrs={'class': 'form-control',
                                                   'placeholder': _('Diastolic pressure')}),
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control',
                                                 'placeholder': _('Beats per minute')}),
            'temperature_c': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1',
                                                    'placeholder': _('Temperature in Celsius')}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control',
                                                       'placeholder': _('Breaths per minute')}),
            'oxygen_saturation': forms.NumberInput(attrs={'class': 'form-control',
                                                        'placeholder': _('Oxygen saturation %')}),
            'measurement_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        """Validate vital signs ranges"""
        cleaned_data = super().clean()
        
        # Blood pressure validation
        systolic = cleaned_data.get('systolic_bp')
        diastolic = cleaned_data.get('diastolic_bp')
        
        if systolic and diastolic and systolic <= diastolic:
            raise ValidationError(_('Systolic blood pressure must be higher than diastolic'))
        
        # Temperature validation
        temperature = cleaned_data.get('temperature_c')
        if temperature and (temperature < 32 or temperature > 44):
            raise ValidationError(_('Temperature reading seems unrealistic'))
        
        # Oxygen saturation validation
        o2_sat = cleaned_data.get('oxygen_saturation')
        if o2_sat and o2_sat < 70:
            raise ValidationError(_('Oxygen saturation below 70% requires immediate medical attention'))
        
        return cleaned_data

class EmergencyContactForm(BaseModelForm):
    """Form for emergency contacts"""
    
    class Meta:
        model = EmergencyContact
        fields = [
            'first_name', 'last_name', 'relationship', 'phone_primary',
            'phone_secondary', 'email', 'address', 'priority_order',
            'can_make_medical_decisions', 'preferred_contact_method',
            'available_24_7', 'availability_notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'relationship': forms.TextInput(attrs={'class': 'form-control',
                                                 'placeholder': _('e.g., Spouse, Parent, Sibling')}),
            'phone_primary': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_secondary': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'can_make_medical_decisions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'preferred_contact_method': forms.Select(attrs={'class': 'form-select'}),
            'available_24_7': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'availability_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class InsurancePolicyForm(BaseModelForm):
    """Form for insurance policy information"""
    
    class Meta:
        model = InsurancePolicy
        fields = [
            'insurance_company', 'policy_number', 'group_number', 'member_id',
            'policy_type', 'effective_date', 'expiration_date', 'coverage_details',
            'copay_amount', 'deductible_amount', 'insurance_phone', 'claims_address'
        ]
        widgets = {
            'insurance_company': forms.TextInput(attrs={'class': 'form-control'}),
            'policy_number': forms.TextInput(attrs={'class': 'form-control'}),
            'group_number': forms.TextInput(attrs={'class': 'form-control'}),
            'member_id': forms.TextInput(attrs={'class': 'form-control'}),
            'policy_type': forms.Select(attrs={'class': 'form-select'}),
            'effective_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expiration_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'coverage_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'copay_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deductible_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'insurance_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'claims_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        """Validate insurance dates"""
        cleaned_data = super().clean()
        effective_date = cleaned_data.get('effective_date')
        expiration_date = cleaned_data.get('expiration_date')
        
        if effective_date and expiration_date and expiration_date <= effective_date:
            raise ValidationError(_('Expiration date must be after effective date'))
        
        return cleaned_data

class PatientNoteForm(BaseModelForm):
    """Form for clinical notes"""
    
    class Meta:
        model = PatientNote
        fields = [
            'note_type', 'title', 'content', 'visit_date', 'department',
            'confidentiality_level'
        ]
        widgets = {
            'note_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'confidentiality_level': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['visit_date'].initial = timezone.now()

class DataSharingAgreementForm(BaseModelForm):
    """Form for data sharing agreements"""
    
    patient_signature = forms.CharField(
        label=_('Patient Digital Signature'),
        widget=forms.TextInput(attrs={'class': 'form-control', 
                                    'placeholder': _('Type your full name to authorize data sharing')}),
        help_text=_('Your digital signature authorizes this data sharing agreement')
    )
    
    class Meta:
        model = DataSharingAgreement
        fields = [
            'sharing_type', 'recipient_organization', 'recipient_contact', 'recipient_email',
            'include_demographics', 'include_medical_history', 'include_medications',
            'include_allergies', 'include_vital_signs', 'include_lab_results',
            'purpose', 'data_retention_period', 'effective_date', 'expiration_date'
        ]
        widgets = {
            'sharing_type': forms.Select(attrs={'class': 'form-select'}),
            'recipient_organization': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'include_demographics': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_medical_history': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_medications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_allergies': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_vital_signs': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_lab_results': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'data_retention_period': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'effective_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'expiration_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
    
    def clean_patient_signature(self):
        """Validate patient signature"""
        signature = self.cleaned_data.get('patient_signature')
        if signature and hasattr(self, 'instance') and self.instance.patient:
            patient_name = self.instance.patient.full_name.lower()
            if signature.lower().strip() != patient_name:
                raise ValidationError(_('Signature must match patient full name exactly'))
        return signature
    
    def clean(self):
        """Validate sharing agreement"""
        cleaned_data = super().clean()
        effective_date = cleaned_data.get('effective_date')
        expiration_date = cleaned_data.get('expiration_date')
        
        if effective_date and expiration_date and expiration_date <= effective_date:
            raise ValidationError(_('Expiration date must be after effective date'))
        
        # Ensure at least one data category is selected
        data_categories = [
            cleaned_data.get('include_demographics'),
            cleaned_data.get('include_medical_history'),
            cleaned_data.get('include_medications'),
            cleaned_data.get('include_allergies'),
            cleaned_data.get('include_vital_signs'),
            cleaned_data.get('include_lab_results')
        ]
        if not any(data_categories):
            raise ValidationError(_('At least one data category must be selected for sharing'))
        
        return cleaned_data

class ConsentCategoryForm(BaseModelForm):
    """Form for consent categories"""
    
    class Meta:
        model = ConsentCategory
        fields = ['name', 'description', 'is_required', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

class MedicalConditionForm(BaseModelForm):
    """Form for medical conditions"""
    
    class Meta:
        model = MedicalCondition
        fields = ['code', 'name', 'category', 'description', 'is_chronic']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_chronic': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MedicationForm(BaseModelForm):
    """Form for medications"""
    
    class Meta:
        model = Medication
        fields = [
            'name', 'generic_name', 'drug_class', 'manufacturer',
            'ndc_number', 'dosage_forms', 'contraindications', 'side_effects'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'drug_class': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'ndc_number': forms.TextInput(attrs={'class': 'form-control'}),
            'dosage_forms': forms.TextInput(attrs={'class': 'form-control'}),
            'contraindications': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'side_effects': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class PatientDocumentForm(BaseModelForm):
    """Form for patient documents"""
    
    file = forms.FileField(
        label=_('Upload Document'),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = PatientDocument
        fields = [
            'document_type', 'title', 'description', 'file_name',
            'file_size', 'mime_type', 'file_hash', 'is_confidential'
        ]
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'file_name': forms.TextInput(attrs={'class': 'form-control'}),
            'file_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'mime_type': forms.TextInput(attrs={'class': 'form-control'}),
            'file_hash': forms.TextInput(attrs={'class': 'form-control'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class HealthcareProviderForm(BaseModelForm):
    """Form for healthcare providers"""
    
    class Meta:
        model = HealthcareProvider
        fields = [
            'name', 'provider_type', 'address', 'phone', 'email',
            'website', 'license_number', 'specialties',
            'is_preferred_provider', 'accepts_insurance'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'provider_type': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'specialties': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_preferred_provider': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_insurance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PatientProviderRelationshipForm(BaseModelForm):
    """Form for patient-provider relationships"""
    
    class Meta:
        model = PatientProviderRelationship
        fields = ['provider', 'relationship_type', 'start_date', 'end_date', 'status', 'notes']
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select'}),
            'relationship_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError(_('End date cannot be before start date'))
        
        return cleaned_data

class PatientPreferencesForm(BaseModelForm):
    """Form for patient preferences"""
    
    class Meta:
        model = PatientPreferences
        fields = [
            'preferred_communication', 'appointment_reminders', 'medication_reminders',
            'health_tips', 'marketing_communications', 'preferred_appointment_time',
            'interpreter_needed', 'interpreter_language', 'mobility_assistance',
            'hearing_assistance', 'visual_assistance', 'allow_voicemail',
            'allow_family_discussion', 'special_instructions'
        ]
        widgets = {
            'preferred_communication': forms.Select(attrs={'class': 'form-select'}),
            'appointment_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'medication_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'health_tips': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'marketing_communications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'preferred_appointment_time': forms.Select(attrs={'class': 'form-select'}),
            'interpreter_needed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'interpreter_language': forms.TextInput(attrs={'class': 'form-control'}),
            'mobility_assistance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hearing_assistance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'visual_assistance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_voicemail': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_family_discussion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'special_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ComplianceReportForm(BaseModelForm):
    """Form for compliance reports"""
    
    class Meta:
        model = ComplianceReport
        fields = [
            'report_type', 'title', 'description', 'date_from', 'date_to',
            'department_filter', 'findings', 'recommendations'
        ]
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'date_from': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'date_to': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'department_filter': forms.TextInput(attrs={'class': 'form-control'}),
            'findings': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_to < date_from:
            raise ValidationError(_('End date must be after start date'))
        
        return cleaned_data