"""
Communication & Notification System Views
Multi-channel notifications, secure messaging, and emergency alerts
"""

import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

from .models import (
    NotificationChannel, NotificationTemplate, Notification,
    SecureMessage, EmergencyAlert, NotificationPreference
)
from .services import NotificationService, MessageEncryptionService

User = get_user_model()


def is_admin_or_dispatcher(user):
    """Check if user is admin or dispatcher"""
    return user.is_authenticated and (
        user.is_staff or 
        user.role in ['ADMIN', 'DISPATCHER'] or
        user.groups.filter(name__in=['Admins', 'Dispatchers']).exists()
    )


def is_healthcare_provider(user):
    """Check if user is a healthcare provider"""
    return user.is_authenticated and (
        user.role in ['DOCTOR', 'NURSE', 'PARAMEDIC', 'EMT'] or
        user.groups.filter(name__in=['Healthcare Providers', 'Medical Staff']).exists()
    )


@login_required
def notification_dashboard(request):
    """Notification management dashboard"""
    
    # Get user's notifications
    user_notifications = Notification.objects.filter(
        recipient_user=request.user
    ).order_by('-created_at')[:10]
    
    # Get notification statistics
    stats = {
        'total_notifications': user_notifications.count(),
        'unread_count': user_notifications.filter(status='pending').count(),
        'delivered_count': user_notifications.filter(status='delivered').count(),
        'failed_count': user_notifications.filter(status='failed').count(),
    }
    
    # Get recent secure messages
    recent_messages = SecureMessage.objects.filter(
        Q(sender=request.user) | Q(recipients=request.user)
    ).distinct().order_by('-created_at')[:5]
    
    # Get active emergency alerts
    active_alerts = EmergencyAlert.objects.filter(
        status='active',
        alert_start__lte=timezone.now()
    ).order_by('-severity', '-alert_start')[:5]
    
    context = {
        'user_notifications': user_notifications,
        'stats': stats,
        'recent_messages': recent_messages,
        'active_alerts': active_alerts,
    }
    
    return render(request, 'communications/dashboard.html', context)


@login_required
def notification_list(request):
    """List user's notifications with filtering"""
    
    # Get query parameters
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    priority_filter = request.GET.get('priority', '')
    
    # Build queryset
    notifications = Notification.objects.filter(recipient_user=request.user)
    
    if status_filter:
        notifications = notifications.filter(status=status_filter)
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)
    if priority_filter:
        notifications = notifications.filter(priority=priority_filter)
    
    notifications = notifications.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notifications': page_obj,
        'filters': {
            'status': status_filter,
            'type': type_filter,
            'priority': priority_filter,
        },
        'status_choices': Notification.STATUS_CHOICES,
        'priority_choices': Notification.PRIORITY_CHOICES,
    }
    
    return render(request, 'communications/notification_list.html', context)


@login_required
@require_POST
@csrf_exempt
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            recipient_user=request.user
        )
        
        notification.mark_delivered()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_healthcare_provider)
def secure_message_list(request):
    """List secure messages for healthcare providers"""
    
    # Get messages where user is sender or recipient
    messages_qs = SecureMessage.objects.filter(
        Q(sender=request.user) | Q(recipients=request.user)
    ).distinct().select_related('sender').prefetch_related('recipients')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        messages_qs = messages_qs.filter(status=status_filter)
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        messages_qs = messages_qs.filter(message_type=type_filter)
    
    messages_qs = messages_qs.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(messages_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'messages': page_obj,
        'filters': {
            'status': status_filter,
            'type': type_filter,
        },
        'status_choices': SecureMessage.STATUS_CHOICES,
        'type_choices': SecureMessage.MESSAGE_TYPE_CHOICES,
    }
    
    return render(request, 'communications/secure_message_list.html', context)


@login_required
@user_passes_test(is_healthcare_provider)
def secure_message_detail(request, message_id):
    """View secure message details"""
    
    message = get_object_or_404(
        SecureMessage,
        id=message_id
    )
    
    # Check if user has access
    if request.user != message.sender and request.user not in message.recipients.all():
        messages.error(request, 'You do not have access to this message.')
        return redirect('communications:secure_message_list')
    
    # Mark as read if user is recipient
    if request.user in message.recipients.all():
        message.mark_read(request.user)
    
    context = {
        'message': message,
    }
    
    return render(request, 'communications/secure_message_detail.html', context)


@login_required
@user_passes_test(is_healthcare_provider)
def secure_message_create(request):
    """Create new secure message"""
    
    if request.method == 'POST':
        try:
            # Get form data
            subject = request.POST.get('subject')
            message_content = request.POST.get('message')
            message_type = request.POST.get('message_type', 'general')
            recipient_ids = request.POST.getlist('recipients')
            related_patient = request.POST.get('related_patient', '')
            
            # Create message
            message = SecureMessage.objects.create(
                sender=request.user,
                subject=subject,
                message=message_content,
                message_type=message_type,
                related_patient=related_patient,
                is_encrypted=True
            )
            
            # Add recipients
            recipients = User.objects.filter(id__in=recipient_ids)
            message.recipients.set(recipients)
            
            # Send the message
            message.send_message()
            
            messages.success(request, 'Secure message sent successfully.')
            return redirect('communications:secure_message_detail', message_id=message.id)
            
        except Exception as e:
            messages.error(request, f'Error sending message: {str(e)}')
    
    # Get potential recipients (healthcare providers)
    potential_recipients = User.objects.filter(
        role__in=['DOCTOR', 'NURSE', 'PARAMEDIC', 'EMT']
    ).exclude(id=request.user.id).order_by('first_name', 'last_name')
    
    context = {
        'potential_recipients': potential_recipients,
        'message_type_choices': SecureMessage.MESSAGE_TYPE_CHOICES,
    }
    
    return render(request, 'communications/secure_message_create.html', context)


