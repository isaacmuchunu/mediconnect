"""
Management command for optimizing system performance
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from hospital_ereferral.monitoring import (
    PerformanceMonitor, DatabaseOptimizer, CacheManager, HealthChecker
)
import json


class Command(BaseCommand):
    help = 'Optimize system performance and generate reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['analyze', 'optimize', 'monitor', 'health', 'cache'],
            default='analyze',
            help='Action to perform'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output file for reports (JSON format)'
        )
        
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run VACUUM ANALYZE on database tables'
        )
        
        parser.add_argument(
            '--warm-cache',
            action='store_true',
            help='Warm up application cache'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        output_file = options.get('output')
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting performance optimization: {action}')
        )
        
        try:
            if action == 'analyze':
                result = self.analyze_performance()
            elif action == 'optimize':
                result = self.optimize_system(options)
            elif action == 'monitor':
                result = self.monitor_system()
            elif action == 'health':
                result = self.check_health()
            elif action == 'cache':
                result = self.manage_cache(options)
            else:
                raise CommandError(f'Unknown action: {action}')
            
            # Output results
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                self.stdout.write(
                    self.style.SUCCESS(f'Results saved to {output_file}')
                )
            else:
                self.stdout.write(json.dumps(result, indent=2, default=str))
            
        except Exception as e:
            raise CommandError(f'Error during {action}: {str(e)}')
    
    def analyze_performance(self):
        """Analyze current system performance"""
        self.stdout.write('Analyzing system performance...')
        
        # Get system metrics
        system_metrics = PerformanceMonitor.get_system_metrics()
        db_metrics = PerformanceMonitor.get_database_metrics()
        app_metrics = PerformanceMonitor.get_application_metrics()
        
        # Analyze slow queries
        slow_queries = DatabaseOptimizer.analyze_slow_queries()
        
        # Get index recommendations
        index_recommendations = DatabaseOptimizer.get_index_recommendations()
        
        # Get cache stats
        cache_stats = CacheManager.get_cache_stats()
        
        result = {
            'timestamp': timezone.now().isoformat(),
            'system_metrics': system_metrics,
            'database_metrics': db_metrics,
            'application_metrics': app_metrics,
            'slow_queries': slow_queries,
            'index_recommendations': index_recommendations,
            'cache_stats': cache_stats
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(result)
        result['recommendations'] = recommendations
        
        self.stdout.write(
            self.style.SUCCESS('Performance analysis completed')
        )
        
        return result
    
    def optimize_system(self, options):
        """Optimize system performance"""
        self.stdout.write('Optimizing system performance...')
        
        results = {
            'timestamp': timezone.now().isoformat(),
            'optimizations': []
        }
        
        # Run VACUUM ANALYZE if requested
        if options.get('vacuum'):
            self.stdout.write('Running VACUUM ANALYZE...')
            if DatabaseOptimizer.vacuum_analyze_tables():
                results['optimizations'].append({
                    'action': 'vacuum_analyze',
                    'status': 'success',
                    'message': 'Database tables optimized'
                })
            else:
                results['optimizations'].append({
                    'action': 'vacuum_analyze',
                    'status': 'failed',
                    'message': 'Failed to optimize database tables'
                })
        
        # Warm cache if requested
        if options.get('warm_cache'):
            self.stdout.write('Warming cache...')
            if CacheManager.warm_cache():
                results['optimizations'].append({
                    'action': 'warm_cache',
                    'status': 'success',
                    'message': 'Cache warmed successfully'
                })
            else:
                results['optimizations'].append({
                    'action': 'warm_cache',
                    'status': 'failed',
                    'message': 'Failed to warm cache'
                })
        
        self.stdout.write(
            self.style.SUCCESS('System optimization completed')
        )
        
        return results
    
    def monitor_system(self):
        """Monitor system in real-time"""
        self.stdout.write('Monitoring system metrics...')
        
        # Collect metrics over time
        metrics_history = []
        
        for i in range(5):  # Collect 5 samples
            metrics = {
                'timestamp': timezone.now().isoformat(),
                'system': PerformanceMonitor.get_system_metrics(),
                'database': PerformanceMonitor.get_database_metrics(),
                'application': PerformanceMonitor.get_application_metrics()
            }
            metrics_history.append(metrics)
            
            if i < 4:  # Don't sleep after last iteration
                import time
                time.sleep(10)  # Wait 10 seconds between samples
        
        result = {
            'monitoring_period': '50 seconds',
            'sample_count': len(metrics_history),
            'metrics_history': metrics_history
        }
        
        self.stdout.write(
            self.style.SUCCESS('System monitoring completed')
        )
        
        return result
    
    def check_health(self):
        """Check overall system health"""
        self.stdout.write('Checking system health...')
        
        health_status = HealthChecker.get_overall_health()
        
        # Display health status
        overall_status = health_status['overall_status']
        if overall_status == 'healthy':
            self.stdout.write(
                self.style.SUCCESS(f'System status: {overall_status.upper()}')
            )
        elif overall_status == 'warning':
            self.stdout.write(
                self.style.WARNING(f'System status: {overall_status.upper()}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'System status: {overall_status.upper()}')
            )
        
        return health_status
    
    def manage_cache(self, options):
        """Manage cache operations"""
        self.stdout.write('Managing cache...')
        
        results = {
            'timestamp': timezone.now().isoformat(),
            'cache_operations': []
        }
        
        # Get cache stats
        cache_stats = CacheManager.get_cache_stats()
        results['cache_stats'] = cache_stats
        
        # Warm cache if requested
        if options.get('warm_cache'):
            if CacheManager.warm_cache():
                results['cache_operations'].append({
                    'action': 'warm_cache',
                    'status': 'success'
                })
            else:
                results['cache_operations'].append({
                    'action': 'warm_cache',
                    'status': 'failed'
                })
        
        self.stdout.write(
            self.style.SUCCESS('Cache management completed')
        )
        
        return results
    
    def _generate_recommendations(self, analysis_result):
        """Generate optimization recommendations based on analysis"""
        recommendations = []
        
        # Check CPU usage
        cpu_percent = analysis_result['system_metrics']['cpu_percent']
        if cpu_percent > 80:
            recommendations.append({
                'priority': 'high',
                'category': 'system',
                'issue': f'High CPU usage: {cpu_percent}%',
                'recommendation': 'Consider scaling up server resources or optimizing CPU-intensive operations'
            })
        
        # Check memory usage
        memory_percent = analysis_result['system_metrics']['memory_percent']
        if memory_percent > 85:
            recommendations.append({
                'priority': 'high',
                'category': 'system',
                'issue': f'High memory usage: {memory_percent}%',
                'recommendation': 'Consider increasing memory or optimizing memory-intensive operations'
            })
        
        # Check slow queries
        slow_queries = analysis_result.get('slow_queries', [])
        if slow_queries:
            recommendations.append({
                'priority': 'medium',
                'category': 'database',
                'issue': f'Found {len(slow_queries)} slow queries',
                'recommendation': 'Review and optimize slow queries, consider adding indexes'
            })
        
        # Check cache hit ratio
        cache_stats = analysis_result.get('cache_stats', {})
        hit_ratio = cache_stats.get('hit_ratio', 0)
        if hit_ratio < 0.8:  # Less than 80% hit ratio
            recommendations.append({
                'priority': 'medium',
                'category': 'cache',
                'issue': f'Low cache hit ratio: {hit_ratio:.2%}',
                'recommendation': 'Review caching strategy and warm cache with frequently accessed data'
            })
        
        # Check active dispatches
        app_metrics = analysis_result['application_metrics']
        emergency_dispatches = app_metrics.get('emergency_dispatches', 0)
        if emergency_dispatches > 5:
            recommendations.append({
                'priority': 'high',
                'category': 'application',
                'issue': f'High number of emergency dispatches: {emergency_dispatches}',
                'recommendation': 'Monitor emergency dispatch queue and ensure adequate ambulance availability'
            })
        
        return recommendations
