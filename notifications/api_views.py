"""
Notification System API Views
REST API endpoints for managing notifications, templates, and preferences.
"""

import logging
from typing import Dict, Any

from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import notification_service, NotificationType, NotificationPriority, NotificationChannel
from .models import Notification, NotificationPreference, NotificationTemplate
from .serializers import (
    NotificationSerializer, NotificationPreferenceSerializer,
    NotificationTemplateSerializer, SendNotificationSerializer
)
from core.permissions import IsDispatcherOrAdmin, IsHospitalStaff

logger = logging.getLogger(__name__)

class NotificationAPIView(APIView):
    """
    API endpoint for managing user notifications.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get user's notifications.
        
        Query parameters:
        - unread_only: true/false
        - priority: low/medium/high/critical/emergency
        - type: notification type filter
        - limit: number of notifications to return
        """
        try:
            queryset = Notification.objects.filter(
                user=request.user,
                is_active=True
            ).order_by('-created_at')
            
            # Apply filters
            unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
            if unread_only:
                queryset = queryset.filter(read_at__isnull=True)
            
            priority = request.query_params.get('priority')
            if priority:
                queryset = queryset.filter(priority=priority.lower())
            
            notification_type = request.query_params.get('type')
            if notification_type:
                queryset = queryset.filter(
                    template__notification_type=notification_type
                )
            
            # Limit results
            limit = request.query_params.get('limit')
            if limit:
                try:
                    limit = int(limit)
                    queryset = queryset[:limit]
                except ValueError:
                    pass
            
            serializer = NotificationSerializer(queryset, many=True)
            
            # Add summary statistics
            unread_count = Notification.objects.filter(
                user=request.user,
                is_active=True,
                read_at__isnull=True
            ).count()
            
            return Response({
                "notifications": serializer.data,
                "unread_count": unread_count,
                "total_count": len(serializer.data)
            })
            
        except Exception as e:
            logger.error(f"Error retrieving notifications: {str(e)}")
            return Response(
                {"error": "Failed to retrieve notifications"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """
        Send a new notification.
        """
        try:
            serializer = SendNotificationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Invalid data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract data
            data = serializer.validated_data
            recipient_ids = data.get('recipients', [])
            message_data = data.get('message', {})
            channels = data.get('channels', ['EMAIL'])
            
            # Send notifications
            results = {}
            for recipient_id in recipient_ids:
                try:
                    # This would integrate with the notification service
                    # For now, create a basic notification record
                    notification = Notification.objects.create(
                        user_id=recipient_id,
                        title=message_data.get('title', 'Notification'),
                        message=message_data.get('body', ''),
                        priority=message_data.get('priority', 'medium'),
                        metadata=message_data.get('data', {})
                    )
                    results[recipient_id] = True
                    
                except Exception as e:
                    logger.error(f"Failed to send notification to {recipient_id}: {str(e)}")
                    results[recipient_id] = False
            
            success_count = sum(1 for success in results.values() if success)
            
            return Response({
                "message": "Notifications sent",
                "results": results,
                "success_count": success_count,
                "total_count": len(recipient_ids)
            })
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
            return Response(
                {"error": "Failed to send notifications"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NotificationDetailAPIView(APIView):
    """
    API endpoint for managing individual notifications.
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, notification_id):
        """
        Update notification (e.g., mark as read).
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            
            # Mark as read
            if request.data.get('read') is True:
                notification.read_at = timezone.now()
                notification.status = 'read'
                notification.save()
            
            serializer = NotificationSerializer(notification)
            return Response(serializer.data)
            
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating notification: {str(e)}")
            return Response(
                {"error": "Failed to update notification"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, notification_id):
        """
        Delete/deactivate notification.
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            
            notification.is_active = False
            notification.save()
            
            return Response({"message": "Notification deleted"})
            
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return Response(
                {"error": "Failed to delete notification"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NotificationPreferenceAPIView(APIView):
    """
    API endpoint for managing user notification preferences.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get user's notification preferences.
        """
        try:
            preference, created = NotificationPreference.objects.get_or_create(
                user=request.user
            )
            
            serializer = NotificationPreferenceSerializer(preference)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving notification preferences: {str(e)}")
            return Response(
                {"error": "Failed to retrieve preferences"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request):
        """
        Update user's notification preferences.
        """
        try:
            preference, created = NotificationPreference.objects.get_or_create(
                user=request.user
            )
            
            serializer = NotificationPreferenceSerializer(
                preference,
                data=request.data,
                partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            else:
                return Response(
                    {"error": "Invalid data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error updating notification preferences: {str(e)}")
            return Response(
                {"error": "Failed to update preferences"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EmergencyAlertAPIView(APIView):
    """
    API endpoint for sending emergency alerts.
    """
    permission_classes = [IsAuthenticated, IsDispatcherOrAdmin]
    
    async def post(self, request):
        """
        Send emergency alert to all relevant users.
        
        Request body:
        {
            "alert_type": "MASS_CASUALTY",
            "message": "Multiple vehicle accident on I-95",
            "affected_areas": ["Zone_A", "Zone_B"],
            "priority": "EMERGENCY"
        }
        """
        try:
            alert_type = request.data.get('alert_type')
            message = request.data.get('message')
            affected_areas = request.data.get('affected_areas', [])
            priority = request.data.get('priority', 'HIGH')
            
            if not alert_type or not message:
                return Response(
                    {"error": "alert_type and message are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Send emergency alert
            success = await notification_service.send_emergency_alert(
                alert_type=alert_type,
                message=message,
                affected_areas=affected_areas
            )
            
            if success:
                return Response({
                    "message": "Emergency alert sent successfully",
                    "alert_type": alert_type,
                    "affected_areas": affected_areas
                })
            else:
                return Response(
                    {"error": "Failed to send emergency alert"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error sending emergency alert: {str(e)}")
            return Response(
                {"error": "Failed to send emergency alert"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NotificationTemplateAPIView(APIView):
    """
    API endpoint for managing notification templates.
    """
    permission_classes = [IsAuthenticated, IsDispatcherOrAdmin]
    
    def get(self, request):
        """
        Get available notification templates.
        """
        try:
            templates = NotificationTemplate.objects.filter(is_active=True)
            
            template_type = request.query_params.get('type')
            if template_type:
                templates = templates.filter(notification_type=template_type)
            
            serializer = NotificationTemplateSerializer(templates, many=True)
            return Response({
                "templates": serializer.data,
                "count": len(serializer.data)
            })
            
        except Exception as e:
            logger.error(f"Error retrieving templates: {str(e)}")
            return Response(
                {"error": "Failed to retrieve templates"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """
        Create a new notification template.
        """
        try:
            serializer = NotificationTemplateSerializer(data=request.data)
            
            if serializer.is_valid():
                template = serializer.save()
                return Response(
                    NotificationTemplateSerializer(template).data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {"error": "Invalid data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            return Response(
                {"error": "Failed to create template"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BulkNotificationAPIView(APIView):
    """
    API endpoint for sending bulk notifications.
    """
    permission_classes = [IsAuthenticated, IsDispatcherOrAdmin]
    
    async def post(self, request):
        """
        Send bulk notifications to multiple recipients.
        
        Request body:
        {
            "template_id": "template_uuid",
            "recipients": ["user1", "user2", "user3"],
            "message_data": {
                "title": "System Maintenance",
                "body": "Scheduled maintenance tonight",
                "priority": "MEDIUM"
            },
            "channels": ["EMAIL", "SMS"],
            "schedule_time": "2024-01-01T20:00:00Z"
        }
        """
        try:
            template_id = request.data.get('template_id')
            recipients = request.data.get('recipients', [])
            message_data = request.data.get('message_data', {})
            channels = request.data.get('channels', ['EMAIL'])
            schedule_time = request.data.get('schedule_time')
            
            if not recipients:
                return Response(
                    {"error": "Recipients list cannot be empty"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process bulk notification
            # This would integrate with the notification service
            # For now, create basic notification records
            
            created_notifications = []
            failed_recipients = []
            
            for recipient_id in recipients:
                try:
                    notification = Notification.objects.create(
                        user_id=recipient_id,
                        title=message_data.get('title', 'Bulk Notification'),
                        message=message_data.get('body', ''),
                        priority=message_data.get('priority', 'medium'),
                        template_id=template_id if template_id else None,
                        metadata=message_data.get('data', {}),
                        scheduled_for=schedule_time
                    )
                    created_notifications.append(notification.id)
                    
                except Exception as e:
                    logger.error(f"Failed to create notification for {recipient_id}: {str(e)}")
                    failed_recipients.append(recipient_id)
            
            return Response({
                "message": "Bulk notifications processed",
                "successful_count": len(created_notifications),
                "failed_count": len(failed_recipients),
                "failed_recipients": failed_recipients,
                "notification_ids": created_notifications
            })
            
        except Exception as e:
            logger.error(f"Error processing bulk notifications: {str(e)}")
            return Response(
                {"error": "Failed to process bulk notifications"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Legacy function-based views for backward compatibility

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsDispatcherOrAdmin])
async def send_referral_notification_view(request):
    """
    Send referral-related notification (legacy endpoint).
    """
    try:
        referral_id = request.data.get('referral_id')
        notification_type = request.data.get('type', 'REFERRAL_REQUEST')
        additional_data = request.data.get('data', {})
        
        if not referral_id:
            return Response(
                {"error": "referral_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert string to enum
        try:
            notif_type = NotificationType(notification_type.upper())
        except ValueError:
            return Response(
                {"error": f"Invalid notification type: {notification_type}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = await notification_service.send_referral_notification(
            referral_id=referral_id,
            notification_type=notif_type,
            additional_data=additional_data
        )
        
        if success:
            return Response({"message": "Referral notification sent successfully"})
        else:
            return Response(
                {"error": "Failed to send referral notification"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Error in send_referral_notification_view: {str(e)}")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notifications_read_view(request):
    """
    Mark multiple notifications as read (legacy endpoint).
    """
    try:
        notification_ids = request.data.get('notification_ids', [])
        mark_all = request.data.get('mark_all', False)
        
        if mark_all:
            # Mark all user's notifications as read
            updated_count = Notification.objects.filter(
                user=request.user,
                read_at__isnull=True
            ).update(
                read_at=timezone.now(),
                status='read'
            )
        else:
            # Mark specific notifications as read
            updated_count = Notification.objects.filter(
                id__in=notification_ids,
                user=request.user,
                read_at__isnull=True
            ).update(
                read_at=timezone.now(),
                status='read'
            )
        
        return Response({
            "message": "Notifications marked as read",
            "updated_count": updated_count
        })
        
    except Exception as e:
        logger.error(f"Error marking notifications as read: {str(e)}")
        return Response(
            {"error": "Failed to mark notifications as read"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_stats_view(request):
    """
    Get notification statistics for the user (legacy endpoint).
    """
    try:
        user_notifications = Notification.objects.filter(user=request.user)
        
        stats = {
            "total_notifications": user_notifications.count(),
            "unread_count": user_notifications.filter(read_at__isnull=True).count(),
            "priority_breakdown": {
                "low": user_notifications.filter(priority='low').count(),
                "medium": user_notifications.filter(priority='medium').count(),
                "high": user_notifications.filter(priority='high').count(),
                "urgent": user_notifications.filter(priority='urgent').count(),
            },
            "recent_notifications": user_notifications.order_by('-created_at')[:5].values(
                'id', 'title', 'priority', 'created_at', 'read_at'
            )
        }
        
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {str(e)}")
        return Response(
            {"error": "Failed to get notification statistics"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )