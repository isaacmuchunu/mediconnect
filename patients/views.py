from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Patient, MedicalHistory, ConsentForm as ConsentFormModel
from .forms import PatientRegistrationForm, MedicalHistoryForm, ConsentForm

class PatientRegistrationView(CreateView):
    """View for patient registration"""
    model = Patient
    form_class = PatientRegistrationForm
    template_name = 'patients/registration.html'
    success_url = reverse_lazy('patients:medical_history_create')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Patient profile created successfully!')
        return super().form_valid(form)

class MedicalHistoryCreateView(LoginRequiredMixin, CreateView):
    """View for creating medical history"""
    model = MedicalHistory
    form_class = MedicalHistoryForm
    template_name = 'patients/medical_history_form.html'
    success_url = reverse_lazy('patients:consent_create')
    
    def form_valid(self, form):
        try:
            form.instance.patient = self.request.user.patient
            messages.success(self.request, 'Medical history saved successfully!')
            return super().form_valid(form)
        except Patient.DoesNotExist:
            messages.error(self.request, 'Please complete your patient profile first.')
            return redirect('patients:registration')

class MedicalHistoryUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating medical history"""
    model = MedicalHistory
    form_class = MedicalHistoryForm
    template_name = 'patients/medical_history_form.html'
    success_url = reverse_lazy('patients:dashboard')
    
    def get_object(self):
        return get_object_or_404(MedicalHistory, patient=self.request.user.patient)
    
    def form_valid(self, form):
        messages.success(self.request, 'Medical history updated successfully!')
        return super().form_valid(form)

class ConsentCreateView(LoginRequiredMixin, CreateView):
    """View for creating consent forms"""
    model = ConsentFormModel
    form_class = ConsentForm
    template_name = 'patients/consent_form.html'
    success_url = reverse_lazy('patients:dashboard')
    
    def form_valid(self, form):
        try:
            form.instance.patient = self.request.user.patient
            form.instance.consent_text = self.get_consent_text()
            form.instance.ip_address = self.request.META.get('REMOTE_ADDR')
            messages.success(self.request, 'Consent preferences saved successfully!')
            return super().form_valid(form)
        except Patient.DoesNotExist:
            messages.error(self.request, 'Please complete your patient profile first.')
            return redirect('patients:registration')
    
    def get_consent_text(self):
        # In a real application, this would pull from a database or file
        return """By providing consent, you agree to allow Hospital E-Referral System to collect, 
        process, and share your personal and medical information as specified in each consent option. 
        You can withdraw consent at any time by updating your preferences."""

class ConsentUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating consent forms"""
    model = ConsentFormModel
    form_class = ConsentForm
    template_name = 'patients/consent_form.html'
    success_url = reverse_lazy('patients:dashboard')
    
    def get_object(self):
        return get_object_or_404(ConsentFormModel, patient=self.request.user.patient, is_active=True)
    
    def form_valid(self, form):
        form.instance.signed_at = timezone.now()
        messages.success(self.request, 'Consent preferences updated successfully!')
        return super().form_valid(form)

@login_required
def patient_dashboard(request):
    """View for patient dashboard showing referrals, appointments, and medical summaries"""
    try:
        patient = request.user.patient
        medical_history = MedicalHistory.objects.filter(patient=patient).first()
        active_consent = ConsentFormModel.objects.filter(patient=patient, is_active=True).first()
        
        # Get referrals, appointments, and ambulance requests
        # These would be imported from their respective apps
        referrals = []
        appointments = []
        ambulance_requests = []
        
        try:
            # If the referrals app is installed and active
            from referrals.models import Referral
            referrals = Referral.objects.filter(patient=patient)
        except (ImportError, LookupError):
            pass
            
        try:
            # If the appointments app is installed and active
            from appointments.models import Appointment
            appointments = Appointment.objects.filter(patient=patient)
        except (ImportError, LookupError):
            pass
            
        try:
            # If the ambulances app is installed and active
            from ambulances.models import Dispatch
            ambulance_requests = Dispatch.objects.filter(referral__patient=patient)
        except (ImportError, LookupError):
            pass
        
        context = {
            'patient': patient,
            'medical_history': medical_history,
            'active_consent': active_consent,
            'referrals': referrals,
            'appointments': appointments,
            'ambulance_requests': ambulance_requests,
        }
        
        return render(request, 'patients/dashboard.html', context)
    except Patient.DoesNotExist:
        messages.info(request, 'Please complete your patient profile to access the dashboard.')
        return redirect('patients:registration')

@login_required
def referral_history(request):
    """View for searching and viewing referral history with status tracking"""
    try:
        patient = request.user.patient
        status_filter = request.GET.get('status', '')
        search_query = request.GET.get('search', '')
        
        try:
            # If the referrals app is installed and active
            from referrals.models import Referral
            
            referrals = Referral.objects.filter(patient=patient)
            
            # Apply filters if provided
            if status_filter:
                referrals = referrals.filter(status=status_filter)
                
            if search_query:
                referrals = referrals.filter(
                    Q(referring_doctor__name__icontains=search_query) |
                    Q(receiving_facility__name__icontains=search_query) |
                    Q(reason__icontains=search_query)
                )
            
            # Get linked ambulance dispatches
            try:
                from ambulances.models import Dispatch
                
                # Create a dictionary of referral_id -> dispatch for quick lookup
                dispatches = {}
                for dispatch in Dispatch.objects.filter(referral__patient=patient):
                    dispatches[dispatch.referral_id] = dispatch
                    
                # Add dispatch information to each referral
                for referral in referrals:
                    referral.dispatch = dispatches.get(referral.id)
            except (ImportError, LookupError):
                # If ambulances app is not available, continue without dispatch info
                pass
                
            context = {
                'referrals': referrals,
                'status_filter': status_filter,
                'search_query': search_query,
                'statuses': Referral.STATUS_CHOICES,  # For the filter dropdown
            }
            
            return render(request, 'patients/referral_history.html', context)
        except (ImportError, LookupError):
            messages.info(request, 'Referral functionality is not available.')
            return redirect('patients:dashboard')
    except Patient.DoesNotExist:
        messages.info(request, 'Please complete your patient profile to access referral history.')
        return redirect('patients:registration')