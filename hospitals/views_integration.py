"""
Hospital Integration Views
Comprehensive hospital capacity management and real-time status monitoring
"""

import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q, Avg, Sum, Count
from django.core.paginator import Paginator

from doctors.models import Hospital
from .models_integration import (
    HospitalCapacity, BedManagement, EmergencyDepartmentStatus,
    SpecialtyUnitStatus, HospitalAlert
)


def is_hospital_staff(user):
    """Check if user is hospital staff"""
    return user.is_authenticated and (
        user.is_staff or 
        user.role in ['DOCTOR', 'NURSE', 'ADMIN', 'HOSPITAL_ADMIN'] or
        user.groups.filter(name__in=['Hospital Staff', 'Doctors', 'Nurses']).exists()
    )


def is_dispatcher_or_hospital_staff(user):
    """Check if user is dispatcher or hospital staff"""
    return user.is_authenticated and (
        user.is_staff or 
        user.role in ['DISPATCHER', 'DOCTOR', 'NURSE', 'ADMIN', 'HOSPITAL_ADMIN'] or
        user.groups.filter(name__in=['Dispatchers', 'Hospital Staff', 'Doctors', 'Nurses']).exists()
    )


@login_required
@user_passes_test(is_dispatcher_or_hospital_staff)
def hospital_capacity_dashboard(request):
    """Hospital capacity overview dashboard"""
    
    # Get all hospitals with capacity data
    hospitals = Hospital.objects.select_related('capacity_status', 'ed_status').prefetch_related(
        'specialty_units', 'alerts'
    ).filter(is_active=True)
    
    # Calculate overall statistics
    total_hospitals = hospitals.count()
    hospitals_at_capacity = hospitals.filter(capacity_status__overall_status='full').count()
    hospitals_on_diversion = hospitals.filter(capacity_status__ambulance_diversion=True).count()
    
    # Get active alerts
    active_alerts = HospitalAlert.objects.filter(
        is_active=True,
        hospital__in=hospitals
    ).select_related('hospital').order_by('-severity', '-alert_start')[:10]
    
    # Calculate bed statistics
    bed_stats = {
        'total_beds': sum(h.capacity_status.total_beds for h in hospitals if h.capacity_status),
        'occupied_beds': sum(h.capacity_status.occupied_beds for h in hospitals if h.capacity_status),
        'available_beds': sum(h.capacity_status.available_beds for h in hospitals if h.capacity_status),
    }
    
    if bed_stats['total_beds'] > 0:
        bed_stats['occupancy_rate'] = (bed_stats['occupied_beds'] / bed_stats['total_beds']) * 100
    else:
        bed_stats['occupancy_rate'] = 0
    
    # Get hospitals needing attention
    critical_hospitals = hospitals.filter(
        Q(capacity_status__overall_status__in=['critical', 'full']) |
        Q(capacity_status__ambulance_diversion=True) |
        Q(ed_status__diversion_status=True)
    )
    
    context = {
        'hospitals': hospitals,
        'critical_hospitals': critical_hospitals,
        'active_alerts': active_alerts,
        'stats': {
            'total_hospitals': total_hospitals,
            'hospitals_at_capacity': hospitals_at_capacity,
            'hospitals_on_diversion': hospitals_on_diversion,
            'bed_stats': bed_stats,
        }
    }
    
    return render(request, 'hospitals/integration/capacity_dashboard.html', context)


