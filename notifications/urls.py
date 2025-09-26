from django.urls import path
from . import views
from .api_views import (
    NotificationAPIView, NotificationDetailAPIView, NotificationPreferenceAPIView,
    EmergencyAlertAPIView, NotificationTemplateAPIView, BulkNotificationAPIView,
    send_referral_notification_view, mark_notifications_read_view, notification_stats_view
)

app_name = 'notifications'

urlpatterns = [
    # Dashboard and main views
    path('', views.notification_dashboard, name='dashboard'),
    path('list/', views.NotificationListView.as_view(), name='list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='detail'),
    
    # Notification management
    path('create/', views.CreateNotificationView.as_view(), name='create'),
    path('preferences/', views.NotificationPreferenceView.as_view(), name='preferences'),
    
    # AJAX endpoints
    path('mark-read/<int:notification_id>/', views.mark_as_read, name='mark_as_read'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('delete/<int:notification_id>/', views.delete_notification, name='delete'),
    path('unread-count/', views.get_unread_count, name='unread_count'),
    path('feed/', views.notification_feed, name='feed'),
    
    # New API Endpoints
    path('api/v2/notifications/', NotificationAPIView.as_view(), name='api_notifications'),
    path('api/v2/notifications/<str:notification_id>/', NotificationDetailAPIView.as_view(), name='api_notification_detail'),
    path('api/v2/preferences/', NotificationPreferenceAPIView.as_view(), name='api_preferences'),
    path('api/v2/emergency/', EmergencyAlertAPIView.as_view(), name='api_emergency_alert'),
    path('api/v2/templates/', NotificationTemplateAPIView.as_view(), name='api_templates'),
    path('api/v2/bulk/', BulkNotificationAPIView.as_view(), name='api_bulk_notifications'),
    
    # Legacy API endpoints (for backward compatibility)
    path('api/v1/referral/', send_referral_notification_view, name='api_referral_notification'),
    path('api/v1/mark-read/', mark_notifications_read_view, name='api_mark_read'),
    path('api/v1/stats/', notification_stats_view, name='api_stats'),
]