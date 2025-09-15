from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Report, ReportTemplate, ReferralAnalytics, AppointmentAnalytics,
    SystemUsageAnalytics, ComplianceReport, ReportSchedule, ReportAccess
)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'template', 'status', 'generated_by', 'created_at', 'file_size_display']
    list_filter = ['template__report_type', 'status', 'created_at', 'updated_at']
    search_fields = ['title', 'generated_by__username']
    readonly_fields = ['created_at', 'updated_at', 'file_size_display', 'file_path']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'template', 'status', 'format')
        }),
        ('Content', {
            'fields': ('content', 'file_path', 'summary')
        }),
        ('Processing', {
            'fields': ('started_at', 'completed_at', 'processing_time', 'error_message')
        }),
        ('Access Control', {
            'fields': ('is_public', 'shared_with')
        }),
        ('Metadata', {
            'fields': ('generated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def file_size_display(self, obj):
        if obj.file_path and hasattr(obj.file_path, 'size'):
            size = obj.file_path.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        return "N/A"
    file_size_display.short_description = "File Size"

@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'frequency', 'is_active', 'created_at']
    list_filter = ['report_type', 'frequency', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'report_type', 'is_active')
        }),
        ('Configuration', {
            'fields': ('query_template', 'parameters', 'frequency', 'auto_generate')
        }),
        ('Recipients', {
            'fields': ('recipients',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(ReferralAnalytics)
class ReferralAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'period_type', 'total_referrals', 'pending_referrals', 'accepted_referrals', 'rejected_referrals']
    list_filter = ['date', 'period_type']
    search_fields = ['specialty_breakdown']
    readonly_fields = ['date', 'created_at', 'updated_at']
    ordering = ['-date']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Period Information', {
            'fields': ('date', 'period_type')
        }),
        ('Referral Metrics', {
            'fields': ('total_referrals', 'pending_referrals', 'accepted_referrals', 'rejected_referrals', 'completed_referrals')
        }),
        ('Quality Metrics', {
            'fields': ('acceptance_rate', 'completion_rate', 'avg_response_time', 'avg_completion_time')
        }),
        ('Breakdown', {
            'fields': ('specialty_breakdown',)
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(AppointmentAnalytics)
class AppointmentAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'period_type', 'total_appointments', 'completed_appointments', 'cancelled_appointments', 'no_show_appointments']
    list_filter = ['date', 'period_type']
    readonly_fields = ['date', 'created_at', 'updated_at']
    ordering = ['-date']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Period Information', {
            'fields': ('date', 'period_type')
        }),
        ('Appointment Metrics', {
            'fields': ('total_appointments', 'scheduled_appointments', 'completed_appointments', 'cancelled_appointments', 'no_show_appointments')
        }),
        ('Time Metrics', {
            'fields': ('avg_wait_time', 'avg_appointment_duration')
        }),
        ('Utilization', {
            'fields': ('utilization_rate', 'no_show_rate')
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(SystemUsageAnalytics)
class SystemUsageAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'hour', 'total_users', 'active_users', 'new_users', 'total_sessions']
    list_filter = ['date', 'hour']
    readonly_fields = ['date', 'created_at', 'updated_at']
    ordering = ['-date', '-hour']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Period Information', {
            'fields': ('date', 'hour')
        }),
        ('User Metrics', {
            'fields': ('total_users', 'active_users', 'new_users')
        }),
        ('Session Metrics', {
            'fields': ('total_sessions', 'avg_session_duration')
        }),
        ('Page Views', {
            'fields': ('page_views', 'unique_page_views')
        }),
        ('Performance', {
            'fields': ('avg_response_time', 'error_rate', 'feature_usage')
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(ComplianceReport)
class ComplianceReportAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'period_start', 'period_end', 'compliance_score', 'risk_level', 'created_at']
    list_filter = ['report_type', 'risk_level', 'period_start', 'created_at']
    search_fields = ['report_type', 'findings', 'recommendations']
    readonly_fields = ['created_at', 'updated_at', 'compliance_percentage']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Compliance Information', {
            'fields': ('report_type', 'period_start', 'period_end', 'compliance_score', 'risk_level')
        }),
        ('Metrics', {
            'fields': ('total_events', 'compliant_events', 'non_compliant_events', 'compliance_percentage')
        }),
        ('Details', {
            'fields': ('findings', 'recommendations')
        }),
        ('Review', {
            'fields': ('generated_by', 'reviewed_by', 'reviewed_at')
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def compliance_percentage(self, obj):
        return f"{obj.compliance_percentage:.1f}%"
    compliance_percentage.short_description = "Compliance %"

@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'frequency', 'is_enabled', 'next_run', 'last_run']
    list_filter = ['frequency', 'is_enabled', 'created_at']
    search_fields = ['name', 'template__name']
    readonly_fields = ['created_at', 'updated_at', 'last_run']
    ordering = ['next_run']
    
    fieldsets = (
        ('Schedule Information', {
            'fields': ('name', 'template', 'frequency', 'is_enabled')
        }),
        ('Schedule Settings', {
            'fields': ('day_of_week', 'day_of_month', 'time_of_day')
        }),
        ('Recipients', {
            'fields': ('recipients',)
        }),
        ('Parameters', {
            'fields': ('default_parameters',)
        }),
        ('Timing', {
            'fields': ('next_run', 'last_run')
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(ReportAccess)
class ReportAccessAdmin(admin.ModelAdmin):
    list_display = ['report', 'user', 'action', 'accessed_at']
    list_filter = ['action', 'accessed_at']
    search_fields = ['report__title', 'user__username']
    readonly_fields = ['accessed_at', 'created_at', 'updated_at']
    ordering = ['-accessed_at']
    
    fieldsets = (
        ('Access Information', {
            'fields': ('report', 'user', 'action')
        }),
        ('Details', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Timing', {
            'fields': ('accessed_at',)
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )