from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    Notification, NotificationPreference, NotificationTemplate,
    NotificationLog, NotificationQueue
)
from .forms import NotificationTemplateForm, BulkNotificationForm

User = get_user_model()

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user', 'priority', 'status', 'is_read',
        'created_at', 'read_at', 'scheduled_for'
    )
    list_filter = (
        'priority', 'status', 'created_at', 'read_at',
        'template__notification_type', 'is_active'
    )
    search_fields = ('title', 'message', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'message', 'priority', 'status')
        }),
        ('Template & Content', {
            'fields': ('template', 'content_type', 'object_id', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {
            'fields': ('scheduled_for',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'read_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    def is_read(self, obj):
        if obj.read_at:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                obj.read_at.strftime('%Y-%m-%d %H:%M')
            )
        return format_html('<span style="color: red;">✗ Unread</span>')
    is_read.short_description = 'Read Status'
    
    actions = ['mark_as_read', 'mark_as_unread', 'deactivate_notifications', 'send_bulk_notification']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.filter(read_at__isnull=True).update(
            read_at=timezone.now(),
            status='read'
        )
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(read_at=None, status='pending')
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark selected notifications as unread'
    
    def deactivate_notifications(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} notifications deactivated.')
    deactivate_notifications.short_description = 'Deactivate selected notifications'
    
    def send_bulk_notification(self, request, queryset):
        """Redirect to bulk notification interface"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('admin:bulk-notification'))
    send_bulk_notification.short_description = 'Send bulk notification'

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'email_notifications', 'sms_notifications',
        'push_notifications', 'digest_frequency'
    )
    list_filter = (
        'email_notifications', 'sms_notifications', 'push_notifications',
        'digest_frequency',
        'referral_notifications', 'appointment_notifications',
        'ambulance_notifications', 'system_notifications',
        'emergency_notifications', 'marketing_notifications',
        'weekend_notifications', 'is_active'
    )
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Delivery Methods', {
            'fields': (
                'email_notifications', 'sms_notifications',
                'push_notifications'
            )
        }),
        ('Notification Types', {
            'fields': (
                'referral_notifications', 'appointment_notifications',
                'ambulance_notifications', 'system_notifications',
                'emergency_notifications', 'marketing_notifications'
            )
        }),
        ('Timing & Frequency Settings', {
            'fields': (
                'digest_frequency', 'quiet_hours_start',
                'quiet_hours_end', 'weekend_notifications'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    form = NotificationTemplateForm
    list_display = (
        'name', 'notification_type', 'default_priority',
        'is_email_enabled', 'is_sms_enabled', 'is_push_enabled',
        'is_active', 'created_at'
    )
    list_filter = (
        'notification_type', 'default_priority', 'is_email_enabled',
        'is_sms_enabled', 'is_push_enabled', 'is_active', 'created_at'
    )
    search_fields = ('name', 'notification_type', 'title_template', 'subject_template')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'notification_type', 'default_priority')
        }),
        ('Templates', {
            'fields': (
                'title_template', 'subject_template', 'message_template',
                'email_template', 'sms_template'
            )
        }),
        ('Delivery Options', {
            'fields': ('is_email_enabled', 'is_sms_enabled', 'is_push_enabled')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['create_bulk_notification']
    
    def create_bulk_notification(self, request, queryset):
        """Create bulk notifications using selected templates"""
        if queryset.count() > 1:
            self.message_user(request, 'Please select only one template for bulk notification.', level='ERROR')
            return
        
        template = queryset.first()
        # Store template ID in session and redirect to bulk notification view
        request.session['bulk_template_id'] = template.id
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('admin:bulk-notification'))
    create_bulk_notification.short_description = 'Create bulk notification from template'

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        'notification', 'delivery_method', 'status', 'attempt_count',
        'sent_at', 'delivered_at', 'created_at'
    )
    list_filter = (
        'delivery_method', 'status', 'sent_at', 'delivered_at', 'created_at'
    )
    search_fields = (
        'notification__title', 'notification__user__username',
        'recipient_email', 'recipient_phone', 'error_message'
    )
    readonly_fields = ('sent_at', 'delivered_at', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification', {
            'fields': ('notification',)
        }),
        ('Delivery Details', {
            'fields': (
                'delivery_method', 'recipient_email', 'recipient_phone',
                'status', 'attempt_count'
            )
        }),
        ('Response & Error Data', {
            'fields': ('response_data', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'sent_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    def has_add_permission(self, request):
        return False  # Logs are created automatically

@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = (
        'notification', 'priority', 'status', 'attempts', 'retry_count',
        'created_at', 'processed_at', 'next_retry'
    )
    list_filter = ('status', 'priority', 'created_at', 'processed_at')
    search_fields = ('notification__title', 'notification__user__username', 'error_message')
    readonly_fields = ('created_at', 'updated_at', 'processed_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification', {
            'fields': ('notification',)
        }),
        ('Queue Settings', {
            'fields': ('priority', 'status', 'retry_count', 'max_retries')
        }),
        ('Scheduling', {
            'fields': ('next_retry',)
        }),
        ('Tracking', {
            'fields': ('attempts', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    actions = ['requeue_notifications', 'mark_as_failed', 'reset_retry_count']
    
    def requeue_notifications(self, request, queryset):
        updated = queryset.update(
            status='pending',
            attempts=0,
            processed_at=None,
            error_message='',
            next_retry=None
        )
        self.message_user(request, f'{updated} notifications requeued.')
    requeue_notifications.short_description = 'Requeue selected notifications'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(
            status='failed',
            processed_at=timezone.now()
        )
        self.message_user(request, f'{updated} notifications marked as failed.')
    mark_as_failed.short_description = 'Mark selected notifications as failed'
    
    def reset_retry_count(self, request, queryset):
        updated = queryset.update(retry_count=0, next_retry=None)
        self.message_user(request, f'Reset retry count for {updated} notifications.')
    reset_retry_count.short_description = 'Reset retry count'
    
    def has_add_permission(self, request):
        return False  # Queue items are created automatically


# Create a custom model proxy for bulk notifications
class BulkNotificationProxy(Notification):
    """Proxy model for bulk notification operations"""
    class Meta:
        proxy = True
        verbose_name = "Bulk Notification"
        verbose_name_plural = "Bulk Notifications"


@admin.register(BulkNotificationProxy)
class BulkNotificationAdmin(admin.ModelAdmin):
    """Admin for bulk notification operations"""
    change_list_template = 'admin/notifications/bulk_notification.html'
    
    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.has_perm('notifications.add_notification')
    
    def has_add_permission(self, request):
        return True
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        if request.method == 'POST':
            form = BulkNotificationForm(request.POST)
            if form.is_valid():
                # Process bulk notification
                recipients = form.cleaned_data['recipients']
                title = form.cleaned_data['title']
                message = form.cleaned_data['message']
                priority = form.cleaned_data['priority']
                scheduled_for = form.cleaned_data.get('scheduled_for')
                delivery_method = form.cleaned_data.get('delivery_method', 'in_app')
                
                # Get template if specified
                template_id = request.session.get('bulk_template_id')
                template = None
                if template_id:
                    try:
                        template = NotificationTemplate.objects.get(id=template_id)
                        request.session.pop('bulk_template_id', None)
                    except NotificationTemplate.DoesNotExist:
                        pass
                
                # Get users based on selection
                users = []
                if recipients == 'all_users':
                    users = User.objects.filter(is_active=True)
                elif recipients == 'doctors':
                    # Assuming you have doctor profiles
                    try:
                        from doctors.models import DoctorProfile
                        users = User.objects.filter(
                            doctorprofile__isnull=False, 
                            is_active=True
                        )
                    except ImportError:
                        self.message_user(request, 'Doctor profiles not available.', level='ERROR')
                        users = []
                elif recipients == 'patients':
                    # Assuming you have patient profiles
                    try:
                        from patients.models import PatientProfile
                        users = User.objects.filter(
                            patientprofile__isnull=False, 
                            is_active=True
                        )
                    except ImportError:
                        self.message_user(request, 'Patient profiles not available.', level='ERROR')
                        users = []
                elif recipients == 'staff':
                    users = User.objects.filter(is_staff=True, is_active=True)
                elif recipients == 'custom':
                    users = form.cleaned_data.get('custom_users', [])
                
                # Create notifications
                count = 0
                for user in users:
                    notification = Notification.objects.create(
                        user=user,
                        title=title,
                        message=message,
                        priority=priority,
                        scheduled_for=scheduled_for,
                        template=template,
                        status='pending'
                    )
                    
                    # Add to queue for processing
                    NotificationQueue.objects.create(
                        notification=notification,
                        priority=1 if priority == 'urgent' else 0,
                        status='pending'
                    )
                    count += 1
                
                self.message_user(
                    request,
                    f'Successfully created {count} notifications.'
                )
        else:
            form = BulkNotificationForm()
            # Pre-populate template data if coming from template
            template_id = request.session.get('bulk_template_id')
            if template_id:
                try:
                    template = NotificationTemplate.objects.get(id=template_id)
                    form.initial['title'] = template.title_template
                    form.initial['message'] = template.message_template
                    form.initial['priority'] = template.default_priority
                except NotificationTemplate.DoesNotExist:
                    pass
        
        extra_context = extra_context or {}
        extra_context['form'] = form
        extra_context['title'] = 'Send Bulk Notification'
        
        return super().changelist_view(request, extra_context)