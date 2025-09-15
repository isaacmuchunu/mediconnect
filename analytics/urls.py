"""
Analytics URLs
URL patterns for analytics and reporting system
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Dashboard
    path('', views.analytics_dashboard, name='dashboard'),
    
    # Widget API
    path('api/widget/<uuid:widget_id>/data/', views.widget_data_api, name='widget_data_api'),
    
    # Reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/generate/<uuid:template_id>/', views.generate_report, name='generate_report'),
    path('reports/<uuid:report_id>/', views.report_detail, name='report_detail'),
    
    # Performance Metrics
    path('metrics/', views.performance_metrics, name='performance_metrics'),
    
    # Analytics Events API
    path('api/events/log/', views.log_analytics_event, name='log_analytics_event'),
]