@login_required
@user_passes_test(is_hospital_staff)
def hospital_detail_capacity(request, hospital_id):
    """Detailed hospital capacity management"""
    
    hospital = get_object_or_404(Hospital, id=hospital_id)
    
    # Get or create capacity status
    capacity, created = HospitalCapacity.objects.get_or_create(
        hospital=hospital,
        defaults={
            'total_beds': 100,  # Default values
            'occupied_beds': 0,
            'available_beds': 100,
        }
    )
    
    # Get or create ED status
    ed_status, created = EmergencyDepartmentStatus.objects.get_or_create(
        hospital=hospital,
        defaults={
            'ed_beds_total': 20,
            'trauma_bays_total': 4,
        }
    )
    
    # Get specialty units
    specialty_units = SpecialtyUnitStatus.objects.filter(hospital=hospital)
    
    # Get bed management
    beds = BedManagement.objects.filter(hospital=hospital).order_by('ward_name', 'bed_number')
    
    # Get recent alerts
    recent_alerts = HospitalAlert.objects.filter(
        hospital=hospital,
        alert_start__gte=timezone.now() - timedelta(days=7)
    ).order_by('-alert_start')[:10]
    
    # Calculate statistics
    bed_stats = {
        'total_beds': beds.count(),
        'available_beds': beds.filter(status='available').count(),
        'occupied_beds': beds.filter(status='occupied').count(),
        'reserved_beds': beds.filter(status='reserved').count(),
        'maintenance_beds': beds.filter(status__in=['maintenance', 'cleaning']).count(),
    }
    
    context = {
        'hospital': hospital,
        'capacity': capacity,
        'ed_status': ed_status,
        'specialty_units': specialty_units,
        'beds': beds,
        'recent_alerts': recent_alerts,
        'bed_stats': bed_stats,
    }
    
    return render(request, 'hospitals/integration/hospital_detail.html', context)


