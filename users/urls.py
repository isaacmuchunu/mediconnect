from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    ChooseRoleView, PatientRegisterView, StaffRegisterView, VerifyEmailView, VerifyEmailMessageView,
    UserLoginView, ProfileView, ProfileUpdateView, UserPasswordResetView, UserPasswordResetConfirmView
)

app_name = 'users'

urlpatterns = [
    # Registration
    path('register/', ChooseRoleView.as_view(), name='register_choice'),
    path('register/patient/', PatientRegisterView.as_view(), name='register_patient'),
    path('register/staff/', StaffRegisterView.as_view(), name='register_staff'),
    path('verify/<uuid:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('verify-email-message/', VerifyEmailMessageView.as_view(), name='verify_email_message'),
    
    # Authentication
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='logout'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    
    # Password Reset
    path('password-reset/', UserPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', UserPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'),
]