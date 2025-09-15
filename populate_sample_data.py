#!/usr/bin/env python
"""
Script to populate the hospital e-referral system with sample data
"""

import os
import sys
import django
from django.utils import timezone
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_ereferral.settings')
django.setup()

from ambulances.models import AmbulanceType, AmbulanceStation, Ambulance
from doctors.models import Hospital, Specialty
from users.models import User


def create_ambulance_types():
    """Create sample ambulance types"""
    print("Creating ambulance types...")
    
    types = [
        {
            'name': 'Basic Life Support',
            'code': 'BLS',
            'description': 'Basic life support ambulance with essential medical equipment',
            'equipment_requirements': ['Oxygen tank', 'First aid kit', 'Stretcher', 'Defibrillator']
        },
        {
            'name': 'Advanced Life Support',
            'code': 'ALS',
            'description': 'Advanced life support ambulance with comprehensive medical equipment',
            'equipment_requirements': ['Ventilator', 'Advanced cardiac monitor', 'IV equipment', 'Medications']
        },
        {
            'name': 'Critical Care Transport',
            'code': 'CCT',
            'description': 'Critical care transport for intensive care patients',
            'equipment_requirements': ['ICU-level equipment', 'Specialized monitors', 'Advanced medications']
        },
        {
            'name': 'Neonatal Transport',
            'code': 'NICU',
            'description': 'Specialized transport for newborns and infants',
            'equipment_requirements': ['Neonatal incubator', 'Pediatric equipment', 'Specialized monitors']
        }
    ]
    
    for type_data in types:
        ambulance_type, created = AmbulanceType.objects.get_or_create(
            code=type_data['code'],
            defaults=type_data
        )
        if created:
            print(f"  ✓ Created ambulance type: {ambulance_type.name}")
        else:
            print(f"  - Ambulance type already exists: {ambulance_type.name}")


def create_ambulance_stations():
    """Create sample ambulance stations"""
    print("Creating ambulance stations...")
    
    stations = [
        {
            'name': 'Central Emergency Station',
            'code': 'CES01',
            'address': '123 Main Street, Downtown',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'phone': '555-0123',
            'capacity': 8,
            'is_24_hour': True
        },
        {
            'name': 'North District Station',
            'code': 'NDS01',
            'address': '456 North Avenue, North District',
            'latitude': 40.7589,
            'longitude': -73.9851,
            'phone': '555-0124',
            'capacity': 6,
            'is_24_hour': True
        },
        {
            'name': 'South Medical Center',
            'code': 'SMC01',
            'address': '789 South Boulevard, Medical District',
            'latitude': 40.6892,
            'longitude': -74.0445,
            'phone': '555-0125',
            'capacity': 10,
            'is_24_hour': True
        },
        {
            'name': 'East Emergency Hub',
            'code': 'EEH01',
            'address': '321 East Road, East Side',
            'latitude': 40.7282,
            'longitude': -73.9942,
            'phone': '555-0126',
            'capacity': 4,
            'is_24_hour': False
        }
    ]
    
    for station_data in stations:
        station, created = AmbulanceStation.objects.get_or_create(
            code=station_data['code'],
            defaults=station_data
        )
        if created:
            print(f"  ✓ Created station: {station.name}")
        else:
            print(f"  - Station already exists: {station.name}")


