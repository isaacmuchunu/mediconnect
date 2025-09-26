#!/usr/bin/env python
"""
Script to fix migration issues and apply all model changes
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection


def setup_django():
    """Setup Django environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_ereferral.settings')
    django.setup()


def reset_migrations():
    """Reset migrations for problematic apps"""
    print("Resetting migrations...")
    
    # Remove migration files (keep __init__.py)
    apps_to_reset = ['referrals', 'ambulances', 'appointments', 'api', 'notifications']
    
    for app in apps_to_reset:
        migrations_dir = f"{app}/migrations"
        if os.path.exists(migrations_dir):
            for file in os.listdir(migrations_dir):
                if file.endswith('.py') and file != '__init__.py':
                    file_path = os.path.join(migrations_dir, file)
                    print(f"Removing {file_path}")
                    os.remove(file_path)
                elif file.endswith('.pyc'):
                    file_path = os.path.join(migrations_dir, file)
                    os.remove(file_path)
        
        # Remove __pycache__ directory
        pycache_dir = f"{app}/migrations/__pycache__"
        if os.path.exists(pycache_dir):
            import shutil
            shutil.rmtree(pycache_dir)


def drop_tables():
    """Drop problematic tables"""
    print("Dropping problematic tables...")
    
    with connection.cursor() as cursor:
        tables_to_drop = [
            'referrals_referral',
            'ambulances_ambulance',
            'ambulances_dispatch',
            'ambulances_ambulancetype',
            'ambulances_ambulancestation',
            'ambulances_ambulancecrew',
            'ambulances_dispatchcrew',
            'ambulances_gpstrackinglog',
            'ambulances_maintenancerecord',
            'ambulances_equipmentinventory',
            'ambulances_fuellog',
            'ambulances_incidentreport',
            'ambulances_performancemetrics',
            'api_apikey',
            'api_apirequestlog',
            'api_webhookendpoint',
            'api_webhookdelivery',
            'api_externalintegration',
            'api_dataexport',
        ]
        
        for table in tables_to_drop:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                print(f"Dropped table: {table}")
            except Exception as e:
                print(f"Error dropping table {table}: {e}")


def clear_migration_history():
    """Clear migration history from django_migrations table"""
    print("Clearing migration history...")
    
    with connection.cursor() as cursor:
        apps_to_clear = ['referrals', 'ambulances', 'appointments', 'api', 'notifications']
        
        for app in apps_to_clear:
            try:
                cursor.execute(
                    "DELETE FROM django_migrations WHERE app = %s",
                    [app]
                )
                print(f"Cleared migration history for: {app}")
            except Exception as e:
                print(f"Error clearing migration history for {app}: {e}")


def create_fresh_migrations():
    """Create fresh migrations"""
    print("Creating fresh migrations...")
    
    apps_to_migrate = ['users', 'patients', 'doctors', 'referrals', 'ambulances', 'appointments', 'notifications', 'reports', 'api']
    
    for app in apps_to_migrate:
        try:
            print(f"Creating migrations for {app}...")
            execute_from_command_line(['manage.py', 'makemigrations', app])
        except Exception as e:
            print(f"Error creating migrations for {app}: {e}")


def apply_migrations():
    """Apply all migrations"""
    print("Applying migrations...")
    
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("All migrations applied successfully!")
    except Exception as e:
        print(f"Error applying migrations: {e}")
        return False
    
    return True


def create_superuser():
    """Create a superuser if none exists"""
    print("Checking for superuser...")
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not User.objects.filter(is_superuser=True).exists():
        print("Creating superuser...")
        try:
            execute_from_command_line(['manage.py', 'createsuperuser', '--noinput', '--username=admin', '--email=admin@hospital.com'])
            
            # Set password
            admin_user = User.objects.get(username='admin')
            admin_user.set_password('admin123')
            admin_user.role = 'ADMIN'
            admin_user.save()
            
            print("Superuser created: admin/admin123")
        except Exception as e:
            print(f"Error creating superuser: {e}")
    else:
        print("Superuser already exists")


