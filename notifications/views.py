from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.contenttypes.models import ContentType
import json

from .models import (
    Notification, NotificationPreference, NotificationTemplate,
    NotificationLog, NotificationQueue
)
from .forms import NotificationPreferenceForm, NotificationForm

class NotificationListView(LoginRequiredMixin, ListView):
    """List view for user notifications"""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Notification.objects.filter(
            user=self.request.user,
            is_active=True
        ).select_related('template', 'content_type')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            if status == 'unread':
                queryset = queryset.filter(read_at__isnull=True)
            elif status == 'read':
                queryset = queryset.filter(read_at__isnull=False)
            else:
                queryset = queryset.filter(status=status)
        
        # Filter by priority
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(message__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get notification counts
        user_notifications = Notification.objects.filter(
            user=self.request.user,
            is_active=True
        )
        
        context.update({
            'unread_count': user_notifications.filter(read_at__isnull=True).count(),
            'total_count': user_notifications.count(),
            'urgent_count': user_notifications.filter(
                priority='urgent',
                read_at__isnull=True
            ).count(),
            'current_status': self.request.GET.get('status', 'all'),
            'current_priority': self.request.GET.get('priority', 'all'),
            'search_query': self.request.GET.get('search', ''),
        })
        
        return context

class NotificationDetailView(LoginRequiredMixin, DetailView):
    """Detail view for individual notifications"""
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            is_active=True
        ).select_related('template', 'content_type')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Mark as read when viewed
        if not obj.is_read:
            obj.mark_as_read()
        return obj

class NotificationPreferenceView(LoginRequiredMixin, UpdateView):
    """View for managing notification preferences"""
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'notifications/preferences.html'
    success_url = reverse_lazy('notifications:preferences')
    
    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj
    
    def form_valid(self, form):
        messages.success(self.request, 'Notification preferences updated successfully!')
        return super().form_valid(form)

@login_required
def notification_dashboard(request):
    """Dashboard view showing notification statistics and recent notifications"""
    user_notifications = Notification.objects.filter(
        user=request.user,
        is_active=True
    )
    
    # Get statistics
    stats = {
        'total': user_notifications.count(),
        'unread': user_notifications.filter(read_at__isnull=True).count(),
        'urgent': user_notifications.filter(
            priority='urgent',
            read_at__isnull=True
        ).count(),
        'today': user_notifications.filter(
            created_at__date=timezone.now().date()
        ).count(),
    }
    
    # Get recent notifications
    recent_notifications = user_notifications.order_by('-created_at')[:10]
    
    # Get notifications by priority
    priority_stats = user_notifications.values('priority').annotate(
        count=Count('id')
    ).order_by('priority')
    
    # Get notifications by type
    type_stats = user_notifications.filter(
        template__isnull=False
    ).values(
        'template__notification_type',
        'template__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'stats': stats,
        'recent_notifications': recent_notifications,
        'priority_stats': priority_stats,
        'type_stats': type_stats,
    }
    
    return render(request, 'notifications/dashboard.html', context)

