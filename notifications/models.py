from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.mail import send_mail
from django.conf import settings
import json

User = get_user_model()

class BaseModel(models.Model):
    """Base model with common fields"""
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        abstract = True

class NotificationTemplate(BaseModel):
    """Templates for different types of notifications"""
    NOTIFICATION_TYPES = [
        ('referral_created', _('Referral Created')),
        ('referral_accepted', _('Referral Accepted')),
        ('referral_rejected', _('Referral Rejected')),
        ('referral_completed', _('Referral Completed')),
        ('appointment_scheduled', _('Appointment Scheduled')),
        ('appointment_reminder', _('Appointment Reminder')),
        ('appointment_cancelled', _('Appointment Cancelled')),
        ('ambulance_requested', _('Ambulance Requested')),
        ('ambulance_dispatched', _('Ambulance Dispatched')),
        ('system_maintenance', _('System Maintenance')),
        ('account_created', _('Account Created')),
        ('password_reset', _('Password Reset')),
        ('profile_updated', _('Profile Updated')),
        ('emergency_alert', _('Emergency Alert')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, unique=True, verbose_name=_('Notification Type'))
    subject_template = models.CharField(max_length=200, verbose_name=_('Subject Template'))
    title_template = models.CharField(max_length=200, blank=True, verbose_name=_('Title Template'))
    message_template = models.TextField(verbose_name=_('Message Template'))
    email_template = models.TextField(blank=True, verbose_name=_('Email Template'))
    sms_template = models.CharField(max_length=160, blank=True, verbose_name=_('SMS Template'))
    is_email_enabled = models.BooleanField(default=True, verbose_name=_('Email Enabled'))
    is_sms_enabled = models.BooleanField(default=False, verbose_name=_('SMS Enabled'))
    is_push_enabled = models.BooleanField(default=True, verbose_name=_('Push Enabled'))
    default_priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name=_('Default Priority'))
    
    def __str__(self):
        return f'{self.name} - {self.get_notification_type_display()}'
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ['name']

class Notification(BaseModel):
    """Main notification model"""
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    DELIVERY_METHODS = [
        ('in_app', _('In-App')),
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('push', _('Push Notification')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('failed', _('Failed')),
        ('read', _('Read')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name=_('User'))
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Template'))
    title = models.CharField(max_length=200, default="Notification", verbose_name=_('Title'))
    message = models.TextField(verbose_name=_('Message'))
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name=_('Priority'))
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHODS, default='in_app', verbose_name=_('Delivery Method'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_('Status'))
    
    # Generic foreign key for linking to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Content Type'))
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('Object ID'))
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Sent At'))
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Delivered At'))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Read At'))
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Metadata'))
    
    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name=_('Scheduled For'))
    
    def __str__(self):
        return f'{self.title} - {self.user.username} ({self.status})'
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.status = 'read'
            self.save(update_fields=['read_at', 'status'])
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        self.sent_at = timezone.now()
        self.status = 'sent'
        self.save(update_fields=['sent_at', 'status'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.delivered_at = timezone.now()
        self.status = 'delivered'
        self.save(update_fields=['delivered_at', 'status'])
    
    @property
    def is_read(self):
        return self.read_at is not None
    
    @property
    def is_urgent(self):
        return self.priority == 'urgent'
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'read_at']),
            models.Index(fields=['priority', 'created_at']),
        ]

