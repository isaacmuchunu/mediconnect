from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

# Import models from their respective apps
from users.models import User
from patients.models import Patient, MedicalHistory
from doctors.models import DoctorProfile
from referrals.models import Referral
from appointments.models import Appointment
from ambulances.models import Ambulance
from notifications.models import Notification
from reports.models import Report

# Import serializers
from .serializers import (
    UserSerializer, UserListSerializer,
    PatientSerializer, PatientListSerializer, MedicalHistorySerializer,
    DoctorProfileSerializer, DoctorListSerializer,
    ReferralSerializer, ReferralListSerializer,
    AppointmentSerializer, AmbulanceSerializer,
    NotificationSerializer, ReportSerializer
)

class BaseViewSet(viewsets.ModelViewSet):
    """Base ViewSet with common authentication and permissions"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

class UserViewSet(BaseViewSet):
    """ViewSet for User model with role-based access control"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email', 'last_name']
    filterset_fields = ['role', 'is_active']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Admin users can perform all actions, others can only view their own profile"""
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response({'error': 'Invalid old password'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully'})

class PatientViewSet(BaseViewSet):
    """ViewSet for Patient model"""
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'phone_number']
    ordering_fields = ['created_at', 'user__last_name']
    filterset_fields = ['gender']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        return PatientSerializer
    
    def get_queryset(self):
        """Filter patients based on user role"""
        user = self.request.user
        if user.is_staff or user.role in ['admin', 'doctor']:
            return Patient.objects.all()
        elif user.role == 'patient':
            return Patient.objects.filter(user=user)
        return Patient.objects.none()

class MedicalHistoryViewSet(BaseViewSet):
    """ViewSet for MedicalHistory model"""
    queryset = MedicalHistory.objects.all()
    serializer_class = MedicalHistorySerializer
    search_fields = ['patient__user__first_name', 'patient__user__last_name']
    ordering_fields = ['created_at']
    
    def get_queryset(self):
        """Filter medical history based on user role"""
        user = self.request.user
        if user.is_staff or user.role in ['admin', 'doctor']:
            return MedicalHistory.objects.all()
        elif user.role == 'patient':
            return MedicalHistory.objects.filter(patient__user=user)
        return MedicalHistory.objects.none()

class DoctorProfileViewSet(BaseViewSet):
    """ViewSet for DoctorProfile model"""
    queryset = DoctorProfile.objects.all()
    serializer_class = DoctorProfileSerializer
    search_fields = ['user__email', 'first_name', 'last_name', 'primary_specialty__name', 'primary_hospital__name']
    ordering_fields = ['created_at', 'last_name', 'primary_specialty__name']
    filterset_fields = ['primary_specialty__name', 'primary_hospital__name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DoctorListSerializer
        return DoctorProfileSerializer
    
    def get_queryset(self):
        """Filter doctor profiles based on user role"""
        user = self.request.user
        if user.is_staff or user.role in ['admin', 'patient']:
            return DoctorProfile.objects.all()
        elif user.role == 'doctor':
            return DoctorProfile.objects.filter(user=user)
        return DoctorProfile.objects.none()
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available doctor profiles"""
        profiles = self.get_queryset().filter(user__is_active=True, is_active=True)
        serializer = self.get_serializer(profiles, many=True)
        return Response(serializer.data)



class ReferralViewSet(BaseViewSet):
    """ViewSet for Referral model"""
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    search_fields = ['patient__user__first_name', 'patient__user__last_name', 'reason']
    ordering_fields = ['created_at', 'priority']
    filterset_fields = ['status', 'priority']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReferralListSerializer
        return ReferralSerializer
    
    def get_queryset(self):
        """Filter referrals based on user role"""
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Referral.objects.all()
        elif user.role == 'doctor':
            doctor = Doctor.objects.filter(user=user).first()
            if doctor:
                return Referral.objects.filter(
                    Q(referring_doctor=doctor) | Q(target_doctor=doctor)
                )
        elif user.role == 'patient':
            patient = Patient.objects.filter(user=user).first()
            if patient:
                return Referral.objects.filter(patient=patient)
        return Referral.objects.none()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a referral"""
        referral = self.get_object()
        referral.status = 'approved'
        referral.save()
        return Response({'message': 'Referral approved successfully'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a referral"""
        referral = self.get_object()
        referral.status = 'rejected'
        referral.save()
        return Response({'message': 'Referral rejected'})

class AppointmentViewSet(BaseViewSet):
    """ViewSet for Appointment model"""
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    search_fields = ['referral__patient__user__first_name', 'referral__patient__user__last_name']
    ordering_fields = ['date_time', 'created_at']
    filterset_fields = ['status']
    
    def get_queryset(self):
        """Filter appointments based on user role"""
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Appointment.objects.all()
        elif user.role == 'doctor':
            doctor = Doctor.objects.filter(user=user).first()
            if doctor:
                return Appointment.objects.filter(
                    Q(referral__referring_doctor=doctor) | Q(referral__target_doctor=doctor)
                )
        elif user.role == 'patient':
            patient = Patient.objects.filter(user=user).first()
            if patient:
                return Appointment.objects.filter(referral__patient=patient)
        return Appointment.objects.none()
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark appointment as completed"""
        appointment = self.get_object()
        appointment.status = 'completed'
        appointment.save()
        return Response({'message': 'Appointment marked as completed'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an appointment"""
        appointment = self.get_object()
        appointment.status = 'cancelled'
        appointment.save()
        return Response({'message': 'Appointment cancelled'})

class AmbulanceViewSet(BaseViewSet):
    """ViewSet for Ambulance model"""
    queryset = Ambulance.objects.all()
    serializer_class = AmbulanceSerializer
    search_fields = ['license_plate', 'driver_name']
    ordering_fields = ['created_at', 'license_plate']
    filterset_fields = ['type', 'status']
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available ambulances"""
        ambulances = self.get_queryset().filter(status='available')
        serializer = self.get_serializer(ambulances, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def dispatch(self, request, pk=None):
        """Dispatch an ambulance"""
        ambulance = self.get_object()
        ambulance.status = 'dispatched'
        ambulance.save()
        return Response({'message': 'Ambulance dispatched successfully'})

class NotificationViewSet(BaseViewSet):
    """ViewSet for Notification model"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    search_fields = ['title', 'message']
    ordering_fields = ['created_at']
    filterset_fields = ['notification_type', 'is_read']
    
    def get_queryset(self):
        """Users can only see their own notifications"""
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        self.get_queryset().update(is_read=True)
        return Response({'message': 'All notifications marked as read'})

class ReportViewSet(BaseViewSet):
    """ViewSet for Report model"""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
    filterset_fields = ['report_type', 'status']
    
    def get_permissions(self):
        """Only admin and authorized users can access reports"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter reports based on user role"""
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Report.objects.all()
        return Report.objects.filter(created_by=user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download report file"""
        report = self.get_object()
        if report.file_path:
            # Implementation for file download would go here
            return Response({'download_url': report.file_path})
        return Response({'error': 'No file available'}, status=status.HTTP_404_NOT_FOUND)