@login_required
@require_POST
def mark_as_read(request, notification_id):
    """Mark a notification as read via AJAX"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )
    
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    
    messages.success(request, 'Notification marked as read')
    return redirect('notifications:list')

@login_required
@require_POST
def mark_all_as_read(request):
    """Mark all notifications as read"""
    updated_count = Notification.objects.filter(
        user=request.user,
        read_at__isnull=True,
        is_active=True
    ).update(
        read_at=timezone.now(),
        status='read'
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} notifications marked as read'
        })
    
    messages.success(request, f'{updated_count} notifications marked as read')
    return redirect('notifications:list')

@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a notification"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )
    
    notification.is_active = False
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted'
        })
    
    messages.success(request, 'Notification deleted')
    return redirect('notifications:list')

@login_required
def get_unread_count(request):
    """Get unread notification count via AJAX"""
    count = Notification.objects.filter(
        user=request.user,
        read_at__isnull=True,
        is_active=True
    ).count()
    
    return JsonResponse({'unread_count': count})

@login_required
def notification_feed(request):
    """JSON feed of recent notifications for real-time updates"""
    since = request.GET.get('since')
    
    queryset = Notification.objects.filter(
        user=request.user,
        is_active=True
    )
    
    if since:
        try:
            since_datetime = timezone.datetime.fromisoformat(since.replace('Z', '+00:00'))
            queryset = queryset.filter(created_at__gt=since_datetime)
        except ValueError:
            pass
    
    notifications = queryset.order_by('-created_at')[:20]
    
    data = []
    for notification in notifications:
        data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'priority': notification.priority,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'url': f'/notifications/{notification.id}/'
        })
    
    return JsonResponse({
        'notifications': data,
        'count': len(data)
    })

class CreateNotificationView(LoginRequiredMixin, CreateView):
    """View for creating notifications (admin/staff only)"""
    model = Notification
    form_class = NotificationForm
    template_name = 'notifications/create_notification.html'
    success_url = reverse_lazy('notifications:list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Access denied. Staff privileges required.')
            return redirect('notifications:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, 'Notification created successfully!')
        return super().form_valid(form)

# Utility functions for creating notifications
def create_notification(user, title, message, priority='medium', 
                       notification_type=None, content_object=None, 
                       metadata=None, scheduled_for=None):
    """Utility function to create notifications"""
    notification_data = {
        'user': user,
        'title': title,
        'message': message,
        'priority': priority,
        'metadata': metadata or {},
        'scheduled_for': scheduled_for,
    }
    
    # Set template if notification_type is provided
    if notification_type:
        try:
            template = NotificationTemplate.objects.get(
                notification_type=notification_type
            )
            notification_data['template'] = template
        except NotificationTemplate.DoesNotExist:
            pass
    
    # Set content object if provided
    if content_object:
        notification_data['content_object'] = content_object
    
    notification = Notification.objects.create(**notification_data)
    
    # Add to queue for processing
    NotificationQueue.objects.create(
        notification=notification,
        priority=1 if priority == 'urgent' else 0
    )
    
    return notification

def create_referral_notification(referral, notification_type):
    """Create notification for referral events"""
    if notification_type == 'referral_created':
        # Notify target doctor
        create_notification(
            user=referral.target_doctor.user,
            title=f'New Referral from Dr. {referral.referring_doctor.get_full_name()}',
            message=f'You have received a new referral for patient {referral.patient.get_full_name()}.',
            priority='high',
            notification_type='referral_created',
            content_object=referral
        )
    
    elif notification_type == 'referral_accepted':
        # Notify referring doctor
        create_notification(
            user=referral.referring_doctor.user,
            title='Referral Accepted',
            message=f'Dr. {referral.target_doctor.get_full_name()} has accepted your referral for {referral.patient.get_full_name()}.',
            priority='medium',
            notification_type='referral_accepted',
            content_object=referral
        )
    
    elif notification_type == 'referral_rejected':
        # Notify referring doctor
        create_notification(
            user=referral.referring_doctor.user,
            title='Referral Rejected',
            message=f'Dr. {referral.target_doctor.get_full_name()} has rejected your referral for {referral.patient.get_full_name()}.',
            priority='high',
            notification_type='referral_rejected',
            content_object=referral
        )

def create_appointment_notification(appointment, notification_type):
    """Create notification for appointment events"""
    if notification_type == 'appointment_scheduled':
        # Notify patient
        create_notification(
            user=appointment.patient.user,
            title='Appointment Scheduled',
            message=f'Your appointment with Dr. {appointment.doctor.get_full_name()} has been scheduled for {appointment.appointment_date}.',
            priority='medium',
            notification_type='appointment_scheduled',
            content_object=appointment
        )
        
        # Notify doctor
        create_notification(
            user=appointment.doctor.user,
            title='New Appointment',
            message=f'New appointment scheduled with {appointment.patient.get_full_name()} for {appointment.appointment_date}.',
            priority='medium',
            notification_type='appointment_scheduled',
            content_object=appointment
        )
    
    elif notification_type == 'appointment_reminder':
        # Notify patient
        create_notification(
            user=appointment.patient.user,
            title='Appointment Reminder',
            message=f'Reminder: You have an appointment with Dr. {appointment.doctor.get_full_name()} tomorrow at {appointment.appointment_date}.',
            priority='medium',
            notification_type='appointment_reminder',
            content_object=appointment
        )