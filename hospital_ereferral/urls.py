from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from users.views import LandingPageView, HomeView, CSSTestView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingPageView.as_view(), name='landing'),
    path('home/', HomeView.as_view(), name='home'),
    path('css-test/', CSSTestView.as_view(), name='css_test'),
    path('users/', include('users.urls', namespace='users')),
    path('patients/', include('patients.urls', namespace='patients')),
    path('doctors/', include('doctors.urls', namespace='doctors')),
    path('referrals/', include('referrals.urls', namespace='referrals')),
    path('appointments/', include('appointments.urls', namespace='appointments')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('ambulances/', include('ambulances.urls', namespace='ambulances')),
    path('hospitals/', include('hospitals.urls', namespace='hospitals')),
    path('communications/', include('communications.urls', namespace='communications')),
    path('analytics/', include('analytics.urls', namespace='analytics')),
    path('api/', include('api.urls')),
]