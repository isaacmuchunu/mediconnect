"""
Progressive Web App Views for Ambulance Crews
Provides mobile-optimized interfaces for field personnel with offline capabilities.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.conf import settings

from .models import Ambulance, AmbulanceCrewMember, DispatchLog
from .services import gps_service
from patients.models import Patient
from referrals.models import Referral
from hospitals.models import Hospital
from core.decorators import ambulance_crew_required

logger = logging.getLogger(__name__)

class AmbulanceCrewDashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard for ambulance crew members with PWA support.
    """
    template_name = 'ambulances/pwa/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get crew member's ambulance
            crew_member = AmbulanceCrewMember.objects.get(user=self.request.user)
            ambulance = crew_member.ambulance
            
            # Get current dispatch
            current_dispatch = DispatchLog.objects.filter(
                ambulance=ambulance,
                status__in=['DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'TRANSPORTING']
            ).order_by('-created_at').first()
            
            # Get recent dispatches
            recent_dispatches = DispatchLog.objects.filter(
                ambulance=ambulance
            ).order_by('-created_at')[:10]
            
            # Get ambulance status
            ambulance_status = {
                'id': str(ambulance.id),
                'call_sign': ambulance.call_sign,
                'status': ambulance.status,
                'current_location': {
                    'latitude': float(ambulance.current_latitude) if ambulance.current_latitude else None,
                    'longitude': float(ambulance.current_longitude) if ambulance.current_longitude else None
                },
                'fuel_level': ambulance.fuel_level,
                'mileage': ambulance.mileage,
                'last_updated': ambulance.last_updated.isoformat() if ambulance.last_updated else None
            }
            
            # PWA configuration
            pwa_config = {
                'offline_mode': True,
                'background_sync': True,
                'push_notifications': True,
                'gps_tracking': True,
                'update_interval': 30000,  # 30 seconds
                'api_endpoints': {
                    'status_update': '/ambulance/api/status/',
                    'gps_update': '/ambulance/api/gps/',
                    'dispatch_accept': '/ambulance/api/dispatch/accept/',
                    'patient_data': '/patients/api/data/'
                }
            }
            
            context.update({
                'crew_member': crew_member,
                'ambulance': ambulance,
                'ambulance_status': ambulance_status,
                'current_dispatch': current_dispatch,
                'recent_dispatches': recent_dispatches,
                'pwa_config': json.dumps(pwa_config),
                'is_pwa': True,
                'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
            })
            
        except AmbulanceCrewMember.DoesNotExist:
            context.update({
                'error': 'You are not assigned to an ambulance crew.',
                'is_pwa': True
            })
        except Exception as e:
            logger.error(f"Error in crew dashboard: {str(e)}")
            context.update({
                'error': 'Unable to load dashboard data.',
                'is_pwa': True
            })
        
        return context

class DispatchView(LoginRequiredMixin, TemplateView):
    """
    Current dispatch information view for ambulance crews.
    """
    template_name = 'ambulances/pwa/dispatch.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            crew_member = AmbulanceCrewMember.objects.get(user=self.request.user)
            ambulance = crew_member.ambulance
            
            # Get current active dispatch
            dispatch = DispatchLog.objects.filter(
                ambulance=ambulance,
                status__in=['DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'TRANSPORTING']
            ).order_by('-created_at').first()
            
            if dispatch:
                # Get patient information (if available)
                patient_data = None
                if hasattr(dispatch, 'patient') and dispatch.patient:
                    patient_data = {
                        'id': str(dispatch.patient.id),
                        'name': f"{dispatch.patient.first_name} {dispatch.patient.last_name}",
                        'age': dispatch.patient.age,
                        'gender': dispatch.patient.gender,
                        'medical_record_number': dispatch.patient.medical_record_number,
                        'emergency_contact': dispatch.patient.emergency_contact_phone,
                        'allergies': dispatch.patient.allergies,
                        'medications': dispatch.patient.current_medications,
                        'medical_history': dispatch.patient.medical_history
                    }
                
                # Get destination hospital
                hospital_data = None
                if hasattr(dispatch, 'destination_hospital') and dispatch.destination_hospital:
                    hospital_data = {
                        'id': str(dispatch.destination_hospital.id),
                        'name': dispatch.destination_hospital.name,
                        'address': dispatch.destination_hospital.address,
                        'phone': dispatch.destination_hospital.emergency_contact,
                        'location': {
                            'latitude': float(dispatch.destination_hospital.latitude),
                            'longitude': float(dispatch.destination_hospital.longitude)
                        }
                    }
                
                dispatch_data = {
                    'id': str(dispatch.id),
                    'incident_type': dispatch.incident_type,
                    'priority': dispatch.priority,
                    'status': dispatch.status,
                    'location': {
                        'address': dispatch.incident_address,
                        'latitude': float(dispatch.incident_latitude) if dispatch.incident_latitude else None,
                        'longitude': float(dispatch.incident_longitude) if dispatch.incident_longitude else None
                    },
                    'created_at': dispatch.created_at.isoformat(),
                    'estimated_arrival': dispatch.estimated_arrival_time.isoformat() if dispatch.estimated_arrival_time else None,
                    'patient': patient_data,
                    'hospital': hospital_data,
                    'notes': dispatch.notes
                }
                
                context.update({
                    'dispatch': dispatch_data,
                    'has_active_dispatch': True
                })
            else:
                context.update({
                    'has_active_dispatch': False,
                    'message': 'No active dispatch assignment'
                })
                
        except AmbulanceCrewMember.DoesNotExist:
            context['error'] = 'You are not assigned to an ambulance crew.'
        except Exception as e:
            logger.error(f"Error in dispatch view: {str(e)}")
            context['error'] = 'Unable to load dispatch information.'
        
        context['is_pwa'] = True
        return context

class NavigationView(LoginRequiredMixin, TemplateView):
    """
    GPS navigation view for ambulance crews.
    """
    template_name = 'ambulances/pwa/navigation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            crew_member = AmbulanceCrewMember.objects.get(user=self.request.user)
            ambulance = crew_member.ambulance
            
            # Get current dispatch for navigation
            dispatch = DispatchLog.objects.filter(
                ambulance=ambulance,
                status__in=['DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'TRANSPORTING']
            ).order_by('-created_at').first()
            
            navigation_data = {
                'ambulance_location': {
                    'latitude': float(ambulance.current_latitude) if ambulance.current_latitude else None,
                    'longitude': float(ambulance.current_longitude) if ambulance.current_longitude else None
                },
                'destinations': []
            }
            
            if dispatch:
                # Add incident location
                if dispatch.incident_latitude and dispatch.incident_longitude:
                    navigation_data['destinations'].append({
                        'type': 'incident',
                        'name': 'Incident Location',
                        'address': dispatch.incident_address,
                        'latitude': float(dispatch.incident_latitude),
                        'longitude': float(dispatch.incident_longitude),
                        'priority': 1
                    })
                
                # Add hospital destination
                if hasattr(dispatch, 'destination_hospital') and dispatch.destination_hospital:
                    hospital = dispatch.destination_hospital
                    navigation_data['destinations'].append({
                        'type': 'hospital',
                        'name': hospital.name,
                        'address': hospital.address,
                        'latitude': float(hospital.latitude),
                        'longitude': float(hospital.longitude),
                        'priority': 2 if dispatch.status in ['ON_SCENE', 'TRANSPORTING'] else 3
                    })
            
            # Get nearby hospitals as alternatives
            if ambulance.current_latitude and ambulance.current_longitude:
                nearby_hospitals = Hospital.objects.filter(
                    is_active=True,
                    accepting_ambulances=True
                )[:5]  # Get first 5 for performance
                
                for hospital in nearby_hospitals:
                    navigation_data['destinations'].append({
                        'type': 'alternative_hospital',
                        'name': f"{hospital.name} (Alternative)",
                        'address': hospital.address,
                        'latitude': float(hospital.latitude),
                        'longitude': float(hospital.longitude),
                        'priority': 5
                    })
            
            context.update({
                'navigation_data': json.dumps(navigation_data),
                'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
                'has_gps': ambulance.current_latitude is not None
            })
            
        except AmbulanceCrewMember.DoesNotExist:
            context['error'] = 'You are not assigned to an ambulance crew.'
        except Exception as e:
            logger.error(f"Error in navigation view: {str(e)}")
            context['error'] = 'Unable to load navigation data.'
        
        context['is_pwa'] = True
        return context

class PatientDataView(LoginRequiredMixin, TemplateView):
    """
    Patient information and data entry view for ambulance crews.
    """
    template_name = 'ambulances/pwa/patient.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            crew_member = AmbulanceCrewMember.objects.get(user=self.request.user)
            ambulance = crew_member.ambulance
            
            # Get current dispatch
            dispatch = DispatchLog.objects.filter(
                ambulance=ambulance,
                status__in=['DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'TRANSPORTING']
            ).order_by('-created_at').first()
            
            patient_data = None
            if dispatch and hasattr(dispatch, 'patient') and dispatch.patient:
                patient = dispatch.patient
                patient_data = {
                    'id': str(patient.id),
                    'name': f"{patient.first_name} {patient.last_name}",
                    'age': patient.age,
                    'gender': patient.gender,
                    'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                    'medical_record_number': patient.medical_record_number,
                    'emergency_contact': patient.emergency_contact_phone,
                    'allergies': patient.allergies,
                    'medications': patient.current_medications,
                    'medical_history': patient.medical_history,
                    'insurance_info': patient.insurance_provider
                }
            
            # Patient assessment form fields
            assessment_fields = [
                {
                    'name': 'chief_complaint',
                    'label': 'Chief Complaint',
                    'type': 'textarea',
                    'required': True
                },
                {
                    'name': 'vital_signs',
                    'label': 'Vital Signs',
                    'type': 'group',
                    'fields': [
                        {'name': 'blood_pressure', 'label': 'Blood Pressure', 'type': 'text'},
                        {'name': 'heart_rate', 'label': 'Heart Rate (bpm)', 'type': 'number'},
                        {'name': 'respiratory_rate', 'label': 'Respiratory Rate', 'type': 'number'},
                        {'name': 'temperature', 'label': 'Temperature (°F)', 'type': 'number'},
                        {'name': 'oxygen_saturation', 'label': 'O2 Saturation (%)', 'type': 'number'},
                        {'name': 'blood_glucose', 'label': 'Blood Glucose', 'type': 'number'}
                    ]
                },
                {
                    'name': 'medications_given',
                    'label': 'Medications Administered',
                    'type': 'textarea'
                },
                {
                    'name': 'procedures_performed',
                    'label': 'Procedures Performed',
                    'type': 'textarea'
                },
                {
                    'name': 'patient_condition',
                    'label': 'Patient Condition',
                    'type': 'select',
                    'options': [
                        'Stable',
                        'Unstable',
                        'Critical',
                        'Deceased'
                    ]
                },
                {
                    'name': 'notes',
                    'label': 'Additional Notes',
                    'type': 'textarea'
                }
            ]
            
            context.update({
                'patient_data': patient_data,
                'assessment_fields': assessment_fields,
                'has_patient': patient_data is not None,
                'dispatch_id': str(dispatch.id) if dispatch else None
            })
            
        except AmbulanceCrewMember.DoesNotExist:
            context['error'] = 'You are not assigned to an ambulance crew.'
        except Exception as e:
            logger.error(f"Error in patient data view: {str(e)}")
            context['error'] = 'Unable to load patient data.'
        
        context['is_pwa'] = True
        return context

class CommunicationView(LoginRequiredMixin, TemplateView):
    """
    Communication center view for ambulance crews.
    """
    template_name = 'ambulances/pwa/communication.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            crew_member = AmbulanceCrewMember.objects.get(user=self.request.user)
            ambulance = crew_member.ambulance
            
            # Emergency contacts
            emergency_contacts = [
                {
                    'name': 'Dispatch Center',
                    'phone': getattr(settings, 'DISPATCH_CENTER_PHONE', '911'),
                    'type': 'dispatch'
                },
                {
                    'name': 'Medical Control',
                    'phone': getattr(settings, 'MEDICAL_CONTROL_PHONE', ''),
                    'type': 'medical'
                },
                {
                    'name': 'Supervisor',
                    'phone': getattr(settings, 'SUPERVISOR_PHONE', ''),
                    'type': 'supervisor'
                }
            ]
            
            # Quick status buttons
            status_options = [
                {'value': 'AVAILABLE', 'label': 'Available', 'color': 'green'},
                {'value': 'EN_ROUTE', 'label': 'En Route', 'color': 'blue'},
                {'value': 'ON_SCENE', 'label': 'On Scene', 'color': 'yellow'},
                {'value': 'TRANSPORTING', 'label': 'Transporting', 'color': 'orange'},
                {'value': 'AT_HOSPITAL', 'label': 'At Hospital', 'color': 'purple'},
                {'value': 'OUT_OF_SERVICE', 'label': 'Out of Service', 'color': 'red'}
            ]
            
            context.update({
                'ambulance': ambulance,
                'emergency_contacts': emergency_contacts,
                'status_options': status_options,
                'current_status': ambulance.status,
                'websocket_url': f"ws://{self.request.get_host()}/ws/ambulance/{ambulance.id}/"
            })
            
        except AmbulanceCrewMember.DoesNotExist:
            context['error'] = 'You are not assigned to an ambulance crew.'
        except Exception as e:
            logger.error(f"Error in communication view: {str(e)}")
            context['error'] = 'Unable to load communication interface.'
        
        context['is_pwa'] = True
        return context

class OfflineView(TemplateView):
    """
    Offline fallback page for PWA.
    """
    template_name = 'ambulances/pwa/offline.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_pwa'] = True
        return context

# API Views for PWA functionality

@csrf_exempt
@require_http_methods(["POST"])
@ambulance_crew_required
def update_ambulance_status(request):
    """
    Update ambulance status via PWA.
    """
    try:
        data = json.loads(request.body)
        crew_member = AmbulanceCrewMember.objects.get(user=request.user)
        ambulance = crew_member.ambulance
        
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        if new_status and new_status in [choice[0] for choice in Ambulance.STATUS_CHOICES]:
            ambulance.status = new_status
            ambulance.last_updated = timezone.now()
            ambulance.save()
            
            # Log status change
            logger.info(f"Ambulance {ambulance.call_sign} status updated to {new_status} by {request.user}")
            
            return JsonResponse({
                'success': True,
                'status': new_status,
                'timestamp': ambulance.last_updated.isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status'
            }, status=400)
            
    except AmbulanceCrewMember.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Not authorized'
        }, status=403)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating ambulance status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@ambulance_crew_required
def update_gps_location(request):
    """
    Update ambulance GPS location via PWA.
    """
    try:
        data = json.loads(request.body)
        crew_member = AmbulanceCrewMember.objects.get(user=request.user)
        ambulance = crew_member.ambulance
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy', 10.0)
        speed = data.get('speed', 0.0)
        heading = data.get('heading', 0.0)
        
        if latitude is not None and longitude is not None:
            # Update ambulance location
            ambulance.current_latitude = latitude
            ambulance.current_longitude = longitude
            ambulance.last_updated = timezone.now()
            ambulance.save()
            
            # Use GPS service for advanced tracking
            from .services import gps_service
            from .services import GPSLocation
            
            gps_location = GPSLocation(
                latitude=latitude,
                longitude=longitude,
                speed=speed,
                heading=heading,
                accuracy=accuracy,
                timestamp=timezone.now()
            )
            
            # Update via GPS service (async)
            # This would typically be called asynchronously
            # await gps_service.update_ambulance_location(str(ambulance.id), gps_location)
            
            return JsonResponse({
                'success': True,
                'location': {
                    'latitude': latitude,
                    'longitude': longitude
                },
                'timestamp': ambulance.last_updated.isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Latitude and longitude required'
            }, status=400)
            
    except AmbulanceCrewMember.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Not authorized'
        }, status=403)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating GPS location: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@require_http_methods(["GET"])
