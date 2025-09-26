"""
Serializers for Notification System
Handles serialization of notifications, preferences, and templates.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Notification, NotificationPreference, NotificationTemplate
from .services import NotificationType, NotificationPriority, NotificationChannel

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    is_read = serializers.SerializerMethodField()
    time_since_created = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'template', 'template_name',
            'title', 'message', 'priority', 'status', 'metadata',
            'is_read', 'created_at', 'read_at', 'scheduled_for',
            'time_since_created', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']
    
    def get_is_read(self, obj) -> bool:
        """Check if notification has been read."""
        return obj.read_at is not None
    
    def get_time_since_created(self, obj) -> str:
        """Get human-readable time since creation."""
        if not obj.created_at:
            return ""
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'email_notifications', 'sms_notifications',
            'push_notifications', 'in_app_notifications', 'phone_number',
            'notification_types', 'digest_frequency', 'quiet_hours_start',
            'quiet_hours_end', 'weekend_notifications', 'is_active'
        ]
        read_only_fields = ['id', 'user']
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value:
            # Remove non-digit characters
            cleaned = ''.join(filter(str.isdigit, value))
            if len(cleaned) < 10:
                raise serializers.ValidationError("Phone number must have at least 10 digits")
        return value
    
    def validate(self, data):
        """Validate quiet hours."""
        start_time = data.get('quiet_hours_start')
        end_time = data.get('quiet_hours_end')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                "Quiet hours start time must be before end time"
            )
        
        return data


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NotificationTemplate model."""
    
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    usage_count = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'notification_type_display',
            'subject_template', 'title_template', 'message_template',
            'email_template', 'sms_template', 'is_email_enabled',
            'is_sms_enabled', 'is_push_enabled', 'default_priority',
            'usage_count', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_usage_count(self, obj) -> int:
        """Get number of times this template has been used."""
        return obj.notifications.count() if hasattr(obj, 'notifications') else 0
    
    def validate_notification_type(self, value):
        """Validate notification type."""
        # Check if the notification type exists in choices
        valid_types = [choice[0] for choice in NotificationTemplate.NOTIFICATION_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid notification type: {value}")
        return value


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for sending notifications via API."""
    
    recipients = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of user IDs to send notification to"
    )
    message = serializers.DictField(
        help_text="Message details including title, body, priority, etc."
    )
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=['EMAIL', 'SMS', 'PUSH', 'IN_APP']),
        default=['EMAIL'],
        help_text="Notification channels to use"
    )
    template_id = serializers.CharField(required=False, help_text="Template ID to use")
    schedule_time = serializers.DateTimeField(
        required=False, 
        help_text="When to send the notification (if not immediate)"
    )
    
    def validate_message(self, value):
        """Validate message structure."""
        required_fields = ['title', 'body']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Message must contain '{field}' field")
        
        # Validate priority if provided
        priority = value.get('priority', 'medium').lower()
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        if priority not in valid_priorities:
            raise serializers.ValidationError(f"Invalid priority: {priority}")
        
        return value
    
    def validate_recipients(self, value):
        """Validate recipients list."""
        if not value:
            raise serializers.ValidationError("Recipients list cannot be empty")
        
        # Check if all recipients exist
        existing_users = User.objects.filter(id__in=value).values_list('id', flat=True)
        missing_users = set(value) - set(str(uid) for uid in existing_users)
        
        if missing_users:
            raise serializers.ValidationError(f"Users not found: {list(missing_users)}")
        
        return value


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notification operations."""
    
    template_id = serializers.CharField(help_text="Template to use for notifications")
    recipients = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of user IDs"
    )
    message_data = serializers.DictField(
        help_text="Data to populate template variables"
    )
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=['EMAIL', 'SMS', 'PUSH', 'IN_APP']),
        default=['EMAIL']
    )
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        default='medium'
    )
    schedule_time = serializers.DateTimeField(required=False)
    
    def validate_template_id(self, value):
        """Validate template exists."""
        try:
            NotificationTemplate.objects.get(id=value, is_active=True)
        except NotificationTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found or inactive")
        return value


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics."""
    
    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    priority_breakdown = serializers.DictField()
    recent_notifications = serializers.ListField()
    delivery_stats = serializers.DictField(required=False)
    
    def to_representation(self, instance):
        """Custom representation for stats."""
        data = super().to_representation(instance)
        
        # Add percentage calculations
        total = data.get('total_notifications', 0)
        unread = data.get('unread_count', 0)
        
        if total > 0:
            data['unread_percentage'] = round((unread / total) * 100, 1)
        else:
            data['unread_percentage'] = 0
        
        return data


class EmergencyAlertSerializer(serializers.Serializer):
    """Serializer for emergency alerts."""
    
    alert_type = serializers.CharField(
        max_length=100,
        help_text="Type of emergency alert"
    )
    message = serializers.CharField(
        max_length=1000,
        help_text="Alert message content"
    )
    affected_areas = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Geographic areas affected by the emergency"
    )
    priority = serializers.ChoiceField(
        choices=['HIGH', 'CRITICAL', 'EMERGENCY'],
        default='HIGH',
        help_text="Alert priority level"
    )
    exclude_users = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="User IDs to exclude from the alert"
    )
    
    def validate_alert_type(self, value):
        """Validate alert type."""
        # Define valid emergency alert types
        valid_types = [
            'MASS_CASUALTY', 'NATURAL_DISASTER', 'HAZMAT_INCIDENT',
            'ACTIVE_SHOOTER', 'BOMB_THREAT', 'HOSPITAL_OVERFLOW',
            'SYSTEM_FAILURE', 'COMMUNICATION_FAILURE', 'OTHER'
        ]
        
        if value.upper() not in valid_types:
            raise serializers.ValidationError(f"Invalid alert type: {value}")
        
        return value.upper()


class NotificationChannelSerializer(serializers.Serializer):
    """Serializer for notification channel information."""
    
    channel_type = serializers.CharField()
    name = serializers.CharField()
    is_available = serializers.BooleanField()
    configuration = serializers.DictField()
    delivery_rate = serializers.FloatField()
    last_used = serializers.DateTimeField()
    
    class Meta:
        fields = [
            'channel_type', 'name', 'is_available', 'configuration',
            'delivery_rate', 'last_used'
        ]


class NotificationLogSerializer(serializers.Serializer):
    """Serializer for notification delivery logs."""
    
    notification_id = serializers.CharField()
    user_id = serializers.CharField()
    channel = serializers.CharField()
    status = serializers.CharField()
    sent_at = serializers.DateTimeField()
    delivered_at = serializers.DateTimeField(required=False)
    error_message = serializers.CharField(required=False)
    attempt_count = serializers.IntegerField()
    
    class Meta:
        fields = [
            'notification_id', 'user_id', 'channel', 'status',
            'sent_at', 'delivered_at', 'error_message', 'attempt_count'
        ]


class NotificationRuleSerializer(serializers.Serializer):
    """Serializer for notification rules and automation."""
    
    name = serializers.CharField(max_length=100)
    trigger_type = serializers.ChoiceField(
        choices=['CREATE', 'UPDATE', 'DELETE', 'SCHEDULE']
    )
    conditions = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of conditions to check"
    )
    template_id = serializers.CharField()
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=['EMAIL', 'SMS', 'PUSH', 'IN_APP'])
    )
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        default='medium'
    )
    delay_minutes = serializers.IntegerField(default=0)
    is_enabled = serializers.BooleanField(default=True)
    
    def validate_conditions(self, value):
        """Validate rule conditions."""
        for condition in value:
            required_fields = ['field', 'operator', 'value']
            for field in required_fields:
                if field not in condition:
                    raise serializers.ValidationError(
                        f"Condition must contain '{field}' field"
                    )
        return value


class UserNotificationSummarySerializer(serializers.Serializer):
    """Serializer for user notification summary."""
    
    user_id = serializers.CharField()
    user_name = serializers.CharField()
    unread_count = serializers.IntegerField()
    high_priority_count = serializers.IntegerField()
    last_notification = serializers.DateTimeField(required=False)
    notification_preferences = NotificationPreferenceSerializer(required=False)
    
    class Meta:
        fields = [
            'user_id', 'user_name', 'unread_count', 'high_priority_count',
            'last_notification', 'notification_preferences'
        ]