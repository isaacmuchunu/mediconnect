"""
Emergency Call Management Views
Comprehensive emergency call intake and dispatch management
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
# GIS functionality removed - using standard latitude/longitude fields instead

from .models import EmergencyCall, CallStatusHistory, CallPriorityAssessment, Ambulance, Dispatch
from .forms_emergency import EmergencyCallForm, CallPriorityAssessmentForm


def is_dispatcher(user):
    """Check if user is a dispatcher"""
    return user.is_authenticated and (
        user.is_staff or 
        user.role in ['DISPATCHER', 'ADMIN'] or
        user.groups.filter(name='Dispatchers').exists()
    )


def is_call_taker(user):
    """Check if user is authorized to take emergency calls"""
    return user.is_authenticated and (
        user.is_staff or 
        user.role in ['DISPATCHER', 'CALL_TAKER', 'ADMIN'] or
        user.groups.filter(name__in=['Dispatchers', 'Call Takers']).exists()
    )


class EmergencyCallListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List view for emergency calls with filtering and search"""
    
    model = EmergencyCall
    template_name = 'ambulances/emergency_calls/call_list.html'
    context_object_name = 'calls'
    paginate_by = 25
    
    def test_func(self):
        return is_call_taker(self.request.user)
    
    def get_queryset(self):
        queryset = EmergencyCall.objects.select_related(
            'call_taker', 'dispatcher'
        ).prefetch_related('status_history')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by priority
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by call type
        call_type = self.request.GET.get('call_type')
        if call_type:
            queryset = queryset.filter(call_type=call_type)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(call_number__icontains=search) |
                Q(caller_name__icontains=search) |
                Q(patient_name__icontains=search) |
                Q(incident_address__icontains=search) |
                Q(chief_complaint__icontains=search)
            )
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(received_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(received_at__date__lte=date_to)
        
        return queryset.order_by('-received_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context.update({
            'status_choices': EmergencyCall.STATUS_CHOICES,
            'priority_choices': EmergencyCall.PRIORITY_CHOICES,
            'call_type_choices': EmergencyCall.CALL_TYPE_CHOICES,
            'current_filters': {
                'status': self.request.GET.get('status', ''),
                'priority': self.request.GET.get('priority', ''),
                'call_type': self.request.GET.get('call_type', ''),
                'search': self.request.GET.get('search', ''),
                'date_from': self.request.GET.get('date_from', ''),
                'date_to': self.request.GET.get('date_to', ''),
            }
        })
        
        # Add statistics
        context['stats'] = {
            'total_calls': EmergencyCall.objects.count(),
            'active_calls': EmergencyCall.objects.filter(
                status__in=['received', 'processing', 'dispatched']
            ).count(),
            'critical_calls': EmergencyCall.objects.filter(
                priority='critical',
                status__in=['received', 'processing', 'dispatched']
            ).count(),
            'avg_response_time': EmergencyCall.objects.filter(
                dispatch_time__isnull=False
            ).aggregate(
                avg_time=Avg('call_duration_seconds')
            )['avg_time'] or 0,
        }
        
        return context


class EmergencyCallDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Detailed view for emergency calls"""
    
    model = EmergencyCall
    template_name = 'ambulances/emergency_calls/call_detail.html'
    context_object_name = 'call'
    
    def test_func(self):
        return is_call_taker(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related dispatches
        context['dispatches'] = Dispatch.objects.filter(
            referral__emergency_call=self.object
        ).select_related('ambulance', 'dispatcher').order_by('-created_at')
        
        # Get available ambulances for dispatch
        if self.object.incident_location:
            context['nearby_ambulances'] = Ambulance.objects.filter(
                status='available',
                is_active=True,
                current_latitude__isnull=False,
                current_longitude__isnull=False
            ).extra(
                select={
                    'distance': """
                        6371 * acos(
                            cos(radians(%s)) * cos(radians(current_latitude)) *
                            cos(radians(current_longitude) - radians(%s)) +
                            sin(radians(%s)) * sin(radians(current_latitude))
                        )
                    """
                },
                select_params=[
                    self.object.incident_location.y,
                    self.object.incident_location.x,
                    self.object.incident_location.y
                ]
            ).order_by('distance')[:5]
        else:
            context['nearby_ambulances'] = Ambulance.objects.filter(
                status='available',
                is_active=True
            )[:5]
        
        return context


class EmergencyCallCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new emergency call"""
    
    model = EmergencyCall
    form_class = EmergencyCallForm
    template_name = 'ambulances/emergency_calls/call_create.html'
    
    def test_func(self):
        return is_call_taker(self.request.user)
    
    def form_valid(self, form):
        # Set call taker
        form.instance.call_taker = self.request.user
        
        # Geocode address if possible
        address = form.cleaned_data.get('incident_address')
        if address:
            # TODO: Implement geocoding service
            # For now, set a default location
            # Store coordinates as separate latitude/longitude fields instead of Point
            # form.instance.incident_latitude = 40.7128  # NYC default
            # form.instance.incident_longitude = -74.0060
        
        response = super().form_valid(form)
        
        # Create priority assessment if provided
        assessment_data = self.request.POST.get('assessment_data')
        if assessment_data:
            try:
                assessment_json = json.loads(assessment_data)
                CallPriorityAssessment.objects.create(
                    emergency_call=self.object,
                    assessed_by=self.request.user,
                    **assessment_json
                )
            except (json.JSONDecodeError, TypeError):
                pass
        
        messages.success(
            self.request,
            f'Emergency call {self.object.call_number} created successfully.'
        )
        
        return response
    
    def get_success_url(self):
        return reverse('ambulances:emergency_call_detail', kwargs={'pk': self.object.pk})


class EmergencyCallUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update emergency call information"""
    
    model = EmergencyCall
    form_class = EmergencyCallForm
    template_name = 'ambulances/emergency_calls/call_update.html'
    
    def test_func(self):
        return is_call_taker(self.request.user)
    
    def form_valid(self, form):
        # Track status changes
        old_status = EmergencyCall.objects.get(pk=self.object.pk).status
        new_status = form.cleaned_data.get('status')
        
        if old_status != new_status:
            CallStatusHistory.objects.create(
                emergency_call=self.object,
                old_status=old_status,
                new_status=new_status,
                changed_by=self.request.user
            )
        
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Emergency call {self.object.call_number} updated successfully.'
        )
        
        return response
    
    def get_success_url(self):
        return reverse('ambulances:emergency_call_detail', kwargs={'pk': self.object.pk})


@login_required
@user_passes_test(is_dispatcher)
def emergency_dispatch_center(request):
    """Main emergency dispatch control center"""
    
    # Get active emergency calls
    active_calls = EmergencyCall.objects.filter(
        status__in=['received', 'processing']
    ).select_related('call_taker').order_by('priority', 'received_at')
    
    # Get dispatched calls
    dispatched_calls = EmergencyCall.objects.filter(
        status='dispatched'
    ).select_related('dispatcher').order_by('-dispatch_time')
    
    # Get available ambulances
    available_ambulances = Ambulance.objects.filter(
        status='available',
        is_active=True
    ).select_related('ambulance_type', 'home_station')
    
    # Get active dispatches
    active_dispatches = Dispatch.objects.filter(
        status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
    ).select_related('ambulance', 'referral').order_by('-created_at')
    
    # Calculate statistics
    stats = {
        'total_active_calls': active_calls.count(),
        'critical_calls': active_calls.filter(priority='critical').count(),
        'emergency_calls': active_calls.filter(priority='emergency').count(),
        'available_ambulances': available_ambulances.count(),
        'active_dispatches': active_dispatches.count(),
        'avg_response_time': EmergencyCall.objects.filter(
            dispatch_time__isnull=False,
            received_at__date=timezone.now().date()
        ).aggregate(
            avg_time=Avg('call_duration_seconds')
        )['avg_time'] or 0,
    }
    
    context = {
        'active_calls': active_calls,
        'dispatched_calls': dispatched_calls,
        'available_ambulances': available_ambulances,
        'active_dispatches': active_dispatches,
        'stats': stats,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }
    
    return render(request, 'ambulances/emergency_calls/dispatch_center.html', context)


@login_required
@user_passes_test(is_dispatcher)
@require_POST
@csrf_exempt
def quick_dispatch(request):
    """Quick dispatch ambulance to emergency call"""
    
    try:
        data = json.loads(request.body)
        call_id = data.get('call_id')
        ambulance_id = data.get('ambulance_id')
        
        emergency_call = get_object_or_404(EmergencyCall, id=call_id)
        ambulance = get_object_or_404(Ambulance, id=ambulance_id, status='available')
        
        # Create referral for the emergency call
        from referrals.models import Referral
        referral = Referral.objects.create(
            patient_name=emergency_call.patient_name or 'Emergency Patient',
            patient_age=emergency_call.patient_age,
            patient_gender=emergency_call.patient_gender,
            chief_complaint=emergency_call.chief_complaint,
            urgency_level=emergency_call.priority,
            pickup_address=emergency_call.incident_address,
            pickup_location=emergency_call.incident_location,
            emergency_call=emergency_call,
            created_by=request.user
        )
        
        # Create dispatch
        dispatch = Dispatch.objects.create(
            referral=referral,
            ambulance=ambulance,
            dispatcher=request.user,
            priority=emergency_call.priority,
            pickup_address=emergency_call.incident_address,
            pickup_latitude=emergency_call.incident_location.y if emergency_call.incident_location else None,
            pickup_longitude=emergency_call.incident_location.x if emergency_call.incident_location else None,
            special_instructions=emergency_call.special_instructions,
            status='dispatched'
        )
        
        # Update ambulance status
        ambulance.status = 'dispatched'
        ambulance.save()
        
        # Update emergency call status
        emergency_call.status = 'dispatched'
        emergency_call.dispatcher = request.user
        emergency_call.dispatch_time = timezone.now()
        emergency_call.save()
        
        # Create status history
        CallStatusHistory.objects.create(
            emergency_call=emergency_call,
            old_status='processing',
            new_status='dispatched',
            changed_by=request.user,
            notes=f'Dispatched ambulance {ambulance.license_plate}'
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Ambulance {ambulance.license_plate} dispatched to call {emergency_call.call_number}',
            'dispatch_id': str(dispatch.id)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_call_taker)
@require_POST
@csrf_exempt
def update_call_status(request):
    """Update emergency call status via AJAX"""
    
    try:
        data = json.loads(request.body)
        call_id = data.get('call_id')
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        emergency_call = get_object_or_404(EmergencyCall, id=call_id)
        old_status = emergency_call.status
        
        # Update status
        emergency_call.status = new_status
        emergency_call.save()
        
        # Create status history
        CallStatusHistory.objects.create(
            emergency_call=emergency_call,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            notes=notes
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Call status updated to {new_status}'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_call_taker)
def priority_assessment_view(request, call_id):
    """Priority assessment interface for emergency calls"""
    
    emergency_call = get_object_or_404(EmergencyCall, id=call_id)
    
    if request.method == 'POST':
        form = CallPriorityAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.emergency_call = emergency_call
            assessment.assessed_by = request.user
            assessment.save()
            
            # Update call priority based on assessment
            emergency_call.priority = assessment.calculated_priority
            emergency_call.save()
            
            messages.success(request, 'Priority assessment completed successfully.')
            return redirect('ambulances:emergency_call_detail', pk=call_id)
    else:
        form = CallPriorityAssessmentForm()
    
    context = {
        'emergency_call': emergency_call,
        'form': form,
    }
    
    return render(request, 'ambulances/emergency_calls/priority_assessment.html', context)
