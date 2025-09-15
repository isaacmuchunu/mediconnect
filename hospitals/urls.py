"""
Hospital Integration URLs
URL patterns for hospital capacity management and integration features
"""

from django.urls import path
from . import views_integration

app_name = 'hospitals'

urlpatterns = [
    # Hospital Capacity Management
    path('capacity/', views_integration.hospital_capacity_dashboard, name='capacity_dashboard'),
    path('capacity/<uuid:hospital_id>/', views_integration.hospital_detail_capacity, name='hospital_detail_capacity'),
    path('capacity/<uuid:hospital_id>/beds/', views_integration.bed_management_view, name='bed_management'),
    path('capacity/<uuid:hospital_id>/alerts/', views_integration.alert_management_view, name='alert_management'),
    
    # API Endpoints
    path('api/capacity/update/', views_integration.update_hospital_capacity, name='update_capacity'),
    path('api/ed/update/', views_integration.update_ed_status, name='update_ed_status'),
    path('api/bed/update/', views_integration.update_bed_status, name='update_bed_status'),
    path('api/alert/create/', views_integration.create_hospital_alert, name='create_alert'),
    path('api/alert/<uuid:alert_id>/acknowledge/', views_integration.acknowledge_alert, name='acknowledge_alert'),
    path('api/alert/<uuid:alert_id>/resolve/', views_integration.resolve_alert, name='resolve_alert'),
    
    # Public API for Ambulance Dispatchers
    path('api/availability/', views_integration.hospital_availability_api, name='hospital_availability'),
]
