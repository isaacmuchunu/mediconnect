"""
Mobile Dispatch Application Views
Progressive Web App for ambulance crews with offline capabilities
"""

import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from .models import Ambulance, Dispatch, GPSTrackingEnhanced, EmergencyCall
from hospitals.models_integration import HospitalCapacity


def is_ambulance_crew(user):
    """Check if user is ambulance crew member"""
    return user.is_authenticated and (
        user.role in ['PARAMEDIC', 'EMT', 'AMBULANCE_DRIVER', 'AMBULANCE_CREW'] or
        user.groups.filter(name__in=['Ambulance Crew', 'Paramedics', 'EMTs']).exists()
    )


@login_required
@user_passes_test(is_ambulance_crew)
def mobile_dashboard(request):
    """Mobile dashboard for ambulance crews"""
    
    # Get user's assigned ambulance
    try:
        ambulance = Ambulance.objects.get(
            Q(primary_crew=request.user) | Q(secondary_crew=request.user)
        )
    except Ambulance.DoesNotExist:
        ambulance = None
    
    # Get current dispatch
    current_dispatch = None
    if ambulance:
        current_dispatch = Dispatch.objects.filter(
            ambulance=ambulance,
            status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
        ).first()
    
    # Get recent dispatches
    recent_dispatches = []
    if ambulance:
        recent_dispatches = Dispatch.objects.filter(
            ambulance=ambulance,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-created_at')[:5]
    
    # Get latest GPS data
    latest_gps = None
    if ambulance:
        latest_gps = GPSTrackingEnhanced.objects.filter(
            ambulance=ambulance
        ).order_by('-timestamp').first()
    
    # Get nearby hospitals
    nearby_hospitals = []
    if latest_gps:
        # TODO: Implement proper distance calculation
        nearby_hospitals = HospitalCapacity.objects.filter(
            hospital__is_active=True,
            overall_status__in=['normal', 'busy']
        ).select_related('hospital')[:5]
    
    context = {
        'ambulance': ambulance,
        'current_dispatch': current_dispatch,
        'recent_dispatches': recent_dispatches,
        'latest_gps': latest_gps,
        'nearby_hospitals': nearby_hospitals,
        'is_mobile': True,
    }
    
    return render(request, 'ambulances/mobile/dashboard.html', context)


@login_required
@user_passes_test(is_ambulance_crew)
def mobile_dispatch_detail(request, dispatch_id=None):
    """Mobile dispatch detail view"""
    
    # Get user's ambulance
    try:
        ambulance = Ambulance.objects.get(
            Q(primary_crew=request.user) | Q(secondary_crew=request.user)
        )
    except Ambulance.DoesNotExist:
        messages.error(request, 'You are not assigned to an ambulance.')
        return redirect('ambulances:mobile_dashboard')
    
    # Get dispatch
    if dispatch_id:
        dispatch = get_object_or_404(Dispatch, id=dispatch_id, ambulance=ambulance)
    else:
        # Get current active dispatch
        dispatch = Dispatch.objects.filter(
            ambulance=ambulance,
            status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
        ).first()
        
        if not dispatch:
            messages.info(request, 'No active dispatch found.')
            return redirect('ambulances:mobile_dashboard')
    
    # Get route optimization
    route_optimization = dispatch.route_optimizations.order_by('-created_at').first()
    
    # Get emergency call details
    emergency_call = None
    if hasattr(dispatch.referral, 'emergency_call'):
        emergency_call = dispatch.referral.emergency_call
    
    # Get destination hospital
    destination_hospital = None
    if dispatch.destination_hospital_id:
        try:
            destination_hospital = dispatch.destination_hospital
            hospital_capacity = getattr(destination_hospital, 'capacity_status', None)
        except:
            hospital_capacity = None
    
    context = {
        'dispatch': dispatch,
        'ambulance': ambulance,
        'route_optimization': route_optimization,
        'emergency_call': emergency_call,
        'destination_hospital': destination_hospital,
        'hospital_capacity': hospital_capacity,
        'is_mobile': True,
    }
    
    return render(request, 'ambulances/mobile/dispatch_detail.html', context)


@login_required
@user_passes_test(is_ambulance_crew)
def mobile_status_update(request):
    """Mobile status update interface"""
    
    # Get user's ambulance
    try:
        ambulance = Ambulance.objects.get(
            Q(primary_crew=request.user) | Q(secondary_crew=request.user)
        )
    except Ambulance.DoesNotExist:
        messages.error(request, 'You are not assigned to an ambulance.')
        return redirect('ambulances:mobile_dashboard')
    
    # Get current dispatch
    current_dispatch = Dispatch.objects.filter(
        ambulance=ambulance,
        status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
    ).first()
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        # Update ambulance status
        old_status = ambulance.status
        ambulance.status = new_status
        ambulance.save()
        
        # Update dispatch status if applicable
        if current_dispatch:
            dispatch_status_map = {
                'available': 'completed',
                'en_route': 'en_route_pickup',
                'on_scene': 'on_scene',
                'transporting': 'patient_loaded',
                'at_hospital': 'en_route_hospital',
            }
            
            if new_status in dispatch_status_map:
                current_dispatch.status = dispatch_status_map[new_status]
                current_dispatch.save()
        
        # Log status change
        # TODO: Implement status change logging
        
        messages.success(request, f'Status updated to {new_status}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': f'Status updated to {new_status}',
                'new_status': new_status
            })
        
        return redirect('ambulances:mobile_dashboard')
    
    context = {
        'ambulance': ambulance,
        'current_dispatch': current_dispatch,
        'status_choices': Ambulance.STATUS_CHOICES,
        'is_mobile': True,
    }
    
    return render(request, 'ambulances/mobile/status_update.html', context)


