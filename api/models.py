from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class BaseModel(models.Model):
    """Abstract base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        abstract = True


class APIKey(BaseModel):
    """API key management for external integrations"""

    PERMISSION_LEVELS = [
        ('read', _('Read Only')),
        ('write', _('Read/Write')),
        ('admin', _('Admin')),
    ]

    name = models.CharField(_('API Key Name'), max_length=100)
    key = models.CharField(_('API Key'), max_length=64, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='api_keys')
    permission_level = models.CharField(_('Permission Level'), max_length=10, choices=PERMISSION_LEVELS, default='read')
    allowed_ips = models.JSONField(_('Allowed IP Addresses'), default=list, blank=True)
    rate_limit = models.PositiveIntegerField(_('Rate Limit (requests/hour)'), default=1000)
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    last_used = models.DateTimeField(_('Last Used'), null=True, blank=True)
    usage_count = models.PositiveIntegerField(_('Usage Count'), default=0)

    class Meta:
        verbose_name = _('API Key')
        verbose_name_plural = _('API Keys')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def increment_usage(self):
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])


class APIRequestLog(BaseModel):
    """Log API requests for monitoring and analytics"""

    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, null=True, blank=True, related_name='request_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    endpoint = models.CharField(_('Endpoint'), max_length=255)
    method = models.CharField(_('HTTP Method'), max_length=10)
    ip_address = models.GenericIPAddressField(_('IP Address'))
    user_agent = models.TextField(_('User Agent'), blank=True)
    request_data = models.JSONField(_('Request Data'), default=dict, blank=True)
    response_status = models.PositiveIntegerField(_('Response Status'))
    response_time_ms = models.PositiveIntegerField(_('Response Time (ms)'))
    error_message = models.TextField(_('Error Message'), blank=True)

    class Meta:
        verbose_name = _('API Request Log')
        verbose_name_plural = _('API Request Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['api_key', 'created_at']),
            models.Index(fields=['endpoint', 'method']),
            models.Index(fields=['response_status']),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.response_status}"


class WebhookEndpoint(BaseModel):
    """Webhook endpoints for external integrations"""

    EVENT_TYPES = [
        ('referral.created', _('Referral Created')),
        ('referral.updated', _('Referral Updated')),
        ('referral.accepted', _('Referral Accepted')),
        ('referral.declined', _('Referral Declined')),
        ('appointment.scheduled', _('Appointment Scheduled')),
        ('appointment.completed', _('Appointment Completed')),
        ('appointment.cancelled', _('Appointment Cancelled')),
        ('dispatch.created', _('Dispatch Created')),
        ('dispatch.completed', _('Dispatch Completed')),
        ('patient.registered', _('Patient Registered')),
    ]

    name = models.CharField(_('Webhook Name'), max_length=100)
    url = models.URLField(_('Webhook URL'))
    secret = models.CharField(_('Secret Key'), max_length=64)
    event_types = models.JSONField(_('Event Types'), default=list)
    is_enabled = models.BooleanField(_('Enabled'), default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    retry_count = models.PositiveIntegerField(_('Max Retry Count'), default=3)
    timeout_seconds = models.PositiveIntegerField(_('Timeout (seconds)'), default=30)

    class Meta:
        verbose_name = _('Webhook Endpoint')
        verbose_name_plural = _('Webhook Endpoints')

    def __str__(self):
        return f"{self.name} - {self.url}"


class WebhookDelivery(BaseModel):
    """Track webhook delivery attempts"""

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('delivered', _('Delivered')),
        ('failed', _('Failed')),
        ('retrying', _('Retrying')),
    ]

    webhook = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(_('Event Type'), max_length=50)
    payload = models.JSONField(_('Payload'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    response_status = models.PositiveIntegerField(_('Response Status'), null=True, blank=True)
    response_body = models.TextField(_('Response Body'), blank=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    attempt_count = models.PositiveIntegerField(_('Attempt Count'), default=0)
    next_retry = models.DateTimeField(_('Next Retry'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)

    class Meta:
        verbose_name = _('Webhook Delivery')
        verbose_name_plural = _('Webhook Deliveries')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.webhook.name} - {self.event_type} ({self.status})"


class ExternalIntegration(BaseModel):
    """External system integrations"""

    INTEGRATION_TYPES = [
        ('hl7', _('HL7 FHIR')),
        ('epic', _('Epic MyChart')),
        ('cerner', _('Cerner')),
        ('allscripts', _('Allscripts')),
        ('custom', _('Custom Integration')),
    ]

    name = models.CharField(_('Integration Name'), max_length=100)
    integration_type = models.CharField(_('Integration Type'), max_length=20, choices=INTEGRATION_TYPES)
    base_url = models.URLField(_('Base URL'))
    api_key = models.CharField(_('API Key'), max_length=255, blank=True)
    username = models.CharField(_('Username'), max_length=100, blank=True)
    password = models.CharField(_('Password'), max_length=255, blank=True)
    configuration = models.JSONField(_('Configuration'), default=dict)
    is_enabled = models.BooleanField(_('Enabled'), default=True)
    last_sync = models.DateTimeField(_('Last Sync'), null=True, blank=True)
    sync_frequency_hours = models.PositiveIntegerField(_('Sync Frequency (hours)'), default=24)

    class Meta:
        verbose_name = _('External Integration')
        verbose_name_plural = _('External Integrations')

    def __str__(self):
        return f"{self.name} ({self.get_integration_type_display()})"


class DataExport(BaseModel):
    """Data export requests and tracking"""

    EXPORT_FORMATS = [
        ('csv', _('CSV')),
        ('json', _('JSON')),
        ('xml', _('XML')),
        ('hl7', _('HL7 FHIR')),
        ('pdf', _('PDF Report')),
    ]

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('expired', _('Expired')),
    ]

    name = models.CharField(_('Export Name'), max_length=100)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='data_exports')
    export_format = models.CharField(_('Export Format'), max_length=10, choices=EXPORT_FORMATS)
    data_type = models.CharField(_('Data Type'), max_length=50)
    filters = models.JSONField(_('Filters'), default=dict)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.FileField(_('Export File'), upload_to='exports/', null=True, blank=True)
    file_size = models.PositiveIntegerField(_('File Size (bytes)'), null=True, blank=True)
    record_count = models.PositiveIntegerField(_('Record Count'), null=True, blank=True)
    started_at = models.DateTimeField(_('Started At'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    error_message = models.TextField(_('Error Message'), blank=True)

    class Meta:
        verbose_name = _('Data Export')
        verbose_name_plural = _('Data Exports')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False