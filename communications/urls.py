"""
Communications URLs
URL patterns for notification and messaging system
"""

from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    # Notification Management
    path('', views.notification_dashboard, name='dashboard'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<uuid:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('preferences/', views.notification_preferences, name='notification_preferences'),
    
    # Secure Messaging
    path('messages/', views.secure_message_list, name='secure_message_list'),
    path('messages/<uuid:message_id>/', views.secure_message_detail, name='secure_message_detail'),
    path('messages/create/', views.secure_message_create, name='secure_message_create'),
    
    # Emergency Alerts
    path('alerts/', views.emergency_alert_list, name='emergency_alert_list'),
    path('alerts/<uuid:alert_id>/', views.emergency_alert_detail, name='emergency_alert_detail'),
    path('alerts/create/', views.emergency_alert_create, name='emergency_alert_create'),
    path('alerts/<uuid:alert_id>/acknowledge/', views.acknowledge_emergency_alert, name='acknowledge_emergency_alert'),
]
