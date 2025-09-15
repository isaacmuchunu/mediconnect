"""
Emergency Call Management Forms
Professional forms for emergency call intake and management
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.geos import Point

from .models import EmergencyCall, CallPriorityAssessment


class EmergencyCallForm(forms.ModelForm):
    """Comprehensive emergency call intake form"""
    
    class Meta:
        model = EmergencyCall
        fields = [
            'caller_phone', 'caller_name', 'caller_relationship',
            'call_type', 'priority', 'incident_address', 'landmark_description',
            'access_instructions', 'patient_name', 'patient_age', 'patient_gender',
            'patient_consciousness', 'patient_breathing', 'chief_complaint',
            'symptoms_description', 'medical_history', 'medications', 'allergies',
            'special_instructions', 'hazards_present', 'hazard_description',
            'police_required', 'fire_required', 'call_notes'
        ]
        
        widgets = {
            'caller_phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Enter caller phone number (e.g., +1-555-123-4567)',
                'pattern': r'^\+?1?\d{9,15}$'
            }),
            'caller_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Enter caller full name'
            }),
            'caller_relationship': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Relationship to patient (e.g., spouse, parent, self)'
            }),
            'call_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200'
            }),
            'incident_address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Enter complete incident address with apartment/unit number',
                'rows': 3
            }),
            'landmark_description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Nearby landmarks, cross streets, or identifying features',
                'rows': 2
            }),
            'access_instructions': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Special access instructions (gate codes, elevator, etc.)',
                'rows': 2
            }),
            'patient_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Patient full name'
            }),
            'patient_age': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Patient age in years',
                'min': 0,
                'max': 150
            }),
            'patient_gender': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200'
            }),
            'patient_consciousness': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200'
            }),
            'patient_breathing': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200'
            }),
            'chief_complaint': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Primary reason for emergency call (what happened?)',
                'rows': 3
            }),
            'symptoms_description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Detailed description of symptoms and current condition',
                'rows': 4
            }),
            'medical_history': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Relevant medical history, chronic conditions, recent surgeries',
                'rows': 3
            }),
            'medications': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Current medications and dosages',
                'rows': 3
            }),
            'allergies': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Known allergies to medications, foods, or other substances',
                'rows': 2
            }),
            'special_instructions': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Special instructions for responding crew',
                'rows': 3
            }),
            'hazards_present': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'hazard_description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Describe any hazards present at the scene',
                'rows': 2
            }),
            'police_required': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'fire_required': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'call_notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Additional notes about the call',
                'rows': 4
            }),
        }
        
        labels = {
            'caller_phone': _('Caller Phone Number *'),
            'caller_name': _('Caller Name'),
            'caller_relationship': _('Relationship to Patient'),
            'call_type': _('Emergency Type *'),
            'priority': _('Priority Level *'),
            'incident_address': _('Incident Address *'),
            'landmark_description': _('Landmarks/Cross Streets'),
            'access_instructions': _('Access Instructions'),
            'patient_name': _('Patient Name'),
            'patient_age': _('Patient Age'),
            'patient_gender': _('Patient Gender'),
            'patient_consciousness': _('Consciousness Level'),
            'patient_breathing': _('Breathing Status'),
            'chief_complaint': _('Chief Complaint *'),
            'symptoms_description': _('Symptoms Description'),
            'medical_history': _('Medical History'),
            'medications': _('Current Medications'),
            'allergies': _('Known Allergies'),
            'special_instructions': _('Special Instructions'),
            'hazards_present': _('Hazards Present at Scene'),
            'hazard_description': _('Hazard Description'),
            'police_required': _('Police Response Required'),
            'fire_required': _('Fire Department Required'),
            'call_notes': _('Call Notes'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields required
        self.fields['caller_phone'].required = True
        self.fields['call_type'].required = True
        self.fields['priority'].required = True
        self.fields['incident_address'].required = True
        self.fields['chief_complaint'].required = True
        
        # Add help text
        self.fields['caller_phone'].help_text = 'Include country code if international'
        self.fields['patient_age'].help_text = 'Enter age in years (0-150)'
        self.fields['chief_complaint'].help_text = 'Brief description of the primary emergency'
        
        # Set initial priority based on call type
        if 'call_type' in self.data:
            call_type = self.data.get('call_type')
            if call_type in ['cardiac', 'respiratory', 'trauma']:
                self.fields['priority'].initial = 'emergency'
            elif call_type in ['medical', 'psychiatric']:
                self.fields['priority'].initial = 'urgent'
    
    def clean_caller_phone(self):
        phone = self.cleaned_data.get('caller_phone')
        if phone:
            # Remove all non-digit characters except +
            import re
            cleaned_phone = re.sub(r'[^\d+]', '', phone)
            if not re.match(r'^\+?1?\d{9,15}$', cleaned_phone):
                raise ValidationError('Please enter a valid phone number.')
            return cleaned_phone
        return phone
    
    def clean_patient_age(self):
        age = self.cleaned_data.get('patient_age')
        if age is not None and (age < 0 or age > 150):
            raise ValidationError('Please enter a valid age between 0 and 150.')
        return age
    
    def clean(self):
        cleaned_data = super().clean()
        
        # If hazards are present, description is required
        hazards_present = cleaned_data.get('hazards_present')
        hazard_description = cleaned_data.get('hazard_description')
        
        if hazards_present and not hazard_description:
            raise ValidationError({
                'hazard_description': 'Please describe the hazards present at the scene.'
            })
        
        return cleaned_data


class CallPriorityAssessmentForm(forms.ModelForm):
    """Priority assessment form for emergency calls"""
    
    class Meta:
        model = CallPriorityAssessment
        fields = [
            'chest_pain', 'difficulty_breathing', 'unconscious', 'severe_bleeding',
            'cardiac_arrest', 'stroke_symptoms', 'severe_trauma', 'overdose',
            'allergic_reaction', 'pregnancy_complications', 'assessment_notes'
        ]
        
        widgets = {
            'chest_pain': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'difficulty_breathing': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'unconscious': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'severe_bleeding': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'cardiac_arrest': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'stroke_symptoms': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'severe_trauma': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'overdose': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'allergic_reaction': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'pregnancy_complications': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-red-600 border-2 border-gray-300 rounded focus:ring-red-500'
            }),
            'assessment_notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
                'placeholder': 'Additional assessment notes and observations',
                'rows': 4
            }),
        }
        
        labels = {
            'chest_pain': _('Chest Pain'),
            'difficulty_breathing': _('Difficulty Breathing'),
            'unconscious': _('Unconscious'),
            'severe_bleeding': _('Severe Bleeding'),
            'cardiac_arrest': _('Cardiac Arrest'),
            'stroke_symptoms': _('Stroke Symptoms'),
            'severe_trauma': _('Severe Trauma'),
            'overdose': _('Drug Overdose'),
            'allergic_reaction': _('Severe Allergic Reaction'),
            'pregnancy_complications': _('Pregnancy Complications'),
            'assessment_notes': _('Assessment Notes'),
        }


class QuickCallForm(forms.Form):
    """Quick emergency call form for urgent situations"""
    
    caller_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border-2 border-red-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
            'placeholder': 'Caller phone number',
            'autofocus': True
        }),
        label=_('Caller Phone *')
    )
    
    incident_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border-2 border-red-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
            'placeholder': 'Incident address',
            'rows': 2
        }),
        label=_('Incident Address *')
    )
    
    chief_complaint = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border-2 border-red-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200',
            'placeholder': 'What is the emergency?',
            'rows': 3
        }),
        label=_('Emergency Description *')
    )
    
    priority = forms.ChoiceField(
        choices=EmergencyCall.PRIORITY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border-2 border-red-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition duration-200'
        }),
        label=_('Priority Level *'),
        initial='emergency'
    )
    
    def clean_caller_phone(self):
        phone = self.cleaned_data.get('caller_phone')
        if phone:
            import re
            cleaned_phone = re.sub(r'[^\d+]', '', phone)
            if not re.match(r'^\+?1?\d{9,15}$', cleaned_phone):
                raise ValidationError('Please enter a valid phone number.')
            return cleaned_phone
        return phone
