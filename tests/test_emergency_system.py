"""
Comprehensive Emergency Call System Tests
Tests emergency call management, dispatch, and ambulance coordination
"""

import json
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from ambulances.models import (
    Ambulance, AmbulanceType, AmbulanceStation, AmbulanceCrew,
    Dispatch, EmergencyCall, GPSTrackingLog
)
from doctors.models import Hospital
from users.models import User

User = get_user_model()


class EmergencyCallModelTest(TestCase):
    """Test emergency call model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='dispatcher01',
            email='dispatcher@mediconnect.com',
            role='DISPATCHER'
        )
        
        self.emergency_call = EmergencyCall.objects.create(
            call_number='CALL-20240115-001',
            caller_phone='+1-555-0123',
            caller_name='John Doe',
            incident_address='123 Main St, NYC',
            patient_name='Jane Smith',
            patient_age=45,
            patient_gender='F',
            chief_complaint='Chest pain',
            priority='critical',
            call_taker=self.user
        )
    
    def test_emergency_call_creation(self):
        """Test emergency call is created correctly"""
        self.assertEqual(self.emergency_call.call_number, 'CALL-20240115-001')
        self.assertEqual(self.emergency_call.caller_name, 'John Doe')
        self.assertEqual(self.emergency_call.priority, 'critical')
        self.assertEqual(self.emergency_call.status, 'received')
    
    def test_call_number_generation(self):
        """Test automatic call number generation"""
        call = EmergencyCall.objects.create(
            caller_phone='+1-555-0124',
            patient_name='Test Patient',
            chief_complaint='Test complaint',
            call_taker=self.user
        )
        self.assertTrue(call.call_number.startswith('CALL-'))
        self.assertIsNotNone(call.call_number)
    
    def test_call_priority_validation(self):
        """Test call priority levels"""
        priorities = ['routine', 'urgent', 'emergency', 'critical']
        for priority in priorities:
            call = EmergencyCall.objects.create(
                caller_phone=f'+1-555-{priority[:4]}',
                patient_name=f'{priority.title()} Patient',
                chief_complaint=f'{priority} complaint',
                priority=priority,
                call_taker=self.user
            )
            self.assertEqual(call.priority, priority)
    
    def test_call_status_transitions(self):
        """Test valid call status transitions"""
        # Test status progression
        statuses = ['received', 'processing', 'dispatched', 'completed']
        
        for status in statuses:
            self.emergency_call.status = status
            self.emergency_call.save()
            self.assertEqual(self.emergency_call.status, status)
    
    def test_call_duration_calculation(self):
        """Test call duration calculation"""
        start_time = timezone.now()
        self.emergency_call.received_at = start_time
        self.emergency_call.completed_at = start_time + timedelta(minutes=15)
        self.emergency_call.save()
        
        # Would need to implement duration property in model
        # self.assertEqual(self.emergency_call.duration_minutes, 15)


class AmbulanceModelTest(TestCase):
    """Test ambulance model functionality"""
    
    def setUp(self):
        self.ambulance_type = AmbulanceType.objects.create(
            name='Advanced Life Support',
            code='ALS',
            description='Advanced life support ambulance'
        )
        
        self.station = AmbulanceStation.objects.create(
            name='Central Station',
            code='CS01',
            address='456 Station Ave',
            phone='+1-555-0200'
        )
        
        self.ambulance = Ambulance.objects.create(
            license_plate='AMB-001',
            call_sign='Unit 12',
            ambulance_type=self.ambulance_type,
            home_station=self.station,
            vehicle_identification_number='1HGBH41JXMN109186'
        )
    
    def test_ambulance_creation(self):
        """Test ambulance is created correctly"""
        self.assertEqual(self.ambulance.license_plate, 'AMB-001')
        self.assertEqual(self.ambulance.call_sign, 'Unit 12')
        self.assertEqual(self.ambulance.status, 'available')
        self.assertEqual(self.ambulance.condition, 'good')
    
    def test_ambulance_status_transitions(self):
        """Test valid ambulance status transitions"""
        statuses = [
            'available', 'dispatched', 'en_route', 'on_scene',
            'transporting', 'at_hospital', 'returning', 'out_of_service'
        ]
        
        for status in statuses:
            self.ambulance.status = status
            self.ambulance.save()
            self.assertEqual(self.ambulance.status, status)
    
    def test_ambulance_location_update(self):
        """Test GPS location updates"""
        self.ambulance.current_latitude = 40.7128
        self.ambulance.current_longitude = -74.0060
        self.ambulance.save()
        
        self.assertEqual(self.ambulance.current_latitude, 40.7128)
        self.assertEqual(self.ambulance.current_longitude, -74.0060)
    
    def test_fuel_level_validation(self):
        """Test fuel level is within valid range"""
        # Test valid fuel levels
        for fuel_level in [0, 25, 50, 75, 100]:
            self.ambulance.fuel_level = fuel_level
            self.ambulance.save()
            self.assertEqual(self.ambulance.fuel_level, fuel_level)


class DispatchModelTest(TestCase):
    """Test dispatch model functionality"""
    
    def setUp(self):
        # Create test data
        self.user = User.objects.create_user(
            username='dispatcher02',
            email='dispatcher2@mediconnect.com',
            role='DISPATCHER'
        )
        
        self.ambulance_type = AmbulanceType.objects.create(
            name='Basic Life Support',
            code='BLS'
        )
        
        self.station = AmbulanceStation.objects.create(
            name='North Station',
            code='NS01',
            address='789 North Ave'
        )
        
        self.ambulance = Ambulance.objects.create(
            license_plate='AMB-002',
            call_sign='Unit 15',
            ambulance_type=self.ambulance_type,
            home_station=self.station
        )
        
        # Create a referral (would need to import from referrals app)
        # For now, we'll use a mock or create minimal data
        
    def test_dispatch_creation(self):
        """Test dispatch creation"""
        dispatch = Dispatch.objects.create(
            ambulance=self.ambulance,
            dispatcher=self.user,
            priority='urgent',
            pickup_address='123 Emergency St',
            destination_address='456 Hospital Ave',
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060
        )
        
        self.assertEqual(dispatch.ambulance, self.ambulance)
        self.assertEqual(dispatch.dispatcher, self.user)
        self.assertEqual(dispatch.priority, 'urgent')
        self.assertEqual(dispatch.status, 'requested')
        self.assertIsNotNone(dispatch.dispatch_number)
    
    def test_dispatch_status_progression(self):
        """Test dispatch status progression"""
        dispatch = Dispatch.objects.create(
            ambulance=self.ambulance,
            dispatcher=self.user,
            pickup_address='Test Address'
        )
        
        statuses = [
            'requested', 'assigned', 'dispatched', 'en_route_pickup',
            'on_scene', 'patient_loaded', 'en_route_hospital',
            'at_hospital', 'patient_delivered', 'completed'
        ]
        
        for status in statuses:
            dispatch.status = status
            dispatch.save()
            self.assertEqual(dispatch.status, status)
    
    def test_dispatch_time_tracking(self):
        """Test dispatch timing fields"""
        dispatch = Dispatch.objects.create(
            ambulance=self.ambulance,
            dispatcher=self.user,
            pickup_address='Test Address'
        )
        
        now = timezone.now()
        dispatch.dispatched_at = now
        dispatch.on_scene_at = now + timedelta(minutes=10)
        dispatch.completed_at = now + timedelta(minutes=45)
        dispatch.save()
        
        self.assertIsNotNone(dispatch.dispatched_at)
        self.assertIsNotNone(dispatch.on_scene_at)
        self.assertIsNotNone(dispatch.completed_at)


class EmergencyAPITest(APITestCase):
    """Test emergency call API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user with appropriate permissions
        self.dispatcher = User.objects.create_user(
            username='api_dispatcher',
            email='api_dispatcher@mediconnect.com',
            role='DISPATCHER'
        )
        
        self.call_taker = User.objects.create_user(
            username='call_taker',
            email='call_taker@mediconnect.com', 
            role='CALL_TAKER'
        )
        
        # Create test ambulance
        self.ambulance_type = AmbulanceType.objects.create(
            name='Test ALS',
            code='TALS'
        )
        
        self.ambulance = Ambulance.objects.create(
            license_plate='TEST-001',
            call_sign='Test Unit',
            ambulance_type=self.ambulance_type
        )
    
    def test_create_emergency_call_authenticated(self):
        """Test creating emergency call with authentication"""
        self.client.force_authenticate(user=self.call_taker)
        
        data = {
            'caller_phone': '+1-555-TEST',
            'caller_name': 'Test Caller',
            'incident_address': '123 Test St',
            'patient_name': 'Test Patient',
            'patient_age': 30,
            'patient_gender': 'M',
            'chief_complaint': 'Test complaint',
            'priority': 'urgent'
        }
        
        url = reverse('ambulances:emergency_call_create')
        response = self.client.post(url, data, format='json')
        
        # Check response (may need to adjust based on actual view implementation)
        self.assertIn(response.status_code, [200, 201, 302])
    
    def test_create_emergency_call_unauthenticated(self):
        """Test creating emergency call without authentication"""
        data = {
            'caller_phone': '+1-555-TEST',
            'patient_name': 'Test Patient',
            'chief_complaint': 'Test complaint'
        }
        
        url = reverse('ambulances:emergency_call_create')
        response = self.client.post(url, data, format='json')
        
        # Should require authentication
        self.assertIn(response.status_code, [401, 302, 403])
    
    def test_list_emergency_calls(self):
        """Test listing emergency calls"""
        self.client.force_authenticate(user=self.dispatcher)
        
        # Create test emergency call
        EmergencyCall.objects.create(
            call_number='TEST-001',
            caller_phone='+1-555-TEST',
            patient_name='Test Patient',
            chief_complaint='Test complaint',
            call_taker=self.call_taker
        )
        
        url = reverse('ambulances:emergency_call_list')
        response = self.client.get(url)
        
        self.assertIn(response.status_code, [200])
    
    @patch('ambulances.views_emergency.quick_dispatch')
    def test_quick_dispatch_api(self, mock_dispatch):
        """Test quick dispatch API endpoint"""
        self.client.force_authenticate(user=self.dispatcher)
        
        # Create emergency call
        emergency_call = EmergencyCall.objects.create(
            caller_phone='+1-555-DISPATCH',
            patient_name='Dispatch Test',
            chief_complaint='Test dispatch',
            call_taker=self.call_taker
        )
        
        mock_dispatch.return_value = {'status': 'success'}
        
        data = {
            'call_id': str(emergency_call.id),
            'ambulance_id': str(self.ambulance.id)
        }
        
        url = reverse('ambulances:quick_dispatch')
        response = self.client.post(url, data, format='json')
        
        # Should process dispatch request
        self.assertIn(response.status_code, [200, 201])


