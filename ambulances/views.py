from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Q, Count, Avg, F, Case, When, IntegerField
from django.utils import timezone
from datetime import datetime, timedelta
# GIS functionality removed - using standard latitude/longitude fields instead
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from django.core.cache import cache
from django.conf import settings
import json
import logging
import time
from datetime import datetime, timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Ambulance, Dispatch, AmbulanceType, AmbulanceStation, AmbulanceCrew,
    DispatchCrew, GPSTrackingLog, MaintenanceRecord, EquipmentInventory,
    FuelLog, IncidentReport, PerformanceMetrics
)
from .forms import AmbulanceForm, DispatchForm, AmbulanceSearchForm, GPSUpdateForm, MaintenanceForm
from referrals.models import Referral

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


def is_ambulance_staff(user):
    """Check if user is ambulance staff"""
    return user.is_authenticated and (
        user.role in ['AMBULANCE_STAFF', 'DISPATCHER', 'ADMIN'] or
        user.is_superuser
    )


def is_dispatcher(user):
    """Check if user is a dispatcher"""
    return user.is_authenticated and (
        user.role in ['DISPATCHER', 'ADMIN'] or
        user.is_superuser
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def find_nearest_ambulance(pickup_lat, pickup_lng, priority='routine'):
    """Find the nearest available ambulance for dispatch"""
    if not pickup_lat or not pickup_lng:
        return Ambulance.objects.filter(status='available', is_active=True).first()

    # Get available ambulances with location data
    available_ambulances = Ambulance.objects.filter(
        status='available',
        is_active=True,
        current_latitude__isnull=False,
        current_longitude__isnull=False
    )

    # Calculate distances and find nearest
    nearest_ambulance = None
    min_distance = float('inf')

    for ambulance in available_ambulances:
        distance = ambulance.calculate_distance_to(pickup_lat, pickup_lng)
        if distance and distance < min_distance:
            min_distance = distance
            nearest_ambulance = ambulance

    # For emergency calls, prioritize ambulances with advanced equipment
    if priority in ['emergency', 'critical']:
        advanced_ambulances = available_ambulances.filter(
            ambulance_type__name__icontains='advanced'
        )
        if advanced_ambulances.exists():
            # Find nearest advanced ambulance
            for ambulance in advanced_ambulances:
                distance = ambulance.calculate_distance_to(pickup_lat, pickup_lng)
                if distance and distance < min_distance * 1.5:  # Allow 50% more distance for advanced ambulance
                    return ambulance

    return nearest_ambulance


def notify_ambulance_crew(dispatch):
    """Notify ambulance crew about new dispatch"""
    try:
        from notifications.models import Notification

        # Get crew members
        crew_members = dispatch.ambulance.assigned_crew.all()

        # Create notifications for each crew member
        for crew_member in crew_members:
            Notification.objects.create(
                recipient=crew_member,
                notification_type='dispatch',
                channel='push',
                priority='high' if dispatch.is_emergency else 'normal',
                subject=f'New Dispatch Assignment - {dispatch.dispatch_number}',
                message=f'You have been assigned to dispatch {dispatch.dispatch_number}. '
                       f'Priority: {dispatch.get_priority_display()}. '
                       f'Location: {dispatch.pickup_address}',
                context_data={
                    'dispatch_id': str(dispatch.id),
                    'dispatch_number': dispatch.dispatch_number,
                    'priority': dispatch.priority,
                    'pickup_address': dispatch.pickup_address
                }
            )

        # Broadcast via WebSocket
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"ambulance_{dispatch.ambulance.id}",
                {
                    "type": "dispatch_assigned",
                    "dispatch_id": str(dispatch.id),
                    "dispatch_number": dispatch.dispatch_number,
                    "priority": dispatch.priority,
                    "pickup_address": dispatch.pickup_address,
                    "timestamp": timezone.now().isoformat()
                }
            )

    except Exception as e:
        logger.error(f"Error notifying ambulance crew: {str(e)}")


