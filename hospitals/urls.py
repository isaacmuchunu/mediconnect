"""
Hospital Integration URLs
URL patterns for hospital capacity management and integration features
"""

from django.urls import path, include
from . import views_integration
from .api_views import (
    HospitalStatusAPIView, BedAvailabilityAPIView, EDStatusAPIView,
    HospitalRecommendationAPIView, hospital_capacity_view, update_hospital_status_view
)

app_name = 'hospitals'

urlpatterns = [
    # Hospital Capacity Management
    path('capacity/', views_integration.hospital_capacity_dashboard, name='capacity_dashboard'),
    path('capacity/<uuid:hospital_id>/', views_integration.hospital_detail_capacity, name='hospital_detail_capacity'),
    path('capacity/<uuid:hospital_id>/beds/', views_integration.bed_management_view, name='bed_management'),
    path('capacity/<uuid:hospital_id>/alerts/', views_integration.alert_management_view, name='alert_management'),
    
    # Legacy API Endpoints (maintaining backward compatibility)
    path('api/capacity/update/', views_integration.update_hospital_capacity, name='update_capacity'),
    path('api/ed/update/', views_integration.update_ed_status, name='update_ed_status'),
    path('api/bed/update/', views_integration.update_bed_status, name='update_bed_status'),
    path('api/alert/create/', views_integration.create_hospital_alert, name='create_alert'),
    path('api/alert/<uuid:alert_id>/acknowledge/', views_integration.acknowledge_alert, name='acknowledge_alert'),
    path('api/alert/<uuid:alert_id>/resolve/', views_integration.resolve_alert, name='resolve_alert'),
    path('api/availability/', views_integration.hospital_availability_api, name='hospital_availability'),
    
    # New Hospital Integration API Endpoints
    path('api/v2/status/', HospitalStatusAPIView.as_view(), name='hospital_status_list'),
    path('api/v2/status/<str:hospital_id>/', HospitalStatusAPIView.as_view(), name='hospital_status_detail'),
    path('api/v2/beds/<str:hospital_id>/', BedAvailabilityAPIView.as_view(), name='bed_availability_update'),
    path('api/v2/ed/<str:hospital_id>/', EDStatusAPIView.as_view(), name='ed_status_update'),
    path('api/v2/recommend/', HospitalRecommendationAPIView.as_view(), name='hospital_recommendation'),
    
    # Legacy function-based API endpoints (for backward compatibility)
    path('api/v1/capacity/<str:hospital_id>/', hospital_capacity_view, name='legacy_hospital_capacity'),
    path('api/v1/status/<str:hospital_id>/update/', update_hospital_status_view, name='legacy_update_status'),
]
