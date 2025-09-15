"""
Communication & Notification System Models
HIPAA-compliant messaging, multi-channel notifications, and emergency alerts
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import json

User = get_user_model()


class BaseModel(models.Model):
    """Base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class NotificationChannel(BaseModel):
    """Notification delivery channels configuration"""
    
    CHANNEL_TYPE_CHOICES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('push', _('Push Notification')),
        ('voice', _('Voice Call')),
        ('slack', _('Slack')),
        ('teams', _('Microsoft Teams')),
        ('webhook', _('Webhook')),
        ('in_app', _('In-App Notification')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('maintenance', _('Under Maintenance')),
        ('error', _('Error State')),
    ]
    
    name = models.CharField(_('Channel Name'), max_length=100)
    channel_type = models.CharField(_('Channel Type'), max_length=20, choices=CHANNEL_TYPE_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Configuration
    configuration = models.JSONField(_('Configuration'), default=dict)
    api_endpoint = models.URLField(_('API Endpoint'), blank=True)
    api_key = models.CharField(_('API Key'), max_length=255, blank=True)
    
    # Rate Limiting
    rate_limit_per_minute = models.PositiveIntegerField(_('Rate Limit (per minute)'), default=60)
    rate_limit_per_hour = models.PositiveIntegerField(_('Rate Limit (per hour)'), default=1000)
    
    # Priority and Reliability
    priority_order = models.PositiveIntegerField(_('Priority Order'), default=1)
    reliability_score = models.FloatField(_('Reliability Score'), default=1.0)
    
    # Usage Statistics
    total_sent = models.PositiveIntegerField(_('Total Sent'), default=0)
    total_delivered = models.PositiveIntegerField(_('Total Delivered'), default=0)
    total_failed = models.PositiveIntegerField(_('Total Failed'), default=0)
    
    class Meta:
        verbose_name = _('Notification Channel')
        verbose_name_plural = _('Notification Channels')
        ordering = ['priority_order', 'name']
    
    @property
    def delivery_rate(self):
        """Calculate delivery success rate"""
        if self.total_sent > 0:
            return (self.total_delivered / self.total_sent) * 100
        return 0
    
    @property
    def is_available(self):
        """Check if channel is available for sending"""
        return self.status == 'active' and self.reliability_score > 0.5
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class NotificationTemplate(BaseModel):
    """Reusable notification templates"""
    
    TEMPLATE_TYPE_CHOICES = [
        ('emergency_dispatch', _('Emergency Dispatch')),
        ('status_update', _('Status Update')),
        ('arrival_notification', _('Arrival Notification')),
        ('completion_alert', _('Completion Alert')),
        ('system_alert', _('System Alert')),
        ('maintenance_notice', _('Maintenance Notice')),
        ('shift_reminder', _('Shift Reminder')),
        ('training_alert', _('Training Alert')),
    ]
    
    name = models.CharField(_('Template Name'), max_length=100)
    template_type = models.CharField(_('Template Type'), max_length=30, choices=TEMPLATE_TYPE_CHOICES)
    
    # Content
    subject_template = models.CharField(_('Subject Template'), max_length=255)
    body_template = models.TextField(_('Body Template'))
    html_template = models.TextField(_('HTML Template'), blank=True)
    
    # Channels
    supported_channels = models.ManyToManyField(
        NotificationChannel,
        verbose_name=_('Supported Channels'),
        blank=True
    )
    
    # Variables
    template_variables = models.JSONField(_('Template Variables'), default=list)
    
    # Settings
    is_active = models.BooleanField(_('Active'), default=True)
    requires_confirmation = models.BooleanField(_('Requires Confirmation'), default=False)
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ['template_type', 'name']
    
    def render_subject(self, context):
        """Render subject with context variables"""
        from django.template import Template, Context
        template = Template(self.subject_template)
        return template.render(Context(context))
    
    def render_body(self, context):
        """Render body with context variables"""
        from django.template import Template, Context
        template = Template(self.body_template)
        return template.render(Context(context))
    
    def render_html(self, context):
        """Render HTML with context variables"""
        if self.html_template:
            from django.template import Template, Context
            template = Template(self.html_template)
            return template.render(Context(context))
        return None
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class Notification(BaseModel):
    """Individual notification records"""
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
        ('expired', _('Expired')),
    ]
    
    # Recipients
    recipient_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_notifications',
        verbose_name=_('Recipient User')
    )
    recipient_email = models.EmailField(_('Recipient Email'), blank=True)
    recipient_phone = models.CharField(
        _('Recipient Phone'),
        max_length=20,
        blank=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Invalid phone number')]
    )
    
    # Content
    subject = models.CharField(_('Subject'), max_length=255)
    message = models.TextField(_('Message'))
    html_content = models.TextField(_('HTML Content'), blank=True)
    
    # Metadata
    notification_type = models.CharField(_('Notification Type'), max_length=30)
    priority = models.CharField(_('Priority'), max_length=20, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Delivery
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Delivery Channel')
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Template Used')
    )
    
    # Timing
    scheduled_at = models.DateTimeField(_('Scheduled At'), null=True, blank=True)
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    
    # Tracking
    external_id = models.CharField(_('External ID'), max_length=255, blank=True)
    delivery_attempts = models.PositiveIntegerField(_('Delivery Attempts'), default=0)
    error_message = models.TextField(_('Error Message'), blank=True)
    
    # Context
    context_data = models.JSONField(_('Context Data'), default=dict)
    
    # Related Objects
    related_dispatch = models.ForeignKey(
        'ambulances.Dispatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_emergency_call = models.ForeignKey(
        'ambulances.EmergencyCall',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_user', 'status']),
            models.Index(fields=['notification_type', 'priority']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def delivery_time(self):
        """Calculate delivery time"""
        if self.sent_at and self.delivered_at:
            return self.delivered_at - self.sent_at
        return None
    
    def mark_sent(self, external_id=None):
        """Mark notification as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if external_id:
            self.external_id = external_id
        self.save()
    
    def mark_delivered(self):
        """Mark notification as delivered"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message):
        """Mark notification as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.delivery_attempts += 1
        self.save()
    
    def __str__(self):
        recipient = self.recipient_user.get_full_name() if self.recipient_user else (
            self.recipient_email or self.recipient_phone
        )
        return f"{self.subject} → {recipient}"


class SecureMessage(BaseModel):
    """HIPAA-compliant secure messaging between healthcare providers"""
    
    MESSAGE_TYPE_CHOICES = [
        ('general', _('General Message')),
        ('patient_update', _('Patient Update')),
        ('consultation', _('Consultation Request')),
        ('emergency', _('Emergency Communication')),
        ('handoff', _('Patient Handoff')),
        ('report', _('Medical Report')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('read', _('Read')),
        ('archived', _('Archived')),
    ]
    
    # Participants
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_secure_messages',
        verbose_name=_('Sender')
    )
    recipients = models.ManyToManyField(
        User,
        related_name='received_secure_messages',
        verbose_name=_('Recipients')
    )
    
    # Content
    subject = models.CharField(_('Subject'), max_length=255)
    message = models.TextField(_('Message'))
    message_type = models.CharField(_('Message Type'), max_length=20, choices=MESSAGE_TYPE_CHOICES)
    
    # Security
    is_encrypted = models.BooleanField(_('Encrypted'), default=True)
    encryption_key_id = models.CharField(_('Encryption Key ID'), max_length=100, blank=True)
    
    # Status
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Timing
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    
    # Attachments
    has_attachments = models.BooleanField(_('Has Attachments'), default=False)
    
    # Related Objects
    related_patient = models.CharField(_('Related Patient ID'), max_length=100, blank=True)
    related_dispatch = models.ForeignKey(
        'ambulances.Dispatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='secure_messages'
    )
    
    # Audit Trail
    access_log = models.JSONField(_('Access Log'), default=list)
    
    class Meta:
        verbose_name = _('Secure Message')
        verbose_name_plural = _('Secure Messages')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'status']),
            models.Index(fields=['message_type', 'created_at']),
            models.Index(fields=['related_patient']),
        ]
    
    def send_message(self):
        """Send the secure message"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
        
        # Log access
        self.log_access(self.sender, 'sent')
        
        # Create notifications for recipients
        for recipient in self.recipients.all():
            Notification.objects.create(
                recipient_user=recipient,
                subject=f"Secure Message: {self.subject}",
                message=f"You have received a secure message from {self.sender.get_full_name()}",
                notification_type='secure_message',
                priority='normal',
                context_data={'message_id': str(self.id)}
            )
    
    def mark_read(self, user):
        """Mark message as read by user"""
        if user in self.recipients.all():
            self.log_access(user, 'read')
            
            # Check if all recipients have read
            read_count = sum(1 for log in self.access_log if log.get('action') == 'read')
            if read_count >= self.recipients.count():
                self.status = 'read'
                self.save()
    
    def log_access(self, user, action):
        """Log access to the message"""
        access_entry = {
            'user_id': str(user.id),
            'user_name': user.get_full_name(),
            'action': action,
            'timestamp': timezone.now().isoformat(),
            'ip_address': None,  # TODO: Get from request
        }
        
        self.access_log.append(access_entry)
        self.save()
    
    def __str__(self):
        return f"{self.subject} - {self.sender.get_full_name()}"


class EmergencyAlert(BaseModel):
    """System-wide emergency alerts and broadcasts"""
    
    ALERT_TYPE_CHOICES = [
        ('mass_casualty', _('Mass Casualty Incident')),
        ('hospital_diversion', _('Hospital Diversion')),
        ('weather_emergency', _('Weather Emergency')),
        ('system_outage', _('System Outage')),
        ('security_alert', _('Security Alert')),
        ('training_drill', _('Training Drill')),
        ('policy_update', _('Policy Update')),
        ('general_alert', _('General Alert')),
    ]
    
    SEVERITY_CHOICES = [
        ('info', _('Information')),
        ('warning', _('Warning')),
        ('alert', _('Alert')),
        ('emergency', _('Emergency')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('active', _('Active')),
        ('resolved', _('Resolved')),
        ('cancelled', _('Cancelled')),
        ('expired', _('Expired')),
    ]
    
    # Alert Details
    title = models.CharField(_('Alert Title'), max_length=200)
    message = models.TextField(_('Alert Message'))
    alert_type = models.CharField(_('Alert Type'), max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(_('Severity'), max_length=20, choices=SEVERITY_CHOICES)
    
    # Status
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Targeting
    target_roles = models.JSONField(_('Target Roles'), default=list)
    target_locations = models.JSONField(_('Target Locations'), default=list)
    target_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='emergency_alerts',
        verbose_name=_('Target Users')
    )
    
    # Timing
    alert_start = models.DateTimeField(_('Alert Start'), auto_now_add=True)
    alert_end = models.DateTimeField(_('Alert End'), null=True, blank=True)
    auto_resolve_at = models.DateTimeField(_('Auto Resolve At'), null=True, blank=True)
    
    # Delivery
    delivery_channels = models.ManyToManyField(
        NotificationChannel,
        verbose_name=_('Delivery Channels')
    )
    
    # Acknowledgment
    requires_acknowledgment = models.BooleanField(_('Requires Acknowledgment'), default=False)
    acknowledged_by = models.ManyToManyField(
        User,
        blank=True,
        related_name='acknowledged_emergency_alerts',
        verbose_name=_('Acknowledged By')
    )

    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_emergency_alerts',
        verbose_name=_('Created By')
    )
    
    # Statistics
    total_recipients = models.PositiveIntegerField(_('Total Recipients'), default=0)
    total_delivered = models.PositiveIntegerField(_('Total Delivered'), default=0)
    total_acknowledged = models.PositiveIntegerField(_('Total Acknowledged'), default=0)
    
    class Meta:
        verbose_name = _('Emergency Alert')
        verbose_name_plural = _('Emergency Alerts')
        ordering = ['-alert_start']
        indexes = [
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['status', 'alert_start']),
        ]
    
    @property
    def is_active(self):
        """Check if alert is currently active"""
        now = timezone.now()
        return (
            self.status == 'active' and
            self.alert_start <= now and
            (not self.alert_end or self.alert_end > now)
        )
    
    @property
    def acknowledgment_rate(self):
        """Calculate acknowledgment rate"""
        if self.total_recipients > 0:
            return (self.total_acknowledged / self.total_recipients) * 100
        return 0
    
    def activate_alert(self):
        """Activate the emergency alert"""
        self.status = 'active'
        self.save()
        
        # Send notifications to all targets
        self.send_to_targets()
    
    def resolve_alert(self, user=None):
        """Resolve the emergency alert"""
        self.status = 'resolved'
        self.alert_end = timezone.now()
        self.save()
    
    def send_to_targets(self):
        """Send alert to all targeted users"""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get targeted users
        target_users = set()

        # Add explicitly targeted users
        target_users.update(self.target_users.all())

        # Add users by role
        if self.target_roles:
            role_users = User.objects.filter(role__in=self.target_roles)
            target_users.update(role_users)

        # Create notifications for each target user
        for user in target_users:
            Notification.objects.create(
                recipient_user=user,
                subject=f"EMERGENCY ALERT: {self.title}",
                message=self.message,
                notification_type='emergency_alert',
                priority='critical',
                context_data={
                    'alert_id': str(self.id),
                    'alert_type': self.alert_type,
                    'severity': self.severity,
                    'requires_acknowledgment': self.requires_acknowledgment
                }
            )

        self.total_recipients = len(target_users)
        self.save()

    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"


class NotificationPreference(BaseModel):
    """User notification preferences"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='communication_preferences'
    )

    # Channel Preferences
    email_enabled = models.BooleanField(_('Email Notifications'), default=True)
    sms_enabled = models.BooleanField(_('SMS Notifications'), default=True)
    push_enabled = models.BooleanField(_('Push Notifications'), default=True)
    in_app_enabled = models.BooleanField(_('In-App Notifications'), default=True)

    # Notification Types
    emergency_alerts = models.BooleanField(_('Emergency Alerts'), default=True)
    dispatch_notifications = models.BooleanField(_('Dispatch Notifications'), default=True)
    status_updates = models.BooleanField(_('Status Updates'), default=True)
    system_alerts = models.BooleanField(_('System Alerts'), default=True)

    # Timing Preferences
    quiet_hours_start = models.TimeField(_('Quiet Hours Start'), null=True, blank=True)
    quiet_hours_end = models.TimeField(_('Quiet Hours End'), null=True, blank=True)
    weekend_notifications = models.BooleanField(_('Weekend Notifications'), default=True)

    # Contact Information
    preferred_email = models.EmailField(_('Preferred Email'), blank=True)
    preferred_phone = models.CharField(
        _('Preferred Phone'),
        max_length=20,
        blank=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Invalid phone number')]
    )

    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')

    def is_in_quiet_hours(self):
        """Check if current time is in quiet hours"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        now = timezone.now().time()

        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            # Quiet hours span midnight
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end

    def should_receive_notification(self, notification_type, channel_type):
        """Check if user should receive notification"""
        # Check if notification type is enabled
        type_enabled = getattr(self, f"{notification_type}_enabled", True)
        if not type_enabled:
            return False

        # Check if channel is enabled
        channel_enabled = getattr(self, f"{channel_type}_enabled", True)
        if not channel_enabled:
            return False

        # Check quiet hours (except for emergency alerts)
        if notification_type != 'emergency_alerts' and self.is_in_quiet_hours():
            return False

        # Check weekend notifications
        if not self.weekend_notifications and timezone.now().weekday() >= 5:
            return False

        return True

    def __str__(self):
        return f"Notification Preferences - {self.user.get_full_name()}"
