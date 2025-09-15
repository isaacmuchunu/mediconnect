"""
Communication Services
Multi-channel notification delivery and message encryption services
"""

import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.template import Template, Context
from twilio.rest import Client as TwilioClient
import logging

from .models import (
    NotificationChannel, NotificationTemplate, Notification,
    NotificationPreference
)

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending multi-channel notifications"""
    
    def __init__(self):
        self.twilio_client = None
        if hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN'):
            self.twilio_client = TwilioClient(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
    
    def send_notification(self, notification_id):
        """Send a notification through appropriate channels"""
        try:
            notification = Notification.objects.get(id=notification_id)
            
            # Check if user has preferences
            if notification.recipient_user:
                preferences = getattr(notification.recipient_user, 'notification_preferences', None)
                if preferences:
                    # Check if user should receive this notification
                    if not self._should_send_notification(notification, preferences):
                        notification.status = 'cancelled'
                        notification.save()
                        return False
            
            # Determine best channel
            channel = self._select_best_channel(notification)
            if not channel:
                notification.mark_failed('No available channels')
                return False
            
            notification.channel = channel
            notification.save()
            
            # Send through selected channel
            success = self._send_through_channel(notification, channel)
            
            if success:
                notification.mark_sent()
                return True
            else:
                notification.mark_failed('Channel delivery failed')
                return False
                
        except Exception as e:
            logger.error(f"Notification sending failed: {str(e)}")
            if 'notification' in locals():
                notification.mark_failed(str(e))
            return False
    
    def _should_send_notification(self, notification, preferences):
        """Check if notification should be sent based on user preferences"""
        
        # Always send critical notifications
        if notification.priority == 'critical':
            return True
        
        # Check notification type preferences
        type_mapping = {
            'emergency_alert': 'emergency_alerts',
            'dispatch': 'dispatch_notifications',
            'status_update': 'status_updates',
            'system_alert': 'system_alerts',
        }
        
        pref_field = type_mapping.get(notification.notification_type)
        if pref_field and not getattr(preferences, pref_field, True):
            return False
        
        # Check quiet hours
        if preferences.is_in_quiet_hours() and notification.priority not in ['urgent', 'critical']:
            return False
        
        return True
    
    def _select_best_channel(self, notification):
        """Select the best available channel for notification"""
        
        # Get user preferences if available
        preferences = None
        if notification.recipient_user:
            preferences = getattr(notification.recipient_user, 'notification_preferences', None)
        
        # Priority order for different notification types
        channel_priority = {
            'critical': ['push', 'sms', 'voice', 'email'],
            'urgent': ['push', 'sms', 'email'],
            'high': ['push', 'email', 'sms'],
            'normal': ['email', 'push'],
            'low': ['email']
        }
        
        priority_channels = channel_priority.get(notification.priority, ['email'])
        
        # Filter by user preferences
        if preferences:
            available_channels = []
            for channel_type in priority_channels:
                if preferences.should_receive_notification(
                    notification.notification_type, 
                    channel_type
                ):
                    available_channels.append(channel_type)
            priority_channels = available_channels
        
        # Find first available channel
        for channel_type in priority_channels:
            channel = NotificationChannel.objects.filter(
                channel_type=channel_type,
                status='active'
            ).first()
            
            if channel and channel.is_available:
                return channel
        
        return None
    
    def _send_through_channel(self, notification, channel):
        """Send notification through specific channel"""
        
        try:
            if channel.channel_type == 'email':
                return self._send_email(notification, channel)
            elif channel.channel_type == 'sms':
                return self._send_sms(notification, channel)
            elif channel.channel_type == 'push':
                return self._send_push_notification(notification, channel)
            elif channel.channel_type == 'voice':
                return self._send_voice_call(notification, channel)
            elif channel.channel_type == 'webhook':
                return self._send_webhook(notification, channel)
            else:
                logger.warning(f"Unsupported channel type: {channel.channel_type}")
                return False
                
        except Exception as e:
            logger.error(f"Channel delivery failed: {str(e)}")
            return False
    
    def _send_email(self, notification, channel):
        """Send email notification"""
        
        try:
            # Get recipient email
            recipient_email = notification.recipient_email
            if not recipient_email and notification.recipient_user:
                recipient_email = notification.recipient_user.email
                
                # Check for preferred email
                preferences = getattr(notification.recipient_user, 'notification_preferences', None)
                if preferences and preferences.preferred_email:
                    recipient_email = preferences.preferred_email
            
            if not recipient_email:
                return False
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification.subject
            msg['From'] = settings.DEFAULT_FROM_EMAIL
            msg['To'] = recipient_email
            
            # Add text content
            text_part = MIMEText(notification.message, 'plain')
            msg.attach(text_part)
            
            # Add HTML content if available
            if notification.html_content:
                html_part = MIMEText(notification.html_content, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                if settings.EMAIL_USE_TLS:
                    server.starttls()
                if settings.EMAIL_HOST_USER:
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                
                server.send_message(msg)
            
            # Update channel statistics
            channel.total_sent += 1
            channel.total_delivered += 1
            channel.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            channel.total_sent += 1
            channel.total_failed += 1
            channel.save()
            return False
    
    def _send_sms(self, notification, channel):
        """Send SMS notification"""
        
        if not self.twilio_client:
            logger.error("Twilio client not configured")
            return False
        
        try:
            # Get recipient phone
            recipient_phone = notification.recipient_phone
            if not recipient_phone and notification.recipient_user:
                # Check for preferred phone
                preferences = getattr(notification.recipient_user, 'notification_preferences', None)
                if preferences and preferences.preferred_phone:
                    recipient_phone = preferences.preferred_phone
                else:
                    # Try to get phone from user profile
                    recipient_phone = getattr(notification.recipient_user, 'phone', None)
            
            if not recipient_phone:
                return False
            
            # Send SMS
            message = self.twilio_client.messages.create(
                body=f"{notification.subject}\n\n{notification.message}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=recipient_phone
            )
            
            notification.external_id = message.sid
            
            # Update channel statistics
            channel.total_sent += 1
            channel.total_delivered += 1
            channel.save()
            
            return True
            
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            channel.total_sent += 1
            channel.total_failed += 1
            channel.save()
            return False
    
    def _send_push_notification(self, notification, channel):
        """Send push notification"""
        
        try:
            # This would integrate with a push notification service like FCM
            # For now, we'll just log it
            logger.info(f"Push notification sent: {notification.subject}")
            
            # Update channel statistics
            channel.total_sent += 1
            channel.total_delivered += 1
            channel.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Push notification failed: {str(e)}")
            channel.total_sent += 1
            channel.total_failed += 1
            channel.save()
            return False
    
    def _send_voice_call(self, notification, channel):
        """Send voice call notification"""
        
        if not self.twilio_client:
            logger.error("Twilio client not configured")
            return False
        
        try:
            # Get recipient phone
            recipient_phone = notification.recipient_phone
            if not recipient_phone and notification.recipient_user:
                preferences = getattr(notification.recipient_user, 'notification_preferences', None)
                if preferences and preferences.preferred_phone:
                    recipient_phone = preferences.preferred_phone
                else:
                    recipient_phone = getattr(notification.recipient_user, 'phone', None)
            
            if not recipient_phone:
                return False
            
            # Create TwiML for voice message
            twiml_url = f"{settings.BASE_URL}/communications/api/voice-message/{notification.id}/"
            
            # Make voice call
            call = self.twilio_client.calls.create(
                twiml=f'<Response><Say>{notification.message}</Say></Response>',
                to=recipient_phone,
                from_=settings.TWILIO_PHONE_NUMBER
            )
            
            notification.external_id = call.sid
            
            # Update channel statistics
            channel.total_sent += 1
            channel.total_delivered += 1
            channel.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Voice call failed: {str(e)}")
            channel.total_sent += 1
            channel.total_failed += 1
            channel.save()
            return False
    
    def _send_webhook(self, notification, channel):
        """Send webhook notification"""
        
        try:
            webhook_url = channel.api_endpoint
            if not webhook_url:
                return False
            
            payload = {
                'notification_id': str(notification.id),
                'subject': notification.subject,
                'message': notification.message,
                'priority': notification.priority,
                'notification_type': notification.notification_type,
                'recipient': {
                    'user_id': str(notification.recipient_user.id) if notification.recipient_user else None,
                    'email': notification.recipient_email,
                    'phone': notification.recipient_phone,
                },
                'context': notification.context_data,
                'timestamp': notification.created_at.isoformat(),
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'MediConnect-Notifications/1.0'
            }
            
            if channel.api_key:
                headers['Authorization'] = f'Bearer {channel.api_key}'
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # Update channel statistics
                channel.total_sent += 1
                channel.total_delivered += 1
                channel.save()
                return True
            else:
                logger.error(f"Webhook failed with status {response.status_code}")
                channel.total_sent += 1
                channel.total_failed += 1
                channel.save()
                return False
                
        except Exception as e:
            logger.error(f"Webhook sending failed: {str(e)}")
            channel.total_sent += 1
            channel.total_failed += 1
            channel.save()
            return False
    
    def send_bulk_notification(self, user_ids, template_name, context_data, priority='normal'):
        """Send bulk notifications using a template"""
        
        try:
            template = NotificationTemplate.objects.get(name=template_name, is_active=True)
            users = User.objects.filter(id__in=user_ids)
            
            notifications_created = 0
            
            for user in users:
                # Render template with context
                user_context = {**context_data, 'user': user}
                subject = template.render_subject(user_context)
                message = template.render_body(user_context)
                html_content = template.render_html(user_context)
                
                # Create notification
                notification = Notification.objects.create(
                    recipient_user=user,
                    subject=subject,
                    message=message,
                    html_content=html_content,
                    notification_type=template.template_type,
                    priority=priority,
                    template=template,
                    context_data=user_context
                )
                
                # Send immediately for critical notifications
                if priority == 'critical':
                    self.send_notification(notification.id)
                
                notifications_created += 1
            
            return notifications_created
            
        except Exception as e:
            logger.error(f"Bulk notification failed: {str(e)}")
            return 0


class MessageEncryptionService:
    """Service for encrypting/decrypting secure messages"""
    
    @staticmethod
    def encrypt_message(message_content):
        """Encrypt message content (placeholder implementation)"""
        # In a real implementation, this would use proper encryption
        # For now, we'll just return the message as-is
        return message_content
    
    @staticmethod
    def decrypt_message(encrypted_content):
        """Decrypt message content (placeholder implementation)"""
        # In a real implementation, this would decrypt the content
        # For now, we'll just return the content as-is
        return encrypted_content
    
    @staticmethod
    def generate_encryption_key():
        """Generate new encryption key"""
        import secrets
        return secrets.token_hex(32)
