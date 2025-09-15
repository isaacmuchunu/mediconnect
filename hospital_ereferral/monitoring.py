"""
Performance monitoring and optimization utilities for Hospital E-Referral System
"""

import time
import logging
import psutil
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from functools import wraps

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor system performance metrics"""
    
    @staticmethod
    def get_system_metrics():
        """Get current system performance metrics"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'active_connections': len(connection.queries),
            'cache_stats': cache._cache.get_stats() if hasattr(cache._cache, 'get_stats') else {},
            'timestamp': timezone.now().isoformat()
        }
    
    @staticmethod
    def get_database_metrics():
        """Get database performance metrics"""
        with connection.cursor() as cursor:
            # Get database size
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                       pg_database_size(current_database()) as db_size_bytes
            """)
            db_info = cursor.fetchone()
            
            # Get active connections
            cursor.execute("""
                SELECT count(*) as active_connections
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            active_conn = cursor.fetchone()[0]
            
            # Get slow queries (if pg_stat_statements is enabled)
            try:
                cursor.execute("""
                    SELECT query, calls, total_time, mean_time
                    FROM pg_stat_statements 
                    ORDER BY mean_time DESC 
                    LIMIT 10
                """)
                slow_queries = cursor.fetchall()
            except:
                slow_queries = []
            
            return {
                'database_size': db_info[0],
                'database_size_bytes': db_info[1],
                'active_connections': active_conn,
                'slow_queries': slow_queries,
                'total_queries': len(connection.queries)
            }
    
    @staticmethod
    def get_application_metrics():
        """Get application-specific metrics"""
        from ambulances.models import Ambulance, Dispatch
        from referrals.models import Referral
        from patients.models import Patient
        from notifications.models import Notification
        
        today = timezone.now().date()
        
        return {
            'total_patients': Patient.objects.count(),
            'total_ambulances': Ambulance.objects.count(),
            'available_ambulances': Ambulance.objects.filter(status='available').count(),
            'active_dispatches': Dispatch.objects.filter(
                status__in=['dispatched', 'en_route_pickup', 'on_scene', 'patient_loaded', 'en_route_hospital']
            ).count(),
            'pending_referrals': Referral.objects.filter(status__in=['draft', 'sent', 'viewed']).count(),
            'todays_referrals': Referral.objects.filter(created_at__date=today).count(),
            'todays_dispatches': Dispatch.objects.filter(created_at__date=today).count(),
            'unread_notifications': Notification.objects.filter(read_at__isnull=True).count(),
            'emergency_dispatches': Dispatch.objects.filter(
                priority__in=['emergency', 'critical'],
                status__in=['requested', 'assigned', 'dispatched']
            ).count()
        }


