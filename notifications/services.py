"""
Multi-Channel Notification Service
Provides SMS, Email, and Push notification capabilities for the hospital e-referral system.
Handles emergency notifications, referral updates, and system alerts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
from enum import Enum
import json

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.cache import cache
from channels.layers import get_channel_layer

# External service imports (these would need to be installed)
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None
    TwilioException = Exception

try:
    import webpush
    from pywebpush import webpush as push_protocol
    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    webpush = None
    push_protocol = None

from .models import NotificationTemplate, NotificationLog, UserNotificationPreference
from patients.models import Patient
from referrals.models import Referral
from ambulances.models import Ambulance
from hospitals.models import Hospital

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of notifications in the system."""
    EMERGENCY_ALERT = "EMERGENCY_ALERT"
    REFERRAL_REQUEST = "REFERRAL_REQUEST"
    REFERRAL_ACCEPTED = "REFERRAL_ACCEPTED"
    REFERRAL_REJECTED = "REFERRAL_REJECTED"
    AMBULANCE_DISPATCH = "AMBULANCE_DISPATCH"
    PATIENT_ARRIVAL = "PATIENT_ARRIVAL"
    HOSPITAL_STATUS = "HOSPITAL_STATUS"
    CAPACITY_ALERT = "CAPACITY_ALERT"
    SYSTEM_MAINTENANCE = "SYSTEM_MAINTENANCE"
    SHIFT_REMINDER = "SHIFT_REMINDER"

class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    WEBHOOK = "WEBHOOK"

class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

@dataclass
class NotificationMessage:
    """Data class for notification messages."""
    type: NotificationType
    priority: NotificationPriority
    title: str
    body: str
    data: Dict[str, Any] = None
    template_name: str = None
    template_context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.template_context is None:
            self.template_context = {}

@dataclass
class NotificationRecipient:
    """Data class for notification recipients."""
    user_id: str
    name: str
    email: str = None
    phone: str = None
    push_subscriptions: List[Dict] = None
    preferred_channels: List[NotificationChannel] = None
    
    def __post_init__(self):
        if self.push_subscriptions is None:
            self.push_subscriptions = []
        if self.preferred_channels is None:
            self.preferred_channels = [NotificationChannel.EMAIL]

