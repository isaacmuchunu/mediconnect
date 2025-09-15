from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse_lazy
import datetime
from .models import Appointment
from .forms import AppointmentForm, AppointmentSearchForm, RescheduleAppointmentForm
from referrals.models import Referral

class BookAppointmentView(View):
    def get(self, request, referral_id):
        referral = get_object_or_404(Referral, id=referral_id)
        form = AppointmentForm()
        return render(request, 'appointments/book.html', {
            'referral': referral,
            'form': form
        })

    def post(self, request, referral_id):
        referral = get_object_or_404(Referral, id=referral_id)
        form = AppointmentForm(request.POST)
        
        if form.is_valid():
            appointment_date = form.cleaned_data['appointment_date']
            appointment_time = form.cleaned_data['appointment_time']
            
            # Combine date and time
            appointment_datetime = timezone.make_aware(
                datetime.datetime.combine(appointment_date, appointment_time)
            )
            
            appointment = Appointment(
                referral=referral,
                appointment_date=appointment_datetime,
                status=form.cleaned_data['status']
            )
            appointment.save()
            messages.success(request, 'Appointment booked successfully!')
            return redirect('appointments:calendar')
        else:
            return render(request, 'appointments/book.html', {
                'referral': referral,
                'form': form
            })

class CalendarView(View):
    def get(self, request):
        search_form = AppointmentSearchForm(request.GET)
        appointments = Appointment.objects.select_related('referral__patient', 'referral__doctor').all()
        
        # Apply filters
        if search_form.is_valid():
            if search_form.cleaned_data['status']:
                appointments = appointments.filter(status=search_form.cleaned_data['status'])
            
            if search_form.cleaned_data['date_from']:
                appointments = appointments.filter(
                    appointment_date__date__gte=search_form.cleaned_data['date_from']
                )
            
            if search_form.cleaned_data['date_to']:
                appointments = appointments.filter(
                    appointment_date__date__lte=search_form.cleaned_data['date_to']
                )
            
            if search_form.cleaned_data['patient_name']:
                appointments = appointments.filter(
                    referral__patient__name__icontains=search_form.cleaned_data['patient_name']
                )
        
        appointments = appointments.order_by('appointment_date')
        
        return render(request, 'appointments/calendar.html', {
            'appointments': appointments,
            'search_form': search_form
        })

class AppointmentListView(ListView):
    model = Appointment
    template_name = 'appointments/list.html'
    context_object_name = 'appointments'
    paginate_by = 20
    
    def get_queryset(self):
        return Appointment.objects.select_related(
            'referral__patient', 'referral__doctor'
        ).order_by('-appointment_date')

class AppointmentDetailView(DetailView):
    model = Appointment
    template_name = 'appointments/detail.html'
    context_object_name = 'appointment'
    
    def get_object(self):
        return get_object_or_404(
            Appointment.objects.select_related('referral__patient', 'referral__doctor'),
            pk=self.kwargs['pk']
        )

class RescheduleAppointmentView(UpdateView):
    model = Appointment
    form_class = RescheduleAppointmentForm
    template_name = 'appointments/reschedule.html'
    success_url = reverse_lazy('appointments:calendar')
    
    def form_valid(self, form):
        appointment = self.get_object()
        new_date = form.cleaned_data['new_appointment_date']
        new_time = form.cleaned_data['new_appointment_time']
        
        # Combine new date and time
        new_datetime = timezone.make_aware(
            datetime.datetime.combine(new_date, new_time)
        )
        
        appointment.appointment_date = new_datetime
        appointment.save()
        
        messages.success(self.request, 'Appointment rescheduled successfully!')
        return super().form_valid(form)

def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    
    if request.method == 'POST':
        appointment.status = 'canceled'
        appointment.save()
        messages.success(request, 'Appointment canceled successfully!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Appointment canceled successfully!'})
        
        return redirect('appointments:calendar')
    
    return render(request, 'appointments/cancel_confirm.html', {'appointment': appointment})

def complete_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    
    if request.method == 'POST':
        appointment.status = 'completed'
        appointment.save()
        messages.success(request, 'Appointment marked as completed!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Appointment completed!'})
        
        return redirect('appointments:calendar')
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def appointment_dashboard(request):
    today = timezone.now().date()
    
    # Statistics
    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(appointment_date__date=today).count()
    scheduled_appointments = Appointment.objects.filter(status='scheduled').count()
    completed_appointments = Appointment.objects.filter(status='completed').count()
    
    # Recent appointments
    recent_appointments = Appointment.objects.select_related(
        'referral__patient', 'referral__doctor'
    ).order_by('-appointment_date')[:10]
    
    # Upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        appointment_date__gte=timezone.now(),
        status='scheduled'
    ).select_related('referral__patient', 'referral__doctor').order_by('appointment_date')[:5]
    
    context = {
        'total_appointments': total_appointments,
        'today_appointments': today_appointments,
        'scheduled_appointments': scheduled_appointments,
        'completed_appointments': completed_appointments,
        'recent_appointments': recent_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    
    return render(request, 'appointments/dashboard.html', context)