class NotificationPreference(BaseModel):
    """User notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences', verbose_name=_('User'))
    
    # Delivery method preferences
    email_notifications = models.BooleanField(default=True, verbose_name=_('Email Notifications'))
    sms_notifications = models.BooleanField(default=False, verbose_name=_('SMS Notifications'))
    push_notifications = models.BooleanField(default=True, verbose_name=_('Push Notifications'))
    
    # Notification type preferences
    referral_notifications = models.BooleanField(default=True, verbose_name=_('Referral Notifications'))
    appointment_notifications = models.BooleanField(default=True, verbose_name=_('Appointment Notifications'))
    ambulance_notifications = models.BooleanField(default=True, verbose_name=_('Ambulance Notifications'))
    system_notifications = models.BooleanField(default=True, verbose_name=_('System Notifications'))
    emergency_notifications = models.BooleanField(default=True, verbose_name=_('Emergency Notifications'))
    marketing_notifications = models.BooleanField(default=False, verbose_name=_('Marketing Notifications'))
    
    # Timing preferences
    quiet_hours_start = models.TimeField(default='22:00', verbose_name=_('Quiet Hours Start'))
    quiet_hours_end = models.TimeField(default='08:00', verbose_name=_('Quiet Hours End'))
    weekend_notifications = models.BooleanField(default=True, verbose_name=_('Weekend Notifications'))
    
    # Frequency settings
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', _('Immediate')),
            ('hourly', _('Hourly')),
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
        ],
        default='immediate',
        verbose_name=_('Digest Frequency')
    )
    
    # Added alias for admin compatibility
    @property
    def notification_frequency(self):
        return self.digest_frequency
    
    def __str__(self):
        return f'Notification preferences for {self.user.username}'
    
    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')

class NotificationLog(BaseModel):
    """Log of notification delivery attempts"""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    delivery_method = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    error_message = models.TextField(blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    attempt_count = models.PositiveIntegerField(default=1)
    
    # Additional fields for admin compatibility
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f'Log for {self.notification.title} - {self.delivery_method} ({self.status})'
    
    class Meta:
        ordering = ['-created_at']

class NotificationQueue(BaseModel):
    """Queue for batch processing notifications"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    priority = models.IntegerField(default=0)  # Higher number = higher priority
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    next_retry = models.DateTimeField(null=True, blank=True)
    
    # Additional fields for admin compatibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f'Queue item for {self.notification.title}'
    
    class Meta:
        ordering = ['-priority', 'created_at']


