from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    # Patient registration and profile
    path('register/', views.PatientRegistrationView.as_view(), name='registration'),
    
    # Medical history management
    path('medical-history/create/', views.MedicalHistoryCreateView.as_view(), name='medical_history_create'),
    path('medical-history/update/', views.MedicalHistoryUpdateView.as_view(), name='medical_history_update'),
    
    # Consent management
    path('consent/create/', views.ConsentCreateView.as_view(), name='consent_create'),
    path('consent/update/', views.ConsentUpdateView.as_view(), name='consent_update'),
    
    # Dashboard and history
    path('dashboard/', views.patient_dashboard, name='dashboard'),
    path('referrals/', views.referral_history, name='referral_history'),
]