def create_hospitals():
    """Create sample hospitals"""
    print("Creating hospitals...")
    
    hospitals = [
        {
            'name': 'General Hospital',
            'address': '100 Hospital Drive',
            'city': 'Medical Center',
            'state': 'NY',
            'zip_code': '10001',
            'phone': '555-0200',
            'email': 'info@generalhospital.com',
            'website': 'https://generalhospital.com',
            'type': 'general',
            'bed_capacity': 500,
            'trauma_center_level': 'I',
            'emergency_services': True,
            'accreditation': 'Joint Commission'
        },
        {
            'name': 'St. Mary\'s Medical Center',
            'address': '200 Saint Mary\'s Way',
            'city': 'Healthcare District',
            'state': 'NY',
            'zip_code': '10002',
            'phone': '555-0300',
            'email': 'contact@stmarys.com',
            'website': 'https://stmarys.com',
            'type': 'general',
            'bed_capacity': 350,
            'trauma_center_level': 'II',
            'emergency_services': True,
            'accreditation': 'Joint Commission'
        },
        {
            'name': 'Children\'s Hospital',
            'address': '300 Kids Avenue',
            'city': 'Pediatric Center',
            'state': 'NY',
            'zip_code': '10003',
            'phone': '555-0400',
            'email': 'info@childrenshospital.com',
            'website': 'https://childrenshospital.com',
            'type': 'specialty',
            'bed_capacity': 200,
            'trauma_center_level': 'III',
            'emergency_services': True,
            'accreditation': 'Joint Commission'
        },
        {
            'name': 'Emergency Medical Center',
            'address': '400 Emergency Street',
            'city': 'Urgent Care',
            'state': 'NY',
            'zip_code': '10004',
            'phone': '555-0500',
            'email': 'emergency@emc.com',
            'website': 'https://emc.com',
            'type': 'emergency',
            'bed_capacity': 150,
            'trauma_center_level': 'I',
            'emergency_services': True,
            'accreditation': 'Joint Commission'
        }
    ]
    
    for hospital_data in hospitals:
        hospital, created = Hospital.objects.get_or_create(
            name=hospital_data['name'],
            defaults=hospital_data
        )
        if created:
            print(f"  ✓ Created hospital: {hospital.name}")
        else:
            print(f"  - Hospital already exists: {hospital.name}")


def create_specialties():
    """Create medical specialties"""
    print("Creating medical specialties...")
    
    specialties = [
        {'name': 'Emergency Medicine', 'code': 'EM', 'description': 'Emergency medical care and trauma'},
        {'name': 'Cardiology', 'code': 'CARD', 'description': 'Heart and cardiovascular system'},
        {'name': 'Neurology', 'code': 'NEURO', 'description': 'Nervous system and brain disorders'},
        {'name': 'Orthopedics', 'code': 'ORTHO', 'description': 'Musculoskeletal system and bones'},
        {'name': 'Pediatrics', 'code': 'PEDS', 'description': 'Medical care for children and infants'},
        {'name': 'Internal Medicine', 'code': 'IM', 'description': 'General internal medicine'},
        {'name': 'Surgery', 'code': 'SURG', 'description': 'Surgical procedures and operations'},
        {'name': 'Obstetrics & Gynecology', 'code': 'OBGYN', 'description': 'Women\'s health and childbirth'},
        {'name': 'Psychiatry', 'code': 'PSYCH', 'description': 'Mental health and psychiatric care'},
        {'name': 'Radiology', 'code': 'RAD', 'description': 'Medical imaging and diagnostics'}
    ]
    
    for specialty_data in specialties:
        try:
            specialty, created = Specialty.objects.get_or_create(
                code=specialty_data['code'],
                defaults=specialty_data
            )
            if created:
                print(f"  ✓ Created specialty: {specialty.name}")
            else:
                print(f"  - Specialty already exists: {specialty.name}")
        except Exception as e:
            # Try to get by name if code fails
            try:
                specialty = Specialty.objects.get(name=specialty_data['name'])
                print(f"  - Specialty already exists: {specialty.name}")
            except Specialty.DoesNotExist:
                print(f"  ❌ Error creating specialty {specialty_data['name']}: {str(e)}")


