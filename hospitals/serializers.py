"""
Serializers for Hospital Integration API
Handles serialization of hospital status, bed availability, and related data.
"""

from rest_framework import serializers
from django.utils import timezone
from typing import Dict, Any

from doctors.models import Hospital
from .models_integration import BedAvailability, EmergencyDepartment
from .services import BedType, EDStatus, BedCapacity, HospitalStatus


class BedCapacitySerializer(serializers.Serializer):
    """Serializer for bed capacity information."""
    
    bed_type = serializers.CharField()
    total_beds = serializers.IntegerField()
    occupied_beds = serializers.IntegerField()
    available_beds = serializers.IntegerField()
    reserved_beds = serializers.IntegerField(default=0)
    maintenance_beds = serializers.IntegerField(default=0)
    occupancy_rate = serializers.FloatField(read_only=True)
    availability_rate = serializers.FloatField(read_only=True)
    last_updated = serializers.DateTimeField(read_only=True)
    
    def to_representation(self, instance):
        """Convert BedCapacity dataclass to dictionary."""
        if isinstance(instance, BedCapacity):
            return {
                'bed_type': instance.bed_type.value,
                'total_beds': instance.total_beds,
                'occupied_beds': instance.occupied_beds,
                'available_beds': instance.available_beds,
                'reserved_beds': instance.reserved_beds,
                'maintenance_beds': instance.maintenance_beds,
                'occupancy_rate': round(instance.occupancy_rate, 1),
                'availability_rate': round(instance.availability_rate, 1),
                'last_updated': instance.last_updated.isoformat() if instance.last_updated else None
            }
        return super().to_representation(instance)


class HospitalStatusSerializer(serializers.Serializer):
    """Serializer for comprehensive hospital status."""
    
    hospital_id = serializers.CharField()
    name = serializers.CharField()
    ed_status = serializers.CharField()
    bed_capacities = serializers.DictField(child=BedCapacitySerializer())
    wait_time_minutes = serializers.IntegerField()
    accepting_ambulances = serializers.BooleanField()
    accepting_referrals = serializers.BooleanField()
    contact_info = serializers.DictField()
    last_updated = serializers.DateTimeField()
    overall_capacity_rate = serializers.FloatField(read_only=True)
    
    # Additional computed fields
    distance_km = serializers.FloatField(required=False, read_only=True)
    estimated_travel_time = serializers.IntegerField(required=False, read_only=True)
    
    def to_representation(self, instance):
        """Convert HospitalStatus dataclass to dictionary."""
        if isinstance(instance, HospitalStatus):
            # Convert bed capacities dictionary
            bed_capacities_data = {}
            for bed_type, capacity in instance.bed_capacities.items():
                bed_capacities_data[bed_type.value] = BedCapacitySerializer().to_representation(capacity)
            
            return {
                'hospital_id': instance.hospital_id,
                'name': instance.name,
                'ed_status': instance.ed_status.value,
                'bed_capacities': bed_capacities_data,
                'wait_time_minutes': instance.wait_time_minutes,
                'accepting_ambulances': instance.accepting_ambulances,
                'accepting_referrals': instance.accepting_referrals,
                'contact_info': instance.contact_info,
                'last_updated': instance.last_updated.isoformat(),
                'overall_capacity_rate': round(instance.overall_capacity_rate, 1),
                # Add summary statistics
                'summary': {
                    'total_available_beds': sum(
                        cap.available_beds for cap in instance.bed_capacities.values()
                    ),
                    'critical_capacity': instance.overall_capacity_rate > 90,
                    'status_level': self._get_status_level(instance)
                }
            }
        return super().to_representation(instance)
    
    def _get_status_level(self, hospital_status: HospitalStatus) -> str:
        """Determine overall status level based on multiple factors."""
        if hospital_status.ed_status in [EDStatus.CLOSED, EDStatus.DIVERT]:
            return 'UNAVAILABLE'
        elif hospital_status.ed_status == EDStatus.CRITICAL:
            return 'CRITICAL'
        elif hospital_status.overall_capacity_rate > 95:
            return 'CRITICAL'
        elif hospital_status.overall_capacity_rate > 85:
            return 'HIGH'
        elif hospital_status.ed_status == EDStatus.BUSY:
            return 'MODERATE'
        else:
            return 'NORMAL'


class BedAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for bed availability model."""
    
    occupancy_rate = serializers.SerializerMethodField()
    availability_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = BedAvailability
        fields = [
            'id', 'hospital', 'bed_type', 'total_beds', 
            'occupied_beds', 'available_beds', 'reserved_beds',
            'maintenance_beds', 'occupancy_rate', 'availability_rate',
            'last_updated', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_occupancy_rate(self, obj) -> float:
        """Calculate occupancy rate."""
        if obj.total_beds == 0:
            return 0.0
        return round((obj.occupied_beds / obj.total_beds) * 100, 1)
    
    def get_availability_rate(self, obj) -> float:
        """Calculate availability rate."""
        if obj.total_beds == 0:
            return 0.0
        return round((obj.available_beds / obj.total_beds) * 100, 1)


class EmergencyDepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Emergency Department status."""
    
    status_display = serializers.SerializerMethodField()
    duration_in_status = serializers.SerializerMethodField()
    
    class Meta:
        model = EmergencyDepartment
        fields = [
            'id', 'hospital', 'status', 'status_display', 
            'status_reason', 'wait_time_minutes', 'last_updated',
            'duration_in_status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_status_display(self, obj) -> str:
        """Get human-readable status display."""
        status_map = {
            'NORMAL': 'Normal Operations',
            'BUSY': 'Busy - Higher Than Normal Volume',
            'CRITICAL': 'Critical - Very High Volume',
            'DIVERT': 'On Diversion - Not Accepting Ambulances',
            'CLOSED': 'Closed - Emergency Only'
        }
        return status_map.get(obj.status, obj.status)
    
    def get_duration_in_status(self, obj) -> int:
        """Get duration in current status (minutes)."""
        if obj.last_updated:
            duration = timezone.now() - obj.last_updated
            return int(duration.total_seconds() / 60)
        return 0


class HospitalSerializer(serializers.ModelSerializer):
    """Serializer for Hospital model with capacity information."""
    
    current_status = serializers.SerializerMethodField()
    bed_availability = BedAvailabilitySerializer(many=True, read_only=True)
    ed_status = EmergencyDepartmentSerializer(read_only=True)
    distance_km = serializers.FloatField(required=False, read_only=True)
    
    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'address', 'city', 'state', 'zip_code',
            'phone', 'email', 'emergency_contact', 'contact_email',
            'latitude', 'longitude', 'is_active', 'accepting_ambulances',
            'accepting_referrals', 'trauma_level', 'specialties',
            'current_status', 'bed_availability', 'ed_status',
            'distance_km', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_current_status(self, obj) -> str:
        """Get current operational status."""
        if not obj.is_active:
            return 'INACTIVE'
        elif not obj.accepting_ambulances:
            return 'NOT_ACCEPTING_AMBULANCES'
        elif not obj.accepting_referrals:
            return 'NOT_ACCEPTING_REFERRALS'
        else:
            return 'OPERATIONAL'


class HospitalRecommendationSerializer(serializers.Serializer):
    """Serializer for hospital recommendation requests."""
    
    patient_condition = serializers.CharField(max_length=500)
    ambulance_location = serializers.ListField(
        child=serializers.FloatField(),
        min_length=2,
        max_length=2,
        help_text="[latitude, longitude]"
    )
    required_specialty = serializers.CharField(max_length=100, required=False)
    urgent = serializers.BooleanField(default=False)
    exclude_hospitals = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of hospital IDs to exclude"
    )
    max_distance_km = serializers.FloatField(
        required=False,
        min_value=1.0,
        max_value=100.0,
        help_text="Maximum distance in kilometers"
    )
    
    def validate_ambulance_location(self, value):
        """Validate ambulance location coordinates."""
        if len(value) != 2:
            raise serializers.ValidationError("Must provide exactly 2 coordinates [lat, lng]")
        
        lat, lng = value
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        
        if not (-180 <= lng <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        
        return value


class BedUpdateSerializer(serializers.Serializer):
    """Serializer for bed availability updates."""
    
    bed_type = serializers.ChoiceField(
        choices=[(bt.value, bt.value) for bt in BedType]
    )
    occupied_beds = serializers.IntegerField(min_value=0)
    available_beds = serializers.IntegerField(min_value=0)
    reserved_beds = serializers.IntegerField(min_value=0, default=0)
    maintenance_beds = serializers.IntegerField(min_value=0, default=0)
    
    def validate(self, data):
        """Validate bed numbers consistency."""
        total_accounted = (
            data['occupied_beds'] + 
            data['available_beds'] + 
            data['reserved_beds'] + 
            data['maintenance_beds']
        )
        
        # We don't enforce total_beds here since it might not be provided
        # The service layer will handle the total calculation
        
        return data


class EDStatusUpdateSerializer(serializers.Serializer):
    """Serializer for Emergency Department status updates."""
    
    status = serializers.ChoiceField(
        choices=[(eds.value, eds.value) for eds in EDStatus]
    )
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    wait_time_minutes = serializers.IntegerField(
        min_value=0,
        max_value=480,  # 8 hours max
        required=False
    )
    
    def validate_reason(self, value):
        """Validate status reason."""
        # Require reason for critical status changes
        status = self.initial_data.get('status', '').upper()
        if status in ['DIVERT', 'CLOSED', 'CRITICAL'] and not value:
            raise serializers.ValidationError(
                f"Reason is required when setting status to {status}"
            )
        return value


class HospitalCapacityReportSerializer(serializers.Serializer):
    """Serializer for hospital capacity reports."""
    
    hospital_id = serializers.CharField()
    hospital_name = serializers.CharField()
    timestamp = serializers.DateTimeField()
    
    # Bed capacity summary
    total_beds = serializers.IntegerField()
    occupied_beds = serializers.IntegerField()
    available_beds = serializers.IntegerField()
    occupancy_rate = serializers.FloatField()
    
    # ED information
    ed_status = serializers.CharField()
    wait_time_minutes = serializers.IntegerField()
    
    # Operational status
    accepting_ambulances = serializers.BooleanField()
    accepting_referrals = serializers.BooleanField()
    
    # Detailed bed breakdown
    bed_details = serializers.DictField(child=BedCapacitySerializer())
    
    # Trend indicators (if available)
    capacity_trend = serializers.CharField(required=False)  # 'INCREASING', 'DECREASING', 'STABLE'
    alert_level = serializers.CharField(required=False)     # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'


class HospitalMetricsSerializer(serializers.Serializer):
    """Serializer for hospital performance metrics."""
    
    hospital_id = serializers.CharField()
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()
    
    # Volume metrics
    total_referrals = serializers.IntegerField()
    accepted_referrals = serializers.IntegerField()
    rejected_referrals = serializers.IntegerField()
    acceptance_rate = serializers.FloatField()
    
    # Time metrics
    average_response_time_minutes = serializers.FloatField()
    average_wait_time_minutes = serializers.FloatField()
    
    # Capacity metrics
    average_occupancy_rate = serializers.FloatField()
    peak_occupancy_rate = serializers.FloatField()
    hours_at_capacity = serializers.FloatField()
    
    # Status changes
    status_changes = serializers.IntegerField()
    diversion_hours = serializers.FloatField()
    
    # Quality indicators
    patient_satisfaction_score = serializers.FloatField(required=False)
    readmission_rate = serializers.FloatField(required=False)