@ambulance_crew_required
def get_current_dispatch(request):
    """
    Get current dispatch information for PWA.
    """
    try:
        crew_member = AmbulanceCrewMember.objects.get(user=request.user)
        ambulance = crew_member.ambulance
        
        dispatch = DispatchLog.objects.filter(
            ambulance=ambulance,
            status__in=['DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'TRANSPORTING']
        ).order_by('-created_at').first()
        
        if dispatch:
            dispatch_data = {
                'id': str(dispatch.id),
                'incident_type': dispatch.incident_type,
                'priority': dispatch.priority,
                'status': dispatch.status,
                'location': {
                    'address': dispatch.incident_address,
                    'latitude': float(dispatch.incident_latitude) if dispatch.incident_latitude else None,
                    'longitude': float(dispatch.incident_longitude) if dispatch.incident_longitude else None
                },
                'created_at': dispatch.created_at.isoformat(),
                'estimated_arrival': dispatch.estimated_arrival_time.isoformat() if dispatch.estimated_arrival_time else None,
                'notes': dispatch.notes
            }
            
            return JsonResponse({
                'success': True,
                'dispatch': dispatch_data
            })
        else:
            return JsonResponse({
                'success': True,
                'dispatch': None,
                'message': 'No active dispatch'
            })
            
    except AmbulanceCrewMember.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Not authorized'
        }, status=403)
    except Exception as e:
        logger.error(f"Error getting current dispatch: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@require_http_methods(["GET"])
def pwa_health_check(request):
    """
    Health check endpoint for PWA.
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.2.0'
    })