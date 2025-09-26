"""
Security Middleware for Hospital E-Referral System
HIPAA-compliant security enhancements and audit logging
"""

import logging
import json
import time
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import ipaddress

logger = logging.getLogger('hospital_ereferral.security')


class SecurityAuditMiddleware(MiddlewareMixin):
    """Comprehensive security audit logging middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Log all requests for security audit"""
        request.start_time = time.time()
        
        # Log security-sensitive requests
        if self.is_sensitive_request(request):
            self.log_security_event(request, 'REQUEST_INITIATED')
        
        # Check for suspicious activity
        if self.detect_suspicious_activity(request):
            self.log_security_event(request, 'SUSPICIOUS_ACTIVITY')
            return HttpResponseForbidden("Access denied due to suspicious activity")
        
        return None
    
    def process_response(self, request, response):
        """Log response and calculate request duration"""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow requests
            if duration > 5.0:  # 5 seconds
                self.log_security_event(request, 'SLOW_REQUEST', {
                    'duration': duration,
                    'status_code': response.status_code
                })
            
            # Log failed authentication attempts
            if response.status_code == 401:
                self.log_security_event(request, 'AUTHENTICATION_FAILED')
            
            # Log access to sensitive endpoints
            if self.is_sensitive_request(request) and response.status_code == 200:
                self.log_security_event(request, 'SENSITIVE_ACCESS_GRANTED')
        
        return response
    
    def is_sensitive_request(self, request):
        """Check if request is accessing sensitive endpoints"""
        sensitive_paths = [
            '/patients/',
            '/api/patients/',
            '/ambulances/emergency/',
            '/admin/',
            '/reports/',
            '/analytics/'
        ]
        
        return any(request.path.startswith(path) for path in sensitive_paths)
    
    def detect_suspicious_activity(self, request):
        """Detect potentially suspicious activity"""
        client_ip = self.get_client_ip(request)
        
        # Rate limiting check
        cache_key = f"requests:{client_ip}"
        requests_count = cache.get(cache_key, 0)
        
        if requests_count > 100:  # More than 100 requests per minute
            return True
        
        cache.set(cache_key, requests_count + 1, 60)  # 1 minute timeout
        
        # Check for SQL injection patterns
        suspicious_patterns = ['union select', 'drop table', '1=1', 'xp_cmdshell']
        query_string = request.GET.urlencode().lower()
        
        for pattern in suspicious_patterns:
            if pattern in query_string:
                return True
        
        return False
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def log_security_event(self, request, event_type, extra_data=None):
        """Log security events for audit compliance"""
        user_id = None
        username = 'anonymous'
        
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            user_id = request.user.id
            username = request.user.username
        
        event_data = {
            'event_type': event_type,
            'timestamp': timezone.now().isoformat(),
            'user_id': user_id,
            'username': username,
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
            'session_key': request.session.session_key if hasattr(request, 'session') else None
        }
        
        if extra_data:
            event_data.update(extra_data)
        
        logger.info(f"SECURITY_EVENT: {json.dumps(event_data)}")


class HIPAAComplianceMiddleware(MiddlewareMixin):
    """HIPAA compliance middleware for healthcare data protection"""
    
    def process_request(self, request):
        """Ensure HIPAA compliance for healthcare data access"""
        if not getattr(settings, 'HIPAA_COMPLIANCE_MODE', False):
            return None
        
        # Check if accessing patient data
        if self.is_patient_data_request(request):
            # Ensure user is authenticated
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required for patient data access")
            
            # Log patient data access
            self.log_patient_data_access(request)
        
        return None
    
    def is_patient_data_request(self, request):
        """Check if request is accessing patient data"""
        patient_data_paths = [
            '/patients/',
            '/api/patients/',
            '/medical-history/',
            '/referrals/',
            '/ambulances/emergency/'
        ]
        
        return any(request.path.startswith(path) for path in patient_data_paths)
    
    def log_patient_data_access(self, request):
        """Log patient data access for HIPAA compliance"""
        access_data = {
            'event_type': 'PATIENT_DATA_ACCESS',
            'timestamp': timezone.now().isoformat(),
            'user_id': request.user.id,
            'username': request.user.username,
            'user_role': getattr(request.user, 'role', 'unknown'),
            'ip_address': self.get_client_ip(request),
            'method': request.method,
            'path': request.path,
            'session_id': request.session.session_key
        }
        
        logger.info(f"HIPAA_ACCESS: {json.dumps(access_data)}")
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class APISecurityMiddleware(MiddlewareMixin):
    """Enhanced API security middleware"""
    
    def process_request(self, request):
        """Enhanced API security checks"""
        if not request.path.startswith('/api/'):
            return None
        
        # Check API rate limiting
        if self.is_rate_limited(request):
            return HttpResponseForbidden("API rate limit exceeded")
        
        # Validate API token format
        if 'HTTP_AUTHORIZATION' in request.META:
            auth_header = request.META['HTTP_AUTHORIZATION']
            if not self.is_valid_token_format(auth_header):
                return HttpResponseForbidden("Invalid API token format")
        
        return None
    
    def is_rate_limited(self, request):
        """Check if request exceeds rate limits"""
        # Implementation would check against Redis or cache
        return False  # Placeholder
    
    def is_valid_token_format(self, auth_header):
        """Validate API token format"""
        if not auth_header.startswith('Token '):
            return False
        
        token = auth_header.replace('Token ', '')
        if len(token) < 40:  # Django tokens are 40 characters
            return False
        
        return True