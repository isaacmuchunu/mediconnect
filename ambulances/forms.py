from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from .models import (
    Ambulance, Dispatch, AmbulanceType, AmbulanceStation,
    MaintenanceRecord, EquipmentInventory, FuelLog, IncidentReport
)
from referrals.models import Referral
from users.models import User

class AmbulanceForm(forms.ModelForm):
    class Meta:
        model = Ambulance
        fields = [
            'license_plate', 'vehicle_identification_number', 'ambulance_type',
            'make', 'model', 'year', 'color', 'patient_capacity', 'crew_capacity',
            'medical_equipment', 'condition', 'fuel_level', 'home_station'
        ]
        widgets = {
            'license_plate': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter license plate number'
            }),
            'vehicle_identification_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': '17-character VIN'
            }),
            'ambulance_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'make': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'model': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': 1990,
                'max': 2030
            }),
            'color': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'patient_capacity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': 1,
                'max': 10
            }),
            'crew_capacity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': 1,
                'max': 6
            }),
            'medical_equipment': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'List available medical equipment'
            }),
            'condition': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'fuel_level': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': 0,
                'max': 100
            }),
            'home_station': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active ambulance types and stations
        try:
            self.fields['ambulance_type'].queryset = AmbulanceType.objects.filter(is_active=True)
            self.fields['home_station'].queryset = AmbulanceStation.objects.filter(is_active=True)
        except:
            # Handle case where models don't exist yet during migrations
            pass

class DispatchForm(forms.ModelForm):
    pickup_latitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    pickup_longitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    destination_latitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    destination_longitude = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Dispatch
        fields = [
            'priority', 'pickup_address', 'destination_address',
            'patient_condition', 'special_instructions', 'contact_person', 'contact_phone'
        ]
        widgets = {
            'priority': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'pickup_address': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 2,
                'placeholder': 'Enter pickup address'
            }),
            'destination_address': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 2,
                'placeholder': 'Enter destination address'
            }),
            'patient_condition': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Describe patient condition'
            }),
            'special_instructions': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Any special instructions'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Contact person name'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Contact phone number'
            })
        }

class AmbulanceSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Search by license plate, make, model...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + [
            ('available', 'Available'),
            ('dispatched', 'Dispatched'),
            ('en_route', 'En Route'),
            ('on_scene', 'On Scene'),
            ('transporting', 'Transporting'),
            ('at_hospital', 'At Hospital'),
            ('returning', 'Returning'),
            ('out_of_service', 'Out of Service'),
            ('maintenance', 'Under Maintenance'),
            ('offline', 'Offline'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )
    condition = forms.ChoiceField(
        required=False,
        choices=[('', 'All Conditions')] + [
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
            ('critical', 'Critical'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )


class GPSUpdateForm(forms.Form):
    """Form for GPS location updates"""
    ambulance_id = forms.UUIDField()
    latitude = forms.FloatField(min_value=-90, max_value=90)
    longitude = forms.FloatField(min_value=-180, max_value=180)
    speed = forms.FloatField(min_value=0, required=False)
    heading = forms.FloatField(min_value=0, max_value=360, required=False)
    accuracy = forms.FloatField(min_value=0, required=False)


class MaintenanceForm(forms.ModelForm):
    """Form for recording maintenance activities"""

    class Meta:
        model = MaintenanceRecord
        fields = [
            'ambulance', 'maintenance_type', 'description', 'performed_by',
            'cost', 'mileage_at_service', 'next_service_mileage', 'service_date', 'next_service_date'
        ]
        widgets = {
            'ambulance': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'maintenance_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 4}),
            'performed_by': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'cost': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'step': '0.01'}),
            'mileage_at_service': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'next_service_mileage': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'service_date': forms.DateTimeInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'type': 'datetime-local'}),
            'next_service_date': forms.DateTimeInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'type': 'datetime-local'}),
        }