"""
WebSocket Consumers for Real-time Ambulance Tracking
Handles GPS updates, dispatch notifications, and emergency communications
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from datetime import datetime

from .models import Ambulance, Dispatch, EmergencyCall
from .services import gps_service, GPSLocation

logger = logging.getLogger(__name__)


class DispatchCenterConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for dispatch center real-time updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Check authentication
        if self.scope["user"] == AnonymousUser():
            await self.close()
            return
        
        # Check if user is dispatcher or admin
        if not await self.is_dispatcher():
            await self.close()
            return
        
        # Join dispatch center group
        await self.channel_layer.group_add(
            "dispatch_center",
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial data
        await self.send_initial_data()
        
        logger.info(f"Dispatcher {self.scope['user'].username} connected to dispatch center")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            "dispatch_center",
            self.channel_name
        )
        
        logger.info(f"Dispatcher {self.scope['user'].username} disconnected from dispatch center")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif message_type == 'request_ambulance_status':
                await self.send_ambulance_status()
            
            elif message_type == 'request_active_calls':
                await self.send_active_calls()
            
            elif message_type == 'update_dispatch_status':
                await self.handle_dispatch_status_update(data)
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in dispatch center WebSocket")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
    
    # Message handlers
    async def ambulance_location_update(self, event):
        """Handle ambulance location updates"""
        await self.send(text_data=json.dumps({
            'type': 'ambulance_location_update',
            'data': event['message']
        }))
    
    async def emergency_call_created(self, event):
        """Handle new emergency call notifications"""
        await self.send(text_data=json.dumps({
            'type': 'emergency_call_created',
            'data': event['message']
        }))
    
    async def dispatch_status_changed(self, event):
        """Handle dispatch status changes"""
        await self.send(text_data=json.dumps({
            'type': 'dispatch_status_changed',
            'data': event['message']
        }))
    
    async def hospital_capacity_update(self, event):
        """Handle hospital capacity updates"""
        await self.send(text_data=json.dumps({
            'type': 'hospital_capacity_update',
            'data': event['message']
        }))
    
    # Helper methods
    @database_sync_to_async
    def is_dispatcher(self):
        """Check if user is a dispatcher"""
        user = self.scope["user"]
        return (user.role in ['DISPATCHER', 'ADMIN'] or 
                user.is_superuser or
                user.groups.filter(name='Dispatchers').exists())
    
    async def send_initial_data(self):
        """Send initial data when dispatcher connects"""
        try:
            # Send ambulance status
            await self.send_ambulance_status()
            
            # Send active calls
            await self.send_active_calls()
            
            # Send active dispatches
            await self.send_active_dispatches()
            
        except Exception as e:
            logger.error(f"Error sending initial data: {str(e)}")
    
    async def send_ambulance_status(self):
        """Send current ambulance status"""
        ambulances = await self.get_ambulance_data()
        await self.send(text_data=json.dumps({
            'type': 'ambulance_status',
            'data': ambulances
        }))
    
    async def send_active_calls(self):
        """Send active emergency calls"""
        calls = await self.get_emergency_calls()
        await self.send(text_data=json.dumps({
            'type': 'active_calls',
            'data': calls
        }))
    
    async def send_active_dispatches(self):
        """Send active dispatches"""
        dispatches = await self.get_active_dispatches()
        await self.send(text_data=json.dumps({
            'type': 'active_dispatches',
            'data': dispatches
        }))
    
    @database_sync_to_async
    def get_ambulance_data(self):
        """Get ambulance data for dispatch center"""
        ambulances = []
        for ambulance in Ambulance.objects.filter(is_active=True):
            ambulances.append({
                'id': str(ambulance.id),
                'license_plate': ambulance.license_plate,
                'status': ambulance.status,
                'location': {
                    'latitude': ambulance.current_latitude,
                    'longitude': ambulance.current_longitude
                } if ambulance.current_latitude and ambulance.current_longitude else None,
                'last_update': ambulance.last_gps_update.isoformat() if ambulance.last_gps_update else None,
                'crew_count': ambulance.assigned_crew.count(),
                'ambulance_type': ambulance.ambulance_type.name
            })
        return ambulances
    
    @database_sync_to_async
    def get_emergency_calls(self):
        """Get active emergency calls"""
        calls = []
        for call in EmergencyCall.objects.filter(status__in=['received', 'processing']).order_by('-received_at'):
            calls.append({
                'id': str(call.id),
                'call_number': call.call_number,
                'call_type': call.call_type,
                'priority': call.priority,
                'incident_address': call.incident_address,
                'patient_name': call.patient_name,
                'caller_name': call.caller_name,
                'received_at': call.received_at.isoformat(),
                'elapsed_time': (timezone.now() - call.received_at).total_seconds() / 60
            })
        return calls
    
    @database_sync_to_async
    def get_active_dispatches(self):
        """Get active dispatches"""
        dispatches = []
        for dispatch in Dispatch.objects.filter(status__in=[
            'dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital'
        ]).select_related('ambulance', 'referral'):
            dispatches.append({
                'id': str(dispatch.id),
                'dispatch_number': dispatch.dispatch_number,
                'ambulance': {
                    'id': str(dispatch.ambulance.id),
                    'license_plate': dispatch.ambulance.license_plate
                },
                'status': dispatch.status,
                'priority': dispatch.priority,
                'pickup_address': dispatch.pickup_address,
                'destination_address': dispatch.destination_address,
                'created_at': dispatch.created_at.isoformat(),
                'estimated_pickup_time': dispatch.estimated_pickup_time.isoformat() if dispatch.estimated_pickup_time else None,
                'estimated_arrival_time': dispatch.estimated_arrival_time.isoformat() if dispatch.estimated_arrival_time else None
            })
        return dispatches
    
    async def handle_dispatch_status_update(self, data):
        """Handle dispatch status update from dispatcher"""
        try:
            dispatch_id = data.get('dispatch_id')
            new_status = data.get('status')
            
            if dispatch_id and new_status:
                await self.update_dispatch_status(dispatch_id, new_status)
                
        except Exception as e:
            logger.error(f"Error updating dispatch status: {str(e)}")
    
    @database_sync_to_async
    def update_dispatch_status(self, dispatch_id, new_status):
        """Update dispatch status in database"""
        try:
            dispatch = Dispatch.objects.get(id=dispatch_id)
            old_status = dispatch.status
            dispatch.update_status(new_status, self.scope["user"])
            
            # Broadcast status change
            return {
                'dispatch_id': str(dispatch.id),
                'old_status': old_status,
                'new_status': new_status,
                'updated_by': self.scope["user"].username,
                'timestamp': timezone.now().isoformat()
            }
        except Dispatch.DoesNotExist:
            logger.error(f"Dispatch {dispatch_id} not found")
            return None


class AmbulanceConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for ambulance crews"""
    
    async def connect(self):
        """Handle WebSocket connection for ambulance crew"""
        # Check authentication
        if self.scope["user"] == AnonymousUser():
            await self.close()
            return
        
        # Get ambulance ID from URL
        self.ambulance_id = self.scope['url_route']['kwargs']['ambulance_id']
        
        # Check if user is assigned to this ambulance
        if not await self.is_ambulance_crew():
            await self.close()
            return
        
        # Join ambulance-specific group
        await self.channel_layer.group_add(
            f"ambulance_{self.ambulance_id}",
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial dispatch data
        await self.send_current_dispatch()
        
        logger.info(f"Ambulance crew {self.scope['user'].username} connected to ambulance {self.ambulance_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            f"ambulance_{self.ambulance_id}",
            self.channel_name
        )
        
        logger.info(f"Ambulance crew {self.scope['user'].username} disconnected from ambulance {self.ambulance_id}")
    
    async def receive(self, text_data):
        """Handle incoming messages from ambulance crew"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'gps_update':
                await self.handle_gps_update(data)
            
            elif message_type == 'status_update':
                await self.handle_status_update(data)
            
            elif message_type == 'request_current_dispatch':
                await self.send_current_dispatch()
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in ambulance WebSocket")
        except Exception as e:
            logger.error(f"Error handling ambulance WebSocket message: {str(e)}")
    
    # Message handlers
    async def gps_location_update(self, event):
        """Send GPS location update to ambulance crew"""
        await self.send(text_data=json.dumps({
            'type': 'gps_location_update',
            'data': event['message']
        }))
    
    async def dispatch_assigned(self, event):
        """Handle new dispatch assignment"""
        await self.send(text_data=json.dumps({
            'type': 'dispatch_assigned',
            'data': event['message']
        }))
    
    async def dispatch_updated(self, event):
        """Handle dispatch updates"""
        await self.send(text_data=json.dumps({
            'type': 'dispatch_updated',
            'data': event['message']
        }))
    
    # Helper methods
    @database_sync_to_async
    def is_ambulance_crew(self):
        """Check if user is assigned to this ambulance"""
        user = self.scope["user"]
        try:
            ambulance = Ambulance.objects.get(id=self.ambulance_id)
            return (user in ambulance.assigned_crew.all() or 
                    user.role in ['ADMIN', 'DISPATCHER'] or
                    user.is_superuser)
        except Ambulance.DoesNotExist:
            return False
    
    async def handle_gps_update(self, data):
        """Handle GPS location update from ambulance"""
        try:
            location_data = data.get('location', {})
            
            location = GPSLocation(
                latitude=float(location_data.get('latitude')),
                longitude=float(location_data.get('longitude')),
                speed=float(location_data.get('speed', 0)),
                heading=float(location_data.get('heading', 0)),
                accuracy=float(location_data.get('accuracy', 10))
            )
            
            # Update location via GPS service
            success = await gps_service.update_ambulance_location(self.ambulance_id, location)
            
            if success:
                await self.send(text_data=json.dumps({
                    'type': 'gps_update_confirmed',
                    'timestamp': timezone.now().isoformat()
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'gps_update_failed',
                    'error': 'Failed to update GPS location'
                }))
                
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid GPS data: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'gps_update_failed',
                'error': 'Invalid GPS data format'
            }))
    
    async def handle_status_update(self, data):
        """Handle ambulance status update"""
        try:
            new_status = data.get('status')
            if new_status:
                await self.update_ambulance_status(new_status)
                
        except Exception as e:
            logger.error(f"Error updating ambulance status: {str(e)}")
    
    @database_sync_to_async
    def update_ambulance_status(self, new_status):
        """Update ambulance status in database"""
        try:
            ambulance = Ambulance.objects.get(id=self.ambulance_id)
            old_status = ambulance.status
            ambulance.status = new_status
            ambulance.save(update_fields=['status'])
            
            return {
                'ambulance_id': str(ambulance.id),
                'old_status': old_status,
                'new_status': new_status,
                'updated_by': self.scope["user"].username,
                'timestamp': timezone.now().isoformat()
            }
        except Ambulance.DoesNotExist:
            logger.error(f"Ambulance {self.ambulance_id} not found")
            return None
    
    async def send_current_dispatch(self):
        """Send current dispatch information to ambulance crew"""
        dispatch_data = await self.get_current_dispatch()
        await self.send(text_data=json.dumps({
            'type': 'current_dispatch',
            'data': dispatch_data
        }))
    
    @database_sync_to_async
    def get_current_dispatch(self):
        """Get current dispatch for this ambulance"""
        try:
            ambulance = Ambulance.objects.get(id=self.ambulance_id)
            dispatch = ambulance.dispatches.filter(status__in=[
                'dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital'
            ]).first()
            
            if dispatch:
                return {
                    'id': str(dispatch.id),
                    'dispatch_number': dispatch.dispatch_number,
                    'status': dispatch.status,
                    'priority': dispatch.priority,
                    'pickup_address': dispatch.pickup_address,
                    'destination_address': dispatch.destination_address,
                    'patient_condition': dispatch.patient_condition,
                    'special_instructions': dispatch.special_instructions,
                    'estimated_pickup_time': dispatch.estimated_pickup_time.isoformat() if dispatch.estimated_pickup_time else None,
                    'estimated_arrival_time': dispatch.estimated_arrival_time.isoformat() if dispatch.estimated_arrival_time else None
                }
            return None
        except Ambulance.DoesNotExist:
            return None