def create_ambulances():
    """Create sample ambulances"""
    print("Creating ambulances...")
    
    # Get required objects
    bls_type = AmbulanceType.objects.get(code='BLS')
    als_type = AmbulanceType.objects.get(code='ALS')
    cct_type = AmbulanceType.objects.get(code='CCT')
    
    central_station = AmbulanceStation.objects.get(code='CES01')
    north_station = AmbulanceStation.objects.get(code='NDS01')
    south_station = AmbulanceStation.objects.get(code='SMC01')
    
    ambulances = [
        {
            'license_plate': 'AMB-001',
            'vehicle_identification_number': '1HGBH41JXMN109001',
            'ambulance_type': bls_type,
            'make': 'Ford',
            'model': 'Transit',
            'year': 2022,
            'color': 'White',
            'patient_capacity': 2,
            'crew_capacity': 3,
            'home_station': central_station,
            'medical_equipment': 'Oxygen tank, First aid kit, Stretcher, Basic defibrillator',
            'fuel_level': 85,
            'mileage': 15000,
            'condition': 'excellent'
        },
        {
            'license_plate': 'AMB-002',
            'vehicle_identification_number': '1HGBH41JXMN109002',
            'ambulance_type': als_type,
            'make': 'Mercedes',
            'model': 'Sprinter',
            'year': 2023,
            'color': 'White',
            'patient_capacity': 2,
            'crew_capacity': 4,
            'home_station': central_station,
            'medical_equipment': 'Advanced cardiac monitor, Ventilator, IV equipment, Medications',
            'fuel_level': 92,
            'mileage': 8500,
            'condition': 'excellent'
        },
        {
            'license_plate': 'AMB-003',
            'vehicle_identification_number': '1HGBH41JXMN109003',
            'ambulance_type': bls_type,
            'make': 'Ford',
            'model': 'Transit',
            'year': 2021,
            'color': 'White',
            'patient_capacity': 2,
            'crew_capacity': 3,
            'home_station': north_station,
            'medical_equipment': 'Oxygen tank, First aid kit, Stretcher, Basic defibrillator',
            'fuel_level': 78,
            'mileage': 22000,
            'condition': 'good'
        },
        {
            'license_plate': 'AMB-004',
            'vehicle_identification_number': '1HGBH41JXMN109004',
            'ambulance_type': cct_type,
            'make': 'Mercedes',
            'model': 'Sprinter',
            'year': 2023,
            'color': 'White',
            'patient_capacity': 1,
            'crew_capacity': 4,
            'home_station': south_station,
            'medical_equipment': 'ICU-level equipment, Specialized monitors, Advanced medications',
            'fuel_level': 95,
            'mileage': 5000,
            'condition': 'excellent'
        },
        {
            'license_plate': 'AMB-005',
            'vehicle_identification_number': '1HGBH41JXMN109005',
            'ambulance_type': als_type,
            'make': 'Ford',
            'model': 'Transit',
            'year': 2022,
            'color': 'White',
            'patient_capacity': 2,
            'crew_capacity': 3,
            'home_station': north_station,
            'medical_equipment': 'Advanced cardiac monitor, Ventilator, IV equipment',
            'fuel_level': 67,
            'mileage': 18000,
            'condition': 'good'
        }
    ]
    
    for ambulance_data in ambulances:
        ambulance, created = Ambulance.objects.get_or_create(
            license_plate=ambulance_data['license_plate'],
            defaults=ambulance_data
        )
        if created:
            print(f"  ✓ Created ambulance: {ambulance.license_plate} ({ambulance.ambulance_type.name})")
        else:
            print(f"  - Ambulance already exists: {ambulance.license_plate}")


def main():
    """Main function to populate all sample data"""
    print("=" * 60)
    print("POPULATING HOSPITAL E-REFERRAL SYSTEM WITH SAMPLE DATA")
    print("=" * 60)
    
    try:
        create_ambulance_types()
        create_ambulance_stations()
        create_hospitals()
        create_specialties()
        create_ambulances()
        
        print("\n" + "=" * 60)
        print("✅ SAMPLE DATA POPULATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  • Ambulance Types: {AmbulanceType.objects.count()}")
        print(f"  • Ambulance Stations: {AmbulanceStation.objects.count()}")
        print(f"  • Hospitals: {Hospital.objects.count()}")
        print(f"  • Medical Specialties: {Specialty.objects.count()}")
        print(f"  • Ambulances: {Ambulance.objects.count()}")
        
        print("\nYou can now:")
        print("  1. Access the admin interface at http://127.0.0.1:8000/admin/")
        print("  2. Login with username: zak")
        print("  3. Explore the ambulance management system")
        print("  4. Test the real-time tracking features")
        
    except Exception as e:
        print(f"\n❌ Error populating sample data: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