class NotificationChannel(BaseModel):
    """Define notification delivery channels and their configurations"""
    
    CHANNEL_TYPES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('push', _('Push Notification')),
        ('webhook', _('Webhook')),
        ('slack', _('Slack')),
        ('teams', _('Microsoft Teams')),
        ('telegram', _('Telegram')),
        ('whatsapp', _('WhatsApp')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('maintenance', _('Maintenance')),
        ('error', _('Error')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES, verbose_name=_('Channel Type'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name=_('Status'))
    
    # Configuration
    configuration = models.JSONField(default=dict, help_text=_('Channel-specific configuration'), verbose_name=_('Configuration'))
    rate_limit = models.IntegerField(default=100, help_text=_('Messages per minute'), verbose_name=_('Rate Limit'))
    retry_attempts = models.IntegerField(default=3, verbose_name=_('Retry Attempts'))
    retry_delay = models.IntegerField(default=300, help_text=_('Delay in seconds'), verbose_name=_('Retry Delay'))
    
    # Statistics
    total_sent = models.IntegerField(default=0, verbose_name=_('Total Sent'))
    total_delivered = models.IntegerField(default=0, verbose_name=_('Total Delivered'))
    total_failed = models.IntegerField(default=0, verbose_name=_('Total Failed'))
    last_used = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Used'))
    
    # Access control
    allowed_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name=_('Allowed Users'))
    is_default = models.BooleanField(default=False, verbose_name=_('Is Default'))
    
    class Meta:
        verbose_name = _('Notification Channel')
        verbose_name_plural = _('Notification Channels')
        ordering = ['name']
        unique_together = ['channel_type', 'name']
    
    def __str__(self):
        return f'{self.name} ({self.get_channel_type_display()})'
    
    @property
    def success_rate(self):
        """Calculate delivery success rate"""
        if self.total_sent == 0:
            return 0
        return (self.total_delivered / self.total_sent) * 100
    
    def increment_stats(self, sent=0, delivered=0, failed=0):
        """Update channel statistics"""
        self.total_sent += sent
        self.total_delivered += delivered
        self.total_failed += failed
        if sent > 0:
            self.last_used = timezone.now()
        self.save()


class NotificationRule(BaseModel):
    """Define rules for automatic notification triggering"""
    
    TRIGGER_TYPES = [
        ('model_created', _('Model Created')),
        ('model_updated', _('Model Updated')),
        ('model_deleted', _('Model Deleted')),
        ('field_changed', _('Field Changed')),
        ('time_based', _('Time Based')),
        ('condition_met', _('Condition Met')),
        ('user_action', _('User Action')),
        ('system_event', _('System Event')),
    ]
    
    CONDITION_OPERATORS = [
        ('equals', _('Equals')),
        ('not_equals', _('Not Equals')),
        ('greater_than', _('Greater Than')),
        ('less_than', _('Less Than')),
        ('contains', _('Contains')),
        ('starts_with', _('Starts With')),
        ('ends_with', _('Ends With')),
        ('in_list', _('In List')),
        ('is_null', _('Is Null')),
        ('is_not_null', _('Is Not Null')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES, verbose_name=_('Trigger Type'))
    
    # Target model and conditions
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_('Target Model'))
    conditions = models.JSONField(default=list, help_text=_('List of conditions to check'), verbose_name=_('Conditions'))
    
    # Notification settings
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, verbose_name=_('Template'))
    channels = models.ManyToManyField(NotificationChannel, verbose_name=_('Channels'))
    priority = models.CharField(max_length=10, choices=Notification.PRIORITY_CHOICES, default='medium', verbose_name=_('Priority'))
    
    # Recipients
    recipient_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='notification_rules', verbose_name=_('Recipient Users'))
    recipient_roles = models.JSONField(default=list, help_text=_('List of user roles to notify'), verbose_name=_('Recipient Roles'))
    recipient_emails = models.TextField(blank=True, help_text=_('Comma-separated email addresses'), verbose_name=_('Recipient Emails'))
    
    # Timing and frequency
    delay_minutes = models.IntegerField(default=0, help_text=_('Delay before sending notification'), verbose_name=_('Delay (minutes)'))
    cooldown_minutes = models.IntegerField(default=0, help_text=_('Minimum time between notifications'), verbose_name=_('Cooldown (minutes)'))
    max_notifications_per_day = models.IntegerField(null=True, blank=True, verbose_name=_('Max Notifications Per Day'))
    
    # Status and statistics
    is_enabled = models.BooleanField(default=True, verbose_name=_('Is Enabled'))
    trigger_count = models.IntegerField(default=0, verbose_name=_('Trigger Count'))
    last_triggered = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Triggered'))
    
    class Meta:
        verbose_name = _('Notification Rule')
        verbose_name_plural = _('Notification Rules')
        ordering = ['name']
    
    def __str__(self):
        return f'{self.name} - {self.get_trigger_type_display()}'
    
    def check_conditions(self, instance):
        """Check if conditions are met for the given instance"""
        for condition in self.conditions:
            field_name = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if not hasattr(instance, field_name):
                return False
            
            field_value = getattr(instance, field_name)
            
            if operator == 'equals' and field_value != value:
                return False
            elif operator == 'not_equals' and field_value == value:
                return False
            elif operator == 'greater_than' and field_value <= value:
                return False
            elif operator == 'less_than' and field_value >= value:
                return False
            elif operator == 'contains' and value not in str(field_value):
                return False
            elif operator == 'is_null' and field_value is not None:
                return False
            elif operator == 'is_not_null' and field_value is None:
                return False
        
        return True
    
    def increment_trigger_count(self):
        """Increment trigger counter"""
        self.trigger_count += 1
        self.last_triggered = timezone.now()
        self.save(update_fields=['trigger_count', 'last_triggered'])


