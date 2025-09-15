from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import User
from patients.models import Patient, MedicalHistory
from doctors.models import DoctorProfile
from referrals.models import Referral
from appointments.models import Appointment
from ambulances.models import Ambulance
from notifications.models import Notification
from reports.models import Report

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with role-based field filtering"""
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'date_joined': {'read_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class PatientSerializer(serializers.ModelSerializer):
    """Serializer for Patient model"""
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Patient
        fields = ['id', 'user', 'user_id', 'date_of_birth', 'gender', 'phone_number', 
                 'address', 'emergency_contact', 'insurance_number', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class MedicalHistorySerializer(serializers.ModelSerializer):
    """Serializer for MedicalHistory model"""
    patient = PatientSerializer(read_only=True)
    patient_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = MedicalHistory
        fields = ['id', 'patient', 'patient_id', 'allergies', 'medications', 
                 'medical_history', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']



class DoctorProfileSerializer(serializers.ModelSerializer):
    """Serializer for DoctorProfile model"""
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = DoctorProfile
        fields = ['id', 'user', 'user_id', 'primary_specialty', 'specialties', 'consultation_fee', 'years_of_experience', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class ReferralSerializer(serializers.ModelSerializer):
    """Serializer for Referral model with nested relationships"""
    patient = PatientSerializer(read_only=True)
    referring_doctor = DoctorProfileSerializer(read_only=True)
    target_doctor = DoctorProfileSerializer(read_only=True)
    patient_id = serializers.IntegerField(write_only=True)
    referring_doctor_id = serializers.IntegerField(write_only=True)
    target_doctor_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Referral
        fields = ['id', 'patient', 'referring_doctor', 'target_doctor', 'patient_id', 
                 'referring_doctor_id', 'target_doctor_id', 'status', 'priority', 
                 'reason', 'notes', 'attachments', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointment model"""
    referral = ReferralSerializer(read_only=True)
    referral_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Appointment
        fields = ['id', 'referral', 'referral_id', 'date_time', 'status', 
                 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class AmbulanceSerializer(serializers.ModelSerializer):
    """Serializer for Ambulance model"""
    
    class Meta:
        model = Ambulance
        fields = ['id', 'license_plate', 'type', 'status', 'location', 
                 'driver_name', 'driver_phone', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'user', 'user_id', 'title', 'message', 'notification_type', 
                 'is_read', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model"""
    created_by = UserSerializer(read_only=True)
    created_by_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'title', 'description', 'report_type', 'status', 
                 'content', 'file_path', 'file_size', 'created_by', 'created_by_id', 
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'file_size', 'file_path']

# Simplified serializers for list views
class UserListSerializer(serializers.ModelSerializer):
    """Simplified User serializer for list views"""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'is_active']

class PatientListSerializer(serializers.ModelSerializer):
    """Simplified Patient serializer for list views"""
    user = UserListSerializer(read_only=True)
    
    class Meta:
        model = Patient
        fields = ['id', 'user', 'phone_number', 'created_at']

class DoctorListSerializer(serializers.ModelSerializer):
    """Simplified DoctorProfile serializer for list views"""
    user = UserListSerializer(read_only=True)
    
    class Meta:
        model = DoctorProfile
        fields = ['id', 'user', 'primary_specialty', 'primary_hospital']

class ReferralListSerializer(serializers.ModelSerializer):
    """Simplified Referral serializer for list views"""
    patient = PatientListSerializer(read_only=True)
    referring_doctor = DoctorListSerializer(read_only=True)
    target_doctor = DoctorListSerializer(read_only=True)
    
    class Meta:
        model = Referral
        fields = ['id', 'patient', 'referring_doctor', 'target_doctor', 
                 'status', 'priority', 'created_at']