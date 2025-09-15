"""
Hospital Integration Models
Comprehensive hospital capacity management, bed tracking, and ED status monitoring
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta

User = get_user_model()


class BaseModel(models.Model):
    """Base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class HospitalCapacity(BaseModel):
    """Real-time hospital capacity tracking"""
    
    CAPACITY_STATUS_CHOICES = [
        ('normal', _('Normal Capacity')),
        ('busy', _('Busy')),
        ('critical', _('Critical Capacity')),
        ('full', _('At Capacity')),
        ('closed', _('Closed to Admissions')),
        ('disaster', _('Disaster Mode')),
    ]
    
    hospital = models.OneToOneField(
        'doctors.Hospital',
        on_delete=models.CASCADE,
        related_name='capacity_status'
    )
    
    # Overall Status
    overall_status = models.CharField(
        _('Overall Status'), 
        max_length=20, 
        choices=CAPACITY_STATUS_CHOICES,
        default='normal'
    )
    last_updated = models.DateTimeField(_('Last Updated'), auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Updated By')
    )
    
    # Bed Capacity
    total_beds = models.PositiveIntegerField(_('Total Beds'), default=0)
    occupied_beds = models.PositiveIntegerField(_('Occupied Beds'), default=0)
    available_beds = models.PositiveIntegerField(_('Available Beds'), default=0)
    reserved_beds = models.PositiveIntegerField(_('Reserved Beds'), default=0)
    
    # Emergency Department
    ed_status = models.CharField(
        _('ED Status'),
        max_length=20,
        choices=CAPACITY_STATUS_CHOICES,
        default='normal'
    )
    ed_wait_time_minutes = models.PositiveIntegerField(_('ED Wait Time (minutes)'), default=0)
    ed_patients_waiting = models.PositiveIntegerField(_('ED Patients Waiting'), default=0)
    
    # Specialty Units
    icu_beds_available = models.PositiveIntegerField(_('ICU Beds Available'), default=0)
    icu_beds_total = models.PositiveIntegerField(_('ICU Beds Total'), default=0)
    or_rooms_available = models.PositiveIntegerField(_('OR Rooms Available'), default=0)
    or_rooms_total = models.PositiveIntegerField(_('OR Rooms Total'), default=0)
    
    # Staffing
    doctors_on_duty = models.PositiveIntegerField(_('Doctors on Duty'), default=0)
    nurses_on_duty = models.PositiveIntegerField(_('Nurses on Duty'), default=0)
    staff_shortage = models.BooleanField(_('Staff Shortage'), default=False)
    
    # Equipment
    ventilators_available = models.PositiveIntegerField(_('Ventilators Available'), default=0)
    ventilators_total = models.PositiveIntegerField(_('Ventilators Total'), default=0)
    
    # Ambulance Diversion
    ambulance_diversion = models.BooleanField(_('Ambulance Diversion'), default=False)
    diversion_reason = models.TextField(_('Diversion Reason'), blank=True)
    diversion_until = models.DateTimeField(_('Diversion Until'), null=True, blank=True)
    
    # Notes
    capacity_notes = models.TextField(_('Capacity Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Hospital Capacity')
        verbose_name_plural = _('Hospital Capacities')
        ordering = ['hospital__name']
    
    @property
    def bed_occupancy_rate(self):
        """Calculate bed occupancy rate as percentage"""
        if self.total_beds > 0:
            return (self.occupied_beds / self.total_beds) * 100
        return 0
    
    @property
    def icu_occupancy_rate(self):
        """Calculate ICU occupancy rate as percentage"""
        if self.icu_beds_total > 0:
            occupied_icu = self.icu_beds_total - self.icu_beds_available
            return (occupied_icu / self.icu_beds_total) * 100
        return 0
    
    @property
    def can_accept_patients(self):
        """Check if hospital can accept new patients"""
        return (
            not self.ambulance_diversion and
            self.overall_status not in ['full', 'closed'] and
            self.available_beds > 0
        )
    
    @property
    def capacity_color(self):
        """Get color code for capacity status"""
        colors = {
            'normal': '#10b981',    # Green
            'busy': '#f59e0b',      # Yellow
            'critical': '#ef4444',  # Red
            'full': '#dc2626',      # Dark Red
            'closed': '#6b7280',    # Gray
            'disaster': '#7c2d12',  # Dark Red
        }
        return colors.get(self.overall_status, '#6b7280')
    
    def update_capacity(self, **kwargs):
        """Update capacity with automatic status calculation"""
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        
        # Auto-calculate available beds
        self.available_beds = max(0, self.total_beds - self.occupied_beds - self.reserved_beds)
        
        # Auto-update overall status based on occupancy
        occupancy_rate = self.bed_occupancy_rate
        if occupancy_rate >= 95:
            self.overall_status = 'full'
        elif occupancy_rate >= 85:
            self.overall_status = 'critical'
        elif occupancy_rate >= 70:
            self.overall_status = 'busy'
        else:
            self.overall_status = 'normal'
        
        self.save()
    
    def __str__(self):
        return f"{self.hospital.name} - {self.get_overall_status_display()}"


class BedManagement(BaseModel):
    """Individual bed tracking and management"""
    
    BED_TYPE_CHOICES = [
        ('general', _('General Ward')),
        ('icu', _('Intensive Care Unit')),
        ('ccu', _('Cardiac Care Unit')),
        ('nicu', _('Neonatal ICU')),
        ('picu', _('Pediatric ICU')),
        ('or', _('Operating Room')),
        ('er', _('Emergency Room')),
        ('maternity', _('Maternity')),
        ('isolation', _('Isolation')),
        ('psychiatric', _('Psychiatric')),
    ]
    
    BED_STATUS_CHOICES = [
        ('available', _('Available')),
        ('occupied', _('Occupied')),
        ('reserved', _('Reserved')),
        ('maintenance', _('Under Maintenance')),
        ('cleaning', _('Being Cleaned')),
        ('blocked', _('Blocked')),
    ]
    
    hospital = models.ForeignKey(
        'doctors.Hospital',
        on_delete=models.CASCADE,
        related_name='beds'
    )
    
    # Bed Information
    bed_number = models.CharField(_('Bed Number'), max_length=20)
    bed_type = models.CharField(_('Bed Type'), max_length=20, choices=BED_TYPE_CHOICES)
    ward_name = models.CharField(_('Ward Name'), max_length=100)
    room_number = models.CharField(_('Room Number'), max_length=20, blank=True)
    
    # Status
    status = models.CharField(_('Status'), max_length=20, choices=BED_STATUS_CHOICES, default='available')
    last_status_change = models.DateTimeField(_('Last Status Change'), auto_now=True)
    
    # Patient Information (if occupied)
    patient_name = models.CharField(_('Patient Name'), max_length=100, blank=True)
    patient_id = models.CharField(_('Patient ID'), max_length=50, blank=True)
    admission_date = models.DateTimeField(_('Admission Date'), null=True, blank=True)
    expected_discharge = models.DateTimeField(_('Expected Discharge'), null=True, blank=True)
    
    # Equipment
    has_ventilator = models.BooleanField(_('Has Ventilator'), default=False)
    has_monitor = models.BooleanField(_('Has Monitor'), default=False)
    has_oxygen = models.BooleanField(_('Has Oxygen'), default=False)
    
    # Maintenance
    last_cleaned = models.DateTimeField(_('Last Cleaned'), null=True, blank=True)
    maintenance_notes = models.TextField(_('Maintenance Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Bed Management')
        verbose_name_plural = _('Bed Management')
        ordering = ['hospital', 'ward_name', 'bed_number']
        unique_together = ['hospital', 'bed_number']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['bed_type', 'status']),
        ]
    
    @property
    def is_available(self):
        """Check if bed is available for new patients"""
        return self.status == 'available'
    
    @property
    def occupancy_duration(self):
        """Calculate how long bed has been occupied"""
        if self.status == 'occupied' and self.admission_date:
            return timezone.now() - self.admission_date
        return None
    
    def reserve_bed(self, patient_name, expected_admission=None):
        """Reserve bed for incoming patient"""
        self.status = 'reserved'
        self.patient_name = patient_name
        if expected_admission:
            self.admission_date = expected_admission
        self.save()
    
    def admit_patient(self, patient_name, patient_id=None):
        """Admit patient to bed"""
        self.status = 'occupied'
        self.patient_name = patient_name
        self.patient_id = patient_id or ''
        self.admission_date = timezone.now()
        self.save()
    
    def discharge_patient(self):
        """Discharge patient and mark bed for cleaning"""
        self.status = 'cleaning'
        self.patient_name = ''
        self.patient_id = ''
        self.admission_date = None
        self.expected_discharge = None
        self.save()
    
    def mark_available(self):
        """Mark bed as available after cleaning"""
        self.status = 'available'
        self.last_cleaned = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.hospital.name} - {self.ward_name} - Bed {self.bed_number}"


