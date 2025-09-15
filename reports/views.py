from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.conf import settings
import json
import csv
import io
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import xlsxwriter

from .models import (
    Report, ReportTemplate, ReferralAnalytics, AppointmentAnalytics,
    SystemUsageAnalytics, ComplianceReport, ReportSchedule, ReportAccess
)
from .forms import (
    ReportForm, ReportTemplateForm, ReportFilterForm, ReportScheduleForm,
    ComplianceReportForm, AnalyticsFilterForm
)
from referrals.models import Referral
from appointments.models import Appointment
from patients.models import Patient
from doctors.models import DoctorProfile

class ReportsDashboardView(LoginRequiredMixin, View):
    """Main dashboard for reports with analytics overview"""
    
    def get(self, request):
        # Get recent reports
        recent_reports = Report.objects.filter(
            generated_by=request.user
        ).order_by('-created_at')[:10]
        
        # Get report statistics
        total_reports = Report.objects.filter(generated_by=request.user).count()
        pending_reports = Report.objects.filter(
            generated_by=request.user, status='pending'
        ).count()
        completed_reports = Report.objects.filter(
            generated_by=request.user, status='completed'
        ).count()
        
        # Get analytics data for charts
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Referral analytics
        referral_analytics = ReferralAnalytics.objects.filter(
            date__gte=week_ago
        ).order_by('date')
        
        # Appointment analytics
        appointment_analytics = AppointmentAnalytics.objects.filter(
            date__gte=week_ago
        ).order_by('date')
        
        # System usage analytics
        system_usage = SystemUsageAnalytics.objects.filter(
            date__gte=week_ago
        ).order_by('date')
        
        # Scheduled reports
        scheduled_reports = ReportSchedule.objects.filter(
            is_enabled=True
        ).order_by('next_run')[:5]
        
        context = {
            'recent_reports': recent_reports,
            'total_reports': total_reports,
            'pending_reports': pending_reports,
            'completed_reports': completed_reports,
            'referral_analytics': referral_analytics,
            'appointment_analytics': appointment_analytics,
            'system_usage': system_usage,
            'scheduled_reports': scheduled_reports,
        }
        
        return render(request, 'reports/dashboard.html', context)

class ReportListView(LoginRequiredMixin, ListView):
    """List all reports with filtering and pagination"""
    model = Report
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Report.objects.all()
        
        # Filter by user's own reports unless they have permission to view all
        if not self.request.user.has_perm('reports.can_view_all_reports'):
            queryset = queryset.filter(
                Q(generated_by=self.request.user) |
                Q(shared_with=self.request.user) |
                Q(is_public=True)
            )
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        report_type = self.request.GET.get('report_type')
        if report_type:
            queryset = queryset.filter(template__report_type=report_type)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ReportFilterForm(self.request.GET)
        context['report_templates'] = ReportTemplate.objects.all()
        return context

