from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    # Doctor Search and Directory
    path('', views.DoctorListView.as_view(), name='doctor_list'),
    path('search/', views.DoctorSearchView.as_view(), name='doctor_search'),
    path('profile/<uuid:pk>/', views.DoctorProfileDetailView.as_view(), name='profile_detail'),
    path('emergency/', views.emergency_doctor_list, name='emergency_list'),
    
    # Doctor Registration and Profile Management
    path('register/', views.DoctorRegistrationView.as_view(), name='registration'),
    path('registration-success/', views.RegistrationSuccessView.as_view(), name='registration_success'),
    path('profile/<uuid:pk>/update/', views.DoctorProfileUpdateView.as_view(), name='profile_update'),
    
    # Doctor Dashboard
    path('dashboard/', views.DoctorDashboardView.as_view(), name='dashboard'),
    path('referrals/', views.ReferralDashboardView.as_view(), name='referral_dashboard'),
    
    # Availability Management
    path('availability/', views.AvailabilityManagementView.as_view(), name='availability_management'),
    path('availability/create/', views.AvailabilityCreateView.as_view(), name='availability_create'),
    path('availability/<uuid:pk>/update/', views.AvailabilityUpdateView.as_view(), name='availability_update'),
    path('availability/<uuid:pk>/delete/', views.AvailabilityDeleteView.as_view(), name='availability_delete'),
    path('availability/bulk-create/', views.BulkAvailabilityCreateView.as_view(), name='bulk_availability_create'),
    
    # Reviews
    path('profile/<uuid:doctor_id>/review/', views.DoctorReviewCreateView.as_view(), name='create_review'),
    
    # Hospital Views
    path('hospitals/', views.HospitalListView.as_view(), name='hospital_list'),
    path('hospitals/<uuid:pk>/', views.HospitalDetailView.as_view(), name='hospital_detail'),
    
    # Admin Views
    path('admin/verification-queue/', views.doctor_verification_queue, name='verification_queue'),
    
    # API Endpoints
    path('api/availability/<uuid:doctor_id>/', views.get_doctor_availability, name='api_doctor_availability'),
    path('api/search/', views.search_doctors_api, name='api_doctor_search'),
    path('api/calendar/', views.availability_calendar_api, name='api_availability_calendar'),
    path('api/referrals/<uuid:referral_id>/update/', views.update_referral_status, name='api_update_referral'),
]