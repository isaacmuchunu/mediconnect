from django.urls import path
from . import views

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
]