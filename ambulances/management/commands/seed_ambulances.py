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

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with ambulance sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing ambulance data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing ambulance data...')
            self.clear_ambulance_data()

        self.stdout.write('Seeding database with ambulance sample data...')
        
        # Create ambulance infrastructure
        self.create_ambulance_types()
        self.create_ambulance_stations()
        self.create_ambulances()
        self.create_ambulance_crews()
        
        # Create operational data
        self.create_dispatches()
        self.create_gps_logs()
        self.create_maintenance_records()
        self.create_equipment_inventory()
        self.create_fuel_logs()
        self.create_incident_reports()
        self.create_performance_metrics()

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded database with ambulance sample data!')
        )

    def clear_ambulance_data(self):
        """Clear existing ambulance data"""
        models_to_clear = [
            PerformanceMetrics, IncidentReport, FuelLog, EquipmentInventory,
            MaintenanceRecord, GPSTrackingLog, Dispatch, AmbulanceCrew,
            Ambulance, AmbulanceStation, AmbulanceType
        ]
        
        for model in models_to_clear:
            model.objects.all().delete()
            self.stdout.write(f'Cleared {model.__name__}')

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
            {'name': 'Central Station', 'code': 'CENT', 'address': '100 Central Ave', 'latitude': 40.7128, 'longitude': -74.0060, 'phone': '+1-555-5001'},
            {'name': 'North Station', 'code': 'NRTH', 'address': '200 North St', 'latitude': 40.7228, 'longitude': -74.0160, 'phone': '+1-555-5002'},
            {'name': 'South Station', 'code': 'SUTH', 'address': '300 South Blvd', 'latitude': 40.7028, 'longitude': -73.9960, 'phone': '+1-555-5003'},
            {'name': 'East Station', 'code': 'EAST', 'address': '400 East Dr', 'latitude': 40.7328, 'longitude': -73.9860, 'phone': '+1-555-5004'},
            {'name': 'West Station', 'code': 'WEST', 'address': '500 West Ave', 'latitude': 40.6928, 'longitude': -74.0260, 'phone': '+1-555-5005'},
            {'name': 'Downtown Station', 'code': 'DOWN', 'address': '600 Downtown St', 'latitude': 40.7428, 'longitude': -74.0360, 'phone': '+1-555-5006'},
            {'name': 'Airport Station', 'code': 'AIRP', 'address': '700 Airport Rd', 'latitude': 40.6828, 'longitude': -73.9760, 'phone': '+1-555-5007'},
            {'name': 'Highway Station', 'code': 'HWAY', 'address': '800 Highway 1', 'latitude': 40.7528, 'longitude': -74.0460, 'phone': '+1-555-5008'},
            {'name': 'Suburban Station', 'code': 'SUBR', 'address': '900 Suburban Way', 'latitude': 40.6728, 'longitude': -73.9660, 'phone': '+1-555-5009'},
            {'name': 'Emergency Hub', 'code': 'EMRG', 'address': '1000 Emergency Blvd', 'latitude': 40.7628, 'longitude': -74.0560, 'phone': '+1-555-5010'},
        ]

        for data in stations_data:
            AmbulanceStation.objects.get_or_create(
                code=data['code'],
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
                    'vehicle_identification_number': f'1HGBH41JXMN{100000 + i}',
                    'ambulance_type': ambulance_types[i % len(ambulance_types)],
                    'home_station': stations[i % len(stations)],
                    'color': random.choice(['White', 'Yellow', 'Red', 'Blue']),
                    'status': random.choice(['available', 'dispatched', 'maintenance']),
                    'condition': random.choice(['excellent', 'good', 'fair']),
                    'fuel_level': random.randint(20, 100),
                    'mileage': random.randint(10000, 150000),
                    'last_maintenance': timezone.now() - timedelta(days=random.randint(1, 90)),
                    'next_maintenance': timezone.now() + timedelta(days=random.randint(30, 180)),
                    'current_latitude': 40.7128 + random.uniform(-0.1, 0.1),
                    'current_longitude': -74.0060 + random.uniform(-0.1, 0.1),
                    'base_latitude': 40.7128 + random.uniform(-0.1, 0.1),
                    'base_longitude': -74.0060 + random.uniform(-0.1, 0.1),
                    'gps_device_id': f'GPS{10000 + i}',
                    'last_gps_update': timezone.now() - timedelta(minutes=random.randint(1, 60)),
                    'speed': random.uniform(0, 80),
                    'heading': random.uniform(0, 360),
                }
            )

    def create_ambulance_crews(self):
        """Create ambulance crew members"""
        ambulances = Ambulance.objects.all()

        crew_data = [
            {'first_name': 'John', 'last_name': 'Smith', 'role': 'paramedic'},
            {'first_name': 'Sarah', 'last_name': 'Johnson', 'role': 'emt'},
            {'first_name': 'Mike', 'last_name': 'Davis', 'role': 'driver'},
            {'first_name': 'Lisa', 'last_name': 'Wilson', 'role': 'paramedic'},
            {'first_name': 'David', 'last_name': 'Brown', 'role': 'emt'},
            {'first_name': 'Jennifer', 'last_name': 'Garcia', 'role': 'driver'},
            {'first_name': 'Robert', 'last_name': 'Miller', 'role': 'paramedic'},
            {'first_name': 'Amanda', 'last_name': 'Taylor', 'role': 'emt'},
            {'first_name': 'Christopher', 'last_name': 'Lee', 'role': 'driver'},
            {'first_name': 'Michelle', 'last_name': 'White', 'role': 'paramedic'},
        ]

        for i, data in enumerate(crew_data):
            # Create user for crew member
            user, created = User.objects.get_or_create(
                username=f"crew_{data['first_name'].lower()}_{data['last_name'].lower()}",
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': f"{data['first_name'].lower()}.{data['last_name'].lower()}@mediconnect.com",
                    'password': 'pbkdf2_sha256$600000$test$test'
                }
            )

            # Create crew assignment
            AmbulanceCrew.objects.get_or_create(
                ambulance=ambulances[i % len(ambulances)],
                crew_member=user,
                defaults={
                    'role': data['role'],
                    'shift_start': timezone.now().replace(hour=random.randint(6, 18), minute=0, second=0, microsecond=0),
                    'shift_end': timezone.now().replace(hour=random.randint(18, 23), minute=0, second=0, microsecond=0),
                    'is_primary': i % 3 == 0,  # Every third crew member is primary
                }
            )

    def create_dispatches(self):
        """Create sample dispatches"""
        ambulances = Ambulance.objects.all()
        users = User.objects.all()
        
        for i in range(10):
            Dispatch.objects.get_or_create(
                dispatch_number=f'DISP-{1000 + i}',
                defaults={
                    'ambulance': ambulances[i % len(ambulances)],
                    'dispatcher': users[0] if users.exists() else None,
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
            for i in range(5):  # 5 logs per ambulance
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
