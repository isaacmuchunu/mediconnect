"""
Analytics & Reporting System Models
Real-time dashboards, performance metrics, and automated reporting
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta, datetime
import json
from decimal import Decimal

User = get_user_model()


class BaseModel(models.Model):
    """Base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class PerformanceMetric(BaseModel):
    """System performance metrics tracking"""
    
    METRIC_TYPE_CHOICES = [
        ('response_time', _('Response Time')),
        ('dispatch_time', _('Dispatch Time')),
        ('transport_time', _('Transport Time')),
        ('hospital_handoff_time', _('Hospital Handoff Time')),
        ('total_call_duration', _('Total Call Duration')),
        ('ambulance_utilization', _('Ambulance Utilization')),
        ('hospital_capacity', _('Hospital Capacity')),
        ('crew_efficiency', _('Crew Efficiency')),
        ('fuel_consumption', _('Fuel Consumption')),
        ('maintenance_cost', _('Maintenance Cost')),
    ]
    
    UNIT_CHOICES = [
        ('minutes', _('Minutes')),
        ('seconds', _('Seconds')),
        ('hours', _('Hours')),
        ('percentage', _('Percentage')),
        ('count', _('Count')),
        ('currency', _('Currency')),
        ('kilometers', _('Kilometers')),
        ('liters', _('Liters')),
    ]
    
    # Metric Details
    metric_type = models.CharField(_('Metric Type'), max_length=30, choices=METRIC_TYPE_CHOICES)
    metric_name = models.CharField(_('Metric Name'), max_length=100)
    value = models.DecimalField(_('Value'), max_digits=10, decimal_places=2)
    unit = models.CharField(_('Unit'), max_length=20, choices=UNIT_CHOICES)
    
    # Context
    ambulance = models.ForeignKey(
        'ambulances.Ambulance',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='analytics_performance_metrics'
    )
    dispatch = models.ForeignKey(
        'ambulances.Dispatch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='performance_metrics'
    )
    hospital = models.ForeignKey(
        'doctors.Hospital',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='performance_metrics'
    )
    crew_member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='performance_metrics'
    )
    
    # Time Period
    measurement_date = models.DateField(_('Measurement Date'))
    measurement_hour = models.PositiveIntegerField(_('Measurement Hour'), null=True, blank=True)
    
    # Additional Data
    metadata = models.JSONField(_('Metadata'), default=dict)
    
    class Meta:
        verbose_name = _('Performance Metric')
        verbose_name_plural = _('Performance Metrics')
        ordering = ['-measurement_date', '-created_at']
        indexes = [
            models.Index(fields=['metric_type', 'measurement_date']),
            models.Index(fields=['ambulance', 'metric_type']),
            models.Index(fields=['hospital', 'metric_type']),
        ]
    
    def __str__(self):
        return f"{self.metric_name}: {self.value} {self.unit}"


class DashboardWidget(BaseModel):
    """Configurable dashboard widgets"""
    
    WIDGET_TYPE_CHOICES = [
        ('chart_line', _('Line Chart')),
        ('chart_bar', _('Bar Chart')),
        ('chart_pie', _('Pie Chart')),
        ('chart_area', _('Area Chart')),
        ('metric_card', _('Metric Card')),
        ('table', _('Data Table')),
        ('map', _('Map View')),
        ('gauge', _('Gauge')),
        ('progress', _('Progress Bar')),
        ('alert_list', _('Alert List')),
    ]
    
    SIZE_CHOICES = [
        ('small', _('Small (1x1)')),
        ('medium', _('Medium (2x1)')),
        ('large', _('Large (2x2)')),
        ('wide', _('Wide (3x1)')),
        ('extra_large', _('Extra Large (3x2)')),
    ]
    
    # Widget Configuration
    title = models.CharField(_('Widget Title'), max_length=100)
    widget_type = models.CharField(_('Widget Type'), max_length=20, choices=WIDGET_TYPE_CHOICES)
    size = models.CharField(_('Size'), max_length=20, choices=SIZE_CHOICES, default='medium')
    
    # Data Configuration
    data_source = models.CharField(_('Data Source'), max_length=100)
    query_parameters = models.JSONField(_('Query Parameters'), default=dict)
    refresh_interval = models.PositiveIntegerField(_('Refresh Interval (seconds)'), default=300)
    
    # Display Configuration
    chart_config = models.JSONField(_('Chart Configuration'), default=dict)
    color_scheme = models.CharField(_('Color Scheme'), max_length=50, default='default')
    
    # Position and Visibility
    dashboard_position = models.PositiveIntegerField(_('Dashboard Position'), default=0)
    is_visible = models.BooleanField(_('Visible'), default=True)
    
    # Access Control
    visible_to_roles = models.JSONField(_('Visible to Roles'), default=list)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_widgets'
    )
    
    class Meta:
        verbose_name = _('Dashboard Widget')
        verbose_name_plural = _('Dashboard Widgets')
        ordering = ['dashboard_position', 'title']
    
    def get_data(self, time_range='24h'):
        """Get widget data based on configuration"""
        # This would implement the actual data fetching logic
        # For now, return sample data
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            'datasets': [{
                'label': self.title,
                'data': [10, 20, 15, 25, 30],
                'backgroundColor': '#3b82f6'
            }]
        }
    
    def __str__(self):
        return f"{self.title} ({self.get_widget_type_display()})"


