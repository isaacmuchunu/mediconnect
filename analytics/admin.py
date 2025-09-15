from django.contrib import admin
from .models import (
    PerformanceMetric, DashboardWidget, ReportTemplate,
    GeneratedReport, AnalyticsEvent, KPITarget
)


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'value', 'unit', 'ambulance', 'measurement_date']
    list_filter = ['metric_type', 'unit', 'measurement_date']
    search_fields = ['metric_name', 'ambulance__license_plate']
    date_hierarchy = 'measurement_date'


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['title', 'widget_type', 'size', 'is_visible', 'dashboard_position']
    list_filter = ['widget_type', 'size', 'is_visible']
    search_fields = ['title', 'data_source']
    ordering = ['dashboard_position']


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'frequency', 'output_format', 'is_active']
    list_filter = ['report_type', 'frequency', 'output_format', 'is_active']
    search_fields = ['name', 'description']
    filter_horizontal = ['recipients']


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'template', 'status', 'generated_by', 'generation_started']
    list_filter = ['status', 'template__report_type', 'generation_started']
    search_fields = ['title', 'template__name']
    readonly_fields = ['generation_duration', 'is_available']
    date_hierarchy = 'generation_started'


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'event_type', 'user', 'timestamp']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['event_name', 'user__email']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(KPITarget)
class KPITargetAdmin(admin.ModelAdmin):
    list_display = ['name', 'kpi_type', 'target_value', 'unit', 'get_status', 'is_active']
    list_filter = ['kpi_type', 'is_active', 'higher_is_better']
    search_fields = ['name', 'description']
    readonly_fields = ['get_current_value', 'get_status']
