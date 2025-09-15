import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from doctors.models import DoctorProfile

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DOCTOR = "DOCTOR", "Doctor"
        PATIENT = "PATIENT", "Patient"
        AMBULANCE_STAFF = "AMBULANCE_STAFF", "Ambulance Staff"

    # Base fields
    role = models.CharField(max_length=50, choices=Role.choices)
    email = models.EmailField(unique=True) # Ensure email is unique
    is_verified = models.BooleanField(default=False) # Admin approval flag
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text=
            'The groups this user belongs to. A user will get all permissions '\
            'granted to each of their groups.',
        related_name="custom_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_set",
        related_query_name="user",
    )

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', default='profiles/default.png')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"



class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True)

    def __str__(self):
        return f"Patient: {self.user.first_name} {self.user.last_name}"

class AmbulanceStaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ambulance_staff_profile')
    employee_id = models.CharField(max_length=50, unique=True)
    driver_license = models.CharField(max_length=100)

    def __str__(self):
        return f"Staff: {self.user.first_name} {self.user.last_name}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a profile based on the user's role upon registration."""
    if created:
        # Create the base profile for all users
        Profile.objects.create(user=instance)
        # Create role-specific profiles
        if instance.role == User.Role.DOCTOR:
            from django.utils import timezone
            from datetime import timedelta
            import random

            # Generate unique identifiers to avoid conflicts
            unique_suffix = f"{instance.id}{random.randint(10000, 99999)}"

            # Create DoctorProfile with default values that can be updated later
            DoctorProfile.objects.create(
                user=instance,
                first_name=instance.first_name or 'Doctor',
                last_name=instance.last_name or 'User',
                gender='M',  # Default, can be updated
                date_of_birth=timezone.now().date() - timedelta(days=365*35),  # Default age 35
                license_number=f'TEMP{unique_suffix}',  # Temporary, must be updated
                license_state='NY',  # Default, can be updated
                license_expiry_date=timezone.now().date() + timedelta(days=365*2),  # 2 years from now
                npi_number=f'{2000000000 + int(unique_suffix[:8])}',  # Generate unique NPI
                phone='+1-555-0000',  # Default, must be updated
                office_address='Address to be updated',  # Default, must be updated
                city='New York',  # Default, can be updated
                state='NY',  # Default, can be updated
                zip_code='10001',  # Default, can be updated
                medical_school='Medical School to be updated',  # Default, must be updated
                graduation_year=2020,  # Default, can be updated
                residency_program='Residency to be updated',  # Default, must be updated
                verification_status='pending'
            )
        elif instance.role == User.Role.PATIENT:
            PatientProfile.objects.create(user=instance)
            # Auto-verify patients
            instance.is_verified = True
            instance.save(update_fields=['is_verified'])
        elif instance.role == User.Role.AMBULANCE_STAFF:
            AmbulanceStaffProfile.objects.create(user=instance)