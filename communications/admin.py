from django.contrib import admin
from .models import (
    NotificationChannel, NotificationTemplate, Notification,
    SecureMessage, EmergencyAlert, NotificationPreference
)


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'status', 'delivery_rate', 'total_sent']
    list_filter = ['channel_type', 'status']
    search_fields = ['name']
    readonly_fields = ['delivery_rate', 'total_sent', 'total_delivered', 'total_failed']


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'subject_template']
    filter_horizontal = ['supported_channels']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['subject', 'recipient_user', 'notification_type', 'priority', 'status', 'created_at']
    list_filter = ['notification_type', 'priority', 'status', 'channel']
    search_fields = ['subject', 'recipient_user__email', 'recipient_email']
    readonly_fields = ['delivery_time', 'is_expired']
    date_hierarchy = 'created_at'


@admin.register(SecureMessage)
class SecureMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sender', 'message_type', 'status', 'sent_at']
    list_filter = ['message_type', 'status', 'is_encrypted']
    search_fields = ['subject', 'sender__email']
    filter_horizontal = ['recipients']
    readonly_fields = ['access_log']


@admin.register(EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'alert_type', 'severity', 'status', 'acknowledgment_rate', 'alert_start']
    list_filter = ['alert_type', 'severity', 'status']
    search_fields = ['title', 'message']
    filter_horizontal = ['target_users', 'delivery_channels', 'acknowledged_by']
    readonly_fields = ['acknowledgment_rate', 'is_active']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'sms_enabled', 'push_enabled', 'emergency_alerts']
    list_filter = ['email_enabled', 'sms_enabled', 'push_enabled', 'emergency_alerts']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
