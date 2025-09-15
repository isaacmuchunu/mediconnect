from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
import uuid

User = get_user_model()

class BaseModel(models.Model):
    """Abstract base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        abstract = True

class AppointmentType(BaseModel):
    """Appointment type configuration"""
    name = models.CharField(_('Type Name'), max_length=100, unique=True)
    code = models.CharField(_('Type Code'), max_length=20, unique=True)
    description = models.TextField(_('Description'), blank=True)
    duration_minutes = models.PositiveIntegerField(_('Default Duration (minutes)'), default=30)
    color_code = models.CharField(_('Color Code'), max_length=7, default='#007bff',
                                help_text=_('Hex color code for calendar display'))
    requires_preparation = models.BooleanField(_('Requires Preparation'), default=False)
    preparation_instructions = models.TextField(_('Preparation Instructions'), blank=True)
    is_emergency = models.BooleanField(_('Emergency Appointment'), default=False)
    display_order = models.PositiveIntegerField(_('Display Order'), default=0)
    
    class Meta:
        verbose_name = _('Appointment Type')
        verbose_name_plural = _('Appointment Types')
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name

class Appointment(BaseModel):
    """Comprehensive appointment model"""
    
    STATUS_CHOICES = [
        ('scheduled', _('Scheduled')),
        ('confirmed', _('Confirmed')),
        ('checked_in', _('Checked In')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
        ('no_show', _('No Show')),
        ('rescheduled', _('Rescheduled')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
        ('emergency', _('Emergency')),
    ]
    
    CANCELLATION_REASONS = [
        ('patient_request', _('Patient Request')),
        ('doctor_unavailable', _('Doctor Unavailable')),
        ('emergency', _('Emergency')),
        ('illness', _('Patient Illness')),
        ('scheduling_conflict', _('Scheduling Conflict')),
        ('weather', _('Weather Conditions')),
        ('other', _('Other')),
    ]
    
    # Core appointment information
    referral = models.ForeignKey('referrals.Referral', on_delete=models.CASCADE, 
                               related_name='appointments', null=True, blank=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, 
                              related_name='appointments', null=True, blank=True)
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, 
                             related_name='appointments', null=True, blank=True)
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='appointments')
    
    # Scheduling information
    appointment_date = models.DateTimeField(_('Appointment Date'), null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(_('Duration (minutes)'), default=30)
    end_time = models.DateTimeField(_('End Time'), null=True, blank=True)
    
    # Location and logistics
    hospital = models.ForeignKey('doctors.Hospital', on_delete=models.CASCADE, 
                               related_name='appointments', null=True, blank=True)
    room_number = models.CharField(_('Room Number'), max_length=20, blank=True)
    department = models.CharField(_('Department'), max_length=100, blank=True)
    
    # Status and priority
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, 
                            default='scheduled')
    priority = models.CharField(_('Priority'), max_length=20, choices=PRIORITY_CHOICES, 
                              default='normal')
    
    # Appointment details
    chief_complaint = models.TextField(_('Chief Complaint'), blank=True)
    notes = models.TextField(_('Appointment Notes'), blank=True)
    preparation_instructions = models.TextField(_('Preparation Instructions'), blank=True)
    
    # Scheduling metadata
    scheduled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                   related_name='scheduled_appointments')
    confirmed_at = models.DateTimeField(_('Confirmed At'), null=True, blank=True)
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='confirmed_appointments')
    
    # Check-in information
    checked_in_at = models.DateTimeField(_('Checked In At'), null=True, blank=True)
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='checked_in_appointments')
    
    # Completion information
    started_at = models.DateTimeField(_('Started At'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    
    # Cancellation information
    cancelled_at = models.DateTimeField(_('Cancelled At'), null=True, blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='cancelled_appointments')
    cancellation_reason = models.CharField(_('Cancellation Reason'), max_length=30, 
                                         choices=CANCELLATION_REASONS, blank=True)
    cancellation_notes = models.TextField(_('Cancellation Notes'), blank=True)
    
    # Rescheduling information
    original_appointment = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='rescheduled_appointments')
    rescheduled_from = models.DateTimeField(_('Rescheduled From'), null=True, blank=True)
    
    # Communication preferences
    send_reminders = models.BooleanField(_('Send Reminders'), default=True)
    reminder_sent_at = models.DateTimeField(_('Reminder Sent At'), null=True, blank=True)
    confirmation_sent_at = models.DateTimeField(_('Confirmation Sent At'), null=True, blank=True)
    
    # Billing and insurance
    estimated_cost = models.DecimalField(_('Estimated Cost'), max_digits=10, decimal_places=2, 
                                       null=True, blank=True)
    insurance_verified = models.BooleanField(_('Insurance Verified'), default=False)
    copay_amount = models.DecimalField(_('Copay Amount'), max_digits=8, decimal_places=2, 
                                     null=True, blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(_('Follow-up Required'), default=False)
    follow_up_instructions = models.TextField(_('Follow-up Instructions'), blank=True)
    
    class Meta:
        verbose_name = _('Appointment')
        verbose_name_plural = _('Appointments')
        ordering = ['appointment_date']
        indexes = [
            models.Index(fields=['patient', 'appointment_date']),
            models.Index(fields=['doctor', 'appointment_date']),
            models.Index(fields=['hospital', 'appointment_date']),
            models.Index(fields=['status', 'appointment_date']),
            models.Index(fields=['appointment_date', 'status']),
        ]
        constraints = [
            # Ensure duration is reasonable
            models.CheckConstraint(
                check=models.Q(duration_minutes__gt=0) & models.Q(duration_minutes__lte=480),
                name='duration_minutes_reasonable'
            ),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-calculate end time if not provided
        if not self.end_time and self.appointment_date and self.duration_minutes:
            self.end_time = self.appointment_date + timedelta(minutes=self.duration_minutes)
        super().save(*args, **kwargs)
    
    def clean(self):
        super().clean()
        
        # Validate required fields
        if not self.patient:
            raise ValidationError(_('Patient is required'))
        if not self.doctor:
            raise ValidationError(_('Doctor is required'))
        if not self.hospital:
            raise ValidationError(_('Hospital is required'))
        if not self.appointment_date:
            raise ValidationError(_('Appointment date is required'))
        
        # Validate appointment is in the future (for new appointments)
        if not self.pk and self.appointment_date:
            # Allow appointments to be scheduled up to 30 minutes in the past (for flexibility)
            if self.appointment_date <= timezone.now() - timedelta(minutes=30):
                raise ValidationError(_('Appointment date cannot be more than 30 minutes in the past'))
        
        # Validate end time is after start time
        if self.end_time and self.appointment_date and self.end_time <= self.appointment_date:
            raise ValidationError(_('End time must be after appointment start time'))
        
        # Validate duration
        if self.duration_minutes and (self.duration_minutes <= 0 or self.duration_minutes > 480):
            raise ValidationError(_('Duration must be between 1 and 480 minutes'))
        
        # Validate cancellation reason is provided when cancelled
        if self.status == 'cancelled' and not self.cancellation_reason:
            raise ValidationError(_('Cancellation reason is required when appointment is cancelled'))
    
    @property
    def is_past(self):
        """Check if appointment is in the past"""
        return self.appointment_date < timezone.now()
    
    @property
    def is_today(self):
        """Check if appointment is today"""
        return self.appointment_date.date() == timezone.now().date()
    
    @property
    def is_upcoming(self):
        """Check if appointment is upcoming (within next 24 hours)"""
        return timezone.now() <= self.appointment_date <= timezone.now() + timedelta(hours=24)
    
    @property
    def can_be_cancelled(self):
        """Check if appointment can be cancelled"""
        return self.status in ['scheduled', 'confirmed'] and not self.is_past
    
    @property
    def can_be_rescheduled(self):
        """Check if appointment can be rescheduled"""
        return self.status in ['scheduled', 'confirmed'] and not self.is_past
    
    @property
    def duration_hours_minutes(self):
        """Return duration as hours and minutes string"""
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        return f"{minutes}m"
    
    def cancel(self, user, reason, notes=''):
        """Cancel the appointment"""
        if not self.can_be_cancelled:
            raise ValidationError(_('This appointment cannot be cancelled'))
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.cancellation_reason = reason
        self.cancellation_notes = notes
        self.save()
    
    def confirm(self, user):
        """Confirm the appointment"""
        if self.status != 'scheduled':
            raise ValidationError(_('Only scheduled appointments can be confirmed'))
        
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.confirmed_by = user
        self.save()
    
    def check_in(self, user):
        """Check in the patient"""
        if self.status not in ['scheduled', 'confirmed']:
            raise ValidationError(_('Patient can only be checked in for scheduled or confirmed appointments'))
        
        self.status = 'checked_in'
        self.checked_in_at = timezone.now()
        self.checked_in_by = user
        self.save()
    
    def start(self):
        """Start the appointment"""
        if self.status != 'checked_in':
            raise ValidationError(_('Appointment must be checked in before starting'))
        
        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.save()
    
    def complete(self):
        """Complete the appointment"""
        if self.status != 'in_progress':
            raise ValidationError(_('Only in-progress appointments can be completed'))
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def reschedule(self, new_date, user):
        """Reschedule the appointment to a new date"""
        if not self.can_be_rescheduled:
            raise ValidationError(_('This appointment cannot be rescheduled'))
        
        self.rescheduled_from = self.appointment_date
        self.appointment_date = new_date
        self.status = 'rescheduled'
        # Reset confirmation if it was confirmed
        if self.confirmed_at:
            self.confirmed_at = None
            self.confirmed_by = None
            self.status = 'scheduled'
        self.save()
    
    def __str__(self):
        return f"{self.patient} - {self.doctor} on {self.appointment_date.strftime('%Y-%m-%d %H:%M')}"

class AppointmentReminder(BaseModel):
    """Appointment reminder tracking"""
    
    REMINDER_TYPES = [
        ('sms', _('SMS')),
        ('email', _('Email')),
        ('phone', _('Phone Call')),
        ('push', _('Push Notification')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, 
                                  related_name='reminders')
    reminder_type = models.CharField(_('Reminder Type'), max_length=20, choices=REMINDER_TYPES)
    scheduled_time = models.DateTimeField(_('Scheduled Time'))
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Message content
    subject = models.CharField(_('Subject'), max_length=200, blank=True)
    message = models.TextField(_('Message'))
    
    # Delivery tracking
    recipient = models.CharField(_('Recipient'), max_length=255)
    delivery_id = models.CharField(_('Delivery ID'), max_length=100, blank=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    
    class Meta:
        verbose_name = _('Appointment Reminder')
        verbose_name_plural = _('Appointment Reminders')
        ordering = ['scheduled_time']
        indexes = [
            models.Index(fields=['appointment', 'reminder_type']),
            models.Index(fields=['scheduled_time', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['appointment', 'reminder_type', 'scheduled_time'],
                name='unique_appointment_reminder'
            ),
        ]
    
    def __str__(self):
        return f"{self.reminder_type} reminder for {self.appointment}"

class AppointmentNote(BaseModel):
    """Notes related to appointments"""
    
    NOTE_TYPES = [
        ('clinical', _('Clinical Note')),
        ('administrative', _('Administrative Note')),
        ('billing', _('Billing Note')),
        ('follow_up', _('Follow-up Note')),
        ('cancellation', _('Cancellation Note')),
        ('rescheduling', _('Rescheduling Note')),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, 
                                  related_name='appointment_notes')
    note_type = models.CharField(_('Note Type'), max_length=20, choices=NOTE_TYPES)
    title = models.CharField(_('Title'), max_length=200)
    content = models.TextField(_('Content'))
    
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                             related_name='appointment_notes')
    is_private = models.BooleanField(_('Private Note'), default=False)
    
    class Meta:
        verbose_name = _('Appointment Note')
        verbose_name_plural = _('Appointment Notes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['appointment', 'note_type']),
            models.Index(fields=['author', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.appointment}"

class AppointmentAttachment(BaseModel):
    """File attachments for appointments"""
    
    ATTACHMENT_TYPES = [
        ('medical_record', _('Medical Record')),
        ('lab_result', _('Lab Result')),
        ('imaging', _('Imaging')),
        ('prescription', _('Prescription')),
        ('insurance', _('Insurance Document')),
        ('consent', _('Consent Form')),
        ('other', _('Other')),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, 
                                  related_name='attachments')
    attachment_type = models.CharField(_('Attachment Type'), max_length=20, choices=ATTACHMENT_TYPES)
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    
    file = models.FileField(_('File'), upload_to='appointments/attachments/%Y/%m/')
    file_size = models.PositiveIntegerField(_('File Size (bytes)'), null=True, blank=True)
    mime_type = models.CharField(_('MIME Type'), max_length=100, blank=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='uploaded_appointment_attachments')
    
    class Meta:
        verbose_name = _('Appointment Attachment')
        verbose_name_plural = _('Appointment Attachments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['appointment', 'attachment_type']),
        ]
    
    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} - {self.appointment}"