@login_required
@user_passes_test(is_ambulance_crew)
def mobile_navigation(request):
    """Mobile GPS navigation interface"""
    
    # Get user's ambulance
    try:
        ambulance = Ambulance.objects.get(
            Q(primary_crew=request.user) | Q(secondary_crew=request.user)
        )
    except Ambulance.DoesNotExist:
        messages.error(request, 'You are not assigned to an ambulance.')
        return redirect('ambulances:mobile_dashboard')
    
    # Get current dispatch
    current_dispatch = Dispatch.objects.filter(
        ambulance=ambulance,
        status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
    ).first()
    
    # Get latest GPS position
    latest_gps = GPSTrackingEnhanced.objects.filter(
        ambulance=ambulance
    ).order_by('-timestamp').first()
    
    # Get route optimization
    route_optimization = None
    if current_dispatch:
        route_optimization = current_dispatch.route_optimizations.order_by('-created_at').first()
    
    context = {
        'ambulance': ambulance,
        'current_dispatch': current_dispatch,
        'latest_gps': latest_gps,
        'route_optimization': route_optimization,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'is_mobile': True,
    }
    
    return render(request, 'ambulances/mobile/navigation.html', context)


@login_required
@user_passes_test(is_ambulance_crew)
def mobile_protocols(request):
    """Mobile emergency protocols reference"""
    
    # Emergency protocols data
    protocols = [
        {
            'category': 'Cardiac Emergencies',
            'protocols': [
                {
                    'name': 'Cardiac Arrest',
                    'steps': [
                        'Check responsiveness and breathing',
                        'Call for AED if available',
                        'Begin CPR (30:2 ratio)',
                        'Apply AED pads when available',
                        'Continue CPR until ROSC or arrival at hospital'
                    ]
                },
                {
                    'name': 'Chest Pain',
                    'steps': [
                        'Assess pain characteristics (OPQRST)',
                        'Obtain vital signs',
                        'Administer oxygen if SpO2 < 94%',
                        'Consider aspirin if no contraindications',
                        'Prepare for 12-lead ECG'
                    ]
                }
            ]
        },
        {
            'category': 'Respiratory Emergencies',
            'protocols': [
                {
                    'name': 'Severe Asthma',
                    'steps': [
                        'Position patient upright',
                        'Administer high-flow oxygen',
                        'Assist with bronchodilator if available',
                        'Monitor for deterioration',
                        'Prepare for possible intubation'
                    ]
                },
                {
                    'name': 'Respiratory Failure',
                    'steps': [
                        'Assess airway patency',
                        'Provide ventilatory support',
                        'Consider advanced airway',
                        'Monitor SpO2 and ETCO2',
                        'Prepare for rapid transport'
                    ]
                }
            ]
        },
        {
            'category': 'Trauma',
            'protocols': [
                {
                    'name': 'Major Trauma',
                    'steps': [
                        'Scene safety assessment',
                        'Primary survey (ABCDE)',
                        'Control major bleeding',
                        'Immobilize spine if indicated',
                        'Rapid transport to trauma center'
                    ]
                },
                {
                    'name': 'Head Injury',
                    'steps': [
                        'Assess level of consciousness (GCS)',
                        'Monitor for signs of increased ICP',
                        'Maintain cervical spine immobilization',
                        'Avoid hypotension and hypoxia',
                        'Transport to appropriate facility'
                    ]
                }
            ]
        }
    ]
    
    context = {
        'protocols': protocols,
        'is_mobile': True,
    }
    
    return render(request, 'ambulances/mobile/protocols.html', context)


@login_required
@user_passes_test(is_ambulance_crew)
def mobile_offline(request):
    """Offline page for PWA"""
    
    context = {
        'is_mobile': True,
    }
    
    return render(request, 'ambulances/mobile/offline.html', context)


@login_required
@user_passes_test(is_ambulance_crew)
@require_POST
@csrf_exempt
def mobile_gps_update(request):
    """Mobile GPS update endpoint with offline support"""
    
    try:
        data = json.loads(request.body)
        
        # Get user's ambulance
        ambulance = Ambulance.objects.get(
            Q(primary_crew=request.user) | Q(secondary_crew=request.user)
        )
        
        # Create GPS tracking record
        gps_record = GPSTrackingEnhanced.objects.create(
            ambulance=ambulance,
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            altitude=data.get('altitude'),
            accuracy=data.get('accuracy'),
            speed_kmh=data.get('speed_kmh', 0.0),
            heading_degrees=data.get('heading_degrees'),
            emergency_lights=data.get('emergency_lights', False),
            siren_active=data.get('siren_active', False),
            battery_level=data.get('battery_level'),
            data_source='mobile_app'
        )
        
        # Update ambulance location
        ambulance.current_latitude = float(data['latitude'])
        ambulance.current_longitude = float(data['longitude'])
        ambulance.last_gps_update = timezone.now()
        ambulance.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'GPS location updated',
            'timestamp': gps_record.timestamp.isoformat()
        })
        
    except Ambulance.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Ambulance not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_ambulance_crew)
@require_POST
@csrf_exempt
def mobile_status_quick_update(request):
    """Quick status update for mobile app"""
    
    try:
        data = json.loads(request.body)
        
        # Get user's ambulance
        ambulance = Ambulance.objects.get(
            Q(primary_crew=request.user) | Q(secondary_crew=request.user)
        )
        
        # Update status
        new_status = data.get('status')
        if new_status in dict(Ambulance.STATUS_CHOICES):
            ambulance.status = new_status
            ambulance.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Status updated to {new_status}',
                'new_status': new_status
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid status'
            }, status=400)
            
    except Ambulance.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Ambulance not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_ambulance_crew)
def mobile_dispatch_history(request):
    """Mobile dispatch history view"""
    
    # Get user's ambulance
    try:
        ambulance = Ambulance.objects.get(
            Q(primary_crew=request.user) | Q(secondary_crew=request.user)
        )
    except Ambulance.DoesNotExist:
        messages.error(request, 'You are not assigned to an ambulance.')
        return redirect('ambulances:mobile_dashboard')
    
    # Get dispatch history
    dispatches = Dispatch.objects.filter(
        ambulance=ambulance
    ).select_related('referral').order_by('-created_at')[:20]
    
    context = {
        'ambulance': ambulance,
        'dispatches': dispatches,
        'is_mobile': True,
    }
    
    return render(request, 'ambulances/mobile/dispatch_history.html', context)


class MobileInstallView(TemplateView):
    """PWA installation instructions"""
    template_name = 'ambulances/mobile/install.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_mobile'] = True
        return context
