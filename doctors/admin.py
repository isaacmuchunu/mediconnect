from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
from django.utils import timezone
import datetime

from .models import (
    Hospital, Specialty, DoctorProfile, Availability, 
    DoctorReview, ReferralStats, EmergencyContact
)


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'city', 'state', 'type', 'bed_capacity', 
        'emergency_services', 'trauma_center_level', 'is_active'
    ]
    list_filter = [
        'type', 'emergency_services', 'trauma_center_level', 
        'state', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'city', 'state', 'zip_code']
    ordering = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'type', 'is_active')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'zip_code')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Facility Details', {
            'fields': ('bed_capacity', 'emergency_services', 'trauma_center_level', 'accreditation')
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            doctor_count=Count('primary_doctors'),
            affiliated_doctor_count=Count('affiliated_doctors')
        )


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'parent_specialty', 'doctor_count', 'is_active']
    list_filter = ['is_active', 'parent_specialty', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    readonly_fields = ['id', 'created_at']
    
    def doctor_count(self, obj):
        return obj.doctors.filter(verification_status='verified').count()
    doctor_count.short_description = 'Verified Doctors'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent_specialty')


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0
    fields = ['date', 'start_time', 'end_time', 'status', 'location', 'max_patients', 'current_bookings']
    readonly_fields = ['current_bookings']


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 1
    fields = ['name', 'relationship', 'phone', 'email', 'is_primary', 'is_active']


class ReferralStatsInline(admin.StackedInline):
    model = ReferralStats
    fields = [
        'total_referrals_received', 'referrals_accepted', 'referrals_declined', 
        'referrals_pending', 'total_referrals_sent', 'average_response_time'
    ]
    readonly_fields = ['last_updated']


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'primary_specialty', 'primary_hospital', 
        'verification_status', 'license_status', 'average_rating', 
        'years_of_experience', 'is_active'
    ]
    list_filter = [
        'verification_status', 'gender', 'primary_specialty', 
        'emergency_availability', 'accepts_referrals', 'telehealth_available',
        'state', 'is_active', 'created_at'
    ]
    search_fields = [
        'first_name', 'last_name', 'license_number', 'npi_number', 
        'user__email', 'primary_hospital__name'
    ]
    ordering = ['last_name', 'first_name']
    readonly_fields = [
        'id', 'average_rating', 'total_reviews', 'referral_acceptance_rate',
        'created_at', 'updated_at', 'verification_date'
    ]
    
    inlines = [EmergencyContactInline, ReferralStatsInline, AvailabilityInline]
    
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'user', 'first_name', 'last_name', 'middle_name', 
                'gender', 'date_of_birth', 'profile_photo'
            )
        }),
        ('Professional Credentials', {
            'fields': (
                'license_number', 'license_state', 'license_expiry_date',
                'npi_number', 'dea_number'
            )
        }),
        ('Contact Information', {
            'fields': (
                'phone', 'emergency_phone', 'office_address', 
                'city', 'state', 'zip_code'
            )
        }),
        ('Education & Training', {
            'fields': (
                'medical_school', 'graduation_year', 'residency_program',
                'fellowship_programs', 'board_certifications'
            )
        }),
        ('Specialties & Affiliations', {
            'fields': (
                'primary_specialty', 'specialties', 'primary_hospital', 
                'affiliated_hospitals'
            )
        }),
        ('Professional Profile', {
            'fields': (
                'bio', 'years_of_experience', 'languages_spoken',
                'consultation_fee', 'accepts_insurance', 'telehealth_available'
            )
        }),
        ('Availability Settings', {
            'fields': (
                'emergency_availability', 'accepts_referrals', 'max_patients_per_day'
            )
        }),
        ('Verification & Status', {
            'fields': (
                'verification_status', 'verification_date', 'verified_by', 'is_active'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'average_rating', 'total_reviews', 'referral_acceptance_rate'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def license_status(self, obj):
        if obj.license_is_valid:
            return format_html('<span style="color: green;">Valid</span>')
        else:
            return format_html('<span style="color: red;">Expired</span>')
    license_status.short_description = 'License Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'primary_specialty', 'primary_hospital'
        ).prefetch_related('specialties', 'affiliated_hospitals')

    actions = ['verify_doctors', 'reject_doctors', 'activate_doctors', 'deactivate_doctors']

    def verify_doctors(self, request, queryset):
        updated = queryset.update(
            verification_status='verified',
            verification_date=timezone.now(),
            verified_by=request.user
        )
        self.message_user(request, f'{updated} doctors were successfully verified.')
    verify_doctors.short_description = 'Verify selected doctors'

    def reject_doctors(self, request, queryset):
        updated = queryset.update(
            verification_status='rejected',
            verification_date=timezone.now(),
            verified_by=request.user
        )
        self.message_user(request, f'{updated} doctors were rejected.')
    reject_doctors.short_description = 'Reject selected doctors'

    def activate_doctors(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} doctors were activated.')
    activate_doctors.short_description = 'Activate selected doctors'

    def deactivate_doctors(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} doctors were deactivated.')
    deactivate_doctors.short_description = 'Deactivate selected doctors'


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = [
        'doctor', 'date', 'start_time', 'end_time', 'status', 
        'location', 'appointment_type', 'booking_status'
    ]
    list_filter = [
        'status', 'appointment_type', 'weekday', 'location', 
        'date', 'is_recurring'
    ]
    search_fields = [
        'doctor__first_name', 'doctor__last_name', 
        'location__name', 'notes'
    ]
    ordering = ['-date', 'start_time']
    readonly_fields = ['id', 'weekday', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('doctor', 'date', 'weekday', 'start_time', 'end_time')
        }),
        ('Slot Configuration', {
            'fields': ('slot_duration', 'max_patients', 'current_bookings', 'status')
        }),
        ('Location & Type', {
            'fields': ('location', 'appointment_type')
        }),
        ('Recurring Settings', {
            'fields': ('is_recurring', 'recurring_until'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'google_calendar_event_id'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def booking_status(self, obj):
        if obj.current_bookings >= obj.max_patients:
            return format_html('<span style="color: red;">Full</span>')
        elif obj.current_bookings > 0:
            return format_html('<span style="color: orange;">{}/{}</span>', 
                             obj.current_bookings, obj.max_patients)
        else:
            return format_html('<span style="color: green;">Available</span>')
    booking_status.short_description = 'Booking Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('doctor', 'location')


@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = [
        'doctor', 'reviewer_name', 'rating', 'visit_date', 
        'would_recommend', 'is_verified', 'is_approved', 'created_at'
    ]
    list_filter = [
        'rating', 'would_recommend', 'is_verified', 'is_approved', 
        'bedside_manner_rating', 'communication_rating', 'expertise_rating',
        'visit_date', 'created_at'
    ]
    search_fields = [
        'doctor__first_name', 'doctor__last_name', 'reviewer_name', 
        'reviewer_email', 'review_title', 'review_text'
    ]
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('doctor', 'reviewer_name', 'reviewer_email', 'visit_date')
        }),
        ('Rating Details', {
            'fields': (
                'rating', 'bedside_manner_rating', 'communication_rating', 
                'expertise_rating', 'would_recommend'
            )
        }),
        ('Review Content', {
            'fields': ('review_title', 'review_text')
        }),
        ('Moderation', {
            'fields': ('is_verified', 'is_approved')
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['approve_reviews', 'reject_reviews', 'verify_reviews']

    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reviews were approved.')
    approve_reviews.short_description = 'Approve selected reviews'

    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} reviews were rejected.')
    reject_reviews.short_description = 'Reject selected reviews'

    def verify_reviews(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} reviews were verified.')
    verify_reviews.short_description = 'Verify selected reviews'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('doctor')


@admin.register(ReferralStats)
class ReferralStatsAdmin(admin.ModelAdmin):
    list_display = [
        'doctor', 'total_referrals_received', 'referrals_accepted', 
        'referrals_declined', 'acceptance_rate_display', 'last_updated'
    ]
    list_filter = ['last_updated']
    search_fields = ['doctor__first_name', 'doctor__last_name']
    ordering = ['-total_referrals_received']
    readonly_fields = ['last_updated']

    def acceptance_rate_display(self, obj):
        rate = obj.acceptance_rate
        if rate >= 80:
            color = 'green'
        elif rate >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
    acceptance_rate_display.short_description = 'Acceptance Rate'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('doctor')


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'name', 'relationship', 'phone', 'is_primary', 'is_active']
    list_filter = ['relationship', 'is_primary', 'is_active']
    search_fields = ['doctor__first_name', 'doctor__last_name', 'name', 'phone']
    ordering = ['doctor', '-is_primary', 'name']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('doctor')


# Custom admin site configuration
admin.site.site_header = "Medical Referral System - Doctor Management"
admin.site.site_title = "Doctor Admin"
admin.site.index_title = "Welcome to Doctor Management Administration"