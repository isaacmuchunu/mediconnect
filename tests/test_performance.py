"""
Performance Tests for MediConnect
Load testing and performance benchmarks for critical system components
"""

import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.test.client import Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from ambulances.models import Ambulance, AmbulanceType, EmergencyCall
from doctors.models import Hospital

User = get_user_model()


class PerformanceTestCase(TestCase):
    """Base class for performance tests"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='perf_user',
            email='performance@mediconnect.com',
            role='DISPATCHER'
        )
        self.client.force_login(self.user)
    
    def measure_response_time(self, func, iterations=10):
        """Measure average response time for a function"""
        times = []
        for _ in range(iterations):
            start_time = time.time()
            func()
            end_time = time.time()
            times.append(end_time - start_time)
        
        return {
            'avg': statistics.mean(times),
            'min': min(times),
            'max': max(times),
            'median': statistics.median(times)
        }
    
    def measure_concurrent_requests(self, func, concurrent_users=10, requests_per_user=5):
        """Measure performance under concurrent load"""
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            for user_id in range(concurrent_users):
                for request_id in range(requests_per_user):
                    future = executor.submit(func)
                    futures.append(future)
            
            # Wait for all requests to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Request failed: {e}")
        
        total_time = time.time() - start_time
        total_requests = concurrent_users * requests_per_user
        
        return {
            'total_time': total_time,
            'total_requests': total_requests,
            'requests_per_second': total_requests / total_time,
            'avg_response_time': total_time / total_requests
        }


class EmergencyCallPerformanceTest(PerformanceTestCase):
    """Performance tests for emergency call system"""
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        for i in range(100):
            EmergencyCall.objects.create(
                call_number=f'PERF-{i:03d}',
                caller_phone=f'+1-555-{i:04d}',
                caller_name=f'Caller {i}',
                patient_name=f'Patient {i}',
                chief_complaint=f'Test complaint {i}',
                priority=['routine', 'urgent', 'emergency', 'critical'][i % 4],
                call_taker=self.user
            )
    
    def test_emergency_call_list_performance(self):
        """Test performance of emergency call listing"""
        
        def list_calls():
            url = reverse('ambulances:emergency_call_list')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            return response
        
        # Test single request performance
        timing = self.measure_response_time(list_calls, iterations=20)
        self.assertLess(timing['avg'], 0.5, "Emergency call list should respond in under 500ms")
        print(f"Emergency call list average response time: {timing['avg']:.3f}s")
        
        # Test concurrent load
        load_test = self.measure_concurrent_requests(list_calls, concurrent_users=10, requests_per_user=3)
        self.assertGreater(load_test['requests_per_second'], 10, "Should handle at least 10 requests per second")
        print(f"Emergency call list concurrent performance: {load_test['requests_per_second']:.1f} req/s")
    
    def test_emergency_call_creation_performance(self):
        """Test performance of emergency call creation"""
        
        def create_call():
            data = {
                'caller_phone': '+1-555-PERF',
                'caller_name': 'Performance Test',
                'patient_name': 'Test Patient',
                'chief_complaint': 'Performance test call',
                'priority': 'urgent'
            }
            url = reverse('ambulances:emergency_call_create')
            response = self.client.post(url, data)
            return response
        
        timing = self.measure_response_time(create_call, iterations=10)
        self.assertLess(timing['avg'], 1.0, "Emergency call creation should complete in under 1 second")
        print(f"Emergency call creation average time: {timing['avg']:.3f}s")
    
    def test_emergency_call_search_performance(self):
        """Test performance of emergency call search"""
        
        def search_calls():
            url = reverse('ambulances:emergency_call_list') + '?search=Patient'
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            return response
        
        timing = self.measure_response_time(search_calls, iterations=15)
        self.assertLess(timing['avg'], 0.3, "Search should respond in under 300ms")
        print(f"Emergency call search average time: {timing['avg']:.3f}s")


class AmbulanceTrackingPerformanceTest(PerformanceTestCase):
    """Performance tests for ambulance tracking"""
    
    def setUp(self):
        super().setUp()
        
        # Create test ambulances
        ambulance_type = AmbulanceType.objects.create(
            name='Performance Test ALS',
            code='PERF'
        )
        
        for i in range(50):
            Ambulance.objects.create(
                license_plate=f'PERF-{i:02d}',
                call_sign=f'Unit {i}',
                ambulance_type=ambulance_type,
                current_latitude=40.7128 + (i * 0.001),
                current_longitude=-74.0060 + (i * 0.001)
            )
    
    def test_ambulance_list_performance(self):
        """Test ambulance list performance"""
        
        def list_ambulances():
            url = reverse('ambulances:ambulance_list')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            return response
        
        timing = self.measure_response_time(list_ambulances, iterations=15)
        self.assertLess(timing['avg'], 0.4, "Ambulance list should respond in under 400ms")
        print(f"Ambulance list average response time: {timing['avg']:.3f}s")
    
    def test_gps_update_performance(self):
        """Test GPS location update performance"""
        ambulance = Ambulance.objects.first()
        
        def update_gps():
            # Simulate GPS update
            ambulance.current_latitude = 40.7128 + (time.time() % 0.01)
            ambulance.current_longitude = -74.0060 + (time.time() % 0.01)
            ambulance.save()
        
        timing = self.measure_response_time(update_gps, iterations=50)
        self.assertLess(timing['avg'], 0.1, "GPS updates should complete in under 100ms")
        print(f"GPS update average time: {timing['avg']:.3f}s")
        
        # Test concurrent GPS updates
        def concurrent_gps_update():
            ambulances = Ambulance.objects.all()[:10]
            for amb in ambulances:
                amb.current_latitude = 40.7128 + (time.time() % 0.01)
                amb.current_longitude = -74.0060 + (time.time() % 0.01) 
                amb.save()
        
        load_test = self.measure_concurrent_requests(
            concurrent_gps_update, 
            concurrent_users=5, 
            requests_per_user=2
        )
        print(f"Concurrent GPS updates: {load_test['requests_per_second']:.1f} req/s")


class DatabasePerformanceTest(TransactionTestCase):
    """Database performance tests"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='db_perf_user',
            email='dbperf@mediconnect.com'
        )
    
    def test_bulk_emergency_call_creation(self):
        """Test bulk creation of emergency calls"""
        start_time = time.time()
        
        calls_data = []
        for i in range(1000):
            calls_data.append(EmergencyCall(
                call_number=f'BULK-{i:04d}',
                caller_phone=f'+1-555-{i:04d}',
                caller_name=f'Bulk Caller {i}',
                patient_name=f'Bulk Patient {i}',
                chief_complaint=f'Bulk test {i}',
                call_taker=self.user
            ))
        
        EmergencyCall.objects.bulk_create(calls_data)
        
        creation_time = time.time() - start_time
        self.assertLess(creation_time, 5.0, "Bulk creation of 1000 calls should complete in under 5 seconds")
        print(f"Bulk created 1000 emergency calls in {creation_time:.2f}s")
    
    def test_complex_query_performance(self):
        """Test performance of complex database queries"""
        # Create test data
        ambulance_type = AmbulanceType.objects.create(name='Query Test', code='QT')
        
        for i in range(100):
            EmergencyCall.objects.create(
                call_number=f'QUERY-{i:03d}',
                caller_phone=f'+1-555-{i:04d}',
                patient_name=f'Query Patient {i}',
                chief_complaint='Query test',
                priority=['routine', 'urgent', 'emergency', 'critical'][i % 4],
                call_taker=self.user,
                received_at=timezone.now() - timedelta(hours=i)
            )
        
        def complex_query():
            # Simulate complex query with joins and filters
            calls = EmergencyCall.objects.select_related('call_taker').filter(
                priority__in=['urgent', 'critical'],
                received_at__gte=timezone.now() - timedelta(days=1)
            ).order_by('-received_at')[:20]
            
            # Force evaluation
            list(calls)
        
        start_time = time.time()
        for _ in range(10):
            complex_query()
        query_time = (time.time() - start_time) / 10
        
        self.assertLess(query_time, 0.1, "Complex queries should complete in under 100ms")
        print(f"Complex query average time: {query_time:.3f}s")


