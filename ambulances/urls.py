from django.urls import path
from . import views
from . import views_emergency
from . import views_gps
from . import views_mobile
from .pwa_views import (
    AmbulanceCrewDashboardView, DispatchView, NavigationView, PatientDataView,
    CommunicationView, OfflineView, update_ambulance_status, update_gps_location,
    get_current_dispatch, pwa_health_check
)

app_name = 'ambulances'

urlpatterns = [
    # PWA Routes for Ambulance Crews (New Enhanced Mobile Interface)
    path('crew/', AmbulanceCrewDashboardView.as_view(), name='crew_dashboard'),
    path('crew/dispatch/', DispatchView.as_view(), name='crew_dispatch'),
    path('crew/navigation/', NavigationView.as_view(), name='crew_navigation'),
    path('crew/patient/', PatientDataView.as_view(), name='crew_patient'),
    path('crew/communication/', CommunicationView.as_view(), name='crew_communication'),
    path('crew/offline/', OfflineView.as_view(), name='crew_offline'),
    
    # PWA API Endpoints
    path('api/status/', update_ambulance_status, name='api_update_status'),
    path('api/gps/', update_gps_location, name='api_update_gps'),
    path('api/dispatch/current/', get_current_dispatch, name='api_current_dispatch'),
    path('api/health/', pwa_health_check, name='api_health_check'),
    
    # Dashboard and Real-time Tracking
    path('', views.ambulance_dashboard, name='dashboard'),
    path('real-time/', views.real_time_dashboard, name='real_time_dashboard'),

    # Mobile Dispatch Application
    path('mobile/', views_mobile.mobile_dashboard, name='mobile_dashboard'),
    path('mobile/dispatch/', views_mobile.mobile_dispatch_detail, name='mobile_dispatch_detail'),
    path('mobile/dispatch/<uuid:dispatch_id>/', views_mobile.mobile_dispatch_detail, name='mobile_dispatch_detail'),
    path('mobile/status/', views_mobile.mobile_status_update, name='mobile_status_update'),
    path('mobile/navigation/', views_mobile.mobile_navigation, name='mobile_navigation'),
    path('mobile/protocols/', views_mobile.mobile_protocols, name='mobile_protocols'),
    path('mobile/history/', views_mobile.mobile_dispatch_history, name='mobile_dispatch_history'),
    path('mobile/offline/', views_mobile.mobile_offline, name='mobile_offline'),
    path('mobile/install/', views_mobile.MobileInstallView.as_view(), name='mobile_install'),

    # Mobile API endpoints
    path('api/mobile/gps/', views_mobile.mobile_gps_update, name='mobile_gps_update'),
    path('api/mobile/status/', views_mobile.mobile_status_quick_update, name='mobile_status_quick_update'),

    # Real-time GPS Tracking
    path('gps/tracking/', views_gps.real_time_tracking_dashboard, name='gps_tracking_dashboard'),
    path('gps/traffic/', views_gps.traffic_conditions_view, name='traffic_conditions'),

    # Emergency Call Management
    path('emergency/', views_emergency.emergency_dispatch_center, name='emergency_dispatch_center'),
    path('emergency/calls/', views_emergency.EmergencyCallListView.as_view(), name='emergency_call_list'),
    path('emergency/calls/create/', views_emergency.EmergencyCallCreateView.as_view(), name='emergency_call_create'),
    path('emergency/calls/<uuid:pk>/', views_emergency.EmergencyCallDetailView.as_view(), name='emergency_call_detail'),
    path('emergency/calls/<uuid:pk>/update/', views_emergency.EmergencyCallUpdateView.as_view(), name='emergency_call_update'),
    path('emergency/calls/<uuid:pk>/assessment/', views_emergency.priority_assessment_view, name='priority_assessment'),

    # Emergency API endpoints
    path('api/emergency/quick-dispatch/', views_emergency.quick_dispatch, name='quick_dispatch'),
    path('api/emergency/update-status/', views_emergency.update_call_status, name='update_call_status'),

    # GPS API endpoints
    path('api/gps/update-enhanced/', views_gps.update_gps_location_enhanced, name='update_gps_enhanced'),
    path('api/gps/optimize-route/', views_gps.optimize_route, name='optimize_route'),
    path('api/gps/location-stream/<uuid:ambulance_id>/', views_gps.ambulance_location_stream, name='gps_location_stream'),
    path('api/gps/traffic/add/', views_gps.add_traffic_condition, name='add_traffic_condition'),

    # Ambulance management
    path('fleet/', views.fleet_list, name='fleet'),
    path('list/', views.AmbulanceListView.as_view(), name='ambulance_list'),
    path('detail/<uuid:pk>/', views.AmbulanceDetailView.as_view(), name='ambulance_detail'),
    path('add/', views.AmbulanceCreateView.as_view(), name='ambulance_add'),
    path('edit/<uuid:pk>/', views.AmbulanceUpdateView.as_view(), name='ambulance_edit'),

    # Dispatch management
    path('request/<uuid:referral_id>/', views.request_ambulance, name='request'),
    path('track/<uuid:dispatch_id>/', views.track_dispatch, name='track_dispatch'),
    path('dispatches/', views.DispatchListView.as_view(), name='dispatch_list'),
    path('dispatch/update-status/<uuid:dispatch_id>/', views.update_dispatch_status, name='update_dispatch_status'),
    path('control-center/', views.dispatch_control_center, name='dispatch_control_center'),

    # API endpoints
    path('api/gps/update/', views.update_gps_location, name='update_gps'),
    path('api/assign-ambulance/', views.assign_ambulance, name='assign_ambulance'),
    path('api/location-stream/<uuid:ambulance_id>/', views.ambulance_location_stream, name='location_stream'),
]