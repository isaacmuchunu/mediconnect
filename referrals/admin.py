from django.contrib import admin
from django.utils.html import format_html
from .models import Referral

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        'patient_name', 'specialty', 'referring_doctor_name', 'target_doctor_name', 
        'priority_badge', 'status_badge', 'ambulance_badge', 'created_at'
    )
    list_filter = (
        'status', 'priority', 'specialty', 'ambulance_required', 
        'referring_doctor', 'target_doctor', 'created_at'
    )
    search_fields = (
        'patient__first_name', 'patient__last_name', 'patient__nhs_number',
        'referring_doctor__first_name', 'referring_doctor__last_name',
        'target_doctor__first_name', 'target_doctor__last_name',
        'specialty', 'reason'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient',)
        }),
        ('Referral Details', {
            'fields': ('specialty', 'priority', 'reason', 'notes', 'ambulance_required')
        }),
        ('Doctor Information', {
            'fields': ('referring_doctor', 'target_doctor')
        }),
        ('Status & Response', {
            'fields': ('status', 'response_notes')
        }),
        ('Attachments', {
            'fields': ('attachments',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'viewed_at', 'responded_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at', 'viewed_at', 'responded_at')
    
    def patient_name(self, obj):
        return obj.patient.get_full_name()
    patient_name.short_description = 'Patient'
    patient_name.admin_order_field = 'patient__last_name'
    
    def referring_doctor_name(self, obj):
        return obj.referring_doctor.get_full_name()
    referring_doctor_name.short_description = 'Referring Doctor'
    referring_doctor_name.admin_order_field = 'referring_doctor__last_name'
    
    def target_doctor_name(self, obj):
        return obj.target_doctor.get_full_name()
    target_doctor_name.short_description = 'Target Doctor'
    target_doctor_name.admin_order_field = 'target_doctor__last_name'
    
    def priority_badge(self, obj):
        colors = {
            'high': '#dc2626',
            'medium': '#f59e0b',
            'low': '#10b981'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.priority, '#6b7280'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    priority_badge.admin_order_field = 'priority'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6b7280',
            'sent': '#3b82f6',
            'viewed': '#f59e0b',
            'accepted': '#10b981',
            'declined': '#ef4444',
            'completed': '#8b5cf6'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def ambulance_badge(self, obj):
        if obj.ambulance_required:
            return format_html(
                '<span style="background-color: #ef4444; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px;">🚑 AMBULANCE</span>'
            )
        return '-'
    ambulance_badge.short_description = 'Ambulance'
    ambulance_badge.admin_order_field = 'ambulance_required'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient', 'referring_doctor', 'target_doctor'
        )
    
    actions = ['mark_as_viewed', 'mark_as_accepted', 'mark_as_completed']
    
    def mark_as_viewed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='sent').update(
            status='viewed',
            viewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} referrals marked as viewed.')
    mark_as_viewed.short_description = 'Mark selected referrals as viewed'
    
    def mark_as_accepted(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['sent', 'viewed']).update(
            status='accepted',
            responded_at=timezone.now()
        )
        self.message_user(request, f'{updated} referrals marked as accepted.')
    mark_as_accepted.short_description = 'Mark selected referrals as accepted'
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='accepted').update(
            status='completed',
            responded_at=timezone.now()
        )
        self.message_user(request, f'{updated} referrals marked as completed.')
    mark_as_completed.short_description = 'Mark selected referrals as completed'