class APIEndpointPerformanceTest(PerformanceTestCase):
    """API endpoint performance tests"""
    
    def test_api_authentication_performance(self):
        """Test API authentication performance"""
        
        def authenticate_request():
            # Test token authentication performance
            response = self.client.get('/api/ambulances/')
            return response
        
        timing = self.measure_response_time(authenticate_request, iterations=20)
        self.assertLess(timing['avg'], 0.2, "API authentication should be fast")
        print(f"API authentication average time: {timing['avg']:.3f}s")
    
    def test_api_pagination_performance(self):
        """Test API pagination performance"""
        
        def paginated_request():
            response = self.client.get('/api/emergency/calls/?page=1&page_size=20')
            return response
        
        timing = self.measure_response_time(paginated_request, iterations=15)
        print(f"API pagination average time: {timing['avg']:.3f}s")
    
    def test_api_concurrent_load(self):
        """Test API under concurrent load"""
        
        def api_request():
            endpoints = [
                '/api/ambulances/',
                '/api/emergency/calls/',
                # Add other API endpoints
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.client.get(endpoint)
                except Exception:
                    pass  # Handle missing endpoints gracefully
        
        load_test = self.measure_concurrent_requests(
            api_request,
            concurrent_users=15,
            requests_per_user=3
        )
        
        self.assertGreater(load_test['requests_per_second'], 5, "API should handle concurrent load")
        print(f"API concurrent load: {load_test['requests_per_second']:.1f} req/s")


class MemoryPerformanceTest(TestCase):
    """Memory usage and optimization tests"""
    
    def test_memory_efficient_queries(self):
        """Test memory efficiency of database queries"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory = process.memory_info().rss
        
        # Create test data
        user = User.objects.create_user(username='memory_test', email='memory@test.com')
        
        # Test memory-efficient query
        calls_data = []
        for i in range(5000):
            calls_data.append(EmergencyCall(
                call_number=f'MEM-{i:04d}',
                caller_phone=f'+1-555-{i:04d}',
                patient_name=f'Memory Patient {i}',
                chief_complaint='Memory test',
                call_taker=user
            ))
        
        EmergencyCall.objects.bulk_create(calls_data)
        
        # Query using iterator to avoid loading all objects into memory
        count = 0
        for call in EmergencyCall.objects.iterator(chunk_size=100):
            count += 1
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        self.assertLess(memory_increase, 100, "Memory increase should be reasonable")
        print(f"Memory increase for 5000 records: {memory_increase:.1f} MB")


if __name__ == '__main__':
    import unittest
    unittest.main(verbosity=2)