def calculate_route_optimization(dispatches):
    """Calculate optimized routes for multiple dispatches"""
    # This is a simplified version - in production, you'd use Google Maps API
    # or other routing services for actual route optimization
    optimized_routes = []

    for dispatch in dispatches:
        if dispatch.pickup_location and dispatch.destination_location:
            # Calculate estimated distance and time
            distance = dispatch.pickup_location.distance(dispatch.destination_location)
            estimated_time = distance.km * 2  # Rough estimate: 2 minutes per km

            optimized_routes.append({
                'dispatch_id': dispatch.id,
                'distance_km': round(distance.km, 2),
                'estimated_time_minutes': round(estimated_time),
                'waypoints': [
                    {'lat': dispatch.pickup_location.y, 'lng': dispatch.pickup_location.x},
                    {'lat': dispatch.destination_location.y, 'lng': dispatch.destination_location.x}
                ]
            })

    return optimized_routes

# ============================================================================
# REAL-TIME TRACKING VIEWS
# ============================================================================

@login_required
def real_time_dashboard(request):
    """Real-time ambulance tracking dashboard"""
    # Get active dispatches
    active_dispatches = Dispatch.objects.filter(
        status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
    ).select_related('ambulance', 'referral__patient').prefetch_related('primary_crew')

    # Get available ambulances
    available_ambulances = Ambulance.objects.filter(
        status='available',
        is_active=True
    ).select_related('ambulance_type', 'home_station')

    # Get emergency dispatches
    emergency_dispatches = active_dispatches.filter(priority__in=['emergency', 'critical'])

    # Performance metrics
    today = timezone.now().date()
    today_metrics = {
        'total_dispatches': Dispatch.objects.filter(created_at__date=today).count(),
        'completed_dispatches': Dispatch.objects.filter(
            created_at__date=today,
            status='completed'
        ).count(),
        'average_response_time': Dispatch.objects.filter(
            created_at__date=today,
            response_time_minutes__isnull=False
        ).aggregate(avg_time=Avg('response_time_minutes'))['avg_time'] or 0,
        'active_ambulances': available_ambulances.count(),
        'total_ambulances': Ambulance.objects.filter(is_active=True).count(),
    }

    context = {
        'active_dispatches': active_dispatches,
        'available_ambulances': available_ambulances,
        'emergency_dispatches': emergency_dispatches,
        'today_metrics': today_metrics,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }

    return render(request, 'ambulances/real_time_dashboard.html', context)