def load_sample_data():
    """Load sample data for testing"""
    print("Loading sample data...")
    
    try:
        from ambulances.models import AmbulanceType, AmbulanceStation
        from doctors.models import Hospital, Specialty
        
        # Create ambulance types
        ambulance_types = [
            {'name': 'Basic Life Support', 'code': 'BLS', 'description': 'Basic life support ambulance'},
            {'name': 'Advanced Life Support', 'code': 'ALS', 'description': 'Advanced life support ambulance'},
            {'name': 'Critical Care Transport', 'code': 'CCT', 'description': 'Critical care transport ambulance'},
        ]
        
        for type_data in ambulance_types:
            AmbulanceType.objects.get_or_create(
                code=type_data['code'],
                defaults=type_data
            )
        
        # Create ambulance stations (GIS functionality removed)
        # from django.contrib.gis.geos import Point
        
        stations = [
            {
                'name': 'Central Station',
                'code': 'CS01',
                'address': '123 Main St, City Center',
                # 'location': Point(-74.0060, 40.7128),  # GIS removed
                'phone': '555-0123'
            },
            {
                'name': 'North Station',
                'code': 'NS01',
                'address': '456 North Ave, North District',
                # 'location': Point(-74.0160, 40.7228),  # GIS removed
                'phone': '555-0124'
            }
        ]
        
        for station_data in stations:
            AmbulanceStation.objects.get_or_create(
                code=station_data['code'],
                defaults=station_data
            )
        
        # Create hospitals
        hospitals = [
            {
                'name': 'General Hospital',
                'address': '789 Hospital Blvd',
                'phone': '555-0200',
                'email': 'info@generalhospital.com'
            },
            {
                'name': 'Emergency Medical Center',
                'address': '321 Emergency St',
                'phone': '555-0300',
                'email': 'info@emergencymc.com'
            }
        ]
        
        for hospital_data in hospitals:
            Hospital.objects.get_or_create(
                name=hospital_data['name'],
                defaults=hospital_data
            )
        
        # Create specialties
        specialties = [
            {'name': 'Emergency Medicine', 'description': 'Emergency medical care'},
            {'name': 'Cardiology', 'description': 'Heart and cardiovascular system'},
            {'name': 'Neurology', 'description': 'Nervous system disorders'},
            {'name': 'Orthopedics', 'description': 'Musculoskeletal system'},
            {'name': 'Pediatrics', 'description': 'Medical care for children'},
        ]
        
        for specialty_data in specialties:
            Specialty.objects.get_or_create(
                name=specialty_data['name'],
                defaults=specialty_data
            )
        
        print("Sample data loaded successfully!")
        
    except Exception as e:
        print(f"Error loading sample data: {e}")


def main():
    """Main function to fix all migration issues"""
    print("=" * 70)
    print("HOSPITAL E-REFERRAL SYSTEM - MIGRATION FIX SCRIPT")
    print("=" * 70)
    
    setup_django()
    
    # Ask for confirmation
    response = input("\nThis will reset all migrations and recreate the database. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    try:
        # Step 1: Reset migrations
        reset_migrations()
        
        # Step 2: Drop problematic tables
        drop_tables()
        
        # Step 3: Clear migration history
        clear_migration_history()
        
        # Step 4: Create fresh migrations
        create_fresh_migrations()
        
        # Step 5: Apply migrations
        if apply_migrations():
            print("\n" + "=" * 50)
            print("MIGRATION FIX COMPLETED SUCCESSFULLY!")
            print("=" * 50)
            
            # Step 6: Create superuser
            create_superuser()
            
            # Step 7: Load sample data
            load_sample_data()
            
            print("\n" + "=" * 50)
            print("SETUP COMPLETED!")
            print("=" * 50)
            print("You can now run the server with: python manage.py runserver")
            print("Admin login: admin/admin123")
            
        else:
            print("Migration fix failed. Please check the errors above.")
            
    except Exception as e:
        print(f"Error during migration fix: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
