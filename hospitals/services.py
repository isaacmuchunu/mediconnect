"""
Hospital Integration Services
Provides real-time hospital capacity monitoring, bed availability tracking,
and emergency department status management for the e-referral system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from django.core.cache import cache
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from channels.layers import get_channel_layer

from doctors.models import Hospital
from patients.models import Patient
from referrals.models import Referral

logger = logging.getLogger(__name__)

class BedType(Enum):
    """Bed types for hospital capacity management."""
    ICU = "ICU"
    CCU = "CCU"
    GENERAL = "GENERAL"
    EMERGENCY = "EMERGENCY"
    PEDIATRIC = "PEDIATRIC"
    MATERNITY = "MATERNITY"
    ISOLATION = "ISOLATION"

class EDStatus(Enum):
    """Emergency Department status levels."""
    NORMAL = "NORMAL"
    BUSY = "BUSY"
    CRITICAL = "CRITICAL"
    DIVERT = "DIVERT"
    CLOSED = "CLOSED"

@dataclass
class BedCapacity:
    """Data class for bed capacity information."""
    bed_type: BedType
    total_beds: int
    occupied_beds: int
    available_beds: int
    reserved_beds: int = 0
    maintenance_beds: int = 0
    last_updated: datetime = None

    @property
    def occupancy_rate(self) -> float:
        """Calculate occupancy rate as percentage."""
        if self.total_beds == 0:
            return 0.0
        return (self.occupied_beds / self.total_beds) * 100

    @property
    def availability_rate(self) -> float:
        """Calculate availability rate as percentage."""
        if self.total_beds == 0:
            return 0.0
        return (self.available_beds / self.total_beds) * 100

@dataclass
class HospitalStatus:
    """Comprehensive hospital status information."""
    hospital_id: str
    name: str
    ed_status: EDStatus
    bed_capacities: Dict[BedType, BedCapacity]
    wait_time_minutes: int
    accepting_ambulances: bool
    accepting_referrals: bool
    contact_info: Dict[str, str]
    last_updated: datetime
    
    @property
    def overall_capacity_rate(self) -> float:
        """Calculate overall hospital capacity rate."""
        if not self.bed_capacities:
            return 0.0
        
        total_beds = sum(capacity.total_beds for capacity in self.bed_capacities.values())
        occupied_beds = sum(capacity.occupied_beds for capacity in self.bed_capacities.values())
        
        if total_beds == 0:
            return 0.0
        return (occupied_beds / total_beds) * 100

class HospitalIntegrationService:
    """
    Service for managing hospital integration, bed availability,
    and emergency department status in real-time.
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.cache_timeout = getattr(settings, 'HOSPITAL_CACHE_TIMEOUT', 300)  # 5 minutes
        
    async def get_hospital_status(self, hospital_id: str) -> Optional[HospitalStatus]:
        """
        Get comprehensive status for a specific hospital.
        
        Args:
            hospital_id: Hospital identifier
            
        Returns:
            HospitalStatus object or None if not found
        """
        try:
            # Check cache first
            cache_key = f"hospital_status_{hospital_id}"
            cached_status = cache.get(cache_key)
            if cached_status:
                return cached_status
            
            # Fetch from database
            hospital = await self._get_hospital(hospital_id)
            if not hospital:
                return None
                
            # Get bed capacities
            bed_capacities = await self._get_bed_capacities(hospital_id)
            
            # Get ED status
            ed_status = await self._get_ed_status(hospital_id)
            
            # Get wait times
            wait_time = await self._calculate_wait_time(hospital_id)
            
            # Build hospital status
            hospital_status = HospitalStatus(
                hospital_id=hospital_id,
                name=hospital.name,
                ed_status=ed_status,
                bed_capacities=bed_capacities,
                wait_time_minutes=wait_time,
                accepting_ambulances=hospital.accepting_ambulances,
                accepting_referrals=hospital.accepting_referrals,
                contact_info={
                    'phone': hospital.emergency_contact,
                    'email': hospital.contact_email,
                    'address': hospital.address
                },
                last_updated=timezone.now()
            )
            
            # Cache the result
            cache.set(cache_key, hospital_status, self.cache_timeout)
            
            return hospital_status
            
        except Exception as e:
            logger.error(f"Error getting hospital status for {hospital_id}: {str(e)}")
            return None
    
    async def get_available_hospitals(
        self, 
        specialty: Optional[str] = None,
        bed_type: Optional[BedType] = None,
        max_distance_km: Optional[float] = None,
        ambulance_location: Optional[Tuple[float, float]] = None
    ) -> List[HospitalStatus]:
        """
        Get list of hospitals with available capacity based on criteria.
        
        Args:
            specialty: Required medical specialty
            bed_type: Required bed type
            max_distance_km: Maximum distance from ambulance location
            ambulance_location: Tuple of (latitude, longitude)
            
        Returns:
            List of HospitalStatus objects sorted by availability
        """
        try:
            # Get all active hospitals
            hospitals = await self._get_active_hospitals()
            
            available_hospitals = []
            
            for hospital in hospitals:
                hospital_status = await self.get_hospital_status(hospital.id)
                if not hospital_status:
                    continue
                
                # Check if hospital meets criteria
                if not self._meets_criteria(
                    hospital_status, 
                    specialty, 
                    bed_type, 
                    max_distance_km, 
                    ambulance_location,
                    hospital
                ):
                    continue
                
                available_hospitals.append(hospital_status)
            
            # Sort by availability and wait time
            available_hospitals.sort(
                key=lambda h: (
                    h.ed_status.value != EDStatus.NORMAL.value,
                    h.wait_time_minutes,
                    -h.overall_capacity_rate
                )
            )
            
            return available_hospitals
            
        except Exception as e:
            logger.error(f"Error getting available hospitals: {str(e)}")
            return []
    
    async def update_bed_availability(
        self, 
        hospital_id: str, 
        bed_type: BedType, 
        occupied_beds: int,
        available_beds: int,
        reserved_beds: int = 0,
        maintenance_beds: int = 0
    ) -> bool:
        """
        Update bed availability for a hospital department.
        
        Args:
            hospital_id: Hospital identifier
            bed_type: Type of bed being updated
            occupied_beds: Number of occupied beds
            available_beds: Number of available beds
            reserved_beds: Number of reserved beds
            maintenance_beds: Number of beds under maintenance
            
        Returns:
            Success status
        """
        try:
            async with transaction.atomic():
                # Update database
                bed_availability, created = await BedAvailability.objects.aupdate_or_create(
                    hospital_id=hospital_id,
                    bed_type=bed_type.value,
                    defaults={
                        'occupied_beds': occupied_beds,
                        'available_beds': available_beds,
                        'reserved_beds': reserved_beds,
                        'maintenance_beds': maintenance_beds,
                        'last_updated': timezone.now()
                    }
                )
                
                # Clear cache
                cache_key = f"hospital_status_{hospital_id}"
                cache.delete(cache_key)
                
                # Broadcast update
                await self._broadcast_bed_update(hospital_id, bed_type, bed_availability)
                
                # Check for critical capacity alerts
                await self._check_capacity_alerts(hospital_id, bed_type, available_beds)
                
                logger.info(f"Updated bed availability for {hospital_id} - {bed_type.value}: {available_beds} available")
                return True
                
        except Exception as e:
            logger.error(f"Error updating bed availability: {str(e)}")
            return False
    
    async def update_ed_status(self, hospital_id: str, status: EDStatus, reason: str = "") -> bool:
        """
        Update Emergency Department status.
        
        Args:
            hospital_id: Hospital identifier
            status: New ED status
            reason: Reason for status change
            
        Returns:
            Success status
        """
        try:
            async with transaction.atomic():
                # Update database
                ed_dept = await self._get_or_create_ed_department(hospital_id)
                ed_dept.status = status.value
                ed_dept.status_reason = reason
                ed_dept.last_updated = timezone.now()
                await ed_dept.asave()
                
                # Clear cache
                cache_key = f"hospital_status_{hospital_id}"
                cache.delete(cache_key)
                
                # Broadcast update
                await self._broadcast_ed_status_update(hospital_id, status, reason)
                
                # Handle critical status changes
                if status in [EDStatus.DIVERT, EDStatus.CLOSED]:
                    await self._handle_critical_status_change(hospital_id, status)
                
                logger.info(f"Updated ED status for {hospital_id}: {status.value} - {reason}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating ED status: {str(e)}")
            return False
    
    async def recommend_hospital(
        self, 
        patient_condition: str,
        ambulance_location: Tuple[float, float],
        required_specialty: Optional[str] = None,
        urgent: bool = False
    ) -> Optional[HospitalStatus]:
        """
        Recommend the best hospital for a patient based on multiple factors.
        
        Args:
            patient_condition: Description of patient condition
            ambulance_location: Current ambulance location (lat, lng)
            required_specialty: Required medical specialty
            urgent: Whether this is an urgent case
            
        Returns:
            Recommended HospitalStatus or None
        """
        try:
            # Get available hospitals
            available_hospitals = await self.get_available_hospitals(
                specialty=required_specialty,
                max_distance_km=50.0 if urgent else 25.0,
                ambulance_location=ambulance_location
            )
            
            if not available_hospitals:
                return None
            
            # Score hospitals based on multiple factors
            scored_hospitals = []
            for hospital in available_hospitals:
                score = await self._calculate_hospital_score(
                    hospital, 
                    patient_condition, 
                    ambulance_location, 
                    urgent
                )
                scored_hospitals.append((hospital, score))
            
            # Sort by score (highest first)
            scored_hospitals.sort(key=lambda x: x[1], reverse=True)
            
            recommended_hospital = scored_hospitals[0][0]
            
            logger.info(f"Recommended hospital {recommended_hospital.name} for condition: {patient_condition}")
            return recommended_hospital
            
        except Exception as e:
            logger.error(f"Error recommending hospital: {str(e)}")
            return None
    
    # Private helper methods
    
    async def _get_hospital(self, hospital_id: str):
        """Get hospital from database."""
        try:
            return await Hospital.objects.aget(id=hospital_id, is_active=True)
        except Hospital.DoesNotExist:
            return None
    
    async def _get_active_hospitals(self):
        """Get all active hospitals."""
        return [hospital async for hospital in Hospital.objects.filter(is_active=True)]
    
    async def _get_bed_capacities(self, hospital_id: str) -> Dict[BedType, BedCapacity]:
        """Get bed capacities for all bed types in a hospital."""
        capacities = {}
        bed_availabilities = [
            bed async for bed in BedAvailability.objects.filter(hospital_id=hospital_id)
        ]
        
        for bed_availability in bed_availabilities:
            bed_type = BedType(bed_availability.bed_type)
            capacities[bed_type] = BedCapacity(
                bed_type=bed_type,
                total_beds=bed_availability.total_beds,
                occupied_beds=bed_availability.occupied_beds,
                available_beds=bed_availability.available_beds,
                reserved_beds=bed_availability.reserved_beds,
                maintenance_beds=bed_availability.maintenance_beds,
                last_updated=bed_availability.last_updated
            )
        
        return capacities
    
    async def _get_ed_status(self, hospital_id: str) -> EDStatus:
        """Get Emergency Department status."""
        try:
            ed_dept = await EmergencyDepartment.objects.aget(hospital_id=hospital_id)
            return EDStatus(ed_dept.status)
        except EmergencyDepartment.DoesNotExist:
            return EDStatus.NORMAL
    
    async def _calculate_wait_time(self, hospital_id: str) -> int:
        """Calculate average wait time based on recent referrals."""
        try:
            # Get recent referrals from last 4 hours
            cutoff_time = timezone.now() - timedelta(hours=4)
            recent_referrals = [
                ref async for ref in Referral.objects.filter(
                    receiving_hospital_id=hospital_id,
                    created_at__gte=cutoff_time,
                    status__in=['ACCEPTED', 'COMPLETED']
                )
            ]
            
            if not recent_referrals:
                return 15  # Default 15 minutes
            
            # Calculate average processing time
            total_time = 0
            count = 0
            
            for referral in recent_referrals:
                if referral.accepted_at and referral.created_at:
                    processing_time = (referral.accepted_at - referral.created_at).total_seconds() / 60
                    total_time += processing_time
                    count += 1
            
            if count == 0:
                return 15
            
            average_wait = int(total_time / count)
            return max(5, min(120, average_wait))  # Between 5 and 120 minutes
            
        except Exception as e:
            logger.error(f"Error calculating wait time: {str(e)}")
            return 20  # Default fallback
    
    async def _meets_criteria(
        self, 
        hospital_status: HospitalStatus, 
        specialty: Optional[str], 
        bed_type: Optional[BedType],
        max_distance_km: Optional[float],
        ambulance_location: Optional[Tuple[float, float]],
        hospital
    ) -> bool:
        """Check if hospital meets the specified criteria."""
        # Check if accepting patients
        if not hospital_status.accepting_ambulances:
            return False
        
        # Check ED status
        if hospital_status.ed_status in [EDStatus.CLOSED, EDStatus.DIVERT]:
            return False
        
        # Check bed availability
        if bed_type and bed_type in hospital_status.bed_capacities:
            if hospital_status.bed_capacities[bed_type].available_beds <= 0:
                return False
        
        # Check distance if ambulance location provided
        if max_distance_km and ambulance_location and hospital:
            distance = self._calculate_distance(
                ambulance_location, 
                (hospital.latitude, hospital.longitude)
            )
            if distance > max_distance_km:
                return False
        
        # Check specialty (would need to implement specialty matching)
        if specialty:
            # This would require a specialties table/field
            pass
        
        return True
    
    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate distance between two points using Haversine formula."""
        import math
        
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    async def _calculate_hospital_score(
        self, 
        hospital: HospitalStatus, 
        patient_condition: str, 
        ambulance_location: Tuple[float, float], 
        urgent: bool
    ) -> float:
        """Calculate a score for hospital recommendation."""
        score = 100.0  # Base score
        
        # Distance factor (closer is better)
        if hasattr(hospital, 'latitude') and hasattr(hospital, 'longitude'):
            distance = self._calculate_distance(
                ambulance_location, 
                (hospital.latitude, hospital.longitude)
            )
            # Reduce score based on distance (max 30 points deduction)
            score -= min(30, distance * 2)
        
        # Wait time factor (shorter is better)
        score -= hospital.wait_time_minutes * 0.5
        
        # ED status factor
        if hospital.ed_status == EDStatus.NORMAL:
            score += 20
        elif hospital.ed_status == EDStatus.BUSY:
            score -= 10
        elif hospital.ed_status == EDStatus.CRITICAL:
            score -= 25
        
        # Capacity factor (more available beds is better)
        if hospital.bed_capacities:
            avg_availability = sum(
                cap.availability_rate for cap in hospital.bed_capacities.values()
            ) / len(hospital.bed_capacities)
            score += avg_availability * 0.3
        
        # Urgent cases prefer closest hospital
        if urgent and hasattr(hospital, 'latitude'):
            distance = self._calculate_distance(
                ambulance_location, 
                (hospital.latitude, hospital.longitude)
            )
            if distance < 10:  # Within 10km
                score += 30
        
        return max(0, score)
    
    async def _broadcast_bed_update(self, hospital_id: str, bed_type: BedType, bed_availability):
        """Broadcast bed availability update to connected clients."""
        if self.channel_layer:
            await self.channel_layer.group_send(
                "hospital_updates",
                {
                    "type": "bed_availability_update",
                    "hospital_id": hospital_id,
                    "bed_type": bed_type.value,
                    "available_beds": bed_availability.available_beds,
                    "timestamp": timezone.now().isoformat()
                }
            )
    
    async def _broadcast_ed_status_update(self, hospital_id: str, status: EDStatus, reason: str):
        """Broadcast ED status update to connected clients."""
        if self.channel_layer:
            await self.channel_layer.group_send(
                "hospital_updates",
                {
                    "type": "ed_status_update",
                    "hospital_id": hospital_id,
                    "status": status.value,
                    "reason": reason,
                    "timestamp": timezone.now().isoformat()
                }
            )
    
    async def _check_capacity_alerts(self, hospital_id: str, bed_type: BedType, available_beds: int):
        """Check for critical capacity alerts and notify relevant parties."""
        if available_beds <= 2:  # Critical threshold
            await self.channel_layer.group_send(
                "dispatch_center",
                {
                    "type": "capacity_alert",
                    "hospital_id": hospital_id,
                    "bed_type": bed_type.value,
                    "available_beds": available_beds,
                    "alert_level": "CRITICAL",
                    "timestamp": timezone.now().isoformat()
                }
            )
    
    async def _handle_critical_status_change(self, hospital_id: str, status: EDStatus):
        """Handle critical status changes like DIVERT or CLOSED."""
        # Notify dispatch center
        await self.channel_layer.group_send(
            "dispatch_center",
            {
                "type": "hospital_status_alert",
                "hospital_id": hospital_id,
                "status": status.value,
                "alert_level": "HIGH",
                "timestamp": timezone.now().isoformat()
            }
        )
        
        # Could also trigger automatic rerouting of pending referrals
        # This would require additional implementation
    
    async def _get_or_create_ed_department(self, hospital_id: str):
        """Get or create Emergency Department record."""
        ed_dept, created = await EmergencyDepartment.objects.aget_or_create(
            hospital_id=hospital_id,
            defaults={
                'status': EDStatus.NORMAL.value,
                'last_updated': timezone.now()
            }
        )
        return ed_dept


# Global service instance
hospital_service = HospitalIntegrationService()