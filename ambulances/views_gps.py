"""
Real-time GPS Tracking and Route Optimization Views
Advanced GPS tracking with live updates, route optimization, and traffic integration
"""

import json
import math
from datetime import timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.db.models import Q, Avg, Max, Min
from django.conf import settings
import requests
import time

from .models import (
    Ambulance, Dispatch, GPSTrackingEnhanced, RouteOptimization, 
    GeofenceZone, TrafficCondition, EmergencyCall
)


def is_dispatcher_or_admin(user):
    """Check if user is a dispatcher or admin"""
    return user.is_authenticated and (
        user.is_staff or 
        user.role in ['DISPATCHER', 'ADMIN'] or
        user.groups.filter(name__in=['Dispatchers', 'Admins']).exists()
    )


@login_required
@user_passes_test(is_dispatcher_or_admin)
def real_time_tracking_dashboard(request):
    """Real-time GPS tracking dashboard with live map"""
    
    # Get all active ambulances with latest GPS data
    active_ambulances = Ambulance.objects.filter(
        is_active=True
    ).select_related('ambulance_type', 'home_station').prefetch_related(
        'gps_tracking_enhanced'
    )
    
    # Get active dispatches
    active_dispatches = Dispatch.objects.filter(
        status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
    ).select_related('ambulance', 'referral').prefetch_related(
        'route_optimizations'
    )
    
    # Get emergency calls needing dispatch
    pending_calls = EmergencyCall.objects.filter(
        status__in=['received', 'processing']
    ).order_by('priority', 'received_at')
    
    # Get traffic conditions
    active_traffic = TrafficCondition.objects.filter(
        start_time__gte=timezone.now() - timedelta(hours=2)
    ).order_by('-severity', '-start_time')
    
    # Calculate statistics
    stats = {
        'total_ambulances': active_ambulances.count(),
        'available_ambulances': active_ambulances.filter(status='available').count(),
        'dispatched_ambulances': active_ambulances.filter(status='dispatched').count(),
        'active_dispatches': active_dispatches.count(),
        'pending_calls': pending_calls.count(),
        'traffic_incidents': active_traffic.count(),
        'avg_response_time': calculate_avg_response_time(),
    }
    
    context = {
        'active_ambulances': active_ambulances,
        'active_dispatches': active_dispatches,
        'pending_calls': pending_calls,
        'active_traffic': active_traffic,
        'stats': stats,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'mapbox_access_token': getattr(settings, 'MAPBOX_ACCESS_TOKEN', ''),
    }
    
    return render(request, 'ambulances/gps/real_time_dashboard.html', context)


