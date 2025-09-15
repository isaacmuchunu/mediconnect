from django.core.management.base import BaseCommand
from users.models import User
from doctors.models import DoctorProfile


class Command(BaseCommand):
    help = 'Test doctor registration functionality'

    def handle(self, *args, **options):
        self.stdout.write('Starting doctor registration test...')

        # Clean up any existing test user first
        existing_users = User.objects.filter(username='testdoctor123')
        if existing_users.exists():
            existing_users.delete()
            self.stdout.write('Cleaned up existing test user')

        # Test creating a doctor user
        try:
            self.stdout.write('Creating test doctor user...')
            # Create a test doctor user
            test_user = User.objects.create_user(
                username='testdoctor123',
                email='testdoctor123@example.com',
                password='testpass123',
                first_name='Test',
                last_name='Doctor',
                role=User.Role.DOCTOR
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created test doctor user: {test_user.username}')
            )
            
            # Check if DoctorProfile was created
            try:
                doctor_profile = DoctorProfile.objects.get(user=test_user)
                self.stdout.write(
                    self.style.SUCCESS(f'DoctorProfile created successfully: {doctor_profile}')
                )
                self.stdout.write(f'License Number: {doctor_profile.license_number}')
                self.stdout.write(f'NPI Number: {doctor_profile.npi_number}')
                self.stdout.write(f'Date of Birth: {doctor_profile.date_of_birth}')
                
            except DoctorProfile.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR('DoctorProfile was not created!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating test doctor: {str(e)}')
            )
            
        # Clean up - delete the test user
        try:
            User.objects.filter(username='testdoctor123').delete()
            self.stdout.write(
                self.style.SUCCESS('Test user cleaned up successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error cleaning up test user: {str(e)}')
            )
