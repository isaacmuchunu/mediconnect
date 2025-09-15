from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    UserViewSet, PatientViewSet, MedicalHistoryViewSet,
    DoctorProfileViewSet, ReferralViewSet,
    AppointmentViewSet, AmbulanceViewSet, NotificationViewSet,
    ReportViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'patients', PatientViewSet)
router.register(r'patient-history', MedicalHistoryViewSet)
router.register(r'doctors', DoctorProfileViewSet)
router.register(r'referrals', ReferralViewSet)
router.register(r'appointments', AppointmentViewSet)
router.register(r'ambulances', AmbulanceViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'reports', ReportViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
]