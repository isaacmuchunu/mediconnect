from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from users.models import Patient, Doctor, DoctorProfile, PatientHistory
from referrals.models import Referral
from appointments.models import Appointment
from ambulances.models import Ambulance
from notifications.models import Notification
from reports.models import Report
from api.serializers import (
    UserSerializer, PatientSerializer, ReferralSerializer,
    AppointmentSerializer, AmbulanceSerializer
)

User = get_user_model()

class BaseAPITestCase(APITestCase):
    """Base test case with common setup for API tests"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test users
        self.patient_user = User.objects.create_user(
            email='patient@test.com',
            password='testpass123',
            role='Patient',
            first_name='John',
            last_name='Doe'
        )
        
        self.doctor_user = User.objects.create_user(
            email='doctor@test.com',
            password='testpass123',
            role='Doctor',
            first_name='Dr. Jane',
            last_name='Smith'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='Admin',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True
        )
        
        # Create tokens for authentication
        self.patient_token = Token.objects.create(user=self.patient_user)
        self.doctor_token = Token.objects.create(user=self.doctor_user)
        self.admin_token = Token.objects.create(user=self.admin_user)
        
        # Create related objects
        self.patient = Patient.objects.create(
            user=self.patient_user,
            date_of_birth='1990-01-01',
            phone_number='1234567890',
            address='123 Test St'
        )
        
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            specialization='Cardiology',
            license_number='DOC123'
        )
        
        self.doctor_profile = DoctorProfile.objects.create(
            doctor=self.doctor,
            bio='Experienced cardiologist',
            years_of_experience=10
        )

class UserAPITests(BaseAPITestCase):
    """Test cases for User API endpoints"""
    
    def test_user_list_requires_authentication(self):
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_list_with_authentication(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_user_detail(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.patient_token.key)
        response = self.client.get(f'/api/users/{self.patient_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'patient@test.com')
    
    def test_change_password(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.patient_token.key)
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass123'
        }
        response = self.client.post(f'/api/users/{self.patient_user.id}/change_password/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class ReferralAPITests(BaseAPITestCase):
    """Test cases for Referral API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.referral = Referral.objects.create(
            patient=self.patient,
            referring_doctor=self.doctor,
            target_doctor=self.doctor,
            status='Draft',
            notes='Test referral'
        )
    
    def test_create_referral(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.doctor_token.key)
        data = {
            'patient': self.patient.id,
            'referring_doctor': self.doctor.id,
            'target_doctor': self.doctor.id,
            'status': 'Draft',
            'notes': 'New test referral'
        }
        response = self.client.post('/api/referrals/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_get_referral(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.doctor_token.key)
        response = self.client.get(f'/api/referrals/{self.referral.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_approve_referral(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.doctor_token.key)
        response = self.client.post(f'/api/referrals/{self.referral.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, 'Approved')
    
    def test_reject_referral(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.doctor_token.key)
        data = {'reason': 'Not suitable'}
        response = self.client.post(f'/api/referrals/{self.referral.id}/reject/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, 'Rejected')

class AppointmentAPITests(BaseAPITestCase):
    """Test cases for Appointment API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date='2024-12-31',
            appointment_time='10:00:00',
            status='Scheduled'
        )
    
    def test_create_appointment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.patient_token.key)
        data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'appointment_date': '2024-12-30',
            'appointment_time': '14:00:00',
            'status': 'Scheduled'
        }
        response = self.client.post('/api/appointments/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_update_appointment_status(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.doctor_token.key)
        data = {'status': 'Completed'}
        response = self.client.post(f'/api/appointments/{self.appointment.id}/update_status/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'Completed')

class AmbulanceAPITests(BaseAPITestCase):
    """Test cases for Ambulance API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.ambulance = Ambulance.objects.create(
            vehicle_number='AMB001',
            driver_name='Test Driver',
            driver_contact='9876543210',
            status='Available'
        )
    
    def test_dispatch_ambulance(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        data = {
            'patient_location': '123 Emergency St',
            'hospital_destination': 'City Hospital'
        }
        response = self.client.post(f'/api/ambulances/{self.ambulance.id}/dispatch/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ambulance.refresh_from_db()
        self.assertEqual(self.ambulance.status, 'Dispatched')

class AuthenticationTests(BaseAPITestCase):
    """Test cases for API authentication"""
    
    def test_obtain_token(self):
        data = {
            'username': 'patient@test.com',
            'password': 'testpass123'
        }
        response = self.client.post('/api/auth/token/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
    
    def test_invalid_credentials(self):
        data = {
            'username': 'patient@test.com',
            'password': 'wrongpassword'
        }
        response = self.client.post('/api/auth/token/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class PermissionTests(BaseAPITestCase):
    """Test cases for API permissions"""
    
    def test_patient_cannot_access_all_users(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.patient_token.key)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_doctor_can_access_referrals(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.doctor_token.key)
        response = self.client.get('/api/referrals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_admin_can_access_everything(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        endpoints = ['/api/users/', '/api/referrals/', '/api/appointments/', '/api/ambulances/']
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])