class EmergencyDepartmentStatus(BaseModel):
    """Emergency Department real-time status tracking"""
    
    TRIAGE_LEVEL_CHOICES = [
        ('1', _('Level 1 - Resuscitation')),
        ('2', _('Level 2 - Emergent')),
        ('3', _('Level 3 - Urgent')),
        ('4', _('Level 4 - Less Urgent')),
        ('5', _('Level 5 - Non-urgent')),
    ]
    
    hospital = models.OneToOneField(
        'doctors.Hospital',
        on_delete=models.CASCADE,
        related_name='ed_status'
    )
    
    # Overall ED Status
    is_open = models.BooleanField(_('ED Open'), default=True)
    diversion_status = models.BooleanField(_('On Diversion'), default=False)
    trauma_center_status = models.BooleanField(_('Trauma Center Active'), default=True)
    
    # Wait Times by Triage Level
    level_1_wait_minutes = models.PositiveIntegerField(_('Level 1 Wait (min)'), default=0)
    level_2_wait_minutes = models.PositiveIntegerField(_('Level 2 Wait (min)'), default=0)
    level_3_wait_minutes = models.PositiveIntegerField(_('Level 3 Wait (min)'), default=0)
    level_4_wait_minutes = models.PositiveIntegerField(_('Level 4 Wait (min)'), default=0)
    level_5_wait_minutes = models.PositiveIntegerField(_('Level 5 Wait (min)'), default=0)
    
    # Patient Counts
    patients_waiting = models.PositiveIntegerField(_('Patients Waiting'), default=0)
    patients_in_treatment = models.PositiveIntegerField(_('Patients in Treatment'), default=0)
    patients_admitted_today = models.PositiveIntegerField(_('Patients Admitted Today'), default=0)
    
    # Capacity
    ed_beds_total = models.PositiveIntegerField(_('ED Beds Total'), default=0)
    ed_beds_occupied = models.PositiveIntegerField(_('ED Beds Occupied'), default=0)
    trauma_bays_total = models.PositiveIntegerField(_('Trauma Bays Total'), default=0)
    trauma_bays_occupied = models.PositiveIntegerField(_('Trauma Bays Occupied'), default=0)
    
    # Staffing
    physicians_on_duty = models.PositiveIntegerField(_('Physicians on Duty'), default=0)
    nurses_on_duty = models.PositiveIntegerField(_('Nurses on Duty'), default=0)
    residents_on_duty = models.PositiveIntegerField(_('Residents on Duty'), default=0)
    
    # Special Alerts
    mass_casualty_alert = models.BooleanField(_('Mass Casualty Alert'), default=False)
    psychiatric_hold_available = models.BooleanField(_('Psychiatric Hold Available'), default=True)
    isolation_rooms_available = models.PositiveIntegerField(_('Isolation Rooms Available'), default=0)
    
    # Last Update
    last_updated = models.DateTimeField(_('Last Updated'), auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Updated By')
    )
    
    class Meta:
        verbose_name = _('Emergency Department Status')
        verbose_name_plural = _('Emergency Department Statuses')
    
    @property
    def average_wait_time(self):
        """Calculate average wait time across all triage levels"""
        total_wait = (
            self.level_1_wait_minutes + self.level_2_wait_minutes + 
            self.level_3_wait_minutes + self.level_4_wait_minutes + 
            self.level_5_wait_minutes
        )
        return total_wait / 5
    
    @property
    def ed_occupancy_rate(self):
        """Calculate ED occupancy rate"""
        if self.ed_beds_total > 0:
            return (self.ed_beds_occupied / self.ed_beds_total) * 100
        return 0
    
    @property
    def trauma_occupancy_rate(self):
        """Calculate trauma bay occupancy rate"""
        if self.trauma_bays_total > 0:
            return (self.trauma_bays_occupied / self.trauma_bays_total) * 100
        return 0
    
    @property
    def can_accept_ambulances(self):
        """Check if ED can accept ambulance patients"""
        return (
            self.is_open and 
            not self.diversion_status and
            self.ed_occupancy_rate < 95 and
            not self.mass_casualty_alert
        )
    
    @property
    def status_color(self):
        """Get color code for ED status"""
        if not self.is_open or self.diversion_status:
            return '#dc2626'  # Red
        elif self.ed_occupancy_rate >= 90:
            return '#ef4444'  # Red
        elif self.ed_occupancy_rate >= 75:
            return '#f59e0b'  # Yellow
        else:
            return '#10b981'  # Green
    
    def update_wait_times(self, triage_data):
        """Update wait times from triage data"""
        for level, wait_time in triage_data.items():
            field_name = f'level_{level}_wait_minutes'
            if hasattr(self, field_name):
                setattr(self, field_name, wait_time)
        self.save()
    
    def __str__(self):
        return f"{self.hospital.name} ED - {'Open' if self.is_open else 'Closed'}"