class ReportTemplate(BaseModel):
    """Automated report templates"""
    
    REPORT_TYPE_CHOICES = [
        ('daily_summary', _('Daily Summary')),
        ('weekly_performance', _('Weekly Performance')),
        ('monthly_analytics', _('Monthly Analytics')),
        ('quarterly_review', _('Quarterly Review')),
        ('annual_report', _('Annual Report')),
        ('incident_report', _('Incident Report')),
        ('compliance_report', _('Compliance Report')),
        ('financial_summary', _('Financial Summary')),
        ('custom_report', _('Custom Report')),
    ]
    
    FREQUENCY_CHOICES = [
        ('manual', _('Manual')),
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('annually', _('Annually')),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', _('PDF')),
        ('excel', _('Excel')),
        ('csv', _('CSV')),
        ('html', _('HTML')),
        ('json', _('JSON')),
    ]
    
    # Template Details
    name = models.CharField(_('Report Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    report_type = models.CharField(_('Report Type'), max_length=30, choices=REPORT_TYPE_CHOICES)
    
    # Generation Settings
    frequency = models.CharField(_('Frequency'), max_length=20, choices=FREQUENCY_CHOICES)
    output_format = models.CharField(_('Output Format'), max_length=10, choices=FORMAT_CHOICES)
    
    # Data Configuration
    data_sources = models.JSONField(_('Data Sources'), default=list)
    filters = models.JSONField(_('Filters'), default=dict)
    date_range_type = models.CharField(_('Date Range Type'), max_length=20, default='relative')
    
    # Template Content
    template_content = models.TextField(_('Template Content'))
    chart_configurations = models.JSONField(_('Chart Configurations'), default=list)
    
    # Recipients
    recipients = models.ManyToManyField(
        User,
        blank=True,
        related_name='report_subscriptions',
        verbose_name=_('Recipients')
    )
    recipient_emails = models.JSONField(_('Additional Email Recipients'), default=list)
    
    # Scheduling
    is_active = models.BooleanField(_('Active'), default=True)
    next_generation = models.DateTimeField(_('Next Generation'), null=True, blank=True)
    last_generated = models.DateTimeField(_('Last Generated'), null=True, blank=True)
    
    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_report_templates'
    )
    
    class Meta:
        verbose_name = _('Report Template')
        verbose_name_plural = _('Report Templates')
        ordering = ['name']
    
    def generate_report(self, date_range=None):
        """Generate report based on template"""
        # This would implement the actual report generation logic
        pass
    
    def schedule_next_generation(self):
        """Calculate next generation time based on frequency"""
        if self.frequency == 'daily':
            self.next_generation = timezone.now() + timedelta(days=1)
        elif self.frequency == 'weekly':
            self.next_generation = timezone.now() + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            self.next_generation = timezone.now() + timedelta(days=30)
        elif self.frequency == 'quarterly':
            self.next_generation = timezone.now() + timedelta(days=90)
        elif self.frequency == 'annually':
            self.next_generation = timezone.now() + timedelta(days=365)
        
        self.save()
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class GeneratedReport(BaseModel):
    """Generated report instances"""
    
    STATUS_CHOICES = [
        ('generating', _('Generating')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Report Details
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='generated_reports'
    )
    title = models.CharField(_('Report Title'), max_length=200)
    
    # Generation Info
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='generating')
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='analytics_generated_reports'
    )
    generation_started = models.DateTimeField(_('Generation Started'), auto_now_add=True)
    generation_completed = models.DateTimeField(_('Generation Completed'), null=True, blank=True)
    
    # Content
    file_path = models.CharField(_('File Path'), max_length=500, blank=True)
    file_size = models.PositiveIntegerField(_('File Size (bytes)'), null=True, blank=True)
    content_hash = models.CharField(_('Content Hash'), max_length=64, blank=True)
    
    # Data Range
    data_start_date = models.DateTimeField(_('Data Start Date'))
    data_end_date = models.DateTimeField(_('Data End Date'))
    
    # Metadata
    generation_parameters = models.JSONField(_('Generation Parameters'), default=dict)
    error_message = models.TextField(_('Error Message'), blank=True)
    
    class Meta:
        verbose_name = _('Generated Report')
        verbose_name_plural = _('Generated Reports')
        ordering = ['-generation_started']
        indexes = [
            models.Index(fields=['template', 'status']),
            models.Index(fields=['generated_by', 'generation_started']),
        ]
    
    @property
    def generation_duration(self):
        """Calculate report generation duration"""
        if self.generation_completed:
            return self.generation_completed - self.generation_started
        return None
    
    @property
    def is_available(self):
        """Check if report file is available"""
        return self.status == 'completed' and self.file_path
    
    def mark_completed(self, file_path, file_size=None):
        """Mark report as completed"""
        self.status = 'completed'
        self.generation_completed = timezone.now()
        self.file_path = file_path
        if file_size:
            self.file_size = file_size
        self.save()
    
    def mark_failed(self, error_message):
        """Mark report as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.save()
    
    def __str__(self):
        return f"{self.title} - {self.generation_started.strftime('%Y-%m-%d %H:%M')}"


class AnalyticsEvent(BaseModel):
    """Track analytics events for system usage"""
    
    EVENT_TYPE_CHOICES = [
        ('user_login', _('User Login')),
        ('dispatch_created', _('Dispatch Created')),
        ('ambulance_assigned', _('Ambulance Assigned')),
        ('status_updated', _('Status Updated')),
        ('hospital_arrival', _('Hospital Arrival')),
        ('call_completed', _('Call Completed')),
        ('report_generated', _('Report Generated')),
        ('alert_sent', _('Alert Sent')),
        ('message_sent', _('Message Sent')),
        ('system_error', _('System Error')),
    ]
    
    # Event Details
    event_type = models.CharField(_('Event Type'), max_length=30, choices=EVENT_TYPE_CHOICES)
    event_name = models.CharField(_('Event Name'), max_length=100)
    
    # Context
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events'
    )
    session_id = models.CharField(_('Session ID'), max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    # Related Objects
    related_dispatch = models.ForeignKey(
        'ambulances.Dispatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events'
    )
    related_ambulance = models.ForeignKey(
        'ambulances.Ambulance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events'
    )
    
    # Event Data
    event_data = models.JSONField(_('Event Data'), default=dict)
    
    # Timing
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)
    duration_ms = models.PositiveIntegerField(_('Duration (ms)'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Analytics Event')
        verbose_name_plural = _('Analytics Events')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['session_id']),
        ]
    
    @classmethod
    def log_event(cls, event_type, event_name, user=None, **kwargs):
        """Log an analytics event"""
        return cls.objects.create(
            event_type=event_type,
            event_name=event_name,
            user=user,
            event_data=kwargs.get('event_data', {}),
            session_id=kwargs.get('session_id', ''),
            ip_address=kwargs.get('ip_address'),
            user_agent=kwargs.get('user_agent', ''),
            related_dispatch=kwargs.get('related_dispatch'),
            related_ambulance=kwargs.get('related_ambulance'),
            duration_ms=kwargs.get('duration_ms')
        )
    
    def __str__(self):
        return f"{self.event_name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class KPITarget(BaseModel):
    """Key Performance Indicator targets and thresholds"""
    
    KPI_TYPE_CHOICES = [
        ('response_time', _('Response Time')),
        ('dispatch_accuracy', _('Dispatch Accuracy')),
        ('hospital_handoff_time', _('Hospital Handoff Time')),
        ('patient_satisfaction', _('Patient Satisfaction')),
        ('crew_utilization', _('Crew Utilization')),
        ('fuel_efficiency', _('Fuel Efficiency')),
        ('maintenance_cost', _('Maintenance Cost')),
        ('system_uptime', _('System Uptime')),
    ]
    
    # KPI Details
    kpi_type = models.CharField(_('KPI Type'), max_length=30, choices=KPI_TYPE_CHOICES)
    name = models.CharField(_('KPI Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    
    # Targets
    target_value = models.DecimalField(_('Target Value'), max_digits=10, decimal_places=2)
    warning_threshold = models.DecimalField(_('Warning Threshold'), max_digits=10, decimal_places=2)
    critical_threshold = models.DecimalField(_('Critical Threshold'), max_digits=10, decimal_places=2)
    
    # Configuration
    unit = models.CharField(_('Unit'), max_length=20)
    higher_is_better = models.BooleanField(_('Higher is Better'), default=True)
    
    # Time Period
    measurement_period = models.CharField(_('Measurement Period'), max_length=20, default='daily')
    
    # Status
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        verbose_name = _('KPI Target')
        verbose_name_plural = _('KPI Targets')
        ordering = ['kpi_type', 'name']
    
    def get_current_value(self):
        """Get current KPI value"""
        # This would implement the actual KPI calculation
        return Decimal('0.00')
    
    def get_status(self):
        """Get current KPI status"""
        current_value = self.get_current_value()
        
        if self.higher_is_better:
            if current_value >= self.target_value:
                return 'target'
            elif current_value >= self.warning_threshold:
                return 'warning'
            else:
                return 'critical'
        else:
            if current_value <= self.target_value:
                return 'target'
            elif current_value <= self.warning_threshold:
                return 'warning'
            else:
                return 'critical'
    
    def __str__(self):
        return f"{self.name} (Target: {self.target_value} {self.unit})"
