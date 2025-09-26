"""
Hospital Integration API Views
Provides REST API endpoints for hospital capacity monitoring,
bed availability tracking, and emergency department status.
"""

import logging
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import hospital_service, BedType, EDStatus, HospitalStatus
from .models import Hospital
from .serializers import HospitalStatusSerializer, BedAvailabilitySerializer
from core.permissions import IsDispatcherOrAdmin, IsHospitalStaff

logger = logging.getLogger(__name__)

class HospitalStatusAPIView(APIView):
    """
    API endpoint for retrieving hospital status information.
    """
    permission_classes = [IsAuthenticated]
    
    async def get(self, request, hospital_id=None):
        """
        Get hospital status information.
        
        Query parameters:
        - specialty: Filter by medical specialty
        - bed_type: Filter by bed type
        - max_distance: Maximum distance in kilometers
        - lat, lng: Ambulance location for distance calculation
        """
        try:
            if hospital_id:
                # Get specific hospital status
                hospital_status = await hospital_service.get_hospital_status(hospital_id)
                if not hospital_status:
                    return Response(
                        {"error": "Hospital not found"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                serializer = HospitalStatusSerializer(hospital_status)
                return Response(serializer.data)
            
            else:
                # Get available hospitals based on criteria
                specialty = request.query_params.get('specialty')
                bed_type_str = request.query_params.get('bed_type')
                max_distance = request.query_params.get('max_distance')
                lat = request.query_params.get('lat')
                lng = request.query_params.get('lng')
                
                # Parse parameters
                bed_type = None
                if bed_type_str:
                    try:
                        bed_type = BedType(bed_type_str.upper())
                    except ValueError:
                        return Response(
                            {"error": f"Invalid bed_type: {bed_type_str}"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                max_distance_km = None
                if max_distance:
                    try:
                        max_distance_km = float(max_distance)
                    except ValueError:
                        return Response(
                            {"error": "Invalid max_distance value"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                ambulance_location = None
                if lat and lng:
                    try:
                        ambulance_location = (float(lat), float(lng))
                    except ValueError:
                        return Response(
                            {"error": "Invalid location coordinates"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Get available hospitals
                available_hospitals = await hospital_service.get_available_hospitals(
                    specialty=specialty,
                    bed_type=bed_type,
                    max_distance_km=max_distance_km,
                    ambulance_location=ambulance_location
                )
                
                serializer = HospitalStatusSerializer(available_hospitals, many=True)
                return Response({
                    "hospitals": serializer.data,
                    "count": len(available_hospitals)
                })
                
        except Exception as e:
            logger.error(f"Error in HospitalStatusAPIView: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BedAvailabilityAPIView(APIView):
    """
    API endpoint for updating bed availability.
    """
    permission_classes = [IsAuthenticated, IsHospitalStaff]
    
    async def post(self, request, hospital_id):
        """
        Update bed availability for a hospital.
        
        Request body:
        {
            "bed_type": "ICU",
            "occupied_beds": 15,
            "available_beds": 3,
            "reserved_beds": 2,
            "maintenance_beds": 1
        }
        """
        try:
            # Validate hospital access
            if not await self._can_update_hospital(request.user, hospital_id):
                return Response(
                    {"error": "Permission denied"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Parse request data
            bed_type_str = request.data.get('bed_type')
            occupied_beds = request.data.get('occupied_beds')
            available_beds = request.data.get('available_beds')
            reserved_beds = request.data.get('reserved_beds', 0)
            maintenance_beds = request.data.get('maintenance_beds', 0)
            
            # Validate required fields
            if not all([bed_type_str is not None, occupied_beds is not None, available_beds is not None]):
                return Response(
                    {"error": "Missing required fields: bed_type, occupied_beds, available_beds"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate bed_type
            try:
                bed_type = BedType(bed_type_str.upper())
            except ValueError:
                return Response(
                    {"error": f"Invalid bed_type: {bed_type_str}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate numeric values
            try:
                occupied_beds = int(occupied_beds)
                available_beds = int(available_beds)
                reserved_beds = int(reserved_beds)
                maintenance_beds = int(maintenance_beds)
                
                if any(val < 0 for val in [occupied_beds, available_beds, reserved_beds, maintenance_beds]):
                    raise ValueError("Negative values not allowed")
                    
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid numeric values"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update bed availability
            success = await hospital_service.update_bed_availability(
                hospital_id=hospital_id,
                bed_type=bed_type,
                occupied_beds=occupied_beds,
                available_beds=available_beds,
                reserved_beds=reserved_beds,
                maintenance_beds=maintenance_beds
            )
            
            if success:
                return Response({
                    "message": "Bed availability updated successfully",
                    "hospital_id": hospital_id,
                    "bed_type": bed_type.value,
                    "available_beds": available_beds
                })
            else:
                return Response(
                    {"error": "Failed to update bed availability"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error updating bed availability: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _can_update_hospital(self, user, hospital_id: str) -> bool:
        """Check if user can update this hospital's data."""
        # Admin can update any hospital
        if user.is_staff or user.is_superuser:
            return True
        
        # Hospital staff can only update their own hospital
        try:
            hospital = await Hospital.objects.aget(id=hospital_id)
            return hasattr(user, 'hospital') and user.hospital == hospital
        except Hospital.DoesNotExist:
            return False

class EDStatusAPIView(APIView):
    """
    API endpoint for updating Emergency Department status.
    """
    permission_classes = [IsAuthenticated, IsHospitalStaff]
    
    async def post(self, request, hospital_id):
        """
        Update Emergency Department status.
        
        Request body:
        {
            "status": "BUSY",
            "reason": "High patient volume"
        }
        """
        try:
            # Validate hospital access
            if not await self._can_update_hospital(request.user, hospital_id):
                return Response(
                    {"error": "Permission denied"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Parse request data
            status_str = request.data.get('status')
            reason = request.data.get('reason', '')
            
            if not status_str:
                return Response(
                    {"error": "Missing required field: status"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate status
            try:
                ed_status = EDStatus(status_str.upper())
            except ValueError:
                return Response(
                    {"error": f"Invalid status: {status_str}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update ED status
            success = await hospital_service.update_ed_status(
                hospital_id=hospital_id,
                status=ed_status,
                reason=reason
            )
            
            if success:
                return Response({
                    "message": "ED status updated successfully",
                    "hospital_id": hospital_id,
                    "status": ed_status.value,
                    "reason": reason
                })
            else:
                return Response(
                    {"error": "Failed to update ED status"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error updating ED status: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _can_update_hospital(self, user, hospital_id: str) -> bool:
        """Check if user can update this hospital's data."""
        # Admin can update any hospital
        if user.is_staff or user.is_superuser:
            return True
        
        # Hospital staff can only update their own hospital
        try:
            hospital = await Hospital.objects.aget(id=hospital_id)
            return hasattr(user, 'hospital') and user.hospital == hospital
        except Hospital.DoesNotExist:
            return False

class HospitalRecommendationAPIView(APIView):
    """
    API endpoint for getting hospital recommendations.
    """
    permission_classes = [IsAuthenticated, IsDispatcherOrAdmin]
    
    async def post(self, request):
        """
        Get hospital recommendation based on patient condition and location.
        
        Request body:
        {
            "patient_condition": "Chest pain, shortness of breath",
            "ambulance_location": [40.7128, -74.0060],
            "required_specialty": "cardiology",
            "urgent": true
        }
        """
        try:
            # Parse request data
            patient_condition = request.data.get('patient_condition')
            ambulance_location = request.data.get('ambulance_location')
            required_specialty = request.data.get('required_specialty')
            urgent = request.data.get('urgent', False)
            
            # Validate required fields
            if not patient_condition or not ambulance_location:
                return Response(
                    {"error": "Missing required fields: patient_condition, ambulance_location"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate ambulance location
            if not isinstance(ambulance_location, list) or len(ambulance_location) != 2:
                return Response(
                    {"error": "ambulance_location must be [latitude, longitude]"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                lat, lng = float(ambulance_location[0]), float(ambulance_location[1])
                ambulance_location = (lat, lng)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid location coordinates"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get hospital recommendation
            recommended_hospital = await hospital_service.recommend_hospital(
                patient_condition=patient_condition,
                ambulance_location=ambulance_location,
                required_specialty=required_specialty,
                urgent=urgent
            )
            
            if recommended_hospital:
                serializer = HospitalStatusSerializer(recommended_hospital)
                return Response({
                    "recommended_hospital": serializer.data,
                    "recommendation_factors": {
                        "patient_condition": patient_condition,
                        "urgent": urgent,
                        "specialty": required_specialty,
                        "distance_considered": True
                    }
                })
            else:
                return Response({
                    "message": "No suitable hospital found",
                    "recommended_hospital": None
                })
                
        except Exception as e:
            logger.error(f"Error getting hospital recommendation: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Legacy function-based views for backward compatibility
@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def hospital_capacity_view(request, hospital_id):
    """Get hospital capacity information (legacy endpoint)."""
    try:
        hospital_status = await hospital_service.get_hospital_status(hospital_id)
        if not hospital_status:
            return Response(
                {"error": "Hospital not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Format response for legacy compatibility
        capacity_data = {}
        for bed_type, capacity in hospital_status.bed_capacities.items():
            capacity_data[bed_type.value] = {
                "total": capacity.total_beds,
                "occupied": capacity.occupied_beds,
                "available": capacity.available_beds,
                "occupancy_rate": capacity.occupancy_rate
            }
        
        return Response({
            "hospital_id": hospital_id,
            "hospital_name": hospital_status.name,
            "ed_status": hospital_status.ed_status.value,
            "accepting_patients": hospital_status.accepting_ambulances,
            "capacity": capacity_data,
            "wait_time_minutes": hospital_status.wait_time_minutes,
            "last_updated": hospital_status.last_updated.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in hospital_capacity_view: {str(e)}")
        return Response(
            {"error": "Internal server error"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@require_http_methods(["POST"])
@login_required
async def update_hospital_status_view(request, hospital_id):
    """Update hospital status (legacy endpoint)."""
    try:
        import json
        data = json.loads(request.body)
        
        # Update ED status if provided
        if 'ed_status' in data:
            ed_status = EDStatus(data['ed_status'].upper())
            await hospital_service.update_ed_status(
                hospital_id, 
                ed_status, 
                data.get('reason', '')
            )
        
        # Update bed availability if provided
        if 'bed_updates' in data:
            for bed_update in data['bed_updates']:
                bed_type = BedType(bed_update['bed_type'].upper())
                await hospital_service.update_bed_availability(
                    hospital_id=hospital_id,
                    bed_type=bed_type,
                    occupied_beds=bed_update['occupied'],
                    available_beds=bed_update['available']
                )
        
        return JsonResponse({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error in update_hospital_status_view: {str(e)}")
        return JsonResponse(
            {"error": "Internal server error"}, 
            status=500
        )