class NotificationService:
    """
    Comprehensive notification service supporting multiple channels
    and emergency communication protocols.
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.twilio_client = self._init_twilio()
        self.rate_limit_cache = {}
        
        # Configuration
        self.rate_limits = {
            NotificationChannel.SMS: {'count': 10, 'window': 3600},  # 10 SMS per hour
            NotificationChannel.EMAIL: {'count': 50, 'window': 3600},  # 50 emails per hour
            NotificationChannel.PUSH: {'count': 100, 'window': 3600},  # 100 push per hour
        }
        
    def _init_twilio(self) -> Optional[TwilioClient]:
        """Initialize Twilio client for SMS notifications."""
        if not TWILIO_AVAILABLE:
            logger.warning("Twilio not available - SMS notifications disabled")
            return None
            
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        
        if account_sid and auth_token:
            try:
                return TwilioClient(account_sid, auth_token)
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}")
        else:
            logger.warning("Twilio credentials not configured")
        
        return None
    
    async def send_notification(
        self,
        recipients: Union[NotificationRecipient, List[NotificationRecipient]],
        message: NotificationMessage,
        channels: Optional[List[NotificationChannel]] = None,
        bypass_preferences: bool = False
    ) -> Dict[str, bool]:
        """
        Send notification to recipients via specified channels.
        
        Args:
            recipients: Recipient(s) to send notification to
            message: Notification message details
            channels: Specific channels to use (overrides recipient preferences)
            bypass_preferences: Ignore user notification preferences for emergency alerts
            
        Returns:
            Dictionary mapping channel names to success status
        """
        if not isinstance(recipients, list):
            recipients = [recipients]
        
        results = {}
        
        for recipient in recipients:
            # Determine which channels to use
            target_channels = self._determine_channels(recipient, channels, message, bypass_preferences)
            
            # Send via each channel
            for channel in target_channels:
                try:
                    # Check rate limits
                    if not await self._check_rate_limit(recipient.user_id, channel):
                        logger.warning(f"Rate limit exceeded for {recipient.user_id} on {channel.value}")
                        results[f"{recipient.user_id}_{channel.value}"] = False
                        continue
                    
                    # Send notification
                    success = await self._send_via_channel(recipient, message, channel)
                    results[f"{recipient.user_id}_{channel.value}"] = success
                    
                    # Log notification
                    await self._log_notification(recipient, message, channel, success)
                    
                except Exception as e:
                    logger.error(f"Error sending {channel.value} notification: {str(e)}")
                    results[f"{recipient.user_id}_{channel.value}"] = False
        
        return results
    
    async def send_emergency_alert(
        self,
        alert_type: str,
        message: str,
        affected_areas: List[str] = None,
        exclude_users: List[str] = None
    ) -> bool:
        """
        Send emergency alert to all relevant users.
        
        Args:
            alert_type: Type of emergency alert
            message: Alert message
            affected_areas: Geographic areas affected
            exclude_users: User IDs to exclude from alert
            
        Returns:
            Success status
        """
        try:
            # Get all emergency responders and hospital staff
            recipients = await self._get_emergency_contacts(affected_areas, exclude_users)
            
            # Create emergency notification
            notification = NotificationMessage(
                type=NotificationType.EMERGENCY_ALERT,
                priority=NotificationPriority.EMERGENCY,
                title=f"EMERGENCY ALERT: {alert_type}",
                body=message,
                data={
                    'alert_type': alert_type,
                    'timestamp': timezone.now().isoformat(),
                    'affected_areas': affected_areas or []
                }
            )
            
            # Send via all channels, bypassing preferences
            results = await self.send_notification(
                recipients=recipients,
                message=notification,
                channels=[NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.EMAIL],
                bypass_preferences=True
            )
            
            # Also broadcast via WebSocket for real-time updates
            await self._broadcast_emergency_alert(notification)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Emergency alert sent: {success_count}/{total_count} successful")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending emergency alert: {str(e)}")
            return False
    
    async def send_referral_notification(
        self,
        referral_id: str,
        notification_type: NotificationType,
        additional_data: Dict[str, Any] = None
    ) -> bool:
        """
        Send referral-related notification to relevant parties.
        
        Args:
            referral_id: ID of the referral
            notification_type: Type of referral notification
            additional_data: Additional data to include
            
        Returns:
            Success status
        """
        try:
            # Get referral and related data
            referral = await self._get_referral_data(referral_id)
            if not referral:
                return False
            
            # Determine recipients based on notification type
            recipients = await self._get_referral_recipients(referral, notification_type)
            
            # Create notification message
            message = await self._create_referral_message(referral, notification_type, additional_data)
            
            # Send notifications
            results = await self.send_notification(recipients, message)
            
            success_count = sum(1 for success in results.values() if success)
            logger.info(f"Referral notification sent for {referral_id}: {success_count} successful")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending referral notification: {str(e)}")
            return False
    
    async def send_hospital_status_alert(
        self,
        hospital_id: str,
        status_type: str,
        message: str,
        severity: NotificationPriority = NotificationPriority.MEDIUM
    ) -> bool:
        """
        Send hospital status alert to dispatch centers and ambulance crews.
        
        Args:
            hospital_id: Hospital identifier
            status_type: Type of status change
            message: Alert message
            severity: Alert severity level
            
        Returns:
            Success status
        """
        try:
            # Get hospital data
            hospital = await self._get_hospital_data(hospital_id)
            if not hospital:
                return False
            
            # Get dispatch centers and ambulance crews in area
            recipients = await self._get_hospital_alert_recipients(hospital_id)
            
            # Create notification
            notification = NotificationMessage(
                type=NotificationType.HOSPITAL_STATUS,
                priority=severity,
                title=f"Hospital Alert: {hospital['name']}",
                body=message,
                data={
                    'hospital_id': hospital_id,
                    'hospital_name': hospital['name'],
                    'status_type': status_type,
                    'severity': severity.value
                }
            )
            
            # Send notifications
            results = await self.send_notification(recipients, notification)
            
            success_count = sum(1 for success in results.values() if success)
            logger.info(f"Hospital status alert sent for {hospital_id}: {success_count} successful")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending hospital status alert: {str(e)}")
            return False
    
    # Private helper methods
    
    def _determine_channels(
        self,
        recipient: NotificationRecipient,
        override_channels: Optional[List[NotificationChannel]],
        message: NotificationMessage,
        bypass_preferences: bool
    ) -> List[NotificationChannel]:
        """Determine which channels to use for a recipient."""
        if override_channels:
            return override_channels
        
        if bypass_preferences or message.priority == NotificationPriority.EMERGENCY:
            # For emergency notifications, use all available channels
            channels = []
            if recipient.email:
                channels.append(NotificationChannel.EMAIL)
            if recipient.phone:
                channels.append(NotificationChannel.SMS)
            if recipient.push_subscriptions:
                channels.append(NotificationChannel.PUSH)
            return channels
        
        return recipient.preferred_channels or [NotificationChannel.EMAIL]
    
    async def _check_rate_limit(self, user_id: str, channel: NotificationChannel) -> bool:
        """Check if user has exceeded rate limit for channel."""
        if channel not in self.rate_limits:
            return True
        
        limit_config = self.rate_limits[channel]
        cache_key = f"rate_limit_{user_id}_{channel.value}"
        
        # Get current count from cache
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit_config['count']:
            return False
        
        # Increment counter
        cache.set(cache_key, current_count + 1, limit_config['window'])
        return True
    
    async def _send_via_channel(
        self,
        recipient: NotificationRecipient,
        message: NotificationMessage,
        channel: NotificationChannel
    ) -> bool:
        """Send notification via specific channel."""
        try:
            if channel == NotificationChannel.EMAIL:
                return await self._send_email(recipient, message)
            elif channel == NotificationChannel.SMS:
                return await self._send_sms(recipient, message)
            elif channel == NotificationChannel.PUSH:
                return await self._send_push(recipient, message)
            elif channel == NotificationChannel.IN_APP:
                return await self._send_in_app(recipient, message)
            else:
                logger.warning(f"Unsupported notification channel: {channel}")
                return False
        except Exception as e:
            logger.error(f"Error sending via {channel.value}: {str(e)}")
            return False
    
    async def _send_email(self, recipient: NotificationRecipient, message: NotificationMessage) -> bool:
        """Send email notification."""
        if not recipient.email:
            return False
        
        try:
            # Use template if specified
            if message.template_name:
                html_content = render_to_string(
                    f'notifications/email/{message.template_name}.html',
                    message.template_context
                )
                text_content = render_to_string(
                    f'notifications/email/{message.template_name}.txt',
                    message.template_context
                )
                
                email = EmailMultiAlternatives(
                    subject=message.title,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient.email]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
            else:
                send_mail(
                    subject=message.title,
                    message=message.body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=False
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            return False
    
    async def _send_sms(self, recipient: NotificationRecipient, message: NotificationMessage) -> bool:
        """Send SMS notification."""
        if not recipient.phone or not self.twilio_client:
            return False
        
        try:
            # Format phone number
            phone = recipient.phone
            if not phone.startswith('+'):
                phone = '+1' + phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
            
            # Send SMS
            message_obj = self.twilio_client.messages.create(
                body=f"{message.title}\n\n{message.body}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone
            )
            
            logger.info(f"SMS sent to {phone}: {message_obj.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio SMS failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return False
    
    async def _send_push(self, recipient: NotificationRecipient, message: NotificationMessage) -> bool:
        """Send push notification."""
        if not recipient.push_subscriptions or not WEBPUSH_AVAILABLE:
            return False
        
        try:
            payload = {
                "title": message.title,
                "body": message.body,
                "data": message.data,
                "icon": "/static/icons/notification-icon.png",
                "badge": "/static/icons/badge-icon.png",
                "requireInteraction": message.priority in [NotificationPriority.HIGH, NotificationPriority.CRITICAL, NotificationPriority.EMERGENCY]
            }
            
            success_count = 0
            for subscription in recipient.push_subscriptions:
                try:
                    webpush.send_notification(
                        subscription_info=subscription,
                        data=json.dumps(payload),
                        vapid_private_key=settings.WEBPUSH_SETTINGS['VAPID_PRIVATE_KEY'],
                        vapid_claims={"sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"}
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send push to subscription: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Push notification failed: {str(e)}")
            return False
    
    async def _send_in_app(self, recipient: NotificationRecipient, message: NotificationMessage) -> bool:
        """Send in-app notification via WebSocket."""
        if not self.channel_layer:
            return False
        
        try:
            await self.channel_layer.group_send(
                f"user_{recipient.user_id}",
                {
                    "type": "notification_message",
                    "notification": {
                        "type": message.type.value,
                        "priority": message.priority.value,
                        "title": message.title,
                        "body": message.body,
                        "data": message.data,
                        "timestamp": timezone.now().isoformat()
                    }
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"In-app notification failed: {str(e)}")
            return False
    
    async def _log_notification(
        self,
        recipient: NotificationRecipient,
        message: NotificationMessage,
        channel: NotificationChannel,
        success: bool
    ):
        """Log notification attempt."""
        try:
            await NotificationLog.objects.acreate(
                user_id=recipient.user_id,
                notification_type=message.type.value,
                channel=channel.value,
                priority=message.priority.value,
                title=message.title,
                body=message.body[:500],  # Truncate for storage
                data=message.data,
                success=success,
                sent_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"Failed to log notification: {str(e)}")
    
    async def _broadcast_emergency_alert(self, notification: NotificationMessage):
        """Broadcast emergency alert via WebSocket."""
        if self.channel_layer:
            await self.channel_layer.group_send(
                "emergency_alerts",
                {
                    "type": "emergency_alert",
                    "alert": {
                        "type": notification.type.value,
                        "priority": notification.priority.value,
                        "title": notification.title,
                        "body": notification.body,
                        "data": notification.data,
                        "timestamp": timezone.now().isoformat()
                    }
                }
            )
    
    # Placeholder methods for data retrieval (would integrate with actual models)
    
    async def _get_emergency_contacts(self, affected_areas: List[str] = None, exclude_users: List[str] = None) -> List[NotificationRecipient]:
        """Get emergency contact recipients."""
        # This would query the user database for emergency responders
        # For now, return empty list as placeholder
        return []
    
    async def _get_referral_data(self, referral_id: str) -> Optional[Dict]:
        """Get referral data."""
        # This would fetch referral from database
        return None
    
    async def _get_referral_recipients(self, referral: Dict, notification_type: NotificationType) -> List[NotificationRecipient]:
        """Get recipients for referral notifications."""
        return []
    
    async def _create_referral_message(self, referral: Dict, notification_type: NotificationType, additional_data: Dict = None) -> NotificationMessage:
        """Create referral notification message."""
        return NotificationMessage(
            type=notification_type,
            priority=NotificationPriority.HIGH,
            title="Referral Update",
            body="A referral has been updated"
        )
    
    async def _get_hospital_data(self, hospital_id: str) -> Optional[Dict]:
        """Get hospital data."""
        return None
    
    async def _get_hospital_alert_recipients(self, hospital_id: str) -> List[NotificationRecipient]:
        """Get recipients for hospital alerts."""
        return []


# Global service instance
notification_service = NotificationService()