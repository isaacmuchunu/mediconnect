from django.urls import path
from . import views

app_name = 'referrals'

urlpatterns = [
    path('', views.ListReferralsView.as_view(), name='list'),
    path('create/', views.CreateReferralView.as_view(), name='create'),
    path('<int:pk>/', views.ReferralDetailView.as_view(), name='detail'),
    path('accept/<int:referral_id>/', views.accept_referral, name='accept'),
    path('decline/<int:referral_id>/', views.decline_referral, name='decline'),
    path('complete/<int:referral_id>/', views.complete_referral, name='complete'),
    path('dashboard/', views.referral_dashboard, name='dashboard'),
]