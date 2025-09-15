#!/usr/bin/env python
"""
Comprehensive test runner for the Hospital E-Referral System
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line


def setup_test_environment():
    """Setup Django test environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_ereferral.settings')
    django.setup()


def run_all_tests():
    """Run all tests for the project"""
    print("=" * 70)
    print("HOSPITAL E-REFERRAL SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    # Test apps in order of dependency
    test_apps = [
        'users',
        'patients', 
        'doctors',
        'referrals',
        'appointments',
        'ambulances',
        'notifications',
        'reports',
        'api'
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_apps = []
    
    for app in test_apps:
        print(f"\n{'='*50}")
        print(f"Testing {app.upper()} app...")
        print(f"{'='*50}")
        
        try:
            # Run tests for specific app
            result = execute_from_command_line([
                'manage.py', 'test', app, '--verbosity=2', '--keepdb'
            ])
            
            if result == 0:
                print(f"✅ {app} tests PASSED")
                passed_tests += 1
            else:
                print(f"❌ {app} tests FAILED")
                failed_apps.append(app)
                
        except Exception as e:
            print(f"❌ Error running {app} tests: {str(e)}")
            failed_apps.append(app)
        
        total_tests += 1
    
    # Print summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total apps tested: {total_tests}")
    print(f"Apps passed: {passed_tests}")
    print(f"Apps failed: {len(failed_apps)}")
    
    if failed_apps:
        print(f"\nFailed apps: {', '.join(failed_apps)}")
        return False
    else:
        print("\n🎉 ALL TESTS PASSED!")
        return True


def run_specific_tests(test_pattern):
    """Run specific tests matching a pattern"""
    print(f"Running tests matching pattern: {test_pattern}")
    
    try:
        execute_from_command_line([
            'manage.py', 'test', test_pattern, '--verbosity=2'
        ])
    except Exception as e:
        print(f"Error running tests: {str(e)}")
        return False
    
    return True


def run_coverage_tests():
    """Run tests with coverage reporting"""
    print("Running tests with coverage analysis...")
    
    try:
        # Install coverage if not available
        import coverage
        
        # Start coverage
        cov = coverage.Coverage()
        cov.start()
        
        # Run tests
        result = run_all_tests()
        
        # Stop coverage and generate report
        cov.stop()
        cov.save()
        
        print("\n" + "="*70)
        print("COVERAGE REPORT")
        print("="*70)
        cov.report()
        
        # Generate HTML coverage report
        cov.html_report(directory='htmlcov')
        print("\nHTML coverage report generated in 'htmlcov' directory")
        
        return result
        
    except ImportError:
        print("Coverage package not installed. Install with: pip install coverage")
        print("Running tests without coverage...")
        return run_all_tests()


def run_performance_tests():
    """Run performance and load tests"""
    print("Running performance tests...")
    
    performance_tests = [
        'ambulances.tests.PerformanceTest',
        'referrals.tests.ReferralPerformanceTest',
        'api.tests.APIPerformanceTest'
    ]
    
    for test in performance_tests:
        print(f"Running {test}...")
        try:
            execute_from_command_line([
                'manage.py', 'test', test, '--verbosity=2'
            ])
        except Exception as e:
            print(f"Error running {test}: {str(e)}")


def run_integration_tests():
    """Run integration tests"""
    print("Running integration tests...")
    
    integration_tests = [
        'tests.integration.test_referral_workflow',
        'tests.integration.test_ambulance_dispatch',
        'tests.integration.test_notification_system'
    ]
    
    for test in integration_tests:
        print(f"Running {test}...")
        try:
            execute_from_command_line([
                'manage.py', 'test', test, '--verbosity=2'
            ])
        except Exception as e:
            print(f"Error running {test}: {str(e)}")


def main():
    """Main test runner function"""
    setup_test_environment()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'all':
            return run_all_tests()
        elif command == 'coverage':
            return run_coverage_tests()
        elif command == 'performance':
            return run_performance_tests()
        elif command == 'integration':
            return run_integration_tests()
        elif command.startswith('app:'):
            app_name = command.split(':')[1]
            return run_specific_tests(app_name)
        elif command.startswith('test:'):
            test_pattern = command.split(':', 1)[1]
            return run_specific_tests(test_pattern)
        else:
            print("Unknown command. Available commands:")
            print("  all         - Run all tests")
            print("  coverage    - Run tests with coverage")
            print("  performance - Run performance tests")
            print("  integration - Run integration tests")
            print("  app:<name>  - Run tests for specific app")
            print("  test:<pattern> - Run specific test pattern")
            return False
    else:
        # Default: run all tests
        return run_all_tests()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
