from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard and main views
    path('', views.ReportsDashboardView.as_view(), name='dashboard'),
    path('list/', views.ReportListView.as_view(), name='report_list'),
    path('create/', views.ReportCreateView.as_view(), name='report_create'),
    path('<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    
    # Export functionality
    path('<int:pk>/export/<str:format>/', views.ReportExportView.as_view(), name='report_export'),
    
    # Analytics
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    
    # Compliance reports
    path('compliance/', views.ComplianceReportView.as_view(), name='compliance'),
    path('compliance/<int:pk>/', views.ReportDetailView.as_view(), name='compliance_detail'),
    
    # Report templates
    path('templates/', views.ReportTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.ReportTemplateCreateView.as_view(), name='template_create'),
    
    # Report scheduling
    path('schedules/', views.ReportScheduleListView.as_view(), name='schedule_list'),
    path('schedules/create/', views.ReportScheduleCreateView.as_view(), name='schedule_create'),
    
    # AJAX endpoints
    path('ajax/status/<int:pk>/', views.ajax_report_status, name='ajax_report_status'),
    path('ajax/delete/<int:pk>/', views.ajax_delete_report, name='ajax_delete_report'),
    path('ajax/share/<int:pk>/', views.ajax_share_report, name='ajax_share_report'),
]