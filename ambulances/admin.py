from django.contrib import admin
from .models import (
    Ambulance, Dispatch, AmbulanceType, AmbulanceStation, AmbulanceCrew,
    DispatchCrew, GPSTrackingLog, MaintenanceRecord, EquipmentInventory,
    FuelLog, IncidentReport, PerformanceMetrics
)


@admin.register(AmbulanceType)
class AmbulanceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(AmbulanceStation)
class AmbulanceStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'phone', 'is_active')
    search_fields = ('name', 'code', 'address')
    list_filter = ('is_active',)


@admin.register(Ambulance)
class AmbulanceAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'ambulance_type', 'make', 'model', 'status', 'condition', 'patient_capacity')
    search_fields = ('license_plate', 'make', 'model', 'vehicle_identification_number')
    list_filter = ('status', 'condition', 'ambulance_type', 'home_station', 'is_active')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_gps_update')

    fieldsets = (
        ('Basic Information', {
            'fields': ('license_plate', 'vehicle_identification_number', 'ambulance_type')
        }),
        ('Vehicle Details', {
            'fields': ('make', 'model', 'year', 'color', 'patient_capacity', 'crew_capacity')
        }),
        ('Status & Condition', {
            'fields': ('status', 'condition', 'fuel_level', 'mileage')
        }),
        ('Location & Assignment', {
            'fields': ('home_station', 'current_location', 'last_gps_update')
        }),
        ('Equipment & Insurance', {
            'fields': ('medical_equipment', 'gps_device_id', 'insurance_policy')
        }),
        ('Maintenance', {
            'fields': ('last_maintenance', 'next_maintenance', 'maintenance_notes')
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = ('dispatch_number', 'ambulance', 'priority', 'status', 'created_at', 'dispatched_at')
    search_fields = ('dispatch_number', 'ambulance__license_plate', 'pickup_address', 'destination_address')
    list_filter = ('status', 'priority', 'created_at')
    readonly_fields = ('id', 'dispatch_number', 'created_at', 'updated_at', 'response_time_minutes')

    fieldsets = (
        ('Basic Information', {
            'fields': ('dispatch_number', 'referral', 'ambulance', 'dispatcher')
        }),
        ('Priority & Status', {
            'fields': ('priority', 'status', 'is_emergency')
        }),
        ('Locations', {
            'fields': ('pickup_location', 'pickup_address', 'destination_location', 'destination_address')
        }),
        ('Patient Information', {
            'fields': ('patient_condition', 'special_instructions')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'contact_phone')
        }),
        ('Timing', {
            'fields': ('created_at', 'dispatched_at', 'on_scene_at', 'patient_loaded_at', 'completed_at', 'response_time_minutes')
        }),
        ('Notes', {
            'fields': ('notes', 'completion_notes'),
            'classes': ('collapse',)
        })
    )


@admin.register(AmbulanceCrew)
class AmbulanceCrewAdmin(admin.ModelAdmin):
    list_display = ('ambulance', 'crew_member', 'role', 'shift_start', 'shift_end', 'is_active')
    search_fields = ('ambulance__license_plate', 'crew_member__username', 'crew_member__first_name', 'crew_member__last_name')
    list_filter = ('role', 'is_active', 'shift_start')


@admin.register(GPSTrackingLog)
class GPSTrackingLogAdmin(admin.ModelAdmin):
    list_display = ('ambulance', 'timestamp', 'speed', 'heading', 'accuracy')
    search_fields = ('ambulance__license_plate',)
    list_filter = ('timestamp', 'ambulance')
    readonly_fields = ('timestamp',)


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ('ambulance', 'maintenance_type', 'service_date', 'cost', 'performed_by')
    search_fields = ('ambulance__license_plate', 'performed_by', 'description')
    list_filter = ('maintenance_type', 'service_date')


@admin.register(EquipmentInventory)
class EquipmentInventoryAdmin(admin.ModelAdmin):
    list_display = ('ambulance', 'equipment_name', 'quantity', 'condition', 'expiry_date')
    search_fields = ('ambulance__license_plate', 'equipment_name', 'equipment_code')
    list_filter = ('condition', 'category', 'expiry_date')


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display = ('ambulance', 'created_at', 'fuel_amount', 'cost', 'mileage')
    search_fields = ('ambulance__license_plate', 'fuel_station')
    list_filter = ('created_at',)


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ('ambulance', 'incident_type', 'severity', 'incident_time', 'reported_by')
    search_fields = ('ambulance__license_plate', 'title', 'description')
    list_filter = ('incident_type', 'severity', 'incident_time', 'injuries', 'property_damage')


@admin.register(PerformanceMetrics)
class PerformanceMetricsAdmin(admin.ModelAdmin):
    list_display = ('ambulance', 'date', 'total_dispatches', 'average_response_time', 'fuel_consumed')
    search_fields = ('ambulance__license_plate',)
    list_filter = ('date',)
    readonly_fields = ('date',)