@login_required
@user_passes_test(is_hospital_staff)
@require_POST
@csrf_exempt
def update_hospital_capacity(request):
    """Update hospital capacity via AJAX"""
    
    try:
        data = json.loads(request.body)
        hospital_id = data.get('hospital_id')
        
        hospital = get_object_or_404(Hospital, id=hospital_id)
        capacity, created = HospitalCapacity.objects.get_or_create(hospital=hospital)
        
        # Update capacity fields
        update_fields = [
            'total_beds', 'occupied_beds', 'reserved_beds',
            'ed_wait_time_minutes', 'ed_patients_waiting',
            'icu_beds_available', 'icu_beds_total',
            'or_rooms_available', 'or_rooms_total',
            'doctors_on_duty', 'nurses_on_duty',
            'ventilators_available', 'ventilators_total',
            'ambulance_diversion', 'diversion_reason'
        ]
        
        for field in update_fields:
            if field in data:
                setattr(capacity, field, data[field])
        
        capacity.updated_by = request.user
        capacity.update_capacity()  # This will auto-calculate status
        
        return JsonResponse({
            'status': 'success',
            'message': 'Hospital capacity updated successfully',
            'capacity_status': capacity.overall_status,
            'occupancy_rate': capacity.bed_occupancy_rate,
            'can_accept_patients': capacity.can_accept_patients
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_hospital_staff)
@require_POST
@csrf_exempt
def update_ed_status(request):
    """Update Emergency Department status"""
    
    try:
        data = json.loads(request.body)
        hospital_id = data.get('hospital_id')
        
        hospital = get_object_or_404(Hospital, id=hospital_id)
        ed_status, created = EmergencyDepartmentStatus.objects.get_or_create(hospital=hospital)
        
        # Update ED fields
        update_fields = [
            'is_open', 'diversion_status', 'trauma_center_status',
            'level_1_wait_minutes', 'level_2_wait_minutes', 'level_3_wait_minutes',
            'level_4_wait_minutes', 'level_5_wait_minutes',
            'patients_waiting', 'patients_in_treatment',
            'ed_beds_occupied', 'trauma_bays_occupied',
            'physicians_on_duty', 'nurses_on_duty', 'residents_on_duty',
            'mass_casualty_alert', 'psychiatric_hold_available',
            'isolation_rooms_available'
        ]
        
        for field in update_fields:
            if field in data:
                setattr(ed_status, field, data[field])
        
        ed_status.updated_by = request.user
        ed_status.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'ED status updated successfully',
            'can_accept_ambulances': ed_status.can_accept_ambulances,
            'average_wait_time': ed_status.average_wait_time,
            'occupancy_rate': ed_status.ed_occupancy_rate
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_hospital_staff)
@require_POST
@csrf_exempt
def update_bed_status(request):
    """Update individual bed status"""
    
    try:
        data = json.loads(request.body)
        bed_id = data.get('bed_id')
        new_status = data.get('status')
        
        bed = get_object_or_404(BedManagement, id=bed_id)
        
        # Handle different status changes
        if new_status == 'occupied':
            patient_name = data.get('patient_name', '')
            patient_id = data.get('patient_id', '')
            bed.admit_patient(patient_name, patient_id)
        elif new_status == 'reserved':
            patient_name = data.get('patient_name', '')
            bed.reserve_bed(patient_name)
        elif new_status == 'available':
            bed.mark_available()
        elif new_status == 'cleaning':
            bed.discharge_patient()
        else:
            bed.status = new_status
            bed.save()
        
        # Update hospital capacity
        hospital_capacity = bed.hospital.capacity_status
        if hospital_capacity:
            hospital_capacity.update_capacity()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Bed {bed.bed_number} status updated to {new_status}',
            'bed_status': bed.status
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_hospital_staff)
@require_POST
@csrf_exempt
def create_hospital_alert(request):
    """Create new hospital alert"""
    
    try:
        data = json.loads(request.body)
        hospital_id = data.get('hospital_id')
        
        hospital = get_object_or_404(Hospital, id=hospital_id)
        
        alert = HospitalAlert.objects.create(
            hospital=hospital,
            alert_type=data['alert_type'],
            severity=data['severity'],
            title=data['title'],
            message=data['message'],
            created_by=request.user
        )
        
        # Auto-create capacity alerts if needed
        if data['alert_type'] == 'capacity':
            capacity = hospital.capacity_status
            if capacity and capacity.overall_status in ['critical', 'full']:
                capacity.ambulance_diversion = True
                capacity.diversion_reason = f"Capacity Alert: {data['title']}"
                capacity.save()
        
        return JsonResponse({
            'status': 'success',
            'alert_id': str(alert.id),
            'message': 'Alert created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_dispatcher_or_hospital_staff)
def hospital_availability_api(request):
    """API endpoint for ambulance dispatchers to check hospital availability"""
    
    # Get query parameters
    emergency_type = request.GET.get('emergency_type', '')
    specialty_required = request.GET.get('specialty', '')
    latitude = request.GET.get('lat')
    longitude = request.GET.get('lng')
    
    # Get available hospitals
    hospitals = Hospital.objects.filter(
        is_active=True,
        capacity_status__isnull=False
    ).select_related('capacity_status', 'ed_status')
    
    # Filter by availability
    available_hospitals = hospitals.filter(
        capacity_status__ambulance_diversion=False,
        capacity_status__overall_status__in=['normal', 'busy'],
        ed_status__is_open=True,
        ed_status__diversion_status=False
    )
    
    # Filter by specialty if required
    if specialty_required:
        available_hospitals = available_hospitals.filter(
            specialty_units__unit_type=specialty_required,
            specialty_units__accepting_patients=True,
            specialty_units__available_capacity__gt=0
        )
    
    # Prepare response data
    hospital_data = []
    for hospital in available_hospitals:
        capacity = hospital.capacity_status
        ed_status = hospital.ed_status
        
        # Calculate distance if coordinates provided
        distance = None
        if latitude and longitude:
            # TODO: Implement distance calculation
            distance = 0  # Placeholder
        
        hospital_info = {
            'id': str(hospital.id),
            'name': hospital.name,
            'address': hospital.address,
            'phone': hospital.phone,
            'distance_km': distance,
            'capacity': {
                'status': capacity.overall_status,
                'available_beds': capacity.available_beds,
                'occupancy_rate': capacity.bed_occupancy_rate,
                'icu_beds_available': capacity.icu_beds_available,
                'can_accept_patients': capacity.can_accept_patients,
            },
            'ed_status': {
                'is_open': ed_status.is_open,
                'average_wait_time': ed_status.average_wait_time,
                'trauma_center': ed_status.trauma_center_status,
                'can_accept_ambulances': ed_status.can_accept_ambulances,
            },
            'specialty_units': []
        }
        
        # Add specialty unit information
        for unit in hospital.specialty_units.filter(accepting_patients=True):
            hospital_info['specialty_units'].append({
                'type': unit.unit_type,
                'name': unit.unit_name,
                'available_capacity': unit.available_capacity,
                'wait_time_minutes': unit.average_wait_time_minutes,
                'can_accept_patients': unit.can_accept_patients,
            })
        
        hospital_data.append(hospital_info)
    
    # Sort by availability and distance
    hospital_data.sort(key=lambda x: (
        not x['capacity']['can_accept_patients'],
        not x['ed_status']['can_accept_ambulances'],
        x['capacity']['occupancy_rate'],
        x['distance_km'] or 999
    ))
    
    return JsonResponse({
        'status': 'success',
        'hospitals': hospital_data,
        'total_available': len(hospital_data),
        'query_params': {
            'emergency_type': emergency_type,
            'specialty_required': specialty_required,
        }
    })


@login_required
@user_passes_test(is_hospital_staff)
def bed_management_view(request, hospital_id):
    """Bed management interface"""
    
    hospital = get_object_or_404(Hospital, id=hospital_id)
    
    # Get beds with filtering
    ward_filter = request.GET.get('ward', '')
    status_filter = request.GET.get('status', '')
    bed_type_filter = request.GET.get('bed_type', '')
    
    beds = BedManagement.objects.filter(hospital=hospital)
    
    if ward_filter:
        beds = beds.filter(ward_name__icontains=ward_filter)
    if status_filter:
        beds = beds.filter(status=status_filter)
    if bed_type_filter:
        beds = beds.filter(bed_type=bed_type_filter)
    
    beds = beds.order_by('ward_name', 'bed_number')
    
    # Pagination
    paginator = Paginator(beds, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get ward statistics
    ward_stats = {}
    for bed in BedManagement.objects.filter(hospital=hospital):
        ward = bed.ward_name
        if ward not in ward_stats:
            ward_stats[ward] = {
                'total': 0,
                'available': 0,
                'occupied': 0,
                'reserved': 0,
                'maintenance': 0
            }
        ward_stats[ward]['total'] += 1
        ward_stats[ward][bed.status] = ward_stats[ward].get(bed.status, 0) + 1
    
    context = {
        'hospital': hospital,
        'beds': page_obj,
        'ward_stats': ward_stats,
        'filters': {
            'ward': ward_filter,
            'status': status_filter,
            'bed_type': bed_type_filter,
        },
        'bed_status_choices': BedManagement.BED_STATUS_CHOICES,
        'bed_type_choices': BedManagement.BED_TYPE_CHOICES,
    }
    
    return render(request, 'hospitals/integration/bed_management.html', context)


@login_required
@user_passes_test(is_hospital_staff)
def alert_management_view(request, hospital_id):
    """Hospital alert management"""
    
    hospital = get_object_or_404(Hospital, id=hospital_id)
    
    # Get alerts with filtering
    status_filter = request.GET.get('status', 'active')
    alert_type_filter = request.GET.get('alert_type', '')
    
    alerts = HospitalAlert.objects.filter(hospital=hospital)
    
    if status_filter == 'active':
        alerts = alerts.filter(is_active=True)
    elif status_filter == 'resolved':
        alerts = alerts.filter(resolved=True)
    elif status_filter == 'acknowledged':
        alerts = alerts.filter(acknowledged=True, resolved=False)
    
    if alert_type_filter:
        alerts = alerts.filter(alert_type=alert_type_filter)
    
    alerts = alerts.order_by('-alert_start')
    
    # Pagination
    paginator = Paginator(alerts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'hospital': hospital,
        'alerts': page_obj,
        'filters': {
            'status': status_filter,
            'alert_type': alert_type_filter,
        },
        'alert_type_choices': HospitalAlert.ALERT_TYPE_CHOICES,
        'severity_choices': HospitalAlert.SEVERITY_CHOICES,
    }
    
    return render(request, 'hospitals/integration/alert_management.html', context)


@login_required
@user_passes_test(is_hospital_staff)
@require_POST
@csrf_exempt
def acknowledge_alert(request, alert_id):
    """Acknowledge hospital alert"""
    
    try:
        alert = get_object_or_404(HospitalAlert, id=alert_id)
        alert.acknowledge(request.user)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Alert acknowledged successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@user_passes_test(is_hospital_staff)
@require_POST
@csrf_exempt
def resolve_alert(request, alert_id):
    """Resolve hospital alert"""
    
    try:
        alert = get_object_or_404(HospitalAlert, id=alert_id)
        alert.resolve(request.user)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Alert resolved successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
