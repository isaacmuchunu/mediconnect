"""
Real-time GPS Tracking and Route Optimization Services
Advanced ambulance tracking with traffic integration
"""

import asyncio
import json
import logging
import math
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Ambulance, Dispatch, GPSTrackingLog, RouteOptimization, 
    TrafficCondition, GeofenceZone
)

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


@dataclass
class GPSLocation:
    """GPS location data structure"""
    latitude: float
    longitude: float
    speed: float = 0.0
    heading: float = 0.0
    accuracy: float = 10.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = timezone.now()


@dataclass
class RouteData:
    """Route information data structure"""
    distance_km: float
    duration_minutes: int
    polyline: str
    traffic_delay_minutes: int = 0
    alternative_routes: List = None
    
    def __post_init__(self):
        if self.alternative_routes is None:
            self.alternative_routes = []


class GPSTrackingService:
    """Advanced GPS tracking service with real-time capabilities"""
    
    def __init__(self):
        self.google_maps_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        self.tracking_interval = 30  # seconds
        self.geofence_check_interval = 60  # seconds
    
    async def update_ambulance_location(self, ambulance_id: str, location: GPSLocation) -> bool:
        """Update ambulance location with real-time broadcasting"""
        try:
            ambulance = await self._get_ambulance(ambulance_id)
            if not ambulance:
                logger.error(f"Ambulance {ambulance_id} not found")
                return False
            
            # Update ambulance location
            await self._update_ambulance_position(ambulance, location)
            
            # Create GPS tracking log
            await self._create_gps_log(ambulance, location)
            
            # Check geofences
            await self._check_geofences(ambulance, location)
            
            # Update active dispatch progress
            await self._update_dispatch_progress(ambulance, location)
            
            # Broadcast location update
            await self._broadcast_location_update(ambulance, location)
            
            return True
            
        except Exception as e:
            logger.error(f"GPS update failed for ambulance {ambulance_id}: {str(e)}")
            return False
    
    async def _get_ambulance(self, ambulance_id: str):
        """Get ambulance object asynchronously"""
        from django.db import sync_to_async
        try:
            return await sync_to_async(Ambulance.objects.get)(id=ambulance_id)
        except Ambulance.DoesNotExist:
            return None
    
    async def _update_ambulance_position(self, ambulance, location: GPSLocation):
        """Update ambulance position in database"""
        from django.db import sync_to_async
        
        ambulance.current_latitude = location.latitude
        ambulance.current_longitude = location.longitude
        ambulance.speed = location.speed
        ambulance.heading = location.heading
        ambulance.last_gps_update = location.timestamp
        
        await sync_to_async(ambulance.save)(
            update_fields=['current_latitude', 'current_longitude', 'speed', 'heading', 'last_gps_update']
        )
    
    async def _create_gps_log(self, ambulance, location: GPSLocation):
        """Create GPS tracking log entry"""
        from django.db import sync_to_async
        
        # Get active dispatch
        dispatch = await sync_to_async(
            lambda: ambulance.dispatches.filter(status__in=[
                'dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital'
            ]).first()
        )()
        
        await sync_to_async(GPSTrackingLog.objects.create)(
            ambulance=ambulance,
            dispatch=dispatch,
            latitude=location.latitude,
            longitude=location.longitude,
            speed=location.speed,
            heading=location.heading,
            accuracy=location.accuracy,
            timestamp=location.timestamp
        )
    
    async def _check_geofences(self, ambulance, location: GPSLocation):
        """Check if ambulance entered/exited geofences"""
        from django.db import sync_to_async
        
        geofences = await sync_to_async(list)(
            GeofenceZone.objects.filter(is_active=True)
        )
        
        for geofence in geofences:
            is_inside = self._point_in_polygon(
                location.latitude, location.longitude,
                geofence.boundary_coordinates
            )
            
            # Check previous state
            cache_key = f"geofence:{ambulance.id}:{geofence.id}"
            was_inside = cache.get(cache_key, False)
            
            if is_inside and not was_inside:
                # Entered geofence
                await self._handle_geofence_entry(ambulance, geofence)
            elif not is_inside and was_inside:
                # Exited geofence
                await self._handle_geofence_exit(ambulance, geofence)
            
            # Update cache
            cache.set(cache_key, is_inside, 300)  # 5 minutes
    
    def _point_in_polygon(self, lat: float, lng: float, polygon_coords: List) -> bool:
        """Check if point is inside polygon using ray casting algorithm"""
        x, y = lng, lat
        n = len(polygon_coords)
        inside = False
        
        p1x, p1y = polygon_coords[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon_coords[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    async def _broadcast_location_update(self, ambulance, location: GPSLocation):
        """Broadcast location update via WebSocket"""
        if not channel_layer:
            return
        
        try:
            location_data = {
                'type': 'gps_update',
                'ambulance_id': str(ambulance.id),
                'location': {
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'speed': location.speed,
                    'heading': location.heading,
                    'accuracy': location.accuracy,
                    'timestamp': location.timestamp.isoformat()
                },
                'status': ambulance.status
            }
            
            # Broadcast to ambulance-specific group
            await channel_layer.group_send(
                f"ambulance_{ambulance.id}",
                {
                    "type": "gps_location_update",
                    "message": location_data
                }
            )
            
            # Broadcast to dispatch center group
            await channel_layer.group_send(
                "dispatch_center",
                {
                    "type": "ambulance_location_update",
                    "message": location_data
                }
            )
            
        except Exception as e:
            logger.error(f"WebSocket broadcast failed: {str(e)}")


# Service instances
gps_service = GPSTrackingService()