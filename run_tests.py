"""
MediConnect Test Suite Runner
Comprehensive testing framework for the hospital e-referral system
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line
import coverage

def run_tests():
    """Run comprehensive test suite with coverage reporting"""
    
    # Start coverage analysis
    cov = coverage.Coverage()
    cov.start()
    
    os.environ['DJANGO_SETTINGS_MODULE'] = 'hospital_ereferral.settings'
    django.setup()
    
    # Test discovery patterns
    test_patterns = [
        'users.tests',
        'patients.tests', 
        'doctors.tests',
        'referrals.tests',
        'appointments.tests',
        'ambulances.tests',
        'notifications.tests',
        'reports.tests',
        'analytics.tests',
        'api.tests'
    ]
    
    # Run tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner(
        verbosity=2,
        interactive=True,
        failfast=False,
        keepdb=True,
        debug_sql=False
    )
    
    failures = test_runner.run_tests(test_patterns)
    
    # Stop coverage and generate report
    cov.stop()
    cov.save()
    
    print("\n" + "="*50)
    print("COVERAGE REPORT")
    print("="*50)
    cov.report()
    
    # Generate HTML coverage report
    cov.html_report(directory='htmlcov')
    print(f"\nHTML coverage report generated in 'htmlcov' directory")
    
    if failures:
        print(f"\n{failures} test(s) failed.")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        
    return failures

def run_integration_tests():
    """Run integration tests"""
    print("Running integration tests...")
    
    test_commands = [
        ['python', 'manage.py', 'test', 'tests.integration', '--verbosity=2'],
    ]
    
    for cmd in test_commands:
        print(f"Running: {' '.join(cmd)}")
        result = os.system(' '.join(cmd))
        if result != 0:
            print(f"Integration tests failed with code {result}")
            return False
    
    print("Integration tests completed successfully!")
    return True

def run_performance_tests():
    """Run performance tests"""
    print("Running performance tests...")
    
    # Performance test commands
    performance_commands = [
        ['python', 'manage.py', 'test', 'tests.performance', '--verbosity=2'],
        ['locust', '--headless', '--users', '50', '--spawn-rate', '5', '--run-time', '60s', '--host', 'http://localhost:8000'],
    ]
    
    for cmd in performance_commands:
        print(f"Running: {' '.join(cmd)}")
        result = os.system(' '.join(cmd))
        if result != 0:
            print(f"Performance test failed: {' '.join(cmd)}")
            continue
    
    print("Performance tests completed!")

def run_security_tests():
    """Run security tests"""
    print("Running security tests...")
    
    security_commands = [
        ['python', 'manage.py', 'test', 'tests.security', '--verbosity=2'],
        ['bandit', '-r', '.', '-f', 'json', '-o', 'security_report.json'],
        ['safety', 'check', '--json', '--output', 'safety_report.json'],
    ]
    
    for cmd in security_commands:
        print(f"Running: {' '.join(cmd)}")
        result = os.system(' '.join(cmd))
        if result != 0:
            print(f"Security test failed: {' '.join(cmd)}")
            continue
    
    print("Security tests completed!")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='MediConnect Test Suite')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    parser.add_argument('--security', action='store_true', help='Run security tests')
    parser.add_argument('--all', action='store_true', help='Run all test suites')
    
    args = parser.parse_args()
    
    if args.all:
        run_tests()
        run_integration_tests()
        run_performance_tests()
        run_security_tests()
    elif args.integration:
        run_integration_tests()
    elif args.performance:
        run_performance_tests()
    elif args.security:
        run_security_tests()
    else:
        run_tests()