def performance_monitor(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_queries = len(connection.queries)
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            end_queries = len(connection.queries)
            
            execution_time = end_time - start_time
            query_count = end_queries - start_queries
            
            # Log performance metrics
            logger.info(f"Performance: {func.__name__} - "
                       f"Time: {execution_time:.3f}s, "
                       f"Queries: {query_count}")
            
            # Store in cache for monitoring dashboard
            cache_key = f"perf_monitor_{func.__name__}_{int(time.time())}"
            cache.set(cache_key, {
                'function': func.__name__,
                'execution_time': execution_time,
                'query_count': query_count,
                'timestamp': timezone.now().isoformat()
            }, timeout=3600)  # Store for 1 hour
            
            return result
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            logger.error(f"Performance Error: {func.__name__} - "
                        f"Time: {execution_time:.3f}s, "
                        f"Error: {str(e)}")
            raise
    
    return wrapper


class DatabaseOptimizer:
    """Database optimization utilities"""
    
    @staticmethod
    def analyze_slow_queries():
        """Analyze and report slow queries"""
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT query, calls, total_time, mean_time, rows
                    FROM pg_stat_statements 
                    WHERE mean_time > 100  -- queries taking more than 100ms on average
                    ORDER BY mean_time DESC 
                    LIMIT 20
                """)
                
                slow_queries = cursor.fetchall()
                
                recommendations = []
                for query, calls, total_time, mean_time, rows in slow_queries:
                    recommendations.append({
                        'query': query[:200] + '...' if len(query) > 200 else query,
                        'calls': calls,
                        'total_time_ms': total_time,
                        'mean_time_ms': mean_time,
                        'rows': rows,
                        'recommendation': DatabaseOptimizer._get_query_recommendation(query, mean_time)
                    })
                
                return recommendations
                
            except Exception as e:
                logger.error(f"Error analyzing slow queries: {str(e)}")
                return []
    
    @staticmethod
    def _get_query_recommendation(query, mean_time):
        """Get optimization recommendation for a query"""
        recommendations = []
        
        if mean_time > 1000:  # > 1 second
            recommendations.append("CRITICAL: Query takes over 1 second")
        elif mean_time > 500:  # > 500ms
            recommendations.append("HIGH: Query takes over 500ms")
        
        if 'SELECT *' in query.upper():
            recommendations.append("Avoid SELECT *, specify needed columns")
        
        if 'ORDER BY' in query.upper() and 'LIMIT' not in query.upper():
            recommendations.append("Consider adding LIMIT to ORDER BY queries")
        
        if query.upper().count('JOIN') > 3:
            recommendations.append("Complex query with multiple JOINs, consider optimization")
        
        if not recommendations:
            recommendations.append("Consider adding appropriate indexes")
        
        return '; '.join(recommendations)
    
    @staticmethod
    def get_index_recommendations():
        """Get index recommendations based on query patterns"""
        with connection.cursor() as cursor:
            try:
                # Get tables with missing indexes
                cursor.execute("""
                    SELECT schemaname, tablename, attname, n_distinct, correlation
                    FROM pg_stats 
                    WHERE schemaname = 'public' 
                    AND n_distinct > 100
                    ORDER BY n_distinct DESC
                """)
                
                stats = cursor.fetchall()
                
                recommendations = []
                for schema, table, column, n_distinct, correlation in stats:
                    if n_distinct > 1000:  # High cardinality columns
                        recommendations.append({
                            'table': table,
                            'column': column,
                            'type': 'btree',
                            'reason': f'High cardinality ({n_distinct} distinct values)',
                            'priority': 'high' if n_distinct > 10000 else 'medium'
                        })
                
                return recommendations
                
            except Exception as e:
                logger.error(f"Error getting index recommendations: {str(e)}")
                return []
    
    @staticmethod
    def vacuum_analyze_tables():
        """Run VACUUM ANALYZE on all tables"""
        with connection.cursor() as cursor:
            try:
                # Get all tables
                cursor.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    cursor.execute(f'VACUUM ANALYZE "{table}"')
                    logger.info(f"VACUUM ANALYZE completed for table: {table}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error running VACUUM ANALYZE: {str(e)}")
                return False


class CacheManager:
    """Cache management utilities"""
    
    @staticmethod
    def get_cache_stats():
        """Get cache statistics"""
        try:
            if hasattr(cache._cache, 'get_stats'):
                stats = cache._cache.get_stats()
                return {
                    'hits': stats.get('get_hits', 0),
                    'misses': stats.get('get_misses', 0),
                    'hit_ratio': stats.get('get_hits', 0) / max(1, stats.get('get_hits', 0) + stats.get('get_misses', 0)),
                    'current_items': stats.get('curr_items', 0),
                    'total_items': stats.get('total_items', 0)
                }
            else:
                return {'error': 'Cache statistics not available'}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def warm_cache():
        """Warm up cache with frequently accessed data"""
        from ambulances.models import Ambulance, AmbulanceType
        from doctors.models import Hospital, Specialty
        
        try:
            # Cache ambulance types
            ambulance_types = list(AmbulanceType.objects.filter(is_active=True))
            cache.set('ambulance_types', ambulance_types, timeout=3600)
            
            # Cache available ambulances
            available_ambulances = list(Ambulance.objects.filter(
                status='available', is_active=True
            ).select_related('ambulance_type', 'home_station'))
            cache.set('available_ambulances', available_ambulances, timeout=300)
            
            # Cache hospitals
            hospitals = list(Hospital.objects.filter(is_active=True))
            cache.set('hospitals', hospitals, timeout=3600)
            
            # Cache specialties
            specialties = list(Specialty.objects.filter(is_active=True))
            cache.set('specialties', specialties, timeout=3600)
            
            logger.info("Cache warmed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error warming cache: {str(e)}")
            return False
    
    @staticmethod
    def clear_expired_cache():
        """Clear expired cache entries"""
        try:
            # This depends on the cache backend
            if hasattr(cache._cache, 'clear'):
                cache._cache.clear()
                logger.info("Cache cleared successfully")
                return True
            else:
                logger.warning("Cache clear not supported by current backend")
                return False
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False


class HealthChecker:
    """System health checking utilities"""
    
    @staticmethod
    def check_database_health():
        """Check database connectivity and performance"""
        try:
            with connection.cursor() as cursor:
                start_time = time.time()
                cursor.execute("SELECT 1")
                response_time = time.time() - start_time
                
                return {
                    'status': 'healthy',
                    'response_time_ms': response_time * 1000,
                    'connection_count': len(connection.queries)
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    @staticmethod
    def check_cache_health():
        """Check cache connectivity and performance"""
        try:
            start_time = time.time()
            cache.set('health_check', 'ok', timeout=60)
            result = cache.get('health_check')
            response_time = time.time() - start_time
            
            if result == 'ok':
                return {
                    'status': 'healthy',
                    'response_time_ms': response_time * 1000
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Cache read/write failed'
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    @staticmethod
    def check_disk_space():
        """Check available disk space"""
        try:
            disk_usage = psutil.disk_usage('/')
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            if free_percent < 10:
                status = 'critical'
            elif free_percent < 20:
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'free_percent': free_percent,
                'free_gb': disk_usage.free / (1024**3),
                'total_gb': disk_usage.total / (1024**3)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    @staticmethod
    def get_overall_health():
        """Get overall system health status"""
        db_health = HealthChecker.check_database_health()
        cache_health = HealthChecker.check_cache_health()
        disk_health = HealthChecker.check_disk_space()
        
        # Determine overall status
        statuses = [db_health['status'], cache_health['status'], disk_health['status']]
        
        if 'unhealthy' in statuses:
            overall_status = 'unhealthy'
        elif 'critical' in statuses:
            overall_status = 'critical'
        elif 'warning' in statuses:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        return {
            'overall_status': overall_status,
            'database': db_health,
            'cache': cache_health,
            'disk': disk_health,
            'timestamp': timezone.now().isoformat()
        }
