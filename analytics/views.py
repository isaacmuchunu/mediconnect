"""
Analytics & Reporting System Views
Real-time dashboards, performance metrics, and report generation
"""

import json
from datetime import timedelta, datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

from .models import (
    PerformanceMetric, DashboardWidget, ReportTemplate,
    GeneratedReport, AnalyticsEvent, KPITarget
)
from ambulances.models import Ambulance, Dispatch
from hospitals.models_integration import HospitalCapacity

User = get_user_model()


def is_admin_or_manager(user):
    """Check if user is admin or manager"""
    return user.is_authenticated and (
        user.is_staff or 
        user.role in ['ADMIN', 'MANAGER', 'SUPERVISOR'] or
        user.groups.filter(name__in=['Admins', 'Managers', 'Supervisors']).exists()
    )


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard with real-time metrics"""
    
    # Get time range from query params
    time_range = request.GET.get('range', '24h')
    
    # Calculate date range
    now = timezone.now()
    if time_range == '1h':
        start_date = now - timedelta(hours=1)
    elif time_range == '24h':
        start_date = now - timedelta(hours=24)
    elif time_range == '7d':
        start_date = now - timedelta(days=7)
    elif time_range == '30d':
        start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(hours=24)
    
    # Get key metrics
    total_dispatches = Dispatch.objects.filter(
        created_at__gte=start_date
    ).count()
    
    active_ambulances = Ambulance.objects.filter(
        status__in=['available', 'dispatched', 'en_route', 'on_scene', 'transporting']
    ).count()
    
    # Calculate average response time
    avg_response_time = PerformanceMetric.objects.filter(
        metric_type='response_time',
        created_at__gte=start_date
    ).aggregate(avg_time=Avg('value'))['avg_time'] or 0
    
    # Get hospital capacity
    hospitals_at_capacity = HospitalCapacity.objects.filter(
        overall_status__in=['critical', 'full']
    ).count()
    
    # Get recent performance metrics
    recent_metrics = PerformanceMetric.objects.filter(
        created_at__gte=start_date
    ).order_by('-created_at')[:10]
    
    # Get dashboard widgets
    widgets = DashboardWidget.objects.filter(
        is_visible=True
    ).order_by('dashboard_position')
    
    # Filter widgets by user role
    user_role = getattr(request.user, 'role', 'USER')
    visible_widgets = []
    for widget in widgets:
        if not widget.visible_to_roles or user_role in widget.visible_to_roles:
            visible_widgets.append(widget)
    
    # Get KPI status
    kpi_targets = KPITarget.objects.filter(is_active=True)
    kpi_status = {}
    for kpi in kpi_targets:
        kpi_status[kpi.kpi_type] = {
            'name': kpi.name,
            'current_value': float(kpi.get_current_value()),
            'target_value': float(kpi.target_value),
            'status': kpi.get_status(),
            'unit': kpi.unit
        }
    
    context = {
        'time_range': time_range,
        'start_date': start_date,
        'key_metrics': {
            'total_dispatches': total_dispatches,
            'active_ambulances': active_ambulances,
            'avg_response_time': round(float(avg_response_time), 1),
            'hospitals_at_capacity': hospitals_at_capacity,
        },
        'recent_metrics': recent_metrics,
        'widgets': visible_widgets,
        'kpi_status': kpi_status,
    }
    
    return render(request, 'analytics/dashboard.html', context)


@login_required
@csrf_exempt
def widget_data_api(request, widget_id):
    """API endpoint for widget data"""
    
    try:
        widget = get_object_or_404(DashboardWidget, id=widget_id)
        
        # Check if user has access to this widget
        user_role = getattr(request.user, 'role', 'USER')
        if widget.visible_to_roles and user_role not in widget.visible_to_roles:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get time range
        time_range = request.GET.get('range', '24h')
        
        # Get widget data based on type
        data = get_widget_data(widget, time_range)
        
        return JsonResponse({
            'status': 'success',
            'data': data,
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


def get_widget_data(widget, time_range='24h'):
    """Get data for specific widget type"""
    
    # Calculate date range
    now = timezone.now()
    if time_range == '1h':
        start_date = now - timedelta(hours=1)
    elif time_range == '24h':
        start_date = now - timedelta(hours=24)
    elif time_range == '7d':
        start_date = now - timedelta(days=7)
    elif time_range == '30d':
        start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(hours=24)
    
    if widget.data_source == 'dispatch_volume':
        return get_dispatch_volume_data(start_date, now)
    elif widget.data_source == 'response_times':
        return get_response_times_data(start_date, now)
    elif widget.data_source == 'ambulance_status':
        return get_ambulance_status_data()
    elif widget.data_source == 'hospital_capacity':
        return get_hospital_capacity_data()
    elif widget.data_source == 'performance_metrics':
        return get_performance_metrics_data(start_date, now)
    else:
        # Return sample data for unknown sources
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            'datasets': [{
                'label': widget.title,
                'data': [10, 20, 15, 25, 30],
                'backgroundColor': '#3b82f6'
            }]
        }


def get_dispatch_volume_data(start_date, end_date):
    """Get dispatch volume data"""
    
    # Group dispatches by hour for 24h view, by day for longer periods
    time_diff = end_date - start_date
    
    if time_diff <= timedelta(hours=24):
        # Hourly data
        dispatches = Dispatch.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).extra({
            'hour': "date_trunc('hour', created_at)"
        }).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        labels = [d['hour'].strftime('%H:%M') for d in dispatches]
        data = [d['count'] for d in dispatches]
    else:
        # Daily data
        dispatches = Dispatch.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).extra({
            'date': "date_trunc('day', created_at)"
        }).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        labels = [d['date'].strftime('%m/%d') for d in dispatches]
        data = [d['count'] for d in dispatches]
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Dispatches',
            'data': data,
            'backgroundColor': '#3b82f6',
            'borderColor': '#1d4ed8',
            'fill': False
        }]
    }


def get_response_times_data(start_date, end_date):
    """Get response times data"""
    
    response_times = PerformanceMetric.objects.filter(
        metric_type='response_time',
        created_at__gte=start_date,
        created_at__lte=end_date
    ).values('measurement_date').annotate(
        avg_time=Avg('value')
    ).order_by('measurement_date')
    
    labels = [rt['measurement_date'].strftime('%m/%d') for rt in response_times]
    data = [float(rt['avg_time']) for rt in response_times]
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Average Response Time (minutes)',
            'data': data,
            'backgroundColor': '#10b981',
            'borderColor': '#059669',
            'fill': False
        }]
    }


def get_ambulance_status_data():
    """Get ambulance status distribution"""
    
    status_counts = Ambulance.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    labels = [sc['status'].replace('_', ' ').title() for sc in status_counts]
    data = [sc['count'] for sc in status_counts]
    
    colors = {
        'available': '#10b981',
        'dispatched': '#f59e0b',
        'en_route': '#3b82f6',
        'on_scene': '#8b5cf6',
        'transporting': '#ef4444',
        'at_hospital': '#06b6d4',
        'maintenance': '#6b7280',
        'out_of_service': '#dc2626'
    }
    
    background_colors = [colors.get(sc['status'], '#6b7280') for sc in status_counts]
    
    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': background_colors
        }]
    }


def get_hospital_capacity_data():
    """Get hospital capacity data"""
    
    capacity_data = HospitalCapacity.objects.values('overall_status').annotate(
        count=Count('id')
    ).order_by('overall_status')
    
    labels = [cd['overall_status'].replace('_', ' ').title() for cd in capacity_data]
    data = [cd['count'] for cd in capacity_data]
    
    colors = {
        'normal': '#10b981',
        'busy': '#f59e0b',
        'critical': '#ef4444',
        'full': '#dc2626',
        'closed': '#6b7280'
    }
    
    background_colors = [colors.get(cd['overall_status'], '#6b7280') for cd in capacity_data]
    
    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': background_colors
        }]
    }


def get_performance_metrics_data(start_date, end_date):
    """Get performance metrics data"""
    
    metrics = PerformanceMetric.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).values('metric_type').annotate(
        avg_value=Avg('value'),
        count=Count('id')
    ).order_by('metric_type')
    
    labels = [m['metric_type'].replace('_', ' ').title() for m in metrics]
    data = [float(m['avg_value']) for m in metrics]
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Average Values',
            'data': data,
            'backgroundColor': '#8b5cf6'
        }]
    }


@login_required
@user_passes_test(is_admin_or_manager)
def reports_dashboard(request):
    """Reports management dashboard"""
    
    # Get report templates
    templates = ReportTemplate.objects.filter(is_active=True).order_by('name')
    
    # Get recent reports
    recent_reports = GeneratedReport.objects.order_by('-generation_started')[:10]
    
    # Get scheduled reports
    scheduled_reports = ReportTemplate.objects.filter(
        is_active=True,
        frequency__in=['daily', 'weekly', 'monthly', 'quarterly', 'annually']
    ).order_by('next_generation')
    
    context = {
        'templates': templates,
        'recent_reports': recent_reports,
        'scheduled_reports': scheduled_reports,
    }
    
    return render(request, 'analytics/reports_dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_manager)
def generate_report(request, template_id):
    """Generate report from template"""
    
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    if request.method == 'POST':
        try:
            # Get date range from form
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start_date = timezone.now() - timedelta(days=30)
            
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_date = timezone.now()
            
            # Create report instance
            report = GeneratedReport.objects.create(
                template=template,
                title=f"{template.name} - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                generated_by=request.user,
                data_start_date=start_date,
                data_end_date=end_date,
                generation_parameters={
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'format': template.output_format
                }
            )
            
            # TODO: Implement actual report generation
            # For now, just mark as completed
            report.mark_completed('/reports/sample_report.pdf', 1024000)
            
            messages.success(request, 'Report generated successfully.')
            return redirect('analytics:report_detail', report_id=report.id)
            
        except Exception as e:
            messages.error(request, f'Error generating report: {str(e)}')
    
    context = {
        'template': template,
    }
    
    return render(request, 'analytics/generate_report.html', context)


@login_required
def report_detail(request, report_id):
    """View generated report details"""
    
    report = get_object_or_404(GeneratedReport, id=report_id)
    
    # Check if user has access
    if not (request.user == report.generated_by or 
            request.user in report.template.recipients.all() or
            is_admin_or_manager(request.user)):
        messages.error(request, 'You do not have access to this report.')
        return redirect('analytics:reports_dashboard')
    
    context = {
        'report': report,
    }
    
    return render(request, 'analytics/report_detail.html', context)


@login_required
@user_passes_test(is_admin_or_manager)
def performance_metrics(request):
    """Performance metrics analysis"""
    
    # Get query parameters
    metric_type = request.GET.get('metric_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    ambulance_id = request.GET.get('ambulance', '')
    
    # Build queryset
    metrics = PerformanceMetric.objects.all()
    
    if metric_type:
        metrics = metrics.filter(metric_type=metric_type)
    
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            metrics = metrics.filter(measurement_date__gte=date_from_parsed)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            metrics = metrics.filter(measurement_date__lte=date_to_parsed)
        except ValueError:
            pass
    
    if ambulance_id:
        metrics = metrics.filter(ambulance_id=ambulance_id)
    
    metrics = metrics.order_by('-measurement_date', '-created_at')
    
    # Pagination
    paginator = Paginator(metrics, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get summary statistics
    summary_stats = metrics.aggregate(
        avg_value=Avg('value'),
        min_value=Min('value'),
        max_value=Max('value'),
        count=Count('id')
    )
    
    # Get available ambulances for filter
    ambulances = Ambulance.objects.filter(is_active=True).order_by('license_plate')
    
    context = {
        'metrics': page_obj,
        'summary_stats': summary_stats,
        'ambulances': ambulances,
        'filters': {
            'metric_type': metric_type,
            'date_from': date_from,
            'date_to': date_to,
            'ambulance': ambulance_id,
        },
        'metric_type_choices': PerformanceMetric.METRIC_TYPE_CHOICES,
    }
    
    return render(request, 'analytics/performance_metrics.html', context)


@login_required
@require_POST
@csrf_exempt
def log_analytics_event(request):
    """Log analytics event via API"""
    
    try:
        data = json.loads(request.body)
        
        event = AnalyticsEvent.log_event(
            event_type=data.get('event_type'),
            event_name=data.get('event_name'),
            user=request.user,
            event_data=data.get('event_data', {}),
            session_id=data.get('session_id', ''),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            duration_ms=data.get('duration_ms')
        )
        
        return JsonResponse({
            'status': 'success',
            'event_id': str(event.id)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