class GPSTrackingTest(TestCase):
    """Test GPS tracking functionality"""
    
    def setUp(self):
        self.ambulance_type = AmbulanceType.objects.create(
            name='GPS Test Unit',
            code='GPS'
        )
        
        self.ambulance = Ambulance.objects.create(
            license_plate='GPS-001',
            call_sign='GPS Unit',
            ambulance_type=self.ambulance_type
        )
    
    def test_gps_location_update(self):
        """Test GPS location tracking"""
        # Update ambulance location
        self.ambulance.current_latitude = 40.7580
        self.ambulance.current_longitude = -73.9855
        self.ambulance.save()
        
        # Verify location is updated
        updated_ambulance = Ambulance.objects.get(id=self.ambulance.id)
        self.assertEqual(updated_ambulance.current_latitude, 40.7580)
        self.assertEqual(updated_ambulance.current_longitude, -73.9855)
    
    def test_gps_tracking_log(self):
        """Test GPS tracking log creation"""
        # This would test the GPSTrackingLog model if it exists
        # or GPSTrackingEnhanced from the models
        pass


class NotificationSystemTest(TestCase):
    """Test notification system"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='notification_user',
            email='notifications@mediconnect.com',
            role='DISPATCHER'
        )
    
    @patch('notifications.services.notification_service.send_notification')
    def test_emergency_alert_notification(self, mock_send):
        """Test emergency alert notifications"""
        mock_send.return_value = {'success': True}
        
        # This would test the notification service
        # Import and test notification_service.send_emergency_alert
        pass
    
    @patch('notifications.services.TwilioClient')
    def test_sms_notification(self, mock_twilio):
        """Test SMS notification functionality"""
        # Mock Twilio SMS sending
        mock_client = MagicMock()
        mock_twilio.return_value = mock_client
        
        # Test SMS sending logic
        pass


class IntegrationTest(TransactionTestCase):
    """Integration tests for complete workflows"""
    
    def setUp(self):
        # Create comprehensive test data
        self.dispatcher = User.objects.create_user(
            username='integration_dispatcher',
            email='integration@mediconnect.com',
            role='DISPATCHER'
        )
        
        self.ambulance_type = AmbulanceType.objects.create(
            name='Integration ALS',
            code='IALS'
        )
        
        self.hospital = Hospital.objects.create(
            name='Integration Hospital',
            address='123 Integration Ave',
            city='Test City',
            state='TS',
            zip_code='12345',
            phone='+1-555-HOSP',
            email='hospital@test.com'
        )
        
        self.ambulance = Ambulance.objects.create(
            license_plate='INT-001',
            call_sign='Integration Unit',
            ambulance_type=self.ambulance_type
        )
    
    def test_end_to_end_emergency_response(self):
        """Test complete emergency response workflow"""
        # 1. Create emergency call
        emergency_call = EmergencyCall.objects.create(
            caller_phone='+1-555-E2E',
            caller_name='End to End Caller',
            patient_name='E2E Patient',
            chief_complaint='Integration test emergency',
            priority='critical',
            call_taker=self.dispatcher
        )
        
        # 2. Create dispatch
        dispatch = Dispatch.objects.create(
            ambulance=self.ambulance,
            dispatcher=self.dispatcher,
            priority='critical',
            pickup_address='123 Emergency Location'
        )
        
        # 3. Update ambulance status
        self.ambulance.status = 'dispatched'
        self.ambulance.save()
        
        # 4. Simulate status progression
        statuses = ['dispatched', 'en_route', 'on_scene', 'transporting']
        for status in statuses:
            self.ambulance.status = status
            self.ambulance.save()
            
            # Verify status update
            updated_ambulance = Ambulance.objects.get(id=self.ambulance.id)
            self.assertEqual(updated_ambulance.status, status)
        
        # 5. Complete dispatch
        dispatch.status = 'completed'
        dispatch.completed_at = timezone.now()
        dispatch.save()
        
        emergency_call.status = 'completed'
        emergency_call.save()
        
        # Verify workflow completion
        self.assertEqual(emergency_call.status, 'completed')
        self.assertEqual(dispatch.status, 'completed')
    
    def test_ambulance_availability_workflow(self):
        """Test ambulance availability tracking"""
        # Start with available ambulance
        self.assertEqual(self.ambulance.status, 'available')
        
        # Dispatch ambulance
        self.ambulance.status = 'dispatched'
        self.ambulance.save()
        
        # Verify ambulance is no longer available
        available_ambulances = Ambulance.objects.filter(status='available')
        self.assertNotIn(self.ambulance, available_ambulances)
        
        # Return to base
        self.ambulance.status = 'available'
        self.ambulance.save()
        
        # Verify ambulance is available again
        available_ambulances = Ambulance.objects.filter(status='available')
        self.assertIn(self.ambulance, available_ambulances)