class ReportDetailView(LoginRequiredMixin, DetailView):
    """View individual report details"""
    model = Report
    template_name = 'reports/report_detail.html'
    context_object_name = 'report'
    
    def get_object(self):
        obj = super().get_object()
        
        # Check permissions
        if not (obj.generated_by == self.request.user or
                obj.shared_with.filter(id=self.request.user.id).exists() or
                obj.is_public or
                self.request.user.has_perm('reports.can_view_all_reports')):
            raise Http404("Report not found")
        
        # Log access
        ReportAccess.objects.create(
            report=obj,
            user=self.request.user,
            action='view',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        return obj
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class ReportCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new report"""
    model = Report
    form_class = ReportForm
    template_name = 'reports/report_form.html'
    permission_required = 'reports.can_generate_reports'
    success_url = reverse_lazy('reports:report_list')
    
    def form_valid(self, form):
        form.instance.generated_by = self.request.user
        form.instance.status = 'pending'
        response = super().form_valid(form)
        
        # Start report generation in background
        self.generate_report_async(self.object)
        
        messages.success(self.request, 'Report generation started successfully.')
        return response
    
    def generate_report_async(self, report):
        """Generate report content based on template"""
        try:
            report.mark_as_started()
            
            if report.template:
                content = self.generate_report_content(report)
                summary = self.generate_report_summary(report)
                report.mark_as_completed(content=content, summary=summary)
            else:
                report.mark_as_failed('No template specified')
                
        except Exception as e:
            report.mark_as_failed(str(e))
    
    def generate_report_content(self, report):
        """Generate report content based on template type"""
        template = report.template
        
        if template.report_type == 'referral_analytics':
            return self.generate_referral_analytics(report)
        elif template.report_type == 'appointment_analytics':
            return self.generate_appointment_analytics(report)
        elif template.report_type == 'patient_demographics':
            return self.generate_patient_demographics(report)
        elif template.report_type == 'doctor_performance':
            return self.generate_doctor_performance(report)
        elif template.report_type == 'system_usage':
            return self.generate_system_usage(report)
        else:
            return 'Report content generation not implemented for this type.'
    
    def generate_referral_analytics(self, report):
        """Generate referral analytics report"""
        date_from = report.date_from or timezone.now().date() - timedelta(days=30)
        date_to = report.date_to or timezone.now().date()
        
        referrals = Referral.objects.filter(
            created_at__date__range=[date_from, date_to]
        )
        
        total_referrals = referrals.count()
        pending_referrals = referrals.filter(status='pending').count()
        accepted_referrals = referrals.filter(status='accepted').count()
        rejected_referrals = referrals.filter(status='rejected').count()
        
        content = f"""
        <h2>Referral Analytics Report</h2>
        <p>Period: {date_from} to {date_to}</p>
        
        <h3>Summary</h3>
        <ul>
            <li>Total Referrals: {total_referrals}</li>
            <li>Pending Referrals: {pending_referrals}</li>
            <li>Accepted Referrals: {accepted_referrals}</li>
            <li>Rejected Referrals: {rejected_referrals}</li>
        </ul>
        
        <h3>Acceptance Rate</h3>
        <p>{(accepted_referrals / total_referrals * 100) if total_referrals > 0 else 0:.1f}%</p>
        """
        
        return content
    
    def generate_appointment_analytics(self, report):
        """Generate appointment analytics report"""
        date_from = report.date_from or timezone.now().date() - timedelta(days=30)
        date_to = report.date_to or timezone.now().date()
        
        appointments = Appointment.objects.filter(
            created_at__date__range=[date_from, date_to]
        )
        
        total_appointments = appointments.count()
        scheduled_appointments = appointments.filter(status='scheduled').count()
        completed_appointments = appointments.filter(status='completed').count()
        cancelled_appointments = appointments.filter(status='cancelled').count()
        
        content = f"""
        <h2>Appointment Analytics Report</h2>
        <p>Period: {date_from} to {date_to}</p>
        
        <h3>Summary</h3>
        <ul>
            <li>Total Appointments: {total_appointments}</li>
            <li>Scheduled Appointments: {scheduled_appointments}</li>
            <li>Completed Appointments: {completed_appointments}</li>
            <li>Cancelled Appointments: {cancelled_appointments}</li>
        </ul>
        
        <h3>Completion Rate</h3>
        <p>{(completed_appointments / total_appointments * 100) if total_appointments > 0 else 0:.1f}%</p>
        """
        
        return content
    
    def generate_patient_demographics(self, report):
        """Generate patient demographics report"""
        patients = Patient.objects.all()
        total_patients = patients.count()
        
        # Age distribution
        today = timezone.now().date()
        age_groups = {
            '0-18': 0,
            '19-35': 0,
            '36-50': 0,
            '51-65': 0,
            '65+': 0
        }
        
        for patient in patients:
            if patient.date_of_birth:
                age = (today - patient.date_of_birth).days // 365
                if age <= 18:
                    age_groups['0-18'] += 1
                elif age <= 35:
                    age_groups['19-35'] += 1
                elif age <= 50:
                    age_groups['36-50'] += 1
                elif age <= 65:
                    age_groups['51-65'] += 1
                else:
                    age_groups['65+'] += 1
        
        content = f"""
        <h2>Patient Demographics Report</h2>
        
        <h3>Total Patients: {total_patients}</h3>
        
        <h3>Age Distribution</h3>
        <ul>
        """
        
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            content += f"<li>{age_group}: {count} ({percentage:.1f}%)</li>"
        
        content += "</ul>"
        
        return content
    
    def generate_doctor_performance(self, report):
        """Generate doctor performance report"""
        date_from = report.date_from or timezone.now().date() - timedelta(days=30)
        date_to = report.date_to or timezone.now().date()
        
        doctors = DoctorProfile.objects.all()
        
        content = f"""
        <h2>Doctor Performance Report</h2>
        <p>Period: {date_from} to {date_to}</p>
        
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr>
                <th>Doctor</th>
                <th>Referrals Received</th>
                <th>Referrals Accepted</th>
                <th>Appointments Completed</th>
                <th>Acceptance Rate</th>
            </tr>
        """
        
        for doctor in doctors:
            referrals_received = Referral.objects.filter(
                target_doctor=doctor,
                created_at__date__range=[date_from, date_to]
            ).count()
            
            referrals_accepted = Referral.objects.filter(
                target_doctor=doctor,
                status='accepted',
                created_at__date__range=[date_from, date_to]
            ).count()
            
            appointments_completed = Appointment.objects.filter(
                doctor=doctor,
                status='completed',
                created_at__date__range=[date_from, date_to]
            ).count()
            
            acceptance_rate = (referrals_accepted / referrals_received * 100) if referrals_received > 0 else 0
            
            content += f"""
            <tr>
                <td>{doctor.user.get_full_name()}</td>
                <td>{referrals_received}</td>
                <td>{referrals_accepted}</td>
                <td>{appointments_completed}</td>
                <td>{acceptance_rate:.1f}%</td>
            </tr>
            """
        
        content += "</table>"
        
        return content
    
    def generate_system_usage(self, report):
        """Generate system usage report"""
        date_from = report.date_from or timezone.now().date() - timedelta(days=7)
        date_to = report.date_to or timezone.now().date()
        
        usage_data = SystemUsageAnalytics.objects.filter(
            date__range=[date_from, date_to]
        ).order_by('date')
        
        content = f"""
        <h2>System Usage Report</h2>
        <p>Period: {date_from} to {date_to}</p>
        
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr>
                <th>Date</th>
                <th>Active Users</th>
                <th>Total Sessions</th>
                <th>Page Views</th>
                <th>Avg Response Time</th>
            </tr>
        """
        
        for data in usage_data:
            content += f"""
            <tr>
                <td>{data.date}</td>
                <td>{data.active_users}</td>
                <td>{data.total_sessions}</td>
                <td>{data.page_views}</td>
                <td>{data.avg_response_time:.2f}s</td>
            </tr>
            """
        
        content += "</table>"
        
        return content
    
    def generate_report_summary(self, report):
        """Generate summary statistics for the report"""
        return {
            'generated_at': timezone.now().isoformat(),
            'parameters': report.parameters,
            'date_range': {
                'from': report.date_from.isoformat() if report.date_from else None,
                'to': report.date_to.isoformat() if report.date_to else None
            }
        }

class ReportExportView(LoginRequiredMixin, View):
    """Export reports in different formats"""
    
    def get(self, request, pk, format):
        report = get_object_or_404(Report, pk=pk)
        
        # Check permissions
        if not (report.generated_by == request.user or
                report.shared_with.filter(id=request.user.id).exists() or
                report.is_public or
                request.user.has_perm('reports.can_view_all_reports')):
            raise Http404("Report not found")
        
        # Log access
        ReportAccess.objects.create(
            report=report,
            user=request.user,
            action='export',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        if format == 'pdf':
            return self.export_pdf(report)
        elif format == 'csv':
            return self.export_csv(report)
        elif format == 'excel':
            return self.export_excel(report)
        elif format == 'json':
            return self.export_json(report)
        else:
            return JsonResponse({'error': 'Unsupported format'}, status=400)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def export_pdf(self, report):
        """Export report as PDF"""
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report.title}.pdf"'
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
        )
        
        # Content
        story = []
        story.append(Paragraph(report.title, title_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Generated: {report.created_at.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Paragraph(f"Generated by: {report.generated_by.get_full_name()}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Add report content (simplified - would need proper HTML parsing)
        content_lines = report.content.split('\n')
        for line in content_lines:
            if line.strip():
                story.append(Paragraph(line, styles['Normal']))
                story.append(Spacer(1, 6))
        
        doc.build(story)
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
    
    def export_csv(self, report):
        """Export report as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report.title}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Report Title', 'Generated Date', 'Generated By', 'Status'])
        writer.writerow([
            report.title,
            report.created_at.strftime('%Y-%m-%d %H:%M'),
            report.generated_by.get_full_name(),
            report.status
        ])
        
        # Add content (simplified)
        writer.writerow([])
        writer.writerow(['Content'])
        content_lines = report.content.split('\n')
        for line in content_lines:
            if line.strip():
                writer.writerow([line.strip()])
        
        return response
    
    def export_excel(self, report):
        """Export report as Excel"""
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{report.title}.xlsx"'
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Report')
        
        # Formats
        title_format = workbook.add_format({'bold': True, 'font_size': 16})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
        
        # Write report info
        worksheet.write('A1', report.title, title_format)
        worksheet.write('A3', 'Generated:', header_format)
        worksheet.write('B3', report.created_at.strftime('%Y-%m-%d %H:%M'))
        worksheet.write('A4', 'Generated by:', header_format)
        worksheet.write('B4', report.generated_by.get_full_name())
        worksheet.write('A5', 'Status:', header_format)
        worksheet.write('B5', report.status)
        
        # Write content
        worksheet.write('A7', 'Content:', header_format)
        content_lines = report.content.split('\n')
        row = 8
        for line in content_lines:
            if line.strip():
                worksheet.write(f'A{row}', line.strip())
                row += 1
        
        workbook.close()
        output.seek(0)
        response.write(output.read())
        
        return response
    
    def export_json(self, report):
        """Export report as JSON"""
        data = {
            'title': report.title,
            'generated_at': report.created_at.isoformat(),
            'generated_by': report.generated_by.get_full_name(),
            'status': report.status,
            'content': report.content,
            'summary': report.summary,
            'parameters': report.parameters
        }
        
        response = JsonResponse(data, json_dumps_params={'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="{report.title}.json"'
        
        return response

class AnalyticsView(LoginRequiredMixin, View):
    """Analytics dashboard with charts and metrics"""
    
    def get(self, request):
        # Get date range from request
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if not date_from:
            date_from = timezone.now().date() - timedelta(days=30)
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        
        if not date_to:
            date_to = timezone.now().date()
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        # Get analytics data
        referral_analytics = ReferralAnalytics.objects.filter(
            date__range=[date_from, date_to]
        ).order_by('date')
        
        appointment_analytics = AppointmentAnalytics.objects.filter(
            date__range=[date_from, date_to]
        ).order_by('date')
        
        system_usage = SystemUsageAnalytics.objects.filter(
            date__range=[date_from, date_to]
        ).order_by('date')
        
        # Prepare chart data
        chart_data = {
            'referrals': {
                'dates': [item.date.strftime('%Y-%m-%d') for item in referral_analytics],
                'total': [item.total_referrals for item in referral_analytics],
                'accepted': [item.accepted_referrals for item in referral_analytics],
                'rejected': [item.rejected_referrals for item in referral_analytics],
            },
            'appointments': {
                'dates': [item.date.strftime('%Y-%m-%d') for item in appointment_analytics],
                'total': [item.total_appointments for item in appointment_analytics],
                'completed': [item.completed_appointments for item in appointment_analytics],
                'cancelled': [item.cancelled_appointments for item in appointment_analytics],
            },
            'system_usage': {
                'dates': [item.date.strftime('%Y-%m-%d') for item in system_usage],
                'active_users': [item.active_users for item in system_usage],
                'sessions': [item.total_sessions for item in system_usage],
                'page_views': [item.page_views for item in system_usage],
            }
        }
        
        context = {
            'date_from': date_from,
            'date_to': date_to,
            'chart_data': json.dumps(chart_data),
            'referral_analytics': referral_analytics,
            'appointment_analytics': appointment_analytics,
            'system_usage': system_usage,
            'filter_form': AnalyticsFilterForm(request.GET)
        }
        
        return render(request, 'reports/analytics.html', context)

@login_required
def ajax_report_status(request, pk):
    """Get report generation status via AJAX"""
    try:
        report = Report.objects.get(pk=pk, generated_by=request.user)
        return JsonResponse({
            'status': report.status,
            'progress': 100 if report.status == 'completed' else 50 if report.status == 'generating' else 0,
            'error_message': report.error_message
        })
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)

@login_required
def ajax_delete_report(request, pk):
    """Delete report via AJAX"""
    if request.method == 'POST':
        try:
            report = Report.objects.get(pk=pk, generated_by=request.user)
            report.delete()
            return JsonResponse({'success': True})
        except Report.DoesNotExist:
            return JsonResponse({'error': 'Report not found'}, status=404)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def ajax_share_report(request, pk):
    """Share report with other users via AJAX"""
    if request.method == 'POST':
        try:
            report = Report.objects.get(pk=pk, generated_by=request.user)
            user_ids = request.POST.getlist('user_ids')
            
            # Clear existing shares and add new ones
            report.shared_with.clear()
            for user_id in user_ids:
                try:
                    from django.contrib.auth.models import User
                    user = User.objects.get(id=user_id)
                    report.shared_with.add(user)
                except User.DoesNotExist:
                    continue
            
            return JsonResponse({'success': True})
        except Report.DoesNotExist:
            return JsonResponse({'error': 'Report not found'}, status=404)
    return JsonResponse({'error': 'Invalid method'}, status=405)

class ComplianceReportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generate compliance reports"""
    permission_required = 'reports.can_generate_reports'
    
    def get(self, request):
        form = ComplianceReportForm()
        recent_reports = ComplianceReport.objects.order_by('-created_at')[:10]
        
        context = {
            'form': form,
            'recent_reports': recent_reports
        }
        
        return render(request, 'reports/compliance.html', context)
    
    def post(self, request):
        form = ComplianceReportForm(request.POST)
        
        if form.is_valid():
            compliance_report = form.save(commit=False)
            compliance_report.generated_by = request.user
            compliance_report.save()
            
            # Generate compliance data
            self.generate_compliance_data(compliance_report)
            
            messages.success(request, 'Compliance report generated successfully.')
            return redirect('reports:compliance_detail', pk=compliance_report.pk)
        
        recent_reports = ComplianceReport.objects.order_by('-created_at')[:10]
        context = {
            'form': form,
            'recent_reports': recent_reports
        }
        
        return render(request, 'reports/compliance.html', context)
    
    def generate_compliance_data(self, compliance_report):
        """Generate compliance data based on report type"""
        # This would contain actual compliance checking logic
        # For now, we'll create sample data
        
        compliance_report.total_events = 1000
        compliance_report.compliant_events = 950
        compliance_report.non_compliant_events = 50
        compliance_report.compliance_score = 95.0
        compliance_report.risk_level = 'low'
        
        compliance_report.findings = [
            {'type': 'info', 'message': 'All user access logs are properly maintained'},
            {'type': 'warning', 'message': '5% of data access events lack proper documentation'},
            {'type': 'success', 'message': 'Encryption standards are fully compliant'}
        ]
        
        compliance_report.recommendations = [
            'Implement automated documentation for all data access events',
            'Conduct quarterly compliance training for all staff',
            'Review and update data retention policies'
        ]
        
        compliance_report.save()

class ReportTemplateListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List and manage report templates"""
    model = ReportTemplate
    template_name = 'reports/template_list.html'
    context_object_name = 'templates'
    permission_required = 'reports.can_generate_reports'
    paginate_by = 20

class ReportTemplateCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new report template"""
    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = 'reports/template_form.html'
    permission_required = 'reports.can_generate_reports'
    success_url = reverse_lazy('reports:template_list')

class ReportScheduleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List and manage scheduled reports"""
    model = ReportSchedule
    template_name = 'reports/schedule_list.html'
    context_object_name = 'schedules'
    permission_required = 'reports.can_schedule_reports'
    paginate_by = 20

class ReportScheduleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new report schedule"""
    model = ReportSchedule
    form_class = ReportScheduleForm
    template_name = 'reports/schedule_form.html'
    permission_required = 'reports.can_schedule_reports'
    success_url = reverse_lazy('reports:schedule_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Calculate next run time
        self.object.calculate_next_run()
        return response