@login_required
@user_passes_test(is_dispatcher_or_admin)
@require_POST
@csrf_exempt
def update_gps_location_enhanced(request):
    """Enhanced GPS location update with additional metadata"""
    
    try:
        data = json.loads(request.body)
        ambulance_id = data.get('ambulance_id')
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        
        ambulance = get_object_or_404(Ambulance, id=ambulance_id)
        
        # Create enhanced GPS tracking record
        gps_record = GPSTrackingEnhanced.objects.create(
            ambulance=ambulance,
            dispatch=ambulance.current_dispatch if hasattr(ambulance, 'current_dispatch') else None,
            latitude=latitude,
            longitude=longitude,
            altitude=data.get('altitude'),
            accuracy=data.get('accuracy'),
            speed_kmh=data.get('speed_kmh', 0.0),
            heading_degrees=data.get('heading_degrees'),
            acceleration=data.get('acceleration'),
            engine_status=data.get('engine_status', True),
            emergency_lights=data.get('emergency_lights', False),
            siren_active=data.get('siren_active', False),
            signal_strength=data.get('signal_strength'),
            battery_level=data.get('battery_level'),
            data_source=data.get('data_source', 'mobile_app')
        )
        
        # Update ambulance current location
        ambulance.current_latitude = latitude
        ambulance.current_longitude = longitude
        ambulance.last_gps_update = timezone.now()
        ambulance.save()
        
        # Check geofences
        check_geofences(ambulance, latitude, longitude)
        
        # Update route progress if on active dispatch
        active_dispatch = Dispatch.objects.filter(
            ambulance=ambulance,
            status__in=['dispatched', 'en_route_pickup', 'en_route_hospital']
        ).first()
        
        if active_dispatch:
            update_route_progress(active_dispatch, latitude, longitude)
        
        # Broadcast update via WebSocket (if implemented)
        broadcast_gps_update(ambulance, gps_record)
        
        return JsonResponse({
            'status': 'success',
            'message': 'GPS location updated successfully',
            'timestamp': gps_record.timestamp.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_dispatcher_or_admin)
@require_POST
@csrf_exempt
def optimize_route(request):
    """Optimize route using Google Maps API with traffic data"""
    
    try:
        data = json.loads(request.body)
        dispatch_id = data.get('dispatch_id')
        route_type = data.get('route_type', 'emergency')
        
        dispatch = get_object_or_404(Dispatch, id=dispatch_id)
        
        # Get current ambulance location
        ambulance = dispatch.ambulance
        if not ambulance.current_latitude or not ambulance.current_longitude:
            return JsonResponse({
                'status': 'error',
                'message': 'Ambulance location not available'
            }, status=400)
        
        origin = f"{ambulance.current_latitude},{ambulance.current_longitude}"
        destination = f"{dispatch.pickup_latitude},{dispatch.pickup_longitude}"
        
        # Call Google Maps Directions API
        route_data = get_optimized_route(origin, destination, route_type)
        
        if route_data:
            # Create route optimization record
            route_opt = RouteOptimization.objects.create(
                dispatch=dispatch,
                origin_latitude=ambulance.current_latitude,
                origin_longitude=ambulance.current_longitude,
                destination_latitude=dispatch.pickup_latitude,
                destination_longitude=dispatch.pickup_longitude,
                route_type=route_type,
                total_distance_km=route_data['distance_km'],
                estimated_duration_minutes=route_data['duration_minutes'],
                traffic_delay_minutes=route_data['traffic_delay_minutes'],
                route_polyline=route_data['polyline'],
                waypoints=route_data['waypoints'],
                traffic_conditions=route_data['traffic_conditions'],
                alternative_routes=route_data['alternative_routes'],
                optimization_score=route_data['optimization_score']
            )
            
            return JsonResponse({
                'status': 'success',
                'route_optimization': {
                    'id': str(route_opt.id),
                    'distance_km': route_opt.total_distance_km,
                    'duration_minutes': route_opt.estimated_duration_minutes,
                    'eta': route_opt.eta.isoformat() if route_opt.eta else None,
                    'polyline': route_opt.route_polyline,
                    'waypoints': route_opt.waypoints,
                    'traffic_delay': route_opt.traffic_delay_minutes,
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to optimize route'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


def get_optimized_route(origin, destination, route_type='emergency'):
    """Get optimized route from Google Maps API"""
    
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    if not api_key:
        return None
    
    # Configure route parameters based on type
    avoid_params = []
    if route_type == 'avoid_traffic':
        avoid_params = ['highways']
    elif route_type == 'emergency':
        # Emergency routes prioritize speed
        pass
    
    url = 'https://maps.googleapis.com/maps/api/directions/json'
    params = {
        'origin': origin,
        'destination': destination,
        'key': api_key,
        'departure_time': 'now',
        'traffic_model': 'best_guess',
        'alternatives': 'true',
        'units': 'metric'
    }
    
    if avoid_params:
        params['avoid'] = '|'.join(avoid_params)
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data['status'] == 'OK' and data['routes']:
            route = data['routes'][0]  # Primary route
            leg = route['legs'][0]
            
            # Extract route information
            distance_km = leg['distance']['value'] / 1000
            duration_minutes = leg['duration']['value'] / 60
            traffic_duration_minutes = leg.get('duration_in_traffic', {}).get('value', leg['duration']['value']) / 60
            traffic_delay_minutes = max(0, traffic_duration_minutes - duration_minutes)
            
            # Extract waypoints
            waypoints = []
            for step in leg['steps']:
                waypoints.append({
                    'lat': step['start_location']['lat'],
                    'lng': step['start_location']['lng'],
                    'instruction': step['html_instructions']
                })
            
            # Get alternative routes
            alternative_routes = []
            for alt_route in data['routes'][1:3]:  # Up to 2 alternatives
                alt_leg = alt_route['legs'][0]
                alternative_routes.append({
                    'distance_km': alt_leg['distance']['value'] / 1000,
                    'duration_minutes': alt_leg['duration']['value'] / 60,
                    'polyline': alt_route['overview_polyline']['points']
                })
            
            # Calculate optimization score (lower is better)
            optimization_score = (duration_minutes * 0.7) + (traffic_delay_minutes * 0.3)
            
            return {
                'distance_km': distance_km,
                'duration_minutes': int(duration_minutes),
                'traffic_delay_minutes': int(traffic_delay_minutes),
                'polyline': route['overview_polyline']['points'],
                'waypoints': waypoints,
                'traffic_conditions': {},  # TODO: Parse traffic data
                'alternative_routes': alternative_routes,
                'optimization_score': optimization_score
            }
    
    except Exception as e:
        print(f"Route optimization error: {e}")
        return None


def check_geofences(ambulance, latitude, longitude):
    """Check if ambulance entered/exited any geofence zones"""
    
    geofences = GeofenceZone.objects.filter(
        Q(zone_type='hospital') | Q(zone_type='station') | Q(zone_type='pickup_zone')
    )
    
    for geofence in geofences:
        is_inside = geofence.is_point_inside(latitude, longitude)
        
        # Get previous GPS record to check if status changed
        previous_gps = GPSTrackingEnhanced.objects.filter(
            ambulance=ambulance
        ).exclude(
            latitude=latitude, longitude=longitude
        ).order_by('-timestamp').first()
        
        if previous_gps:
            was_inside = geofence.is_point_inside(previous_gps.latitude, previous_gps.longitude)
            
            if is_inside and not was_inside:
                # Entered geofence
                handle_geofence_entry(ambulance, geofence)
            elif not is_inside and was_inside:
                # Exited geofence
                handle_geofence_exit(ambulance, geofence)


def handle_geofence_entry(ambulance, geofence):
    """Handle ambulance entering a geofence zone"""
    
    if geofence.auto_status_change and geofence.target_status:
        ambulance.status = geofence.target_status
        ambulance.save()
    
    # Create notification
    if geofence.notification_enabled:
        create_geofence_notification(ambulance, geofence, 'entered')


def handle_geofence_exit(ambulance, geofence):
    """Handle ambulance exiting a geofence zone"""
    
    # Create notification
    if geofence.notification_enabled:
        create_geofence_notification(ambulance, geofence, 'exited')


def create_geofence_notification(ambulance, geofence, action):
    """Create notification for geofence events"""
    
    # TODO: Implement notification system
    print(f"Ambulance {ambulance.license_plate} {action} {geofence.name}")


def update_route_progress(dispatch, latitude, longitude):
    """Update route progress and ETA for active dispatch"""
    
    # Get latest route optimization
    route_opt = dispatch.route_optimizations.order_by('-created_at').first()
    
    if route_opt:
        # Calculate distance to destination
        distance_to_dest = calculate_distance(
            latitude, longitude,
            route_opt.destination_latitude, route_opt.destination_longitude
        )
        
        # Update GPS record with route progress
        latest_gps = GPSTrackingEnhanced.objects.filter(
            ambulance=dispatch.ambulance
        ).order_by('-timestamp').first()
        
        if latest_gps:
            latest_gps.distance_to_destination_km = distance_to_dest
            
            # Estimate ETA based on current speed and distance
            if latest_gps.speed_kmh > 0:
                eta_hours = distance_to_dest / latest_gps.speed_kmh
                latest_gps.eta_minutes = int(eta_hours * 60)
            
            latest_gps.save()


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates using Haversine formula"""
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in kilometers
    r = 6371
    
    return r * c


def calculate_avg_response_time():
    """Calculate average response time for completed dispatches"""
    
    completed_dispatches = Dispatch.objects.filter(
        status='completed',
        created_at__gte=timezone.now() - timedelta(days=30)
    )
    
    total_time = 0
    count = 0
    
    for dispatch in completed_dispatches:
        if dispatch.completed_at:
            response_time = (dispatch.completed_at - dispatch.created_at).total_seconds() / 60
            total_time += response_time
            count += 1
    
    return total_time / count if count > 0 else 0


def broadcast_gps_update(ambulance, gps_record):
    """Broadcast GPS update via WebSocket (placeholder for future implementation)"""
    
    # TODO: Implement WebSocket broadcasting
    # This would use Django Channels to send real-time updates to connected clients
    pass


@login_required
@user_passes_test(is_dispatcher_or_admin)
def ambulance_location_stream(request, ambulance_id):
    """Server-sent events stream for real-time ambulance location updates"""
    
    def event_stream():
        ambulance = get_object_or_404(Ambulance, id=ambulance_id)
        last_update = None
        
        while True:
            # Get latest GPS record
            latest_gps = GPSTrackingEnhanced.objects.filter(
                ambulance=ambulance
            ).order_by('-timestamp').first()
            
            if latest_gps and latest_gps.timestamp != last_update:
                data = {
                    'ambulance_id': str(ambulance.id),
                    'latitude': latest_gps.latitude,
                    'longitude': latest_gps.longitude,
                    'speed_kmh': latest_gps.speed_kmh,
                    'heading_degrees': latest_gps.heading_degrees,
                    'emergency_lights': latest_gps.emergency_lights,
                    'siren_active': latest_gps.siren_active,
                    'timestamp': latest_gps.timestamp.isoformat(),
                    'eta_minutes': latest_gps.eta_minutes,
                    'distance_to_destination_km': latest_gps.distance_to_destination_km,
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                last_update = latest_gps.timestamp
            
            time.sleep(5)  # Update every 5 seconds
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response


@login_required
@user_passes_test(is_dispatcher_or_admin)
def traffic_conditions_view(request):
    """View and manage traffic conditions"""
    
    active_conditions = TrafficCondition.objects.filter(
        start_time__gte=timezone.now() - timedelta(hours=6)
    ).order_by('-severity', '-start_time')
    
    context = {
        'traffic_conditions': active_conditions,
    }
    
    return render(request, 'ambulances/gps/traffic_conditions.html', context)


@login_required
@user_passes_test(is_dispatcher_or_admin)
@require_POST
@csrf_exempt
def add_traffic_condition(request):
    """Add new traffic condition"""
    
    try:
        data = json.loads(request.body)
        
        condition = TrafficCondition.objects.create(
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            radius_meters=int(data.get('radius_meters', 500)),
            condition_type=data['condition_type'],
            severity=data['severity'],
            description=data['description'],
            speed_reduction_percent=int(data.get('speed_reduction_percent', 0)),
            delay_minutes=int(data.get('delay_minutes', 0)),
            estimated_end_time=data.get('estimated_end_time'),
            data_source='manual'
        )
        
        return JsonResponse({
            'status': 'success',
            'condition_id': str(condition.id),
            'message': 'Traffic condition added successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