@login_required
@require_POST
@csrf_exempt
def update_gps_location(request):
    """Update ambulance GPS location via AJAX"""
    try:
        data = json.loads(request.body)
        ambulance_id = data.get('ambulance_id')
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        speed = float(data.get('speed', 0))
        heading = float(data.get('heading', 0))
        accuracy = float(data.get('accuracy', 0))

        ambulance = get_object_or_404(Ambulance, id=ambulance_id)

        # Update ambulance location
        ambulance.update_location(latitude, longitude, speed, heading)

        # Log GPS tracking
        gps_log = GPSTrackingLog.objects.create(
            ambulance=ambulance,
            latitude=latitude,
            longitude=longitude,
            speed=speed,
            heading=heading,
            accuracy=accuracy
        )

        # If ambulance is on active dispatch, update dispatch GPS log
        active_dispatch = Dispatch.objects.filter(
            ambulance=ambulance,
            status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
        ).first()

        if active_dispatch:
            gps_log.dispatch = active_dispatch
            gps_log.save()

        # Broadcast location update via WebSocket
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"ambulance_{ambulance_id}",
                {
                    "type": "location_update",
                    "ambulance_id": str(ambulance_id),
                    "latitude": latitude,
                    "longitude": longitude,
                    "speed": speed,
                    "heading": heading,
                    "timestamp": timezone.now().isoformat(),
                    "status": ambulance.status
                }
            )

        return JsonResponse({
            'status': 'success',
            'message': 'Location updated successfully'
        })

    except Exception as e:
        logger.error(f"GPS update error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
def ambulance_location_stream(request, ambulance_id):
    """Server-sent events stream for real-time location updates"""
    def event_stream():
        ambulance = get_object_or_404(Ambulance, id=ambulance_id)
        last_update = timezone.now()

        while True:
            # Check for new GPS logs
            new_logs = GPSTrackingLog.objects.filter(
                ambulance=ambulance,
                timestamp__gt=last_update
            ).order_by('-timestamp')

            for log in new_logs:
                data = {
                    'ambulance_id': str(ambulance.id),
                    'latitude': log.location.y,
                    'longitude': log.location.x,
                    'speed': log.speed,
                    'heading': log.heading,
                    'timestamp': log.timestamp.isoformat(),
                    'status': ambulance.status
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_update = log.timestamp

            time.sleep(5)  # Update every 5 seconds

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response


@login_required
def request_ambulance(request, referral_id):
    """Enhanced ambulance request with intelligent dispatch"""
    referral = get_object_or_404(Referral, id=referral_id)

    if request.method == 'POST':
        form = DispatchForm(request.POST)
        if form.is_valid():
            dispatch = form.save(commit=False)
            dispatch.referral = referral
            dispatch.dispatcher = request.user
            dispatch.status = 'requested'

            # Set pickup and destination locations
            pickup_lat = form.cleaned_data.get('pickup_latitude')
            pickup_lng = form.cleaned_data.get('pickup_longitude')
            dest_lat = form.cleaned_data.get('destination_latitude')
            dest_lng = form.cleaned_data.get('destination_longitude')

            if pickup_lat and pickup_lng:
                dispatch.pickup_latitude = pickup_lat
                dispatch.pickup_longitude = pickup_lng
            if dest_lat and dest_lng:
                dispatch.destination_latitude = dest_lat
                dispatch.destination_longitude = dest_lng

            dispatch.save()

            # Find best available ambulance
            best_ambulance = find_nearest_ambulance(dispatch.pickup_latitude, dispatch.pickup_longitude, dispatch.priority)
            if best_ambulance:
                dispatch.ambulance = best_ambulance
                dispatch.status = 'assigned'
                best_ambulance.status = 'dispatched'
                best_ambulance.save()
                dispatch.save()

                # Notify ambulance crew
                notify_ambulance_crew(dispatch)

            messages.success(request, 'Ambulance requested successfully.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Ambulance requested successfully.',
                    'dispatch_id': str(dispatch.id),
                    'ambulance_assigned': best_ambulance is not None
                })
            return redirect('ambulances:track_dispatch', dispatch_id=dispatch.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                })
    else:
        form = DispatchForm()

    return render(request, 'ambulances/request.html', {
        'form': form,
        'referral': referral,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    })

@login_required
def track_dispatch(request, dispatch_id):
    """Enhanced dispatch tracking with real-time updates"""
    dispatch = get_object_or_404(Dispatch, id=dispatch_id)

    # Get GPS tracking history
    gps_history = GPSTrackingLog.objects.filter(
        dispatch=dispatch
    ).order_by('timestamp')

    # Calculate route progress
    route_progress = calculate_route_progress(dispatch, gps_history)

    # Get estimated arrival time
    eta = calculate_eta(dispatch)

    context = {
        'dispatch': dispatch,
        'gps_history': gps_history,
        'route_progress': route_progress,
        'eta': eta,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'websocket_url': f'ws://localhost:8000/ws/ambulance/{dispatch.ambulance.id}/'
    }

    return render(request, 'ambulances/track_dispatch.html', context)


def calculate_route_progress(dispatch, gps_history):
    """Calculate route completion percentage"""
    if not dispatch.pickup_location or not dispatch.destination_location or not gps_history:
        return 0

    total_distance = dispatch.pickup_location.distance(dispatch.destination_location)
    if total_distance.km == 0:
        return 100

    # Get current location from latest GPS log
    current_location = gps_history.last().location
    remaining_distance = current_location.distance(dispatch.destination_location)

    progress = max(0, min(100, ((total_distance.km - remaining_distance.km) / total_distance.km) * 100))
    return round(progress, 1)


