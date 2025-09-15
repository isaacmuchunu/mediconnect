from django.core.management.base import BaseCommand
from users.models import User
from doctors.models import DoctorProfile
import random


class Command(BaseCommand):
    help = 'Simple test for doctor registration functionality'

    def handle(self, *args, **options):
        self.stdout.write('Testing doctor registration...')
        
        # Generate a unique username
        username = f'testdoc{random.randint(1000, 9999)}'
        email = f'{username}@example.com'
        
        try:
            # Create a test doctor user
            self.stdout.write(f'Creating doctor user: {username}')
            test_user = User.objects.create_user(
                username=username,
                email=email,
                password='testpass123',
                first_name='Test',
                last_name='Doctor',
                role=User.Role.DOCTOR
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully created doctor user: {test_user.username}')
            )
            
            # Check if DoctorProfile was created by the signal
            try:
                doctor_profile = DoctorProfile.objects.get(user=test_user)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ DoctorProfile created successfully!')
                )
                self.stdout.write(f'   - Name: {doctor_profile.first_name} {doctor_profile.last_name}')
                self.stdout.write(f'   - License: {doctor_profile.license_number}')
                self.stdout.write(f'   - NPI: {doctor_profile.npi_number}')
                self.stdout.write(f'   - DOB: {doctor_profile.date_of_birth}')
                self.stdout.write(f'   - Status: {doctor_profile.verification_status}')
                
                # Test that we can access the profile through the user
                self.stdout.write(f'   - User profile access: {test_user.doctor_profile}')
                
                self.stdout.write(
                    self.style.SUCCESS('✅ All tests passed! Doctor registration is working correctly.')
                )
                
            except DoctorProfile.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR('❌ DoctorProfile was not created by the signal!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating doctor: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