class NotificationBatch(BaseModel):
    """Batch notifications for bulk sending"""
    
    BATCH_STATUS = [
        ('draft', _('Draft')),
        ('scheduled', _('Scheduled')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, verbose_name=_('Template'))
    channels = models.ManyToManyField(NotificationChannel, verbose_name=_('Channels'))
    
    # Recipients
    recipient_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name=_('Recipient Users'))
    recipient_filters = models.JSONField(default=dict, help_text=_('Filters to select recipients'), verbose_name=_('Recipient Filters'))
    external_recipients = models.TextField(blank=True, help_text=_('External email addresses, one per line'), verbose_name=_('External Recipients'))
    
    # Content
    subject = models.CharField(max_length=200, verbose_name=_('Subject'))
    message = models.TextField(verbose_name=_('Message'))
    variables = models.JSONField(default=dict, help_text=_('Template variables'), verbose_name=_('Variables'))
    
    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name=_('Scheduled For'))
    send_immediately = models.BooleanField(default=False, verbose_name=_('Send Immediately'))
    
    # Status and statistics
    status = models.CharField(max_length=20, choices=BATCH_STATUS, default='draft', verbose_name=_('Status'))
    total_recipients = models.IntegerField(default=0, verbose_name=_('Total Recipients'))
    sent_count = models.IntegerField(default=0, verbose_name=_('Sent Count'))
    delivered_count = models.IntegerField(default=0, verbose_name=_('Delivered Count'))
    failed_count = models.IntegerField(default=0, verbose_name=_('Failed Count'))
    
    # Processing
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Started At'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Completed At'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_batches', verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Notification Batch')
        verbose_name_plural = _('Notification Batches')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.total_recipients} recipients)'
    
    @property
    def success_rate(self):
        """Calculate delivery success rate"""
        if self.sent_count == 0:
            return 0
        return (self.delivered_count / self.sent_count) * 100
    
    @property
    def is_completed(self):
        """Check if batch processing is completed"""
        return self.status in ['completed', 'failed', 'cancelled']
    
    def update_stats(self, sent=0, delivered=0, failed=0):
        """Update batch statistics"""
        self.sent_count += sent
        self.delivered_count += delivered
        self.failed_count += failed
        self.save()


class NotificationAttachment(BaseModel):
    """File attachments for notifications"""
    
    ATTACHMENT_TYPES = [
        ('document', _('Document')),
        ('image', _('Image')),
        ('video', _('Video')),
        ('audio', _('Audio')),
        ('archive', _('Archive')),
        ('other', _('Other')),
    ]
    
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True, verbose_name=_('Notification'))
    batch = models.ForeignKey(NotificationBatch, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True, verbose_name=_('Batch'))
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True, verbose_name=_('Template'))
    
    name = models.CharField(max_length=255, verbose_name=_('Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    file = models.FileField(upload_to='notification_attachments/', verbose_name=_('File'))
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name=_('File Size'))
    content_type = models.CharField(max_length=100, blank=True, verbose_name=_('Content Type'))
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES, default='document', verbose_name=_('Attachment Type'))
    
    # Access control
    is_public = models.BooleanField(default=False, verbose_name=_('Is Public'))
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Expires At'))
    download_count = models.IntegerField(default=0, verbose_name=_('Download Count'))
    max_downloads = models.IntegerField(null=True, blank=True, verbose_name=_('Max Downloads'))
    
    # Metadata
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Uploaded By'))
    checksum = models.CharField(max_length=64, blank=True, verbose_name=_('Checksum'))
    
    class Meta:
        verbose_name = _('Notification Attachment')
        verbose_name_plural = _('Notification Attachments')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.get_attachment_type_display()})'
    
    @property
    def is_expired(self):
        """Check if attachment has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        if self.max_downloads and self.download_count >= self.max_downloads:
            return True
        return False
    
    def increment_download(self):
        """Increment download counter"""
        self.download_count += 1
        self.save(update_fields=['download_count'])
    
    def save(self, *args, **kwargs):
        """Override save to set file size and content type"""
        if self.file:
            self.file_size = self.file.size
            # You might want to use python-magic for better content type detection
            import mimetypes
            self.content_type = mimetypes.guess_type(self.file.name)[0] or 'application/octet-stream'
        super().save(*args, **kwargs)