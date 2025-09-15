from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random
from decimal import Decimal

from ambulances.models import (
    Ambulance, AmbulanceType, AmbulanceStation, AmbulanceCrew,
    Dispatch, GPSTrackingLog, MaintenanceRecord, EquipmentInventory,
    FuelLog, IncidentReport, PerformanceMetrics
)
from doctors.models import DoctorProfile, Hospital, Specialty
from patients.models import Patient
from referrals.models import Referral

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample data for all models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self.clear_data()

        self.stdout.write('Seeding database with sample data...')
        
        # Create users first
        self.create_users()

        # Create doctors and patients
        self.create_doctors()
        self.create_patients()
        
        # Create ambulance infrastructure
        self.create_ambulance_types()
        self.create_ambulance_stations()
        self.create_ambulances()
        self.create_ambulance_crews()
        
        # Create operational data
        self.create_referrals()
        self.create_dispatches()
        self.create_gps_logs()
        self.create_maintenance_records()
        self.create_equipment_inventory()
        self.create_fuel_logs()
        self.create_incident_reports()
        self.create_performance_metrics()

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded database with sample data!')
        )

    def clear_data(self):
        """Clear existing data"""
        models_to_clear = [
            PerformanceMetrics, IncidentReport, FuelLog, EquipmentInventory,
            MaintenanceRecord, GPSTrackingLog, Dispatch, AmbulanceCrew,
            Ambulance, AmbulanceStation, AmbulanceType, Referral,
            Patient, DoctorProfile
        ]
        
        for model in models_to_clear:
            model.objects.all().delete()
            self.stdout.write(f'Cleared {model.__name__}')

    def create_users(self):
        """Create sample users"""
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@mediconnect.com',
                password='admin123',
                first_name='System',
                last_name='Administrator'
            )
        
        # Create regular users
        for i in range(1, 11):
            if not User.objects.filter(username=f'user{i}').exists():
                User.objects.create_user(
                    username=f'user{i}',
                    email=f'user{i}@mediconnect.com',
                    password='password123',
                    first_name=f'User{i}',
                    last_name='Test'
                )



    def create_doctors(self):
        """Create sample doctors and hospitals"""
        # First create hospitals
        hospitals_data = [
            {'name': 'MediConnect General Hospital', 'address': '123 Medical Center Dr', 'city': 'New York', 'state': 'NY', 'zip_code': '10001', 'phone': '+1-555-0101', 'email': 'info@mediconnect.com'},
            {'name': 'City Emergency Medical Center', 'address': '456 Emergency Ave', 'city': 'Los Angeles', 'state': 'CA', 'zip_code': '90001', 'phone': '+1-555-0102', 'email': 'info@cityemc.com'},
            {'name': 'Regional Trauma Center', 'address': '789 Trauma Blvd', 'city': 'Chicago', 'state': 'IL', 'zip_code': '60601', 'phone': '+1-555-0103', 'email': 'info@rtc.com'},
            {'name': 'Community Health Hospital', 'address': '321 Community St', 'city': 'Houston', 'state': 'TX', 'zip_code': '77001', 'phone': '+1-555-0104', 'email': 'info@chh.com'},
            {'name': 'Specialized Care Institute', 'address': '654 Specialty Rd', 'city': 'Phoenix', 'state': 'AZ', 'zip_code': '85001', 'phone': '+1-555-0105', 'email': 'info@sci.com'},
        ]

        hospitals = []
        for data in hospitals_data:
            hospital, created = Hospital.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            hospitals.append(hospital)

        # Create specialties
        specialties_data = [
            {'name': 'Cardiology', 'code': 'CARD'},
            {'name': 'Neurology', 'code': 'NEUR'},
            {'name': 'Orthopedics', 'code': 'ORTH'},
            {'name': 'Emergency Medicine', 'code': 'EMER'},
            {'name': 'Pediatrics', 'code': 'PEDI'},
            {'name': 'Surgery', 'code': 'SURG'},
            {'name': 'Internal Medicine', 'code': 'INTM'},
            {'name': 'Radiology', 'code': 'RADI'},
            {'name': 'Anesthesiology', 'code': 'ANES'},
            {'name': 'Psychiatry', 'code': 'PSYC'},
        ]

        specialties = []
        for data in specialties_data:
            specialty, created = Specialty.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            specialties.append(specialty)

        # Create doctors
        for i in range(10):
            user, created = User.objects.get_or_create(
                username=f'doctor{i+1}',
                defaults={
                    'email': f'doctor{i+1}@mediconnect.com',
                    'first_name': f'John{i+1}',
                    'last_name': f'Doctor{i+1}',
                    'password': 'pbkdf2_sha256$600000$test$test'
                }
            )

            DoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': f'John{i+1}',
                    'last_name': f'Doctor{i+1}',
                    'gender': random.choice(['M', 'F']),
                    'date_of_birth': timezone.now().date() - timedelta(days=random.randint(365*30, 365*65)),
                    'license_number': f'MD{10000 + i}',
                    'license_state': 'NY',
                    'license_expiry_date': timezone.now().date() + timedelta(days=365*2),
                    'npi_number': f'{1000000000 + i}',
                    'phone': f'+1-555-{2000 + i}',
                    'office_address': f'{(i+1)*100} Medical Plaza',
                    'city': 'New York',
                    'state': 'NY',
                    'zip_code': '10001',
                    'medical_school': f'Medical University {i+1}',
                    'graduation_year': random.randint(1990, 2020),
                    'residency_program': f'Residency Program {i+1}',
                    'primary_hospital': hospitals[i % len(hospitals)],
                    'primary_specialty': specialties[i % len(specialties)],
                    'bio': f'Experienced {specialties[i % len(specialties)].name} specialist.',
                    'years_of_experience': random.randint(1, 30),
                    'consultation_fee': Decimal(str(random.randint(100, 500))),
                    'verification_status': 'verified',
                    'verification_date': timezone.now(),
                }
            )

    def create_patients(self):
        """Create sample patients"""
        for i in range(1, 11):
            user, created = User.objects.get_or_create(
                username=f'patient{i}',
                defaults={
                    'email': f'patient{i}@example.com',
                    'first_name': f'Patient{i}',
                    'last_name': 'Test',
                    'password': 'pbkdf2_sha256$600000$test$test'
                }
            )

            Patient.objects.get_or_create(
                user=user,
                defaults={
                    'patient_id': f'PAT{10000 + i}',
                    'first_name': f'Patient{i}',
                    'last_name': 'Test',
                    'date_of_birth': timezone.now().date() - timedelta(days=random.randint(365*18, 365*80)),
                    'gender': random.choice(['M', 'F', 'NB', 'O']),
                    'marital_status': random.choice(['S', 'M', 'D', 'W']),
                    'phone_primary': f'+1-555-{3000 + i}',
                    'email': f'patient{i}@example.com',
                    'address_line1': f'{i*100} Patient St',
                    'city': 'New York',
                    'state_province': 'NY',
                    'postal_code': '10001',
                    'emergency_contact_1_name': f'Emergency Contact {i}',
                    'emergency_contact_1_phone': f'+1-555-{4000 + i}',
                    'emergency_contact_1_relationship': 'Spouse',
                    'insurance_provider': f'Insurance Company {i}',
                }
            )

    def create_ambulance_types(self):
        """Create ambulance types"""
        types_data = [
            {'name': 'Basic Life Support (BLS)', 'code': 'BLS', 'description': 'Basic emergency medical care'},
            {'name': 'Advanced Life Support (ALS)', 'code': 'ALS', 'description': 'Advanced emergency medical care'},
            {'name': 'Critical Care Transport (CCT)', 'code': 'CCT', 'description': 'Critical care patient transport'},
            {'name': 'Neonatal Intensive Care Unit (NICU)', 'code': 'NICU', 'description': 'Specialized neonatal transport'},
            {'name': 'Bariatric Transport', 'code': 'BARI', 'description': 'Heavy-duty patient transport'},
            {'name': 'Air Medical', 'code': 'AIR', 'description': 'Helicopter emergency medical service'},
            {'name': 'Mobile Intensive Care Unit (MICU)', 'code': 'MICU', 'description': 'Mobile ICU capabilities'},
            {'name': 'Psychiatric Transport', 'code': 'PSYC', 'description': 'Specialized psychiatric patient transport'},
            {'name': 'Hazmat Response', 'code': 'HAZ', 'description': 'Hazardous materials response unit'},
            {'name': 'Mass Casualty Unit', 'code': 'MCU', 'description': 'Multiple patient transport capability'},
        ]

        for data in types_data:
            AmbulanceType.objects.get_or_create(
                code=data['code'],
                defaults=data
            )

    def create_ambulance_stations(self):
        """Create ambulance stations"""
        stations_data = [
            {'name': 'Central Station', 'address': '100 Central Ave', 'phone': '+1-555-5001'},
            {'name': 'North Station', 'address': '200 North St', 'phone': '+1-555-5002'},
            {'name': 'South Station', 'address': '300 South Blvd', 'phone': '+1-555-5003'},
            {'name': 'East Station', 'address': '400 East Dr', 'phone': '+1-555-5004'},
            {'name': 'West Station', 'address': '500 West Ave', 'phone': '+1-555-5005'},
            {'name': 'Downtown Station', 'address': '600 Downtown St', 'phone': '+1-555-5006'},
            {'name': 'Airport Station', 'address': '700 Airport Rd', 'phone': '+1-555-5007'},
            {'name': 'Highway Station', 'address': '800 Highway 1', 'phone': '+1-555-5008'},
            {'name': 'Suburban Station', 'address': '900 Suburban Way', 'phone': '+1-555-5009'},
            {'name': 'Emergency Hub', 'address': '1000 Emergency Blvd', 'phone': '+1-555-5010'},
        ]
        
        for data in stations_data:
            AmbulanceStation.objects.get_or_create(
                name=data['name'],
                defaults=data
            )

    def create_ambulances(self):
        """Create sample ambulances"""
        ambulance_types = AmbulanceType.objects.all()
        stations = AmbulanceStation.objects.all()

        ambulances_data = [
            {'license_plate': 'AMB-001', 'make': 'Ford', 'model': 'Transit', 'year': 2022},
            {'license_plate': 'AMB-002', 'make': 'Mercedes', 'model': 'Sprinter', 'year': 2023},
            {'license_plate': 'AMB-003', 'make': 'Chevrolet', 'model': 'Express', 'year': 2021},
            {'license_plate': 'AMB-004', 'make': 'Ford', 'model': 'E-Series', 'year': 2022},
            {'license_plate': 'AMB-005', 'make': 'Ram', 'model': 'ProMaster', 'year': 2023},
            {'license_plate': 'AMB-006', 'make': 'Mercedes', 'model': 'Sprinter', 'year': 2022},
            {'license_plate': 'AMB-007', 'make': 'Ford', 'model': 'Transit', 'year': 2021},
            {'license_plate': 'AMB-008', 'make': 'Chevrolet', 'model': 'Express', 'year': 2023},
            {'license_plate': 'AMB-009', 'make': 'Ford', 'model': 'E-Series', 'year': 2022},
            {'license_plate': 'AMB-010', 'make': 'Ram', 'model': 'ProMaster', 'year': 2023},
        ]

        for i, data in enumerate(ambulances_data):
            Ambulance.objects.get_or_create(
                license_plate=data['license_plate'],
                defaults={
                    **data,
                    'ambulance_type': ambulance_types[i % len(ambulance_types)],
                    'home_station': stations[i % len(stations)],
                    'status': random.choice(['available', 'in_use', 'under_maintenance']),
                    'fuel_level': random.randint(20, 100),
                    'mileage': random.randint(10000, 150000),
                    'last_maintenance_date': timezone.now().date() - timedelta(days=random.randint(1, 90)),
                    'next_maintenance_due': timezone.now().date() + timedelta(days=random.randint(30, 180)),
                    'equipment_status': random.choice(['fully_equipped', 'partially_equipped', 'needs_restocking']),
                    'gps_enabled': True,
                    'current_latitude': Decimal(str(40.7128 + random.uniform(-0.1, 0.1))),
                    'current_longitude': Decimal(str(-74.0060 + random.uniform(-0.1, 0.1))),
                }
            )

    def create_ambulance_crews(self):
        """Create ambulance crew members"""
        ambulances = Ambulance.objects.all()

        crew_data = [
            {'name': 'John Smith', 'role': 'paramedic', 'license': 'PM001', 'phone': '+1-555-6001'},
            {'name': 'Sarah Johnson', 'role': 'emt', 'license': 'EMT001', 'phone': '+1-555-6002'},
            {'name': 'Mike Davis', 'role': 'driver', 'license': 'CDL001', 'phone': '+1-555-6003'},
            {'name': 'Lisa Wilson', 'role': 'paramedic', 'license': 'PM002', 'phone': '+1-555-6004'},
            {'name': 'David Brown', 'role': 'emt', 'license': 'EMT002', 'phone': '+1-555-6005'},
            {'name': 'Jennifer Garcia', 'role': 'driver', 'license': 'CDL002', 'phone': '+1-555-6006'},
            {'name': 'Robert Miller', 'role': 'paramedic', 'license': 'PM003', 'phone': '+1-555-6007'},
            {'name': 'Amanda Taylor', 'role': 'emt', 'license': 'EMT003', 'phone': '+1-555-6008'},
            {'name': 'Christopher Lee', 'role': 'driver', 'license': 'CDL003', 'phone': '+1-555-6009'},
            {'name': 'Michelle White', 'role': 'paramedic', 'license': 'PM004', 'phone': '+1-555-6010'},
        ]

        for i, data in enumerate(crew_data):
            AmbulanceCrew.objects.get_or_create(
                name=data['name'],
                defaults={
                    **data,
                    'ambulance': ambulances[i % len(ambulances)],
                    'years_of_experience': random.randint(1, 20),
                    'certification_expiry': timezone.now().date() + timedelta(days=random.randint(30, 730)),
                    'is_active': random.choice([True, False]),
                    'shift_start': timezone.now().time().replace(hour=random.randint(6, 18)),
                    'shift_end': timezone.now().time().replace(hour=random.randint(18, 23)),
                }
            )

    def create_referrals(self):
        """Create sample referrals"""
        patients = Patient.objects.all()
        doctors = DoctorProfile.objects.all()

        for i in range(10):
            Referral.objects.get_or_create(
                patient=patients[i % len(patients)],
                defaults={
                    'referring_doctor': doctors[i % len(doctors)],
                    'referred_to_doctor': doctors[(i+1) % len(doctors)],
                    'reason_for_referral': f'Medical condition requiring specialized care {i+1}',
                    'urgency_level': random.choice(['low', 'medium', 'high', 'emergency']),
                    'status': random.choice(['pending', 'approved', 'completed', 'cancelled']),
                    'notes': f'Additional notes for referral {i+1}',
                    'appointment_date': timezone.now().date() + timedelta(days=random.randint(1, 30)),
                }
            )

    def create_dispatches(self):
        """Create sample dispatches"""
        ambulances = Ambulance.objects.all()
        referrals = Referral.objects.all()
        users = User.objects.all()

        for i in range(10):
            Dispatch.objects.get_or_create(
                dispatch_number=f'DISP-{1000 + i}',
                defaults={
                    'ambulance': ambulances[i % len(ambulances)],
                    'referral': referrals[i % len(referrals)],
                    'dispatcher': users[i % len(users)],
                    'priority': random.choice(['routine', 'urgent', 'emergency']),
                    'status': random.choice(['requested', 'dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital', 'at_hospital', 'completed']),
                    'pickup_address': f'{(i+1)*100} Pickup St, City, State',
                    'pickup_latitude': Decimal(str(40.7128 + random.uniform(-0.1, 0.1))),
                    'pickup_longitude': Decimal(str(-74.0060 + random.uniform(-0.1, 0.1))),
                    'destination_address': f'{(i+1)*200} Hospital Ave, City, State',
                    'destination_latitude': Decimal(str(40.7128 + random.uniform(-0.1, 0.1))),
                    'destination_longitude': Decimal(str(-74.0060 + random.uniform(-0.1, 0.1))),
                    'estimated_pickup_time': timezone.now() + timedelta(minutes=random.randint(5, 30)),
                    'estimated_arrival_time': timezone.now() + timedelta(minutes=random.randint(30, 90)),
                    'distance_km': Decimal(str(random.uniform(1.0, 50.0))),
                    'special_instructions': f'Special instructions for dispatch {i+1}',
                    'contact_person': f'Contact Person {i+1}',
                    'contact_phone': f'+1-555-{7000 + i}',
                }
            )

    def create_gps_logs(self):
        """Create GPS tracking logs"""
        ambulances = Ambulance.objects.all()

        for ambulance in ambulances:
            for i in range(10):
                GPSTrackingLog.objects.get_or_create(
                    ambulance=ambulance,
                    timestamp=timezone.now() - timedelta(hours=random.randint(1, 24)),
                    defaults={
                        'latitude': Decimal(str(40.7128 + random.uniform(-0.1, 0.1))),
                        'longitude': Decimal(str(-74.0060 + random.uniform(-0.1, 0.1))),
                        'speed': Decimal(str(random.uniform(0, 80))),
                        'heading': random.randint(0, 360),
                        'altitude': Decimal(str(random.uniform(0, 500))),
                    }
                )

    def create_maintenance_records(self):
        """Create maintenance records"""
        ambulances = Ambulance.objects.all()

        maintenance_types = ['routine', 'repair', 'inspection', 'emergency']

        for i, ambulance in enumerate(ambulances):
            MaintenanceRecord.objects.get_or_create(
                ambulance=ambulance,
                maintenance_date=timezone.now().date() - timedelta(days=random.randint(1, 90)),
                defaults={
                    'maintenance_type': random.choice(maintenance_types),
                    'description': f'Maintenance work performed on {ambulance.license_plate}',
                    'cost': Decimal(str(random.uniform(100, 5000))),
                    'performed_by': f'Technician {i+1}',
                    'next_maintenance_due': timezone.now().date() + timedelta(days=random.randint(30, 180)),
                    'parts_replaced': f'Sample parts for {ambulance.license_plate}',
                    'labor_hours': Decimal(str(random.uniform(1, 8))),
                }
            )

    def create_equipment_inventory(self):
        """Create equipment inventory"""
        ambulances = Ambulance.objects.all()

        equipment_items = [
            'Defibrillator', 'Oxygen Tank', 'Stretcher', 'First Aid Kit',
            'Blood Pressure Monitor', 'Pulse Oximeter', 'Splints', 'Bandages',
            'IV Supplies', 'Medications'
        ]

        for i, ambulance in enumerate(ambulances):
            item = equipment_items[i % len(equipment_items)]
            EquipmentInventory.objects.get_or_create(
                ambulance=ambulance,
                item_name=item,
                defaults={
                    'quantity': random.randint(1, 10),
                    'condition': random.choice(['excellent', 'good', 'fair', 'needs_replacement']),
                    'last_checked': timezone.now().date() - timedelta(days=random.randint(1, 30)),
                    'expiry_date': timezone.now().date() + timedelta(days=random.randint(30, 365)),
                    'supplier': f'Medical Supply Co {i+1}',
                    'cost_per_unit': Decimal(str(random.uniform(10, 1000))),
                }
            )

    def create_fuel_logs(self):
        """Create fuel logs"""
        ambulances = Ambulance.objects.all()

        for i, ambulance in enumerate(ambulances):
            FuelLog.objects.get_or_create(
                ambulance=ambulance,
                date=timezone.now().date() - timedelta(days=random.randint(1, 30)),
                defaults={
                    'fuel_amount': Decimal(str(random.uniform(20, 80))),
                    'cost': Decimal(str(random.uniform(50, 200))),
                    'odometer_reading': random.randint(ambulance.mileage, ambulance.mileage + 1000),
                    'fuel_station': f'Gas Station {i+1}',
                    'driver_name': f'Driver {i+1}',
                }
            )

    def create_incident_reports(self):
        """Create incident reports"""
        dispatches = Dispatch.objects.all()

        for i, dispatch in enumerate(dispatches[:10]):
            IncidentReport.objects.get_or_create(
                dispatch=dispatch,
                defaults={
                    'incident_type': random.choice(['medical_emergency', 'accident', 'equipment_failure', 'other']),
                    'description': f'Incident report for dispatch {dispatch.dispatch_number}',
                    'severity': random.choice(['low', 'medium', 'high', 'critical']),
                    'reported_by': f'Crew Member {i+1}',
                    'actions_taken': f'Actions taken for incident {i+1}',
                    'outcome': random.choice(['resolved', 'ongoing', 'escalated']),
                    'follow_up_required': random.choice([True, False]),
                }
            )

    def create_performance_metrics(self):
        """Create performance metrics"""
        ambulances = Ambulance.objects.all()

        for i, ambulance in enumerate(ambulances):
            PerformanceMetrics.objects.get_or_create(
                ambulance=ambulance,
                date=timezone.now().date() - timedelta(days=random.randint(1, 30)),
                defaults={
                    'total_calls': random.randint(1, 20),
                    'average_response_time': Decimal(str(random.uniform(5, 30))),
                    'fuel_efficiency': Decimal(str(random.uniform(8, 15))),
                    'distance_traveled': Decimal(str(random.uniform(50, 500))),
                    'patient_satisfaction_score': Decimal(str(random.uniform(3.0, 5.0))),
                    'crew_performance_score': Decimal(str(random.uniform(3.0, 5.0))),
                    'equipment_reliability_score': Decimal(str(random.uniform(3.0, 5.0))),
                }
            )
