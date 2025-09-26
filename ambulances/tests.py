from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
# GIS functionality removed - using standard latitude/longitude fields
# from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    Ambulance, AmbulanceType, AmbulanceStation, Dispatch,
    GPSTrackingLog, MaintenanceRecord, EquipmentInventory
)
from referrals.models import Referral
from patients.models import Patient
from doctors.models import DoctorProfile, Hospital

User = get_user_model()


class AmbulanceModelTest(TestCase):
    """Test cases for Ambulance model"""

    def setUp(self):
        self.ambulance_type = AmbulanceType.objects.create(
            name="Advanced Life Support",
            code="ALS",
            description="Advanced life support ambulance"
        )

        self.station = AmbulanceStation.objects.create(
            name="Central Station",
            code="CS01",
            address="123 Main St",
            # location coordinates stored as separate lat/lng fields
            # latitude=-74.0060, longitude=40.7128,
            phone="555-0123"
        )

        self.ambulance = Ambulance.objects.create(
            license_plate="AMB-001",
            vehicle_identification_number="1HGBH41JXMN109186",
            ambulance_type=self.ambulance_type,
            make="Ford",
            model="Transit",
            year=2022,
            color="White",
            patient_capacity=2,
            crew_capacity=3,
            home_station=self.station,
            # current_location coordinates stored as separate lat/lng fields
            # current_latitude=-74.0060, current_longitude=40.7128
        )

    def test_ambulance_creation(self):
        """Test ambulance creation with all required fields"""
        self.assertEqual(self.ambulance.license_plate, "AMB-001")
        self.assertEqual(self.ambulance.ambulance_type, self.ambulance_type)
        self.assertTrue(self.ambulance.is_available)
        self.assertTrue(self.ambulance.is_operational)

    def test_ambulance_str_representation(self):
        """Test string representation of ambulance"""
        expected = f"{self.ambulance_type.name} - AMB-001"
        self.assertEqual(str(self.ambulance), expected)

    def test_ambulance_location_update(self):
        """Test GPS location update functionality"""
        new_lat, new_lng = 40.7589, -73.9851
        self.ambulance.update_location(new_lat, new_lng, speed=50.0, heading=90.0)

        self.ambulance.refresh_from_db()
        self.assertEqual(self.ambulance.current_location.y, new_lat)
        self.assertEqual(self.ambulance.current_location.x, new_lng)
        self.assertEqual(self.ambulance.speed, 50.0)
        self.assertEqual(self.ambulance.heading, 90.0)
        self.assertIsNotNone(self.ambulance.last_gps_update)

    def test_fuel_status_property(self):
        """Test fuel status calculation"""
        self.ambulance.fuel_level = 80
        self.assertEqual(self.ambulance.fuel_status, 'full')

        self.ambulance.fuel_level = 60
        self.assertEqual(self.ambulance.fuel_status, 'good')

        self.ambulance.fuel_level = 30
        self.assertEqual(self.ambulance.fuel_status, 'low')

        self.ambulance.fuel_level = 10
        self.assertEqual(self.ambulance.fuel_status, 'critical')

    def test_maintenance_needed(self):
        """Test maintenance requirement check"""
        # Set next maintenance to past date
        self.ambulance.next_maintenance = timezone.now() - timedelta(days=1)
        self.assertTrue(self.ambulance.needs_maintenance)

        # Set next maintenance to future date
        self.ambulance.next_maintenance = timezone.now() + timedelta(days=30)
        self.assertFalse(self.ambulance.needs_maintenance)