def calculate_eta(dispatch):
    """Calculate estimated time of arrival"""
    if not dispatch.ambulance.current_location or not dispatch.destination_location:
        return None

    distance = dispatch.ambulance.current_location.distance(dispatch.destination_location)
    # Assume average speed of 40 km/h in urban areas
    estimated_minutes = (distance.km / 40) * 60

    return timezone.now() + timedelta(minutes=estimated_minutes)


@login_required
@user_passes_test(is_dispatcher)
def dispatch_control_center(request):
    """Advanced dispatch control center for dispatchers"""
    # Get all active dispatches
    active_dispatches = Dispatch.objects.filter(
        status__in=['requested', 'assigned', 'dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
    ).select_related('ambulance', 'referral__patient', 'dispatcher').prefetch_related('primary_crew')

    # Get available ambulances with their locations
    available_ambulances = Ambulance.objects.filter(
        status='available',
        is_active=True
    ).select_related('ambulance_type', 'home_station')

    # Get pending requests
    pending_requests = active_dispatches.filter(status='requested')

    # Performance metrics for today
    today = timezone.now().date()
    performance_metrics = {
        'total_dispatches_today': Dispatch.objects.filter(created_at__date=today).count(),
        'completed_today': Dispatch.objects.filter(created_at__date=today, status='completed').count(),
        'average_response_time': Dispatch.objects.filter(
            created_at__date=today,
            response_time_minutes__isnull=False
        ).aggregate(avg_time=Avg('response_time_minutes'))['avg_time'] or 0,
        'emergency_calls_today': Dispatch.objects.filter(
            created_at__date=today,
            priority__in=['emergency', 'critical']
        ).count(),
    }

    context = {
        'active_dispatches': active_dispatches,
        'available_ambulances': available_ambulances,
        'pending_requests': pending_requests,
        'performance_metrics': performance_metrics,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }

    return render(request, 'ambulances/dispatch_control_center.html', context)


@login_required
@user_passes_test(is_dispatcher)
@require_POST
def assign_ambulance(request):
    """Assign ambulance to a dispatch request"""
    try:
        data = json.loads(request.body)
        dispatch_id = data.get('dispatch_id')
        ambulance_id = data.get('ambulance_id')

        dispatch = get_object_or_404(Dispatch, id=dispatch_id, status='requested')
        ambulance = get_object_or_404(Ambulance, id=ambulance_id, status='available')

        # Assign ambulance to dispatch
        dispatch.ambulance = ambulance
        dispatch.status = 'assigned'
        dispatch.dispatched_at = timezone.now()
        dispatch.save()

        # Update ambulance status
        ambulance.status = 'dispatched'
        ambulance.save()

        # Notify crew
        notify_ambulance_crew(dispatch)

        # Update dispatch status history
        dispatch.update_status('dispatched', request.user)

        return JsonResponse({
            'status': 'success',
            'message': f'Ambulance {ambulance.license_plate} assigned to dispatch {dispatch.dispatch_number}'
        })

    except Exception as e:
        logger.error(f"Error assigning ambulance: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
def fleet_list(request):
    form = AmbulanceSearchForm(request.GET)
    ambulances = Ambulance.objects.all().select_related('ambulance_type', 'home_station')

    if form.is_valid():
        search = form.cleaned_data.get('search')
        status = form.cleaned_data.get('status')
        condition = form.cleaned_data.get('condition')

        if search:
            ambulances = ambulances.filter(
                Q(license_plate__icontains=search) |
                Q(make__icontains=search) |
                Q(model__icontains=search) |
                Q(ambulance_type__name__icontains=search)
            )

        if status:
            ambulances = ambulances.filter(status=status)

        if condition:
            ambulances = ambulances.filter(condition=condition)

    return render(request, 'ambulances/fleet.html', {
        'ambulances': ambulances,
        'form': form
    })

class AmbulanceListView(LoginRequiredMixin, ListView):
    model = Ambulance
    template_name = 'ambulances/ambulance_list.html'
    context_object_name = 'ambulances'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('ambulance_type', 'home_station')
        form = AmbulanceSearchForm(self.request.GET)

        if form.is_valid():
            search = form.cleaned_data.get('search')
            status = form.cleaned_data.get('status')
            condition = form.cleaned_data.get('condition')

            if search:
                queryset = queryset.filter(
                    Q(license_plate__icontains=search) |
                    Q(make__icontains=search) |
                    Q(model__icontains=search) |
                    Q(ambulance_type__name__icontains=search)
                )

            if status:
                queryset = queryset.filter(status=status)

            if condition:
                queryset = queryset.filter(condition=condition)

        return queryset.order_by('license_plate')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AmbulanceSearchForm(self.request.GET)
        context['total_ambulances'] = Ambulance.objects.count()
        context['available_count'] = Ambulance.objects.filter(status='available').count()
        context['dispatched_count'] = Ambulance.objects.filter(status='dispatched').count()
        context['maintenance_count'] = Ambulance.objects.filter(status='maintenance').count()
        context['out_of_service_count'] = Ambulance.objects.filter(status='out_of_service').count()
        return context

class AmbulanceDetailView(LoginRequiredMixin, DetailView):
    model = Ambulance
    template_name = 'ambulances/ambulance_detail.html'
    context_object_name = 'ambulance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get recent dispatches for this ambulance
        context['recent_dispatches'] = Dispatch.objects.filter(
            ambulance=self.object
        ).order_by('-created_at')[:5]
        return context

class AmbulanceCreateView(LoginRequiredMixin, CreateView):
    model = Ambulance
    form_class = AmbulanceForm
    template_name = 'ambulances/ambulance_form.html'
    success_url = reverse_lazy('ambulances:fleet')
    
    def form_valid(self, form):
        messages.success(self.request, 'Ambulance added successfully.')
        return super().form_valid(form)

class AmbulanceUpdateView(LoginRequiredMixin, UpdateView):
    model = Ambulance
    form_class = AmbulanceForm
    template_name = 'ambulances/ambulance_form.html'
    success_url = reverse_lazy('ambulances:fleet')
    
    def form_valid(self, form):
        messages.success(self.request, 'Ambulance updated successfully.')
        return super().form_valid(form)

class DispatchListView(LoginRequiredMixin, ListView):
    model = Dispatch
    template_name = 'ambulances/dispatch_list.html'
    context_object_name = 'dispatches'
    paginate_by = 20
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'ambulance', 'referral', 'dispatcher'
        ).order_by('-estimated_arrival_time')

@login_required
def update_dispatch_status(request, dispatch_id):
    if request.method == 'POST':
        dispatch = get_object_or_404(Dispatch, id=dispatch_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(Dispatch._meta.get_field('status').choices):
            dispatch.status = new_status
            dispatch.save()
            
            # Update ambulance status based on dispatch status
            if new_status == 'dispatched':
                dispatch.ambulance.status = 'in_use'
            elif new_status == 'completed':
                dispatch.ambulance.status = 'available'
            
            dispatch.ambulance.save()
            
            messages.success(request, f'Dispatch status updated to {dispatch.get_status_display()}.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f'Status updated to {dispatch.get_status_display()}'
                })
        
        return redirect('ambulances:track_dispatch', dispatch_id=dispatch.id)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def ambulance_dashboard(request):
    """Dashboard view for ambulance management overview"""
    context = {
        'total_ambulances': Ambulance.objects.count(),
        'available_ambulances': Ambulance.objects.filter(status='available').count(),
        'in_use_ambulances': Ambulance.objects.filter(status='in_use').count(),
        'maintenance_ambulances': Ambulance.objects.filter(status='under_maintenance').count(),
        'active_dispatches': Dispatch.objects.filter(status__in=['dispatched', 'en_route']).count(),
        'recent_dispatches': Dispatch.objects.select_related(
            'ambulance', 'referral', 'dispatcher'
        ).order_by('-created_at')[:10],
        'urgent_dispatches': Dispatch.objects.filter(
            status__in=['requested', 'dispatched'],
            estimated_arrival_time__lte=datetime.now() + timedelta(hours=2)
        ).count()
    }
    
    return render(request, 'ambulances/dashboard.html', context)