@login_required
@user_passes_test(is_admin_or_dispatcher)
def emergency_alert_list(request):
    """List emergency alerts for admins/dispatchers"""
    
    alerts = EmergencyAlert.objects.all().order_by('-alert_start')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        alerts = alerts.filter(status=status_filter)
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        alerts = alerts.filter(alert_type=type_filter)
    
    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'alerts': page_obj,
        'filters': {
            'status': status_filter,
            'type': type_filter,
        },
        'status_choices': EmergencyAlert.STATUS_CHOICES,
        'type_choices': EmergencyAlert.ALERT_TYPE_CHOICES,
    }
    
    return render(request, 'communications/emergency_alert_list.html', context)


@login_required
@user_passes_test(is_admin_or_dispatcher)
def emergency_alert_create(request):
    """Create new emergency alert"""
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            message = request.POST.get('message')
            alert_type = request.POST.get('alert_type')
            severity = request.POST.get('severity')
            target_roles = request.POST.getlist('target_roles')
            requires_acknowledgment = request.POST.get('requires_acknowledgment') == 'on'
            
            # Create alert
            alert = EmergencyAlert.objects.create(
                title=title,
                message=message,
                alert_type=alert_type,
                severity=severity,
                target_roles=target_roles,
                requires_acknowledgment=requires_acknowledgment,
                created_by=request.user
            )
            
            # Activate immediately if requested
            if request.POST.get('activate_now') == 'on':
                alert.activate_alert()
                messages.success(request, 'Emergency alert created and activated.')
            else:
                messages.success(request, 'Emergency alert created as draft.')
            
            return redirect('communications:emergency_alert_detail', alert_id=alert.id)
            
        except Exception as e:
            messages.error(request, f'Error creating alert: {str(e)}')
    
    # Get available roles
    available_roles = [
        ('DOCTOR', 'Doctors'),
        ('NURSE', 'Nurses'),
        ('PARAMEDIC', 'Paramedics'),
        ('EMT', 'EMTs'),
        ('DISPATCHER', 'Dispatchers'),
        ('ADMIN', 'Administrators'),
    ]
    
    context = {
        'alert_type_choices': EmergencyAlert.ALERT_TYPE_CHOICES,
        'severity_choices': EmergencyAlert.SEVERITY_CHOICES,
        'available_roles': available_roles,
    }
    
    return render(request, 'communications/emergency_alert_create.html', context)


@login_required
def emergency_alert_detail(request, alert_id):
    """View emergency alert details"""
    
    alert = get_object_or_404(EmergencyAlert, id=alert_id)
    
    # Check if user can acknowledge
    can_acknowledge = (
        alert.requires_acknowledgment and
        alert.status == 'active' and
        request.user not in alert.acknowledged_by.all()
    )
    
    context = {
        'alert': alert,
        'can_acknowledge': can_acknowledge,
    }
    
    return render(request, 'communications/emergency_alert_detail.html', context)


@login_required
@require_POST
@csrf_exempt
def acknowledge_emergency_alert(request, alert_id):
    """Acknowledge emergency alert"""
    
    try:
        alert = get_object_or_404(EmergencyAlert, id=alert_id)
        
        if alert.requires_acknowledgment and alert.status == 'active':
            alert.acknowledged_by.add(request.user)
            alert.total_acknowledged += 1
            alert.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Alert acknowledged successfully'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Alert cannot be acknowledged'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
def notification_preferences(request):
    """Manage user notification preferences"""
    
    # Get or create preferences
    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'POST':
        try:
            # Update preferences
            preferences.email_enabled = request.POST.get('email_enabled') == 'on'
            preferences.sms_enabled = request.POST.get('sms_enabled') == 'on'
            preferences.push_enabled = request.POST.get('push_enabled') == 'on'
            preferences.in_app_enabled = request.POST.get('in_app_enabled') == 'on'
            
            preferences.emergency_alerts = request.POST.get('emergency_alerts') == 'on'
            preferences.dispatch_notifications = request.POST.get('dispatch_notifications') == 'on'
            preferences.status_updates = request.POST.get('status_updates') == 'on'
            preferences.system_alerts = request.POST.get('system_alerts') == 'on'
            
            preferences.weekend_notifications = request.POST.get('weekend_notifications') == 'on'
            
            # Update contact information
            preferred_email = request.POST.get('preferred_email')
            if preferred_email:
                preferences.preferred_email = preferred_email
            
            preferred_phone = request.POST.get('preferred_phone')
            if preferred_phone:
                preferences.preferred_phone = preferred_phone
            
            preferences.save()
            
            messages.success(request, 'Notification preferences updated successfully.')
            
        except Exception as e:
            messages.error(request, f'Error updating preferences: {str(e)}')
    
    context = {
        'preferences': preferences,
    }
    
    return render(request, 'communications/notification_preferences.html', context)
