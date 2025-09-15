from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import CreateView, UpdateView, TemplateView
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetConfirmView
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Profile, DoctorProfile, PatientProfile, AmbulanceStaffProfile
from .forms import (
    PatientRegistrationForm, StaffRegistrationForm, ProfileUpdateForm,
    DoctorProfileForm, PatientProfileForm, AmbulanceStaffProfileForm,
    CustomLoginForm
)

# --- Home and Dashboard Views ---

class LandingPageView(View):
    """Professional landing page for the hospital e-referral system"""
    def get(self, request):
        return render(request, 'landing.html')


class CSSTestView(View):
    """CSS test page to verify Tailwind CSS functionality"""
    def get(self, request):
        return render(request, 'css_test.html')


class HomeView(View):
    """Main home view that redirects users to appropriate dashboards"""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('users:login')

        # Redirect based on user role
        if request.user.role == User.Role.PATIENT:
            return redirect('patients:dashboard')
        elif request.user.role == User.Role.DOCTOR:
            return redirect('doctors:dashboard')
        elif request.user.role == User.Role.AMBULANCE_STAFF:
            return redirect('ambulances:dashboard')
        elif request.user.role == User.Role.ADMIN or request.user.is_staff:
            return redirect('admin:index')
        else:
            return redirect('users:profile')

# --- Registration Views ---

class ChooseRoleView(TemplateView):
    template_name = 'users/choose_role.html'

class PatientRegisterView(CreateView):
    model = User
    form_class = PatientRegistrationForm
    template_name = 'users/register_patient.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, 'Registration successful! You can now log in.')
        return redirect(self.success_url)

class StaffRegisterView(CreateView):
    model = User
    form_class = StaffRegistrationForm
    template_name = 'users/register_staff.html'

    def get_success_url(self):
        return reverse('verify_email_message')

    def form_valid(self, form):
        user = form.save()

        # Send verification email
        token = user.verification_token
        verify_url = self.request.build_absolute_uri(reverse('verify_email', kwargs={'token': token}))
        send_mail(
            'Verify Your Email Address',
            f'Hi {user.username},\n\nPlease click the link to verify your email: {verify_url}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return redirect(self.get_success_url())

class VerifyEmailView(View):
    def get(self, request, token):
        user = get_object_or_404(User, verification_token=token)
        if not user.is_active:
            user.is_active = True
            user.save()
            messages.success(request, 'Your email has been verified! Please wait for an administrator to approve your account.')
        else:
            messages.info(request, 'This account has already been verified.')
        return redirect('users:login')

class VerifyEmailMessageView(TemplateView):
    template_name = 'users/verify_email_message.html'

# --- Authentication and Profile Views ---

class UserLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = CustomLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_active:
            messages.error(self.request, 'This account is inactive. Please verify your email.')
            return self.form_invalid(form)
        if user.role in [User.Role.DOCTOR, User.Role.AMBULANCE_STAFF] and not user.is_verified:
            messages.error(self.request, 'This account has not been approved by an administrator yet.')
            return self.form_invalid(form)
        
        login(self.request, user)
        messages.success(self.request, f'Welcome back, {user.get_full_name() or user.username}!')
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username/email or password. Please check your credentials and try again.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('home')

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

class ProfileUpdateView(LoginRequiredMixin, View):
    template_name = 'users/profile_form.html'

    def get(self, request, *args, **kwargs):
        profile_form = ProfileUpdateForm(instance=request.user.profile)
        role_form = self.get_role_form(request.user)
        return render(request, self.template_name, {'profile_form': profile_form, 'role_form': role_form})

    def post(self, request, *args, **kwargs):
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        role_form = self.get_role_form(request.user, data=request.POST)

        if profile_form.is_valid() and (role_form is None or role_form.is_valid()):
            profile_form.save()
            if role_form:
                role_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile')
        
        return render(request, self.template_name, {'profile_form': profile_form, 'role_form': role_form})

    def get_role_form(self, user, data=None):
        if user.role == User.Role.DOCTOR:
            return DoctorProfileForm(data, instance=user.doctor_profile)
        if user.role == User.Role.PATIENT:
            return PatientProfileForm(data, instance=user.patient_profile)
        if user.role == User.Role.AMBULANCE_STAFF:
            return AmbulanceStaffProfileForm(data, instance=user.ambulance_staff_profile)
        return None

# --- Password Reset Views ---

class UserPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset_form.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')

class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')