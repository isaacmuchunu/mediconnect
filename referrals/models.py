from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import uuid

class BaseModel(models.Model):
    """Base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        abstract = True

class Referral(BaseModel):
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('sent', _('Sent')),
        ('viewed', _('Viewed')),
        ('accepted', _('Accepted')),
        ('declined', _('Declined')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]

    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
        ('emergency', _('Emergency')),
    ]

    URGENCY_LEVELS = [
        ('routine', _('Routine')),
        ('urgent', _('Urgent')),
        ('emergency', _('Emergency')),
        ('stat', _('STAT')),
    ]

    # Core referral information
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE,
                               related_name='referrals', verbose_name=_('Patient'))
    referring_doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE,
                                       related_name='sent_referrals', verbose_name=_('Referring Doctor'))
    target_doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE,
                                    related_name='received_referrals', null=True, blank=True,
                                    verbose_name=_('Target Doctor'))
    referring_hospital = models.ForeignKey('doctors.Hospital', on_delete=models.CASCADE,
                                         related_name='outgoing_referrals', verbose_name=_('Referring Hospital'))
    target_hospital = models.ForeignKey('doctors.Hospital', on_delete=models.CASCADE,
                                      related_name='incoming_referrals', null=True, blank=True,
                                      verbose_name=_('Target Hospital'))

    # Referral details
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft', verbose_name=_('Status'))
    priority = models.CharField(max_length=15, choices=PRIORITY_CHOICES, default='medium', verbose_name=_('Priority'))
    urgency_level = models.CharField(max_length=15, choices=URGENCY_LEVELS, default='routine', verbose_name=_('Urgency Level'))
    specialty = models.ForeignKey('doctors.Specialty', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Specialty'))
    specialty_text = models.CharField(max_length=100, default="General", verbose_name=_('Specialty (Text)'))

    # Clinical information
    chief_complaint = models.TextField(verbose_name=_('Chief Complaint'))
    clinical_summary = models.TextField(verbose_name=_('Clinical Summary'))
    reason = models.TextField(verbose_name=_('Reason for Referral'))
    relevant_history = models.TextField(blank=True, verbose_name=_('Relevant Medical History'))
    current_medications = models.TextField(blank=True, verbose_name=_('Current Medications'))
    allergies = models.TextField(blank=True, verbose_name=_('Known Allergies'))

    # Additional information
    notes = models.TextField(blank=True, verbose_name=_('Additional Notes'))
    response_notes = models.TextField(blank=True, verbose_name=_('Response Notes'))
    internal_notes = models.TextField(blank=True, verbose_name=_('Internal Notes'))

    # File attachments
    attachments = models.FileField(
        upload_to='referrals/attachments/%Y/%m/',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])],
        verbose_name=_('Attachments')
    )

    # Transport and logistics
    ambulance_required = models.BooleanField(default=False, verbose_name=_('Ambulance Required'))
    transport_urgency = models.CharField(max_length=15, choices=URGENCY_LEVELS, default='routine',
                                       verbose_name=_('Transport Urgency'))
    special_requirements = models.TextField(blank=True, verbose_name=_('Special Requirements'))

    # Timing and workflow
    requested_appointment_date = models.DateTimeField(null=True, blank=True, verbose_name=_('Requested Appointment Date'))
    viewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Viewed At'))
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Responded At'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Completed At'))
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Cancelled At'))

    # Response information
    response_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='referral_responses',
                                  verbose_name=_('Responded By'))
    estimated_wait_time = models.DurationField(null=True, blank=True, verbose_name=_('Estimated Wait Time'))

    # Follow-up
    follow_up_required = models.BooleanField(default=False, verbose_name=_('Follow-up Required'))
    follow_up_instructions = models.TextField(blank=True, verbose_name=_('Follow-up Instructions'))

    # Quality metrics
    satisfaction_rating = models.PositiveIntegerField(null=True, blank=True,
                                                    choices=[(i, i) for i in range(1, 6)],
                                                    verbose_name=_('Satisfaction Rating'))
    feedback = models.TextField(blank=True, verbose_name=_('Feedback'))

    class Meta:
        verbose_name = _('Referral')
        verbose_name_plural = _('Referrals')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['referring_doctor', 'status']),
            models.Index(fields=['target_doctor', 'status']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['created_at', 'status']),
            models.Index(fields=['urgency_level', 'created_at']),
            models.Index(fields=['ambulance_required', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(satisfaction_rating__gte=1) & models.Q(satisfaction_rating__lte=5),
                name='valid_satisfaction_rating'
            ),
        ]

    def __str__(self):
        target_name = f"Dr. {self.target_doctor.first_name} {self.target_doctor.last_name}" if self.target_doctor else "Unassigned"
        return f'Referral from Dr. {self.referring_doctor.first_name} {self.referring_doctor.last_name} to {target_name} for {self.patient.full_name}'

    def save(self, *args, **kwargs):
        # Auto-set timestamps based on status changes
        if self.pk:
            old_instance = Referral.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == 'viewed' and not self.viewed_at:
                    self.viewed_at = timezone.now()
                elif self.status in ['accepted', 'declined'] and not self.responded_at:
                    self.responded_at = timezone.now()
                elif self.status == 'completed' and not self.completed_at:
                    self.completed_at = timezone.now()
                elif self.status == 'cancelled' and not self.cancelled_at:
                    self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def get_status_display_class(self):
        status_classes = {
            'draft': 'secondary',
            'sent': 'primary',
            'viewed': 'info',
            'accepted': 'success',
            'declined': 'danger',
            'completed': 'dark',
            'cancelled': 'warning'
        }
        return status_classes.get(self.status, 'secondary')

    def get_priority_display_class(self):
        priority_classes = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'urgent': 'dark',
            'emergency': 'danger'
        }
        return priority_classes.get(self.priority, 'secondary')

    def get_urgency_display_class(self):
        urgency_classes = {
            'routine': 'success',
            'urgent': 'warning',
            'emergency': 'danger',
            'stat': 'dark'
        }
        return urgency_classes.get(self.urgency_level, 'secondary')

    @property
    def is_urgent(self):
        return self.priority in ['urgent', 'emergency'] or self.urgency_level in ['emergency', 'stat']

    @property
    def response_time(self):
        if self.responded_at and self.created_at:
            return self.responded_at - self.created_at
        return None

    @property
    def completion_time(self):
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return None

    def can_be_cancelled(self):
        return self.status in ['draft', 'sent', 'viewed']

    def can_be_accepted(self):
        return self.status in ['sent', 'viewed']

    def can_be_completed(self):
        return self.status == 'accepted'


class ReferralAttachment(BaseModel):
    """Additional file attachments for referrals"""
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='additional_attachments')
    file = models.FileField(
        upload_to='referrals/attachments/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'dicom'])]
    )
    file_type = models.CharField(max_length=50, choices=[
        ('medical_record', _('Medical Record')),
        ('lab_result', _('Lab Result')),
        ('imaging', _('Medical Imaging')),
        ('prescription', _('Prescription')),
        ('other', _('Other'))
    ])
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = _('Referral Attachment')
        verbose_name_plural = _('Referral Attachments')

    def __str__(self):
        return f"{self.referral} - {self.get_file_type_display()}"


class ReferralStatusHistory(BaseModel):
    """Track status changes for referrals"""
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=15, choices=Referral.STATUS_CHOICES)
    new_status = models.CharField(max_length=15, choices=Referral.STATUS_CHOICES)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Referral Status History')
        verbose_name_plural = _('Referral Status Histories')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.referral} - {self.old_status} to {self.new_status}"


class ReferralTemplate(BaseModel):
    """Templates for common referral types"""
    name = models.CharField(max_length=100)
    specialty = models.ForeignKey('doctors.Specialty', on_delete=models.CASCADE)
    template_text = models.TextField()
    required_fields = models.JSONField(default=list)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Referral Template')
        verbose_name_plural = _('Referral Templates')

    def __str__(self):
        return f"{self.name} - {self.specialty}"