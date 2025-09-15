from django.db import models
# Temporarily disable GIS for basic setup
# from django.contrib.gis.db import models as geomodels
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
import uuid
from datetime import timedelta


class BaseModel(models.Model):
    """Abstract base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        abstract = True


class AmbulanceType(BaseModel):
    """Ambulance type configuration"""
    name = models.CharField(_('Type Name'), max_length=100, unique=True)
    code = models.CharField(_('Type Code'), max_length=20, unique=True)
    description = models.TextField(_('Description'), blank=True)
    equipment_requirements = models.JSONField(_('Equipment Requirements'), default=list)
    staff_requirements = models.JSONField(_('Staff Requirements'), default=list)
    capacity_range = models.CharField(_('Capacity Range'), max_length=20, default='1-2')

    class Meta:
        verbose_name = _('Ambulance Type')
        verbose_name_plural = _('Ambulance Types')
        ordering = ['name']

    def __str__(self):
        return self.name


class Ambulance(BaseModel):
    """Enhanced ambulance model with comprehensive tracking"""

    STATUS_CHOICES = [
        ('available', _('Available')),
        ('dispatched', _('Dispatched')),
        ('en_route', _('En Route')),
        ('on_scene', _('On Scene')),
        ('transporting', _('Transporting')),
        ('at_hospital', _('At Hospital')),
        ('returning', _('Returning')),
        ('out_of_service', _('Out of Service')),
        ('maintenance', _('Under Maintenance')),
        ('offline', _('Offline')),
    ]

    CONDITION_CHOICES = [
        ('excellent', _('Excellent')),
        ('good', _('Good')),
        ('fair', _('Fair')),
        ('poor', _('Poor')),
        ('critical', _('Critical')),
    ]

    # Basic Information
    license_plate = models.CharField(
        _('License Plate'),
        max_length=15,
        unique=True,
        validators=[RegexValidator(regex=r'^[A-Z0-9\-\s]+$', message='Invalid license plate format')]
    )
    vehicle_identification_number = models.CharField(
        _('VIN'),
        max_length=17,
        unique=True,
        validators=[RegexValidator(regex=r'^[A-HJ-NPR-Z0-9]{17}$', message='Invalid VIN format')]
    )
    ambulance_type = models.ForeignKey(AmbulanceType, on_delete=models.CASCADE, verbose_name=_('Ambulance Type'))

    # Vehicle Details
    make = models.CharField(_('Make'), max_length=50)
    model = models.CharField(_('Model'), max_length=50)
    year = models.PositiveIntegerField(
        _('Year'),
        validators=[MinValueValidator(1990), MaxValueValidator(2030)]
    )
    color = models.CharField(_('Color'), max_length=30)
    mileage = models.PositiveIntegerField(_('Mileage'), default=0)

    # Capacity and Equipment
    patient_capacity = models.PositiveIntegerField(
        _('Patient Capacity'),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    crew_capacity = models.PositiveIntegerField(
        _('Crew Capacity'),
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    equipment_list = models.JSONField(_('Equipment List'), default=list)
    medical_equipment = models.TextField(_('Medical Equipment'), blank=True)

    # Status and Location
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='available')
    condition = models.CharField(_('Condition'), max_length=15, choices=CONDITION_CHOICES, default='good')
    current_latitude = models.FloatField(_('Current Latitude'), null=True, blank=True)
    current_longitude = models.FloatField(_('Current Longitude'), null=True, blank=True)
    base_latitude = models.FloatField(_('Base Latitude'), null=True, blank=True)
    base_longitude = models.FloatField(_('Base Longitude'), null=True, blank=True)

    # Operational Information
    fuel_level = models.PositiveIntegerField(
        _('Fuel Level (%)'),
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    last_maintenance = models.DateTimeField(_('Last Maintenance'), null=True, blank=True)
    next_maintenance = models.DateTimeField(_('Next Maintenance'), null=True, blank=True)

    # Assignment
    assigned_crew = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='AmbulanceCrew',
        related_name='assigned_ambulances',
        verbose_name=_('Assigned Crew')
    )
    home_station = models.ForeignKey(
        'AmbulanceStation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Home Station')
    )

    # Tracking and Monitoring
    gps_device_id = models.CharField(_('GPS Device ID'), max_length=50, blank=True)
    last_gps_update = models.DateTimeField(_('Last GPS Update'), null=True, blank=True)
    speed = models.FloatField(_('Current Speed (km/h)'), default=0.0)
    heading = models.FloatField(_('Heading (degrees)'), default=0.0)

    # Insurance and Registration
    insurance_policy = models.CharField(_('Insurance Policy'), max_length=100, blank=True)
    registration_expiry = models.DateField(_('Registration Expiry'), null=True, blank=True)
    inspection_expiry = models.DateField(_('Inspection Expiry'), null=True, blank=True)

    class Meta:
        verbose_name = _('Ambulance')
        verbose_name_plural = _('Ambulances')
        ordering = ['license_plate']
        indexes = [
            models.Index(fields=['status', 'ambulance_type']),
            models.Index(fields=['home_station', 'status']),
            models.Index(fields=['last_gps_update']),
        ]

    def __str__(self):
        return f"{self.ambulance_type.name} - {self.license_plate}"

    @property
    def is_available(self):
        return self.status == 'available' and self.is_active

    @property
    def is_operational(self):
        return self.status not in ['out_of_service', 'maintenance', 'offline']

    @property
    def needs_maintenance(self):
        if self.next_maintenance:
            return self.next_maintenance <= timezone.now()
        return False

    @property
    def fuel_status(self):
        if self.fuel_level >= 75:
            return 'full'
        elif self.fuel_level >= 50:
            return 'good'
        elif self.fuel_level >= 25:
            return 'low'
        else:
            return 'critical'

    def update_location(self, latitude, longitude, speed=0.0, heading=0.0):
        """Update ambulance location from GPS"""
        self.current_latitude = latitude
        self.current_longitude = longitude
        self.speed = speed
        self.heading = heading
        self.last_gps_update = timezone.now()
        self.save(update_fields=['current_latitude', 'current_longitude', 'speed', 'heading', 'last_gps_update'])

    def calculate_distance_to(self, latitude, longitude):
        """Calculate distance to a given point using Haversine formula"""
        if self.current_latitude and self.current_longitude:
            import math

            # Convert latitude and longitude from degrees to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [self.current_latitude, self.current_longitude, latitude, longitude])

            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))

            # Radius of earth in kilometers
            r = 6371
            return c * r
        return None


class AmbulanceStation(BaseModel):
    """Ambulance stations/bases"""
    name = models.CharField(_('Station Name'), max_length=100)
    code = models.CharField(_('Station Code'), max_length=10, unique=True)
    address = models.TextField(_('Address'))
    latitude = models.FloatField(_('Latitude'))
    longitude = models.FloatField(_('Longitude'))
    phone = models.CharField(_('Phone'), max_length=20)
    capacity = models.PositiveIntegerField(_('Ambulance Capacity'), default=5)
    is_24_hour = models.BooleanField(_('24 Hour Operation'), default=True)

    class Meta:
        verbose_name = _('Ambulance Station')
        verbose_name_plural = _('Ambulance Stations')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class AmbulanceCrew(BaseModel):
    """Ambulance crew assignments"""

    ROLE_CHOICES = [
        ('driver', _('Driver')),
        ('paramedic', _('Paramedic')),
        ('emt', _('EMT')),
        ('nurse', _('Nurse')),
        ('doctor', _('Doctor')),
    ]

    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE)
    crew_member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(_('Role'), max_length=20, choices=ROLE_CHOICES)
    shift_start = models.DateTimeField(_('Shift Start'))
    shift_end = models.DateTimeField(_('Shift End'))
    is_primary = models.BooleanField(_('Primary Assignment'), default=False)

    class Meta:
        verbose_name = _('Ambulance Crew')
        verbose_name_plural = _('Ambulance Crews')
        unique_together = ['ambulance', 'crew_member', 'shift_start']

    def __str__(self):
        return f"{self.crew_member} - {self.ambulance} ({self.role})"


class Dispatch(BaseModel):
    """Enhanced dispatch model with comprehensive tracking"""

    STATUS_CHOICES = [
        ('requested', _('Requested')),
        ('assigned', _('Assigned')),
        ('dispatched', _('Dispatched')),
        ('en_route_pickup', _('En Route to Pickup')),
        ('on_scene', _('On Scene')),
        ('patient_loaded', _('Patient Loaded')),
        ('en_route_hospital', _('En Route to Hospital')),
        ('at_hospital', _('At Hospital')),
        ('patient_delivered', _('Patient Delivered')),
        ('returning', _('Returning to Base')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
        ('failed', _('Failed')),
    ]

    PRIORITY_CHOICES = [
        ('routine', _('Routine')),
        ('urgent', _('Urgent')),
        ('emergency', _('Emergency')),
        ('critical', _('Critical')),
    ]

    # Core dispatch information
    dispatch_number = models.CharField(_('Dispatch Number'), max_length=20, unique=True)
    referral = models.ForeignKey('referrals.Referral', on_delete=models.CASCADE,
                               related_name='dispatches', verbose_name=_('Referral'))
    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE,
                                related_name='dispatches', verbose_name=_('Ambulance'))

    # Personnel
    primary_crew = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='DispatchCrew',
        related_name='dispatches',
        verbose_name=_('Dispatch Crew')
    )
    dispatcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='dispatched_calls',
        verbose_name=_('Dispatcher')
    )

    # Status and Priority
    status = models.CharField(_('Status'), max_length=25, choices=STATUS_CHOICES, default='requested')
    priority = models.CharField(_('Priority'), max_length=15, choices=PRIORITY_CHOICES, default='routine')

    # Location Information
    pickup_latitude = models.FloatField(_('Pickup Latitude'), null=True, blank=True)
    pickup_longitude = models.FloatField(_('Pickup Longitude'), null=True, blank=True)
    pickup_address = models.TextField(_('Pickup Address'))
    destination_latitude = models.FloatField(_('Destination Latitude'), null=True, blank=True)
    destination_longitude = models.FloatField(_('Destination Longitude'), null=True, blank=True)
    destination_address = models.TextField(_('Destination Address'))

    # Route and Navigation
    planned_route_data = models.JSONField(_('Planned Route Data'), null=True, blank=True)
    actual_route_data = models.JSONField(_('Actual Route Data'), null=True, blank=True)
    distance_km = models.FloatField(_('Distance (km)'), null=True, blank=True)

    # Timing
    requested_at = models.DateTimeField(_('Requested At'), auto_now_add=True)
    dispatched_at = models.DateTimeField(_('Dispatched At'), null=True, blank=True)
    en_route_at = models.DateTimeField(_('En Route At'), null=True, blank=True)
    on_scene_at = models.DateTimeField(_('On Scene At'), null=True, blank=True)
    patient_loaded_at = models.DateTimeField(_('Patient Loaded At'), null=True, blank=True)
    at_hospital_at = models.DateTimeField(_('At Hospital At'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)

    # Estimates
    estimated_pickup_time = models.DateTimeField(_('Estimated Pickup Time'), null=True, blank=True)
    estimated_arrival_time = models.DateTimeField(_('Estimated Arrival Time'), null=True, blank=True)

    # Medical Information
    patient_condition = models.TextField(_('Patient Condition'), blank=True)
    medical_equipment_used = models.JSONField(_('Medical Equipment Used'), default=list)
    vital_signs = models.JSONField(_('Vital Signs'), default=dict)
    medications_administered = models.JSONField(_('Medications Administered'), default=list)

    # Communication
    contact_person = models.CharField(_('Contact Person'), max_length=100, blank=True)
    contact_phone = models.CharField(_('Contact Phone'), max_length=20, blank=True)
    special_instructions = models.TextField(_('Special Instructions'), blank=True)

    # Quality and Feedback
    response_time_minutes = models.PositiveIntegerField(_('Response Time (minutes)'), null=True, blank=True)
    transport_time_minutes = models.PositiveIntegerField(_('Transport Time (minutes)'), null=True, blank=True)
    patient_satisfaction = models.PositiveIntegerField(
        _('Patient Satisfaction'),
        null=True,
        blank=True,
        choices=[(i, i) for i in range(1, 6)]
    )

    # Administrative
    billing_code = models.CharField(_('Billing Code'), max_length=50, blank=True)
    insurance_authorization = models.CharField(_('Insurance Authorization'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('Dispatch')
        verbose_name_plural = _('Dispatches')
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['ambulance', 'status']),
            models.Index(fields=['requested_at', 'status']),
            models.Index(fields=['dispatch_number']),
        ]

    def save(self, *args, **kwargs):
        # Generate dispatch number if not set
        if not self.dispatch_number:
            from django.utils.crypto import get_random_string
            self.dispatch_number = f"DISP-{timezone.now().strftime('%Y%m%d')}-{get_random_string(6, '0123456789')}"

        # Auto-calculate response time
        if self.dispatched_at and self.on_scene_at:
            self.response_time_minutes = int((self.on_scene_at - self.dispatched_at).total_seconds() / 60)

        # Auto-calculate transport time
        if self.patient_loaded_at and self.at_hospital_at:
            self.transport_time_minutes = int((self.at_hospital_at - self.patient_loaded_at).total_seconds() / 60)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.dispatch_number} - {self.ambulance} ({self.get_status_display()})"

    @property
    def total_time(self):
        if self.completed_at and self.requested_at:
            return self.completed_at - self.requested_at
        return None

    @property
    def is_active(self):
        return self.status not in ['completed', 'cancelled', 'failed']

    @property
    def is_emergency(self):
        return self.priority in ['emergency', 'critical']

    def update_status(self, new_status, user=None):
        """Update dispatch status with automatic timestamp setting"""
        old_status = self.status
        self.status = new_status

        # Set appropriate timestamps
        now = timezone.now()
        if new_status == 'dispatched':
            self.dispatched_at = now
        elif new_status == 'en_route_pickup':
            self.en_route_at = now
        elif new_status == 'on_scene':
            self.on_scene_at = now
        elif new_status == 'patient_loaded':
            self.patient_loaded_at = now
        elif new_status == 'at_hospital':
            self.at_hospital_at = now
        elif new_status == 'completed':
            self.completed_at = now

        self.save()

        # Create status history record
        DispatchStatusHistory.objects.create(
            dispatch=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=user,
            timestamp=now
        )


class DispatchCrew(BaseModel):
    """Crew assignments for specific dispatches"""
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE)
    crew_member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(_('Role'), max_length=20, choices=AmbulanceCrew.ROLE_CHOICES)
    is_lead = models.BooleanField(_('Lead Crew Member'), default=False)

    class Meta:
        verbose_name = _('Dispatch Crew')
        verbose_name_plural = _('Dispatch Crews')
        unique_together = ['dispatch', 'crew_member']

    def __str__(self):
        return f"{self.crew_member} - {self.dispatch} ({self.role})"


class DispatchStatusHistory(BaseModel):
    """Track status changes for dispatches"""
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(_('Old Status'), max_length=25, choices=Dispatch.STATUS_CHOICES)
    new_status = models.CharField(_('New Status'), max_length=25, choices=Dispatch.STATUS_CHOICES)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)
    notes = models.TextField(_('Notes'), blank=True)

    class Meta:
        verbose_name = _('Dispatch Status History')
        verbose_name_plural = _('Dispatch Status Histories')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.dispatch.dispatch_number} - {self.old_status} to {self.new_status}"


class GPSTrackingLog(BaseModel):
    """GPS tracking history for ambulances"""
    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE, related_name='gps_logs')
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE, null=True, blank=True, related_name='gps_logs')
    latitude = models.FloatField(_('Latitude'))
    longitude = models.FloatField(_('Longitude'))
    speed = models.FloatField(_('Speed (km/h)'), default=0.0)
    heading = models.FloatField(_('Heading (degrees)'), default=0.0)
    altitude = models.FloatField(_('Altitude (m)'), null=True, blank=True)
    accuracy = models.FloatField(_('GPS Accuracy (m)'), null=True, blank=True)
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)

    class Meta:
        verbose_name = _('GPS Tracking Log')
        verbose_name_plural = _('GPS Tracking Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ambulance', 'timestamp']),
            models.Index(fields=['dispatch', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.ambulance} - {self.timestamp}"


class MaintenanceRecord(BaseModel):
    """Ambulance maintenance records"""

    MAINTENANCE_TYPES = [
        ('routine', _('Routine Maintenance')),
        ('repair', _('Repair')),
        ('inspection', _('Inspection')),
        ('emergency', _('Emergency Repair')),
        ('upgrade', _('Equipment Upgrade')),
    ]

    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_type = models.CharField(_('Maintenance Type'), max_length=20, choices=MAINTENANCE_TYPES)
    description = models.TextField(_('Description'))
    performed_by = models.CharField(_('Performed By'), max_length=100)
    cost = models.DecimalField(_('Cost'), max_digits=10, decimal_places=2, null=True, blank=True)
    parts_replaced = models.JSONField(_('Parts Replaced'), default=list)
    mileage_at_service = models.PositiveIntegerField(_('Mileage at Service'))
    next_service_mileage = models.PositiveIntegerField(_('Next Service Mileage'), null=True, blank=True)
    service_date = models.DateTimeField(_('Service Date'))
    next_service_date = models.DateTimeField(_('Next Service Date'), null=True, blank=True)

    class Meta:
        verbose_name = _('Maintenance Record')
        verbose_name_plural = _('Maintenance Records')
        ordering = ['-service_date']

    def __str__(self):
        return f"{self.ambulance} - {self.get_maintenance_type_display()} ({self.service_date.date()})"


class EquipmentInventory(BaseModel):
    """Equipment inventory for ambulances"""

    CONDITION_CHOICES = [
        ('new', _('New')),
        ('excellent', _('Excellent')),
        ('good', _('Good')),
        ('fair', _('Fair')),
        ('poor', _('Poor')),
        ('defective', _('Defective')),
    ]

    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE, related_name='equipment_inventory')
    equipment_name = models.CharField(_('Equipment Name'), max_length=100)
    equipment_code = models.CharField(_('Equipment Code'), max_length=50, blank=True)
    category = models.CharField(_('Category'), max_length=50)
    quantity = models.PositiveIntegerField(_('Quantity'), default=1)
    condition = models.CharField(_('Condition'), max_length=15, choices=CONDITION_CHOICES, default='good')
    serial_number = models.CharField(_('Serial Number'), max_length=100, blank=True)
    expiry_date = models.DateField(_('Expiry Date'), null=True, blank=True)
    last_checked = models.DateTimeField(_('Last Checked'), null=True, blank=True)
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(_('Notes'), blank=True)

    class Meta:
        verbose_name = _('Equipment Inventory')
        verbose_name_plural = _('Equipment Inventories')
        unique_together = ['ambulance', 'equipment_name', 'serial_number']

    def __str__(self):
        return f"{self.ambulance} - {self.equipment_name}"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date <= timezone.now().date()
        return False

    @property
    def needs_check(self):
        if self.last_checked:
            return self.last_checked <= timezone.now() - timedelta(days=30)
        return True


class FuelLog(BaseModel):
    """Fuel consumption tracking"""
    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE, related_name='fuel_logs')
    fuel_amount = models.FloatField(_('Fuel Amount (L)'))
    cost = models.DecimalField(_('Cost'), max_digits=8, decimal_places=2)
    mileage = models.PositiveIntegerField(_('Mileage'))
    fuel_station = models.CharField(_('Fuel Station'), max_length=100, blank=True)
    filled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    receipt_number = models.CharField(_('Receipt Number'), max_length=50, blank=True)

    class Meta:
        verbose_name = _('Fuel Log')
        verbose_name_plural = _('Fuel Logs')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ambulance} - {self.fuel_amount}L ({self.created_at.date()})"


class IncidentReport(BaseModel):
    """Incident reports for ambulances and dispatches"""

    INCIDENT_TYPES = [
        ('accident', _('Traffic Accident')),
        ('mechanical', _('Mechanical Failure')),
        ('medical', _('Medical Emergency')),
        ('equipment', _('Equipment Failure')),
        ('personnel', _('Personnel Issue')),
        ('patient', _('Patient Incident')),
        ('other', _('Other')),
    ]

    SEVERITY_LEVELS = [
        ('minor', _('Minor')),
        ('moderate', _('Moderate')),
        ('major', _('Major')),
        ('critical', _('Critical')),
    ]

    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE, related_name='incident_reports')
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE, null=True, blank=True, related_name='incident_reports')
    incident_type = models.CharField(_('Incident Type'), max_length=20, choices=INCIDENT_TYPES)
    severity = models.CharField(_('Severity'), max_length=15, choices=SEVERITY_LEVELS)
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    incident_latitude = models.FloatField(_('Incident Latitude'), null=True, blank=True)
    incident_longitude = models.FloatField(_('Incident Longitude'), null=True, blank=True)
    location_description = models.CharField(_('Location Description'), max_length=255, blank=True)
    incident_time = models.DateTimeField(_('Incident Time'))
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_incidents')
    witnesses = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='witnessed_incidents')
    injuries = models.BooleanField(_('Injuries Involved'), default=False)
    property_damage = models.BooleanField(_('Property Damage'), default=False)
    police_involved = models.BooleanField(_('Police Involved'), default=False)
    police_report_number = models.CharField(_('Police Report Number'), max_length=50, blank=True)
    insurance_claim = models.CharField(_('Insurance Claim Number'), max_length=50, blank=True)
    follow_up_required = models.BooleanField(_('Follow-up Required'), default=False)
    resolved = models.BooleanField(_('Resolved'), default=False)
    resolution_notes = models.TextField(_('Resolution Notes'), blank=True)

    class Meta:
        verbose_name = _('Incident Report')
        verbose_name_plural = _('Incident Reports')
        ordering = ['-incident_time']

    def __str__(self):
        return f"{self.ambulance} - {self.title} ({self.incident_time.date()})"


class PerformanceMetrics(BaseModel):
    """Performance metrics for ambulances and crews"""
    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE, related_name='performance_metrics')
    date = models.DateField(_('Date'))

    # Response metrics
    total_dispatches = models.PositiveIntegerField(_('Total Dispatches'), default=0)
    completed_dispatches = models.PositiveIntegerField(_('Completed Dispatches'), default=0)
    cancelled_dispatches = models.PositiveIntegerField(_('Cancelled Dispatches'), default=0)
    average_response_time = models.DurationField(_('Average Response Time'), null=True, blank=True)

    # Operational metrics
    total_distance = models.FloatField(_('Total Distance (km)'), default=0.0)
    fuel_consumed = models.FloatField(_('Fuel Consumed (L)'), default=0.0)
    operational_hours = models.FloatField(_('Operational Hours'), default=0.0)
    downtime_hours = models.FloatField(_('Downtime Hours'), default=0.0)

    # Quality metrics
    patient_satisfaction_avg = models.FloatField(_('Average Patient Satisfaction'), null=True, blank=True)
    incident_count = models.PositiveIntegerField(_('Incident Count'), default=0)

    class Meta:
        verbose_name = _('Performance Metrics')
        verbose_name_plural = _('Performance Metrics')
        unique_together = ['ambulance', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.ambulance} - {self.date}"


# ============================================================================
# EMERGENCY CALL MANAGEMENT MODELS
# ============================================================================

class EmergencyCall(BaseModel):
    """
    Emergency call intake and management model
    Handles all aspects of emergency call processing
    """

    CALL_TYPE_CHOICES = [
        ('medical', _('Medical Emergency')),
        ('trauma', _('Trauma/Accident')),
        ('cardiac', _('Cardiac Emergency')),
        ('respiratory', _('Respiratory Emergency')),
        ('psychiatric', _('Psychiatric Emergency')),
        ('obstetric', _('Obstetric Emergency')),
        ('pediatric', _('Pediatric Emergency')),
        ('overdose', _('Drug Overdose')),
        ('burn', _('Burn Injury')),
        ('poisoning', _('Poisoning')),
        ('other', _('Other Emergency')),
    ]

    PRIORITY_CHOICES = [
        ('critical', _('Critical - Life Threatening')),
        ('emergency', _('Emergency - Urgent')),
        ('urgent', _('Urgent - Non-Life Threatening')),
        ('routine', _('Routine Transport')),
    ]

    STATUS_CHOICES = [
        ('received', _('Call Received')),
        ('processing', _('Processing')),
        ('dispatched', _('Ambulance Dispatched')),
        ('completed', _('Call Completed')),
        ('cancelled', _('Call Cancelled')),
        ('transferred', _('Transferred to Other Agency')),
    ]

    CONSCIOUSNESS_CHOICES = [
        ('conscious', _('Conscious and Alert')),
        ('drowsy', _('Drowsy/Confused')),
        ('unconscious', _('Unconscious')),
        ('unknown', _('Unknown')),
    ]

    BREATHING_CHOICES = [
        ('normal', _('Normal Breathing')),
        ('difficulty', _('Difficulty Breathing')),
        ('not_breathing', _('Not Breathing')),
        ('unknown', _('Unknown')),
    ]

    # Core Call Information
    call_number = models.CharField(_('Call Number'), max_length=20, unique=True)
    received_at = models.DateTimeField(_('Call Received At'), auto_now_add=True)
    caller_phone = models.CharField(
        _('Caller Phone'),
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Invalid phone number')]
    )
    caller_name = models.CharField(_('Caller Name'), max_length=100, blank=True)
    caller_relationship = models.CharField(_('Relationship to Patient'), max_length=50, blank=True)

    # Emergency Details
    call_type = models.CharField(_('Call Type'), max_length=20, choices=CALL_TYPE_CHOICES)
    priority = models.CharField(_('Priority Level'), max_length=20, choices=PRIORITY_CHOICES)
    status = models.CharField(_('Call Status'), max_length=20, choices=STATUS_CHOICES, default='received')

    # Location Information
    incident_address = models.TextField(_('Incident Address'))
    # incident_location = gis_models.PointField(_('Incident Location'), null=True, blank=True)
    landmark_description = models.TextField(_('Landmark Description'), blank=True)
    access_instructions = models.TextField(_('Access Instructions'), blank=True)

    # Patient Information
    patient_name = models.CharField(_('Patient Name'), max_length=100, blank=True)
    patient_age = models.PositiveIntegerField(
        _('Patient Age'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(150)]
    )
    patient_gender = models.CharField(
        _('Patient Gender'),
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other'), ('unknown', 'Unknown')],
        blank=True
    )
    patient_consciousness = models.CharField(
        _('Consciousness Level'),
        max_length=20,
        choices=CONSCIOUSNESS_CHOICES,
        blank=True
    )
    patient_breathing = models.CharField(
        _('Breathing Status'),
        max_length=20,
        choices=BREATHING_CHOICES,
        blank=True
    )

    # Medical Information
    chief_complaint = models.TextField(_('Chief Complaint'))
    symptoms_description = models.TextField(_('Symptoms Description'), blank=True)
    medical_history = models.TextField(_('Relevant Medical History'), blank=True)
    medications = models.TextField(_('Current Medications'), blank=True)
    allergies = models.TextField(_('Known Allergies'), blank=True)

    # Call Processing
    call_taker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='emergency_calls_taken',
        verbose_name=_('Call Taker')
    )
    dispatcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emergency_calls_dispatched',
        verbose_name=_('Dispatcher')
    )

    # Timing Information
    call_duration_seconds = models.PositiveIntegerField(_('Call Duration (seconds)'), null=True, blank=True)
    dispatch_time = models.DateTimeField(_('Dispatch Time'), null=True, blank=True)
    response_time_target = models.PositiveIntegerField(_('Response Time Target (minutes)'), default=8)

    # Additional Information
    special_instructions = models.TextField(_('Special Instructions'), blank=True)
    hazards_present = models.BooleanField(_('Hazards Present'), default=False)
    hazard_description = models.TextField(_('Hazard Description'), blank=True)
    police_required = models.BooleanField(_('Police Required'), default=False)
    fire_required = models.BooleanField(_('Fire Department Required'), default=False)

    # Call Recording
    call_recording_url = models.URLField(_('Call Recording URL'), blank=True)
    call_notes = models.TextField(_('Call Notes'), blank=True)

    class Meta:
        verbose_name = _('Emergency Call')
        verbose_name_plural = _('Emergency Calls')
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['call_number']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['received_at']),
            models.Index(fields=['caller_phone']),
        ]

    def save(self, *args, **kwargs):
        # Generate call number if not set
        if not self.call_number:
            today = timezone.now().strftime('%Y%m%d')
            from django.utils.crypto import get_random_string
            self.call_number = f"EC-{today}-{get_random_string(6, '0123456789')}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.call_number} - {self.get_call_type_display()} ({self.get_priority_display()})"

    def get_absolute_url(self):
        return reverse('ambulances:emergency_call_detail', kwargs={'pk': self.pk})

    @property
    def response_time_elapsed(self):
        """Calculate elapsed time since call received"""
        if self.status in ['completed', 'cancelled']:
            return None
        return (timezone.now() - self.received_at).total_seconds() / 60

    @property
    def is_overdue(self):
        """Check if response time target has been exceeded"""
        elapsed = self.response_time_elapsed
        return elapsed and elapsed > self.response_time_target

    @property
    def priority_color(self):
        """Get color code for priority level"""
        colors = {
            'critical': '#dc2626',  # Red
            'emergency': '#ea580c',  # Orange
            'urgent': '#d97706',     # Amber
            'routine': '#059669',    # Green
        }
        return colors.get(self.priority, '#6b7280')


class CallStatusHistory(BaseModel):
    """Track status changes for emergency calls"""

    emergency_call = models.ForeignKey(
        EmergencyCall,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(_('Previous Status'), max_length=20)
    new_status = models.CharField(_('New Status'), max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Changed By')
    )
    timestamp = models.DateTimeField(_('Changed At'), auto_now_add=True)
    notes = models.TextField(_('Change Notes'), blank=True)

    class Meta:
        verbose_name = _('Call Status History')
        verbose_name_plural = _('Call Status Histories')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.emergency_call.call_number}: {self.old_status} → {self.new_status}"


class CallPriorityAssessment(BaseModel):
    """Detailed priority assessment for emergency calls"""

    emergency_call = models.OneToOneField(
        EmergencyCall,
        on_delete=models.CASCADE,
        related_name='priority_assessment'
    )

    # Assessment Questions
    chest_pain = models.BooleanField(_('Chest Pain'), default=False)
    difficulty_breathing = models.BooleanField(_('Difficulty Breathing'), default=False)
    unconscious = models.BooleanField(_('Unconscious'), default=False)
    severe_bleeding = models.BooleanField(_('Severe Bleeding'), default=False)
    cardiac_arrest = models.BooleanField(_('Cardiac Arrest'), default=False)
    stroke_symptoms = models.BooleanField(_('Stroke Symptoms'), default=False)
    severe_trauma = models.BooleanField(_('Severe Trauma'), default=False)
    overdose = models.BooleanField(_('Drug Overdose'), default=False)
    allergic_reaction = models.BooleanField(_('Severe Allergic Reaction'), default=False)
    pregnancy_complications = models.BooleanField(_('Pregnancy Complications'), default=False)

    # Assessment Results
    calculated_priority = models.CharField(_('Calculated Priority'), max_length=20)
    priority_score = models.PositiveIntegerField(_('Priority Score'), default=0)
    assessment_notes = models.TextField(_('Assessment Notes'), blank=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Assessed By')
    )
    assessed_at = models.DateTimeField(_('Assessed At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Call Priority Assessment')
        verbose_name_plural = _('Call Priority Assessments')

    def calculate_priority(self):
        """Calculate priority based on assessment criteria"""
        # Critical conditions
        if any([self.cardiac_arrest, self.unconscious and self.difficulty_breathing]):
            return 'critical'

        # Emergency conditions
        if any([self.chest_pain, self.severe_bleeding, self.stroke_symptoms,
                self.severe_trauma, self.allergic_reaction]):
            return 'emergency'

        # Urgent conditions
        if any([self.difficulty_breathing, self.overdose, self.pregnancy_complications]):
            return 'urgent'

        # Default to routine
        return 'routine'

    def save(self, *args, **kwargs):
        # Auto-calculate priority if not set
        if not self.calculated_priority:
            self.calculated_priority = self.calculate_priority()

        # Calculate priority score
        score = 0
        critical_conditions = [
            self.cardiac_arrest, self.unconscious and self.difficulty_breathing
        ]
        emergency_conditions = [
            self.chest_pain, self.severe_bleeding, self.stroke_symptoms,
            self.severe_trauma, self.allergic_reaction
        ]
        urgent_conditions = [
            self.difficulty_breathing, self.overdose, self.pregnancy_complications
        ]

        score += sum(critical_conditions) * 50
        score += sum(emergency_conditions) * 30
        score += sum(urgent_conditions) * 20

        self.priority_score = score

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.emergency_call.call_number} - {self.calculated_priority} (Score: {self.priority_score})"


# ============================================================================
# REAL-TIME GPS TRACKING & ROUTING MODELS
# ============================================================================

class RouteOptimization(BaseModel):
    """Route optimization and traffic integration"""

    ROUTE_TYPE_CHOICES = [
        ('fastest', _('Fastest Route')),
        ('shortest', _('Shortest Route')),
        ('avoid_traffic', _('Avoid Traffic')),
        ('emergency', _('Emergency Route')),
    ]

    dispatch = models.ForeignKey(
        'Dispatch',
        on_delete=models.CASCADE,
        related_name='route_optimizations'
    )
    origin_latitude = models.FloatField(_('Origin Latitude'))
    origin_longitude = models.FloatField(_('Origin Longitude'))
    destination_latitude = models.FloatField(_('Destination Latitude'))
    destination_longitude = models.FloatField(_('Destination Longitude'))

    # Route Information
    route_type = models.CharField(_('Route Type'), max_length=20, choices=ROUTE_TYPE_CHOICES, default='emergency')
    total_distance_km = models.FloatField(_('Total Distance (km)'), null=True, blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(_('Estimated Duration (minutes)'), null=True, blank=True)
    traffic_delay_minutes = models.PositiveIntegerField(_('Traffic Delay (minutes)'), default=0)

    # Route Data
    route_polyline = models.TextField(_('Route Polyline'), blank=True)  # Encoded polyline
    waypoints = models.JSONField(_('Waypoints'), default=list)
    traffic_conditions = models.JSONField(_('Traffic Conditions'), default=dict)

    # Optimization Results
    alternative_routes = models.JSONField(_('Alternative Routes'), default=list)
    optimization_score = models.FloatField(_('Optimization Score'), default=0.0)
    last_updated = models.DateTimeField(_('Last Updated'), auto_now=True)

    class Meta:
        verbose_name = _('Route Optimization')
        verbose_name_plural = _('Route Optimizations')
        ordering = ['-created_at']

    def calculate_eta(self):
        """Calculate estimated time of arrival"""
        if self.estimated_duration_minutes:
            from django.utils import timezone
            return timezone.now() + timedelta(minutes=self.estimated_duration_minutes + self.traffic_delay_minutes)
        return None

    @property
    def eta(self):
        return self.calculate_eta()

    def __str__(self):
        return f"Route for {self.dispatch} - {self.route_type} ({self.estimated_duration_minutes}min)"


class GPSTrackingEnhanced(BaseModel):
    """Enhanced GPS tracking with additional metadata"""

    ambulance = models.ForeignKey(
        'Ambulance',
        on_delete=models.CASCADE,
        related_name='gps_tracking_enhanced'
    )
    dispatch = models.ForeignKey(
        'Dispatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gps_tracking_enhanced'
    )

    # Location Data
    latitude = models.FloatField(_('Latitude'))
    longitude = models.FloatField(_('Longitude'))
    altitude = models.FloatField(_('Altitude (meters)'), null=True, blank=True)
    accuracy = models.FloatField(_('GPS Accuracy (meters)'), null=True, blank=True)

    # Movement Data
    speed_kmh = models.FloatField(_('Speed (km/h)'), default=0.0)
    heading_degrees = models.FloatField(_('Heading (degrees)'), null=True, blank=True)
    acceleration = models.FloatField(_('Acceleration (m/s²)'), null=True, blank=True)

    # Status Information
    engine_status = models.BooleanField(_('Engine On'), default=True)
    emergency_lights = models.BooleanField(_('Emergency Lights'), default=False)
    siren_active = models.BooleanField(_('Siren Active'), default=False)

    # Route Progress
    distance_to_destination_km = models.FloatField(_('Distance to Destination (km)'), null=True, blank=True)
    eta_minutes = models.PositiveIntegerField(_('ETA (minutes)'), null=True, blank=True)
    route_deviation_meters = models.FloatField(_('Route Deviation (meters)'), default=0.0)

    # Data Quality
    signal_strength = models.PositiveIntegerField(_('GPS Signal Strength'), null=True, blank=True)
    battery_level = models.PositiveIntegerField(_('Device Battery Level'), null=True, blank=True)
    data_source = models.CharField(_('Data Source'), max_length=50, default='mobile_app')

    # Geofencing
    in_service_area = models.BooleanField(_('In Service Area'), default=True)
    near_hospital = models.BooleanField(_('Near Hospital'), default=False)
    at_pickup_location = models.BooleanField(_('At Pickup Location'), default=False)

    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)

    class Meta:
        verbose_name = _('Enhanced GPS Tracking')
        verbose_name_plural = _('Enhanced GPS Tracking')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ambulance', '-timestamp']),
            models.Index(fields=['dispatch', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def calculate_distance_traveled(self, previous_point=None):
        """Calculate distance traveled from previous GPS point"""
        if not previous_point:
            previous_point = GPSTrackingEnhanced.objects.filter(
                ambulance=self.ambulance,
                timestamp__lt=self.timestamp
            ).first()

        if previous_point:
            import math

            # Haversine formula for distance calculation
            lat1, lon1 = math.radians(previous_point.latitude), math.radians(previous_point.longitude)
            lat2, lon2 = math.radians(self.latitude), math.radians(self.longitude)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))

            # Earth's radius in kilometers
            r = 6371

            return r * c
        return 0.0

    def __str__(self):
        return f"{self.ambulance} GPS at {self.timestamp.strftime('%H:%M:%S')} - {self.speed_kmh}km/h"


class GeofenceZone(BaseModel):
    """Geofencing zones for automatic status updates"""

    ZONE_TYPE_CHOICES = [
        ('hospital', _('Hospital Zone')),
        ('station', _('Ambulance Station')),
        ('service_area', _('Service Area')),
        ('restricted', _('Restricted Zone')),
        ('pickup_zone', _('Pickup Zone')),
        ('emergency_zone', _('Emergency Zone')),
    ]

    name = models.CharField(_('Zone Name'), max_length=100)
    zone_type = models.CharField(_('Zone Type'), max_length=20, choices=ZONE_TYPE_CHOICES)
    description = models.TextField(_('Description'), blank=True)

    # Zone Boundaries (simplified as center + radius for now)
    center_latitude = models.FloatField(_('Center Latitude'))
    center_longitude = models.FloatField(_('Center Longitude'))
    radius_meters = models.PositiveIntegerField(_('Radius (meters)'), default=100)

    # Zone Properties
    auto_status_change = models.BooleanField(_('Auto Status Change'), default=False)
    target_status = models.CharField(_('Target Status'), max_length=20, blank=True)
    notification_enabled = models.BooleanField(_('Notification Enabled'), default=True)

    # Associated Objects
    hospital = models.ForeignKey(
        'doctors.Hospital',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='geofence_zones'
    )
    ambulance_station = models.ForeignKey(
        'AmbulanceStation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='geofence_zones'
    )

    class Meta:
        verbose_name = _('Geofence Zone')
        verbose_name_plural = _('Geofence Zones')
        ordering = ['name']

    def is_point_inside(self, latitude, longitude):
        """Check if a GPS point is inside this geofence zone"""
        import math

        # Calculate distance from center
        lat1, lon1 = math.radians(self.center_latitude), math.radians(self.center_longitude)
        lat2, lon2 = math.radians(latitude), math.radians(longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in meters
        r = 6371000
        distance_meters = r * c

        return distance_meters <= self.radius_meters

    def __str__(self):
        return f"{self.name} ({self.get_zone_type_display()})"


class TrafficCondition(BaseModel):
    """Real-time traffic conditions for route optimization"""

    SEVERITY_CHOICES = [
        ('light', _('Light Traffic')),
        ('moderate', _('Moderate Traffic')),
        ('heavy', _('Heavy Traffic')),
        ('severe', _('Severe Traffic')),
        ('blocked', _('Road Blocked')),
    ]

    CONDITION_TYPE_CHOICES = [
        ('traffic', _('Traffic Congestion')),
        ('accident', _('Accident')),
        ('construction', _('Construction')),
        ('weather', _('Weather Condition')),
        ('event', _('Special Event')),
        ('emergency', _('Emergency Situation')),
    ]

    # Location
    latitude = models.FloatField(_('Latitude'))
    longitude = models.FloatField(_('Longitude'))
    radius_meters = models.PositiveIntegerField(_('Affected Radius (meters)'), default=500)

    # Condition Details
    condition_type = models.CharField(_('Condition Type'), max_length=20, choices=CONDITION_TYPE_CHOICES)
    severity = models.CharField(_('Severity'), max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField(_('Description'))

    # Impact
    speed_reduction_percent = models.PositiveIntegerField(_('Speed Reduction (%)'), default=0)
    delay_minutes = models.PositiveIntegerField(_('Expected Delay (minutes)'), default=0)

    # Timing
    start_time = models.DateTimeField(_('Start Time'), auto_now_add=True)
    estimated_end_time = models.DateTimeField(_('Estimated End Time'), null=True, blank=True)
    last_updated = models.DateTimeField(_('Last Updated'), auto_now=True)

    # Data Source
    data_source = models.CharField(_('Data Source'), max_length=100, default='manual')
    confidence_score = models.FloatField(_('Confidence Score'), default=1.0)

    class Meta:
        verbose_name = _('Traffic Condition')
        verbose_name_plural = _('Traffic Conditions')
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['condition_type', 'severity']),
            models.Index(fields=['start_time']),
        ]

    @property
    def is_active(self):
        """Check if traffic condition is currently active"""
        from django.utils import timezone
        now = timezone.now()

        if self.estimated_end_time:
            return now < self.estimated_end_time

        # If no end time, consider active for 2 hours by default
        return (now - self.start_time).total_seconds() < 7200

    def affects_route(self, route_points):
        """Check if this traffic condition affects a given route"""
        import math

        for point in route_points:
            lat, lon = point['lat'], point['lng']

            # Calculate distance from traffic condition
            lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
            lat2, lon2 = math.radians(lat), math.radians(lon)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))

            distance_meters = 6371000 * c

            if distance_meters <= self.radius_meters:
                return True

        return False

    def __str__(self):
        return f"{self.get_condition_type_display()} - {self.get_severity_display()} at {self.latitude}, {self.longitude}"