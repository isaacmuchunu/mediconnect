from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.contrib import messages
from django.db.models import Q, Avg, Count, F
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, timedelta, date
import json

from .models import (
    DoctorProfile, Hospital, Specialty, Availability, 
    DoctorReview, ReferralStats, EmergencyContact
)
from .forms import (
    DoctorRegistrationForm, DoctorProfileUpdateForm, AvailabilityForm,
    DoctorSearchForm, DoctorReviewForm
)


class DoctorListView(ListView):
    """View for listing all verified doctors"""
    model = DoctorProfile
    template_name = 'doctors/doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 20

    def get_queryset(self):
        return DoctorProfile.objects.filter(
            verification_status='verified',
            is_active=True
        ).order_by('last_name', 'first_name')

class DoctorSearchView(ListView):
    """Search for doctors by various criteria"""
    model = DoctorProfile
    template_name = 'doctors/search.html'
    context_object_name = 'doctors'
    paginate_by = 12

    def get_queryset(self):
        queryset = DoctorProfile.objects.filter(
            verification_status='verified',
            is_active=True
        ).select_related(
            'primary_specialty', 'primary_hospital'
        ).prefetch_related('specialties', 'affiliated_hospitals')
        
        # Search parameters
        query = self.request.GET.get('q')
        specialty = self.request.GET.get('specialty')
        location = self.request.GET.get('location')
        hospital = self.request.GET.get('hospital')
        min_rating = self.request.GET.get('min_rating')
        accepts_insurance = self.request.GET.get('accepts_insurance')
        telehealth = self.request.GET.get('telehealth')
        emergency_available = self.request.GET.get('emergency_available')
        gender = self.request.GET.get('gender')
        sort_by = self.request.GET.get('sort_by', 'name')

        # Apply filters
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(specialties__name__icontains=query) |
                Q(primary_hospital__name__icontains=query)
            ).distinct()

        if specialty:
            queryset = queryset.filter(
                Q(primary_specialty__id=specialty) |
                Q(specialties__id=specialty)
            ).distinct()

        if location:
            queryset = queryset.filter(
                Q(city__icontains=location) |
                Q(state__icontains=location) |
                Q(zip_code__icontains=location)
            )

        if hospital:
            queryset = queryset.filter(
                Q(primary_hospital__id=hospital) |
                Q(affiliated_hospitals__id=hospital)
            ).distinct()

        if min_rating:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(average_rating__gte=min_rating)
            except ValueError:
                pass

        if accepts_insurance == 'true':
            queryset = queryset.filter(accepts_insurance=True)

        if telehealth == 'true':
            queryset = queryset.filter(telehealth_available=True)

        if emergency_available == 'true':
            queryset = queryset.filter(emergency_availability=True)

        if gender:
            queryset = queryset.filter(gender=gender)

        # Sorting
        if sort_by == 'rating':
            queryset = queryset.order_by('-average_rating', 'last_name')
        elif sort_by == 'experience':
            queryset = queryset.order_by('-years_of_experience', 'last_name')
        elif sort_by == 'name':
            queryset = queryset.order_by('last_name', 'first_name')
        elif sort_by == 'location':
            queryset = queryset.order_by('city', 'state', 'last_name')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = DoctorSearchForm(self.request.GET)
        context['specialties'] = Specialty.objects.filter(is_active=True).order_by('name')
        context['hospitals'] = Hospital.objects.filter(is_active=True).order_by('name')
        context['search_params'] = self.request.GET.dict()
        
        # Statistics for search results
        if self.get_queryset():
            context['total_results'] = self.get_queryset().count()
            context['avg_rating'] = self.get_queryset().aggregate(
                avg_rating=Avg('average_rating')
            )['avg_rating'] or 0
        else:
            context['total_results'] = 0
            context['avg_rating'] = 0
            
        return context


