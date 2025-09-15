from django.contrib import admin
from .models_integration import (
    HospitalCapacity, BedManagement, EmergencyDepartmentStatus,
    SpecialtyUnitStatus, HospitalAlert
)


@admin.register(HospitalCapacity)
class HospitalCapacityAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'overall_status', 'total_beds', 'available_beds', 'bed_occupancy_rate', 'last_updated']
    list_filter = ['overall_status', 'ambulance_diversion', 'last_updated']
    search_fields = ['hospital__name']
    readonly_fields = ['bed_occupancy_rate', 'icu_occupancy_rate', 'can_accept_patients']


@admin.register(BedManagement)
class BedManagementAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'bed_number', 'bed_type', 'ward_name', 'status', 'patient_name']
    list_filter = ['hospital', 'bed_type', 'status', 'ward_name']
    search_fields = ['hospital__name', 'bed_number', 'patient_name']


@admin.register(EmergencyDepartmentStatus)
class EmergencyDepartmentStatusAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'is_open', 'diversion_status', 'average_wait_time', 'patients_waiting']
    list_filter = ['is_open', 'diversion_status', 'trauma_center_status']
    search_fields = ['hospital__name']


@admin.register(SpecialtyUnitStatus)
class SpecialtyUnitStatusAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'unit_name', 'unit_type', 'occupancy_rate', 'accepting_patients']
    list_filter = ['hospital', 'unit_type', 'accepting_patients', 'is_operational']
    search_fields = ['hospital__name', 'unit_name']


@admin.register(HospitalAlert)
class HospitalAlertAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'title', 'alert_type', 'severity', 'is_active', 'alert_start']
    list_filter = ['alert_type', 'severity', 'is_active', 'acknowledged', 'resolved']
    search_fields = ['hospital__name', 'title', 'message']
    readonly_fields = ['duration']