class SpecialtyUnitStatus(BaseModel):
    """Specialty unit capacity and status tracking"""
    
    UNIT_TYPE_CHOICES = [
        ('icu', _('Intensive Care Unit')),
        ('ccu', _('Cardiac Care Unit')),
        ('nicu', _('Neonatal ICU')),
        ('picu', _('Pediatric ICU')),
        ('or', _('Operating Rooms')),
        ('cath_lab', _('Cardiac Catheterization Lab')),
        ('dialysis', _('Dialysis Unit')),
        ('oncology', _('Oncology Unit')),
        ('maternity', _('Maternity Ward')),
        ('psychiatric', _('Psychiatric Unit')),
        ('burn', _('Burn Unit')),
        ('stroke', _('Stroke Unit')),
    ]
    
    hospital = models.ForeignKey(
        'doctors.Hospital',
        on_delete=models.CASCADE,
        related_name='specialty_units'
    )
    
    unit_type = models.CharField(_('Unit Type'), max_length=20, choices=UNIT_TYPE_CHOICES)
    unit_name = models.CharField(_('Unit Name'), max_length=100)
    
    # Capacity
    total_capacity = models.PositiveIntegerField(_('Total Capacity'), default=0)
    current_occupancy = models.PositiveIntegerField(_('Current Occupancy'), default=0)
    available_capacity = models.PositiveIntegerField(_('Available Capacity'), default=0)
    
    # Status
    is_operational = models.BooleanField(_('Operational'), default=True)
    accepting_patients = models.BooleanField(_('Accepting Patients'), default=True)
    
    # Staffing
    required_staff_ratio = models.FloatField(_('Required Staff Ratio'), default=1.0)
    current_staff_count = models.PositiveIntegerField(_('Current Staff Count'), default=0)
    is_adequately_staffed = models.BooleanField(_('Adequately Staffed'), default=True)
    
    # Equipment
    critical_equipment_available = models.BooleanField(_('Critical Equipment Available'), default=True)
    equipment_notes = models.TextField(_('Equipment Notes'), blank=True)
    
    # Wait Times
    average_wait_time_minutes = models.PositiveIntegerField(_('Average Wait Time (min)'), default=0)
    
    # Last Update
    last_updated = models.DateTimeField(_('Last Updated'), auto_now=True)
    
    class Meta:
        verbose_name = _('Specialty Unit Status')
        verbose_name_plural = _('Specialty Unit Statuses')
        unique_together = ['hospital', 'unit_type', 'unit_name']
        ordering = ['hospital', 'unit_type', 'unit_name']
    
    @property
    def occupancy_rate(self):
        """Calculate occupancy rate as percentage"""
        if self.total_capacity > 0:
            return (self.current_occupancy / self.total_capacity) * 100
        return 0
    
    @property
    def can_accept_patients(self):
        """Check if unit can accept new patients"""
        return (
            self.is_operational and
            self.accepting_patients and
            self.available_capacity > 0 and
            self.is_adequately_staffed and
            self.critical_equipment_available
        )
    
    @property
    def status_indicator(self):
        """Get status indicator color"""
        if not self.can_accept_patients:
            return '#dc2626'  # Red
        elif self.occupancy_rate >= 90:
            return '#f59e0b'  # Yellow
        else:
            return '#10b981'  # Green
    
    def update_capacity(self, occupancy_change=0):
        """Update capacity with occupancy change"""
        self.current_occupancy = max(0, self.current_occupancy + occupancy_change)
        self.available_capacity = max(0, self.total_capacity - self.current_occupancy)
        self.save()
    
    def __str__(self):
        return f"{self.hospital.name} - {self.unit_name}"