class DoctorProfileDetailView(DetailView):
    """Detailed view of doctor profile"""
    model = DoctorProfile
    template_name = 'doctors/profile_detail.html'
    context_object_name = 'doctor'

    def get_queryset(self):
        return DoctorProfile.objects.filter(
            verification_status='verified',
            is_active=True
        ).select_related(
            'primary_specialty', 'primary_hospital'
        ).prefetch_related(
            'specialties', 'affiliated_hospitals', 'reviews'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.get_object()
        
        # Get recent reviews
        context['recent_reviews'] = doctor.reviews.filter(
            is_approved=True
        ).order_by('-created_at')[:5]
        
        # Get upcoming availability
        today = timezone.now().date()
        context['upcoming_availability'] = doctor.availability_slots.filter(
            date__gte=today,
            status='available'
        ).order_by('date', 'start_time')[:10]
        
        # Get affiliated hospitals
        context['affiliated_hospitals'] = doctor.affiliated_hospitals.filter(is_active=True)
        
        # Review statistics
        reviews = doctor.reviews.filter(is_approved=True)
        if reviews.exists():
            context['review_stats'] = {
                'total_reviews': reviews.count(),
                'avg_bedside_manner': reviews.aggregate(avg=Avg('bedside_manner_rating'))['avg'],
                'avg_communication': reviews.aggregate(avg=Avg('communication_rating'))['avg'],
                'avg_expertise': reviews.aggregate(avg=Avg('expertise_rating'))['avg'],
                'recommend_percentage': (reviews.filter(would_recommend=True).count() / reviews.count()) * 100
            }
        
        # Referral statistics
        try:
            context['referral_stats'] = doctor.referral_stats
        except ReferralStats.DoesNotExist:
            context['referral_stats'] = None
            
        return context


class DoctorRegistrationView(CreateView):
    """Doctor registration view"""
    model = DoctorProfile
    form_class = DoctorRegistrationForm
    template_name = 'doctors/registration.html'
    success_url = reverse_lazy('doctors:registration_success')

    def form_valid(self, form):
        # Create user account
        user = User.objects.create_user(
            username=form.cleaned_data['email'],
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
        )
        
        # Create doctor profile
        form.instance.user = user
        response = super().form_valid(form)
        
        # Create referral stats record
        ReferralStats.objects.create(doctor=self.object)
        
        messages.success(
            self.request,
            'Registration successful! Your profile is pending verification.'
        )
        return response


class DoctorProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update doctor profile"""
    model = DoctorProfile
    form_class = DoctorProfileUpdateForm
    template_name = 'doctors/profile_update.html'

    def test_func(self):
        doctor = self.get_object()
        return self.request.user == doctor.user or self.request.user.is_staff

    def get_success_url(self):
        messages.success(self.request, 'Profile updated successfully!')
        return reverse('doctors:profile_detail', kwargs={'pk': self.object.pk})


class DoctorDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Doctor dashboard with metrics and management tools"""
    template_name = 'doctors/dashboard.html'

    def test_func(self):
        return hasattr(self.request.user, 'doctor_profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.request.user.doctor_profile
        
        # Dashboard metrics
        today = timezone.now().date()
        
        # Upcoming appointments
        context['upcoming_appointments'] = doctor.availability_slots.filter(
            date__gte=today,
            current_bookings__gt=0
        ).order_by('date', 'start_time')[:5]
        
        # Recent reviews
        context['recent_reviews'] = doctor.reviews.filter(
            is_approved=True
        ).order_by('-created_at')[:3]
        
        # Performance metrics
        context['metrics'] = {
            'total_patients_today': doctor.availability_slots.filter(
                date=today
            ).aggregate(total=Count('current_bookings'))['total'] or 0,
            
            'avg_rating': doctor.average_rating,
            'total_reviews': doctor.total_reviews,
            
            'availability_this_week': doctor.availability_slots.filter(
                date__range=[today, today + timedelta(days=7)],
                status='available'
            ).count(),
            
            'referral_acceptance_rate': doctor.referral_acceptance_rate,
        }
        
        # Referral statistics
        try:
            referral_stats = doctor.referral_stats
            context['referral_metrics'] = {
                'pending_referrals': referral_stats.referrals_pending,
                'total_received': referral_stats.total_referrals_received,
                'acceptance_rate': referral_stats.acceptance_rate,
                'avg_response_time': referral_stats.average_response_time,
            }
        except ReferralStats.DoesNotExist:
            context['referral_metrics'] = None
        
        # Calendar integration status
        context['calendar_integrated'] = bool(doctor.availability_slots.filter(
            google_calendar_event_id__isnull=False
        ).exists())
        
        return context


class AvailabilityManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Manage doctor availability"""
    template_name = 'doctors/availability_management.html'

    def test_func(self):
        return hasattr(self.request.user, 'doctor_profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.request.user.doctor_profile
        
        # Get availability for next 30 days
        today = timezone.now().date()
        end_date = today + timedelta(days=30)
        
        context['availability_slots'] = doctor.availability_slots.filter(
            date__range=[today, end_date]
        ).order_by('date', 'start_time')
        
        context['form'] = AvailabilityForm()
        context['bulk_form'] = BulkAvailabilityForm()
        context['hospitals'] = Hospital.objects.filter(is_active=True)
        
        return context


class AvailabilityCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create availability slot"""
    model = Availability
    form_class = AvailabilityForm
    template_name = 'doctors/availability_form.html'

    def test_func(self):
        return hasattr(self.request.user, 'doctor_profile')

    def form_valid(self, form):
        form.instance.doctor = self.request.user.doctor_profile
        form.instance.weekday = form.cleaned_data['date'].strftime('%A').lower()
        response = super().form_valid(form)
        messages.success(self.request, 'Availability slot created successfully!')
        return response

    def get_success_url(self):
        return reverse('doctors:availability_management')


class AvailabilityUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update availability slot"""
    model = Availability
    form_class = AvailabilityForm
    template_name = 'doctors/availability_form.html'

    def test_func(self):
        availability = self.get_object()
        return availability.doctor.user == self.request.user

    def get_success_url(self):
        messages.success(self.request, 'Availability updated successfully!')
        return reverse('doctors:availability_management')


class AvailabilityDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete availability slot"""
    model = Availability

    def test_func(self):
        availability = self.get_object()
        return availability.doctor.user == self.request.user

    def get_success_url(self):
        messages.success(self.request, 'Availability slot deleted successfully!')
        return reverse('doctors:availability_management')


class BulkAvailabilityCreateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Create multiple availability slots at once"""
    template_name = 'doctors/bulk_availability.html'

    def test_func(self):
        return hasattr(self.request.user, 'doctor_profile')

    def post(self, request, *args, **kwargs):
        form = BulkAvailabilityForm(request.POST)
        if form.is_valid():
            doctor = request.user.doctor_profile
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            days_of_week = form.cleaned_data['days_of_week']
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            location = form.cleaned_data['location']
            appointment_type = form.cleaned_data['appointment_type']
            slot_duration = form.cleaned_data['slot_duration']
            max_patients = form.cleaned_data['max_patients']

            created_slots = []
            current_date = start_date

            while current_date <= end_date:
                weekday = current_date.strftime('%A').lower()
                if weekday in days_of_week:
                    # Check if slot already exists
                    existing = Availability.objects.filter(
                        doctor=doctor,
                        date=current_date,
                        start_time=start_time,
                        location=location
                    ).exists()

                    if not existing:
                        availability = Availability.objects.create(
                            doctor=doctor,
                            date=current_date,
                            start_time=start_time,
                            end_time=end_time,
                            weekday=weekday,
                            location=location,
                            appointment_type=appointment_type,
                            slot_duration=slot_duration,
                            max_patients=max_patients,
                        )
                        created_slots.append(availability)

                current_date += timedelta(days=1)

            messages.success(
                request,
                f'Successfully created {len(created_slots)} availability slots!'
            )
            return redirect('doctors:availability_management')
        else:
            return self.render_to_response({'form': form})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BulkAvailabilityForm()
        context['hospitals'] = Hospital.objects.filter(is_active=True)
        return context


@login_required
def availability_calendar_api(request):
    """API endpoint for calendar view of availability"""
    if not hasattr(request.user, 'doctor_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    doctor = request.user.doctor_profile
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)

        availability_slots = doctor.availability_slots.filter(
            date__range=[start_date, end_date]
        )

        events = []
        for slot in availability_slots:
            events.append({
                'id': str(slot.id),
                'title': f'{slot.get_appointment_type_display()} - {slot.location.name}',
                'start': f'{slot.date}T{slot.start_time}',
                'end': f'{slot.date}T{slot.end_time}',
                'backgroundColor': {
                    'available': '#28a745',
                    'booked': '#ffc107',
                    'blocked': '#dc3545',
                    'emergency': '#17a2b8'
                }.get(slot.status, '#6c757d'),
                'extendedProps': {
                    'status': slot.status,
                    'current_bookings': slot.current_bookings,
                    'max_patients': slot.max_patients,
                    'location': slot.location.name,
                }
            })

        return JsonResponse(events, safe=False)

    return JsonResponse({'error': 'Missing date parameters'}, status=400)


class DoctorReviewCreateView(CreateView):
    """Create a review for a doctor"""
    model = DoctorReview
    form_class = DoctorReviewForm
    template_name = 'doctors/review_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor'] = get_object_or_404(DoctorProfile, pk=self.kwargs['doctor_id'])
        return context

    def form_valid(self, form):
        doctor = get_object_or_404(DoctorProfile, pk=self.kwargs['doctor_id'])
        form.instance.doctor = doctor
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            'Thank you for your review! It will be published after approval.'
        )
        return response

    def get_success_url(self):
        return reverse('doctors:profile_detail', kwargs={'pk': self.kwargs['doctor_id']})


class ReferralDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard for managing referrals"""
    template_name = 'doctors/referral_dashboard.html'

    def test_func(self):
        return hasattr(self.request.user, 'doctor_profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.request.user.doctor_profile

        # Import here to avoid circular imports
        from referrals.models import Referral

        # Incoming referrals
        context['incoming_referrals'] = Referral.objects.filter(
            referred_to=doctor,
            status__in=['pending', 'accepted']
        ).select_related('patient', 'referring_doctor').order_by('-created_at')[:10]

        # Outgoing referrals
        context['outgoing_referrals'] = Referral.objects.filter(
            referring_doctor=doctor
        ).select_related('patient', 'referred_to').order_by('-created_at')[:10]

        # Referral statistics
        try:
            stats = doctor.referral_stats
            context['referral_stats'] = {
                'pending': stats.referrals_pending,
                'accepted': stats.referrals_accepted,
                'declined': stats.referrals_declined,
                'acceptance_rate': stats.acceptance_rate,
                'avg_response_time': stats.average_response_time,
            }
        except ReferralStats.DoesNotExist:
            context['referral_stats'] = None

        return context


@login_required
def update_referral_status(request, referral_id):
    """AJAX endpoint to update referral status"""
    if not hasattr(request.user, 'doctor_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        try:
            # Import here to avoid circular imports
            from referrals.models import Referral
            
            referral = get_object_or_404(Referral, id=referral_id)
            
            # Check if user is authorized to update this referral
            if referral.referred_to.user != request.user:
                return JsonResponse({'error': 'Unauthorized'}, status=403)

            data = json.loads(request.body)
            new_status = data.get('status')
            notes = data.get('notes', '')

            if new_status in ['accepted', 'declined']:
                referral.status = new_status
                if notes:
                    referral.response_notes = notes
                referral.response_date = timezone.now()
                referral.save()

                # Update doctor's referral statistics
                stats = referral.referred_to.referral_stats
                if new_status == 'accepted':
                    stats.referrals_accepted += 1
                else:
                    stats.referrals_declined += 1
                
                stats.referrals_pending = max(0, stats.referrals_pending - 1)
                stats.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Referral {new_status} successfully!'
                })
            else:
                return JsonResponse({'error': 'Invalid status'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


class DoctorListView(ListView):
    """List all verified doctors"""
    model = DoctorProfile
    template_name = 'doctors/doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 20

    def get_queryset(self):
        return DoctorProfile.objects.filter(
            verification_status='verified',
            is_active=True
        ).select_related(
            'primary_specialty', 'primary_hospital'
        ).order_by('last_name', 'first_name')


class HospitalListView(ListView):
    """List all hospitals"""
    model = Hospital
    template_name = 'doctors/hospital_list.html'
    context_object_name = 'hospitals'
    paginate_by = 20

    def get_queryset(self):
        return Hospital.objects.filter(is_active=True).order_by('name')


class HospitalDetailView(DetailView):
    """Detailed view of hospital"""
    model = Hospital
    template_name = 'doctors/hospital_detail.html'
    context_object_name = 'hospital'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital = self.get_object()
        
        # Get doctors affiliated with this hospital
        context['affiliated_doctors'] = DoctorProfile.objects.filter(
            Q(primary_hospital=hospital) | Q(affiliated_hospitals=hospital),
            verification_status='verified',
            is_active=True
        ).distinct().select_related('primary_specialty')[:12]
        
        # Get specialties available at this hospital
        context['available_specialties'] = Specialty.objects.filter(
            doctors__in=context['affiliated_doctors']
        ).distinct().order_by('name')
        
        return context


@login_required
def doctor_verification_queue(request):
    """View for admins to verify doctor profiles"""
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access this page.")

    pending_doctors = DoctorProfile.objects.filter(
        verification_status='pending'
    ).order_by('created_at')

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        action = request.POST.get('action')
        
        try:
            doctor = DoctorProfile.objects.get(id=doctor_id)
            
            if action == 'approve':
                doctor.verification_status = 'verified'
                doctor.verification_date = timezone.now()
                doctor.verified_by = request.user
                doctor.save()
                messages.success(request, f'Dr. {doctor.full_name} has been verified.')
                
            elif action == 'reject':
                doctor.verification_status = 'rejected'
                doctor.verification_date = timezone.now()
                doctor.verified_by = request.user
                doctor.save()
                messages.warning(request, f'Dr. {doctor.full_name} verification has been rejected.')
                
        except DoctorProfile.DoesNotExist:
            messages.error(request, 'Doctor not found.')

        return redirect('doctors:verification_queue')

    return render(request, 'doctors/verification_queue.html', {
        'pending_doctors': pending_doctors
    })


@login_required
def emergency_doctor_list(request):
    """List of doctors available for emergency consultations"""
    emergency_doctors = DoctorProfile.objects.filter(
        verification_status='verified',
        is_active=True,
        emergency_availability=True
    ).select_related('primary_specialty', 'primary_hospital')

    # Filter by specialty if provided
    specialty_id = request.GET.get('specialty')
    if specialty_id:
        emergency_doctors = emergency_doctors.filter(
            Q(primary_specialty__id=specialty_id) | 
            Q(specialties__id=specialty_id)
        ).distinct()

    # Filter by location if provided
    location = request.GET.get('location')
    if location:
        emergency_doctors = emergency_doctors.filter(
            Q(city__icontains=location) |
            Q(state__icontains=location)
        )

    return render(request, 'doctors/emergency_list.html', {
        'emergency_doctors': emergency_doctors,
        'specialties': Specialty.objects.filter(is_active=True).order_by('name'),
    })


class RegistrationSuccessView(TemplateView):
    """Success page after doctor registration"""
    template_name = 'doctors/registration_success.html'


# AJAX Views for dynamic functionality

@login_required
def get_doctor_availability(request, doctor_id):
    """Get doctor's availability for booking"""
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter required'}, status=400)
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    availability_slots = doctor.availability_slots.filter(
        date=selected_date,
        status='available'
    ).order_by('start_time')
    
    slots_data = []
    for slot in availability_slots:
        if slot.is_available:
            slots_data.append({
                'id': str(slot.id),
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'location': slot.location.name,
                'appointment_type': slot.get_appointment_type_display(),
                'available_spots': slot.max_patients - slot.current_bookings,
            })
    
    return JsonResponse({'slots': slots_data})


@login_required
def search_doctors_api(request):
    """API endpoint for dynamic doctor search"""
    query = request.GET.get('q', '')
    specialty = request.GET.get('specialty', '')
    limit = int(request.GET.get('limit', 10))
    
    doctors = DoctorProfile.objects.filter(
        verification_status='verified',
        is_active=True
    )
    
    if query:
        doctors = doctors.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    
    if specialty:
        doctors = doctors.filter(
            Q(primary_specialty__name__icontains=specialty) |
            Q(specialties__name__icontains=specialty)
        ).distinct()
    
    doctors = doctors.select_related('primary_specialty')[:limit]
    
    results = []
    for doctor in doctors:
        results.append({
            'id': str(doctor.id),
            'name': doctor.full_name,
            'specialty': doctor.primary_specialty.name if doctor.primary_specialty else '',
            'hospital': doctor.primary_hospital.name if doctor.primary_hospital else '',
            'rating': float(doctor.average_rating),
            'photo_url': doctor.profile_photo.url if doctor.profile_photo else None,
        })
    
    return JsonResponse({'doctors': results})