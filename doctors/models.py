from django.db import models
# Remove this line: from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
import uuid

# Remove this line: User = get_user_model()

class BaseModel(models.Model):
    """Abstract base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        abstract = True

class Hospital(BaseModel):
    """Hospital/Medical Facility Model"""
    name = models.CharField(_('Hospital Name'), max_length=200)
    address = models.TextField(_('Address'))
    city = models.CharField(_('City'), max_length=100)
    state = models.CharField(_('State'), max_length=50)
    zip_code = models.CharField(_('ZIP Code'), max_length=10)
    phone = models.CharField(_('Phone'), max_length=20)
    email = models.EmailField(_('Email'))
    website = models.URLField(_('Website'), blank=True, null=True)
    type = models.CharField(_('Hospital Type'), max_length=50, choices=[
        ('general', _('General Hospital')),
        ('specialty', _('Specialty Hospital')),
        ('clinic', _('Clinic')),
        ('emergency', _('Emergency Center')),
        ('rehabilitation', _('Rehabilitation Center')),
        ('psychiatric', _('Psychiatric Hospital')),
    ])
    bed_capacity = models.PositiveIntegerField(_('Bed Capacity'), default=0)
    emergency_services = models.BooleanField(_('Emergency Services'), default=True)
    trauma_center_level = models.CharField(_('Trauma Center Level'), max_length=10, choices=[
        ('I', _('Level I')),
        ('II', _('Level II')),
        ('III', _('Level III')),
        ('IV', _('Level IV')),
        ('N/A', _('Not Applicable')),
    ], default='N/A')
    accreditation = models.CharField(_('Accreditation'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('Hospital')
        verbose_name_plural = _('Hospitals')
        ordering = ['name']
        indexes = [
            models.Index(fields=['city', 'state']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"

class Specialty(BaseModel):
    """Medical Specialty Model"""
    name = models.CharField(_('Specialty Name'), max_length=100, unique=True)
    code = models.CharField(_('Specialty Code'), max_length=10, unique=True)
    description = models.TextField(_('Description'), blank=True)
    parent_specialty = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                                       related_name='subspecialties', verbose_name=_('Parent Specialty'))

    class Meta:
        verbose_name = _('Specialty')
        verbose_name_plural = _('Specialties')
        ordering = ['name']

    def __str__(self):
        return self.name

class DoctorProfile(BaseModel):
    """Doctor Profile Model"""
    VERIFICATION_STATUS_CHOICES = [
        ('pending', _('Pending Verification')),
        ('verified', _('Verified')),
        ('rejected', _('Rejected')),
        ('suspended', _('Suspended')),
    ]

    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
        ('O', _('Other')),
        ('N', _('Prefer not to say')),
    ]

    # Use string reference instead of get_user_model()
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='doctor_profile')
    
    # Personal Information
    first_name = models.CharField(_('First Name'), max_length=100)
    last_name = models.CharField(_('Last Name'), max_length=100)
    middle_name = models.CharField(_('Middle Name'), max_length=100, blank=True)
    gender = models.CharField(_('Gender'), max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(_('Date of Birth'))
    profile_photo = models.ImageField(_('Profile Photo'), upload_to='doctors/photos/', blank=True, null=True)
    
    # Professional Information
    license_number = models.CharField(_('License Number'), max_length=50, unique=True)
    license_state = models.CharField(_('License State'), max_length=50)
    license_expiry_date = models.DateField(_('License Expiry Date'))
    npi_number = models.CharField(_('NPI Number'), max_length=10, unique=True, validators=[
        RegexValidator(regex=r'^\d{10}$', message='NPI must be 10 digits')
    ])
    dea_number = models.CharField(_('DEA Number'), max_length=9, blank=True, validators=[
        RegexValidator(regex=r'^[A-Z]{2}\d{7}$', message='DEA number format: XX1234567')
    ])
    
    # Contact Information
    phone = models.CharField(_('Phone Number'), max_length=20)
    emergency_phone = models.CharField(_('Emergency Phone'), max_length=20, blank=True)
    office_address = models.TextField(_('Office Address'))
    city = models.CharField(_('City'), max_length=100)
    state = models.CharField(_('State'), max_length=50)
    zip_code = models.CharField(_('ZIP Code'), max_length=10)
    
    # Professional Details
    medical_school = models.CharField(_('Medical School'), max_length=200)
    graduation_year = models.PositiveIntegerField(_('Graduation Year'))
    residency_program = models.CharField(_('Residency Program'), max_length=200)
    fellowship_programs = models.TextField(_('Fellowship Programs'), blank=True, help_text="List fellowship programs separated by commas")
    board_certifications = models.TextField(_('Board Certifications'), blank=True, help_text="List certifications separated by commas")
    
    # Affiliations and Specialties
    primary_hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, 
                                       related_name='primary_doctors', verbose_name=_('Primary Hospital'))
    affiliated_hospitals = models.ManyToManyField(Hospital, related_name='affiliated_doctors', 
                                                 blank=True, verbose_name=_('Affiliated Hospitals'))
    primary_specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, 
                                        related_name='primary_doctors', verbose_name=_('Primary Specialty'))
    specialties = models.ManyToManyField(Specialty, related_name='doctors', blank=True, 
                                       verbose_name=_('Specialties'))
    
    # Additional Professional Information
    bio = models.TextField(_('Biography'), max_length=2000, blank=True)
    years_of_experience = models.PositiveIntegerField(_('Years of Experience'), default=0)
    languages_spoken = models.CharField(_('Languages Spoken'), max_length=200, blank=True, help_text="Languages separated by commas")
    accepts_insurance = models.BooleanField(_('Accepts Insurance'), default=True)
    telehealth_available = models.BooleanField(_('Telehealth Available'), default=False)
    
    # Verification and Status
    verification_status = models.CharField(_('Verification Status'), max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    verification_date = models.DateTimeField(_('Verification Date'), null=True, blank=True)
    # Use string reference for verified_by field too
    verified_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='verified_doctors', verbose_name=_('Verified By'))
    
    # Practice Information
    consultation_fee = models.DecimalField(_('Consultation Fee'), max_digits=10, decimal_places=2, default=0.00)
    emergency_availability = models.BooleanField(_('Emergency Availability'), default=False)
    accepts_referrals = models.BooleanField(_('Accepts Referrals'), default=True)
    max_patients_per_day = models.PositiveIntegerField(_('Max Patients Per Day'), default=20)
    
    # Performance Metrics
    average_rating = models.DecimalField(_('Average Rating'), max_digits=3, decimal_places=2, default=0.00, 
                                       validators=[MinValueValidator(0.00), MaxValueValidator(5.00)])
    total_reviews = models.PositiveIntegerField(_('Total Reviews'), default=0)
    referral_acceptance_rate = models.DecimalField(_('Referral Acceptance Rate'), max_digits=5, decimal_places=2, default=0.00)
    
    class Meta:
        verbose_name = _('Doctor Profile')
        verbose_name_plural = _('Doctor Profiles')
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['primary_specialty']),
        ]

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"Dr. {self.first_name} {self.middle_name} {self.last_name}".replace('  ', ' ')

    @property
    def is_verified(self):
        return self.verification_status == 'verified'

    @property
    def license_is_valid(self):
        return self.license_expiry_date > timezone.now().date()

    def get_absolute_url(self):
        return reverse('doctors:profile_detail', kwargs={'pk': self.pk})

    def get_specialties_display(self):
        return ", ".join([specialty.name for specialty in self.specialties.all()])

    def update_rating(self, new_rating):
        """Update average rating when new review is added"""
        total_rating = self.average_rating * self.total_reviews + new_rating
        self.total_reviews += 1
        self.average_rating = total_rating / self.total_reviews
        self.save(update_fields=['average_rating', 'total_reviews'])

class Availability(BaseModel):
    """Doctor Availability Model"""
    WEEKDAY_CHOICES = [
        ('monday', _('Monday')),
        ('tuesday', _('Tuesday')),
        ('wednesday', _('Wednesday')),
        ('thursday', _('Thursday')),
        ('friday', _('Friday')),
        ('saturday', _('Saturday')),
        ('sunday', _('Sunday')),
    ]

    STATUS_CHOICES = [
        ('available', _('Available')),
        ('booked', _('Booked')),
        ('blocked', _('Blocked')),
        ('emergency', _('Emergency Only')),
    ]

    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, 
                              related_name='availability_slots', verbose_name=_('Doctor'))
    
    # Time Slot Information
    date = models.DateField(_('Date'))
    start_time = models.TimeField(_('Start Time'))
    end_time = models.TimeField(_('End Time'))
    weekday = models.CharField(_('Weekday'), max_length=10, choices=WEEKDAY_CHOICES)
    
    # Slot Configuration
    slot_duration = models.PositiveIntegerField(_('Slot Duration'), default=30, help_text="Duration in minutes")
    max_patients = models.PositiveIntegerField(_('Max Patients'), default=1)
    current_bookings = models.PositiveIntegerField(_('Current Bookings'), default=0)
    
    # Status and Location
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='available')
    location = models.ForeignKey(Hospital, on_delete=models.CASCADE, 
                                related_name='doctor_availability', verbose_name=_('Location'))
    appointment_type = models.CharField(_('Appointment Type'), max_length=50, choices=[
        ('consultation', _('Consultation')),
        ('follow_up', _('Follow-up')),
        ('emergency', _('Emergency')),
        ('procedure', _('Procedure')),
        ('telehealth', _('Telehealth')),
    ], default='consultation')
    
    # Additional Information
    notes = models.TextField(_('Notes'), blank=True)
    is_recurring = models.BooleanField(_('Is Recurring'), default=False)
    recurring_until = models.DateField(_('Recurring Until'), null=True, blank=True)
    google_calendar_event_id = models.CharField(_('Google Calendar Event ID'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('Availability')
        verbose_name_plural = _('Availability Slots')
        ordering = ['date', 'start_time']
        unique_together = ['doctor', 'date', 'start_time', 'location']
        indexes = [
            models.Index(fields=['doctor', 'date']),
            models.Index(fields=['date', 'status']),
        ]

    def __str__(self):
        return f"{self.doctor} - {self.date} {self.start_time}-{self.end_time}"

    @property
    def is_available(self):
        return self.status == 'available' and self.current_bookings < self.max_patients

    @property
    def is_past(self):
        slot_datetime = datetime.combine(self.date, self.start_time)
        return slot_datetime < timezone.now()

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time.')
        if self.date < timezone.now().date():
            raise ValidationError('Cannot create availability in the past.')

class DoctorReview(BaseModel):
    """Doctor Review and Rating Model"""
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, 
                              related_name='reviews', verbose_name=_('Doctor'))
    reviewer_name = models.CharField(_('Reviewer Name'), max_length=100)
    reviewer_email = models.EmailField(_('Reviewer Email'))
    
    rating = models.PositiveIntegerField(_('Overall Rating'), validators=[MinValueValidator(1), MaxValueValidator(5)])
    review_title = models.CharField(_('Review Title'), max_length=200)
    review_text = models.TextField(_('Review Text'))
    
    # Detailed Ratings
    bedside_manner_rating = models.PositiveIntegerField(_('Bedside Manner Rating'), validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication_rating = models.PositiveIntegerField(_('Communication Rating'), validators=[MinValueValidator(1), MaxValueValidator(5)])
    expertise_rating = models.PositiveIntegerField(_('Expertise Rating'), validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    visit_date = models.DateField(_('Visit Date'))
    would_recommend = models.BooleanField(_('Would Recommend'), default=True)
    
    is_verified = models.BooleanField(_('Is Verified'), default=False)
    is_approved = models.BooleanField(_('Is Approved'), default=False)

    class Meta:
        verbose_name = _('Doctor Review')
        verbose_name_plural = _('Doctor Reviews')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['doctor', '-created_at']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"Review for {self.doctor} - {self.rating} stars"

class ReferralStats(BaseModel):
    """Doctor Referral Statistics Model"""
    doctor = models.OneToOneField(DoctorProfile, on_delete=models.CASCADE, 
                                 related_name='referral_stats', verbose_name=_('Doctor'))
    
    total_referrals_received = models.PositiveIntegerField(_('Total Referrals Received'), default=0)
    referrals_accepted = models.PositiveIntegerField(_('Referrals Accepted'), default=0)
    referrals_declined = models.PositiveIntegerField(_('Referrals Declined'), default=0)
    referrals_pending = models.PositiveIntegerField(_('Referrals Pending'), default=0)
    
    total_referrals_sent = models.PositiveIntegerField(_('Total Referrals Sent'), default=0)
    
    average_response_time = models.DurationField(_('Average Response Time'), default=timedelta(hours=24))
    
    last_updated = models.DateTimeField(_('Last Updated'), auto_now=True)

    class Meta:
        verbose_name = _('Referral Statistics')
        verbose_name_plural = _('Referral Statistics')
        ordering = ['-last_updated']

    def __str__(self):
        return f"Referral Stats for {self.doctor}"

    @property
    def acceptance_rate(self):
        if self.total_referrals_received == 0:
            return 0
        return (self.referrals_accepted / self.total_referrals_received) * 100

class EmergencyContact(BaseModel):
    """Doctor Emergency Contact Model"""
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, 
                              related_name='emergency_contacts', verbose_name=_('Doctor'))
    
    name = models.CharField(_('Name'), max_length=100)
    relationship = models.CharField(_('Relationship'), max_length=50)
    phone = models.CharField(_('Phone Number'), max_length=20)
    email = models.EmailField(_('Email Address'), blank=True)
    
    is_primary = models.BooleanField(_('Is Primary Contact'), default=False)

    class Meta:
        verbose_name = _('Emergency Contact')
        verbose_name_plural = _('Emergency Contacts')
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f"{self.name} - {self.doctor} ({'Primary' if self.is_primary else 'Secondary'})"