class HospitalAlert(BaseModel):
    """Hospital-wide alerts and notifications"""
    
    ALERT_TYPE_CHOICES = [
        ('capacity', _('Capacity Alert')),
        ('diversion', _('Ambulance Diversion')),
        ('emergency', _('Emergency Situation')),
        ('staffing', _('Staffing Issue')),
        ('equipment', _('Equipment Failure')),
        ('system', _('System Alert')),
        ('weather', _('Weather Alert')),
        ('security', _('Security Alert')),
    ]
    
    SEVERITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    hospital = models.ForeignKey(
        'doctors.Hospital',
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    
    alert_type = models.CharField(_('Alert Type'), max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(_('Severity'), max_length=20, choices=SEVERITY_CHOICES)
    title = models.CharField(_('Alert Title'), max_length=200)
    message = models.TextField(_('Alert Message'))
    
    # Status
    is_active = models.BooleanField(_('Active'), default=True)
    acknowledged = models.BooleanField(_('Acknowledged'), default=False)
    resolved = models.BooleanField(_('Resolved'), default=False)
    
    # Timing
    alert_start = models.DateTimeField(_('Alert Start'), auto_now_add=True)
    alert_end = models.DateTimeField(_('Alert End'), null=True, blank=True)
    acknowledged_at = models.DateTimeField(_('Acknowledged At'), null=True, blank=True)
    resolved_at = models.DateTimeField(_('Resolved At'), null=True, blank=True)
    
    # Personnel
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_alerts',
        verbose_name=_('Created By')
    )
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        verbose_name=_('Acknowledged By')
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        verbose_name=_('Resolved By')
    )
    
    class Meta:
        verbose_name = _('Hospital Alert')
        verbose_name_plural = _('Hospital Alerts')
        ordering = ['-alert_start', '-severity']
        indexes = [
            models.Index(fields=['hospital', 'is_active']),
            models.Index(fields=['alert_type', 'severity']),
        ]
    
    @property
    def duration(self):
        """Calculate alert duration"""
        end_time = self.alert_end or timezone.now()
        return end_time - self.alert_start
    
    @property
    def severity_color(self):
        """Get color code for severity level"""
        colors = {
            'low': '#10b981',      # Green
            'medium': '#f59e0b',   # Yellow
            'high': '#ef4444',     # Red
            'critical': '#dc2626', # Dark Red
        }
        return colors.get(self.severity, '#6b7280')
    
    def acknowledge(self, user):
        """Acknowledge the alert"""
        self.acknowledged = True
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save()
    
    def resolve(self, user):
        """Resolve the alert"""
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.is_active = False
        self.alert_end = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.hospital.name} - {self.title} ({self.get_severity_display()})"
