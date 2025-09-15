from django import forms
from django.contrib.auth import get_user_model  # ✅ Changed this line
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Report, ReportTemplate, ReportSchedule, ComplianceReport
)
from patients.models import Patient
from doctors.models import DoctorProfile

User = get_user_model()  # ✅ Added this line

class ReportForm(forms.ModelForm):
    """Form for creating and editing reports"""
    
    class Meta:
        model = Report
        fields = [
            'title', 'template', 'date_from', 'date_to', 
            'parameters', 'is_public', 'shared_with'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter report title'
            }),
            'template': forms.Select(attrs={
                'class': 'form-control'
            }),
            'date_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_to': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'parameters': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter report parameters as JSON'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'shared_with': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 5
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shared_with'].queryset = User.objects.filter(is_active=True)
        self.fields['shared_with'].required = False
        self.fields['template'].queryset = ReportTemplate.objects.filter(is_active=True)
        
        # Set default date range (last 30 days)
        if not self.instance.pk:
            self.fields['date_to'].initial = timezone.now().date()
            self.fields['date_from'].initial = timezone.now().date() - timedelta(days=30)
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to:
            if date_from > date_to:
                raise ValidationError('Start date must be before end date.')
            
            if date_to > timezone.now().date():
                raise ValidationError('End date cannot be in the future.')
            
            # Limit date range to 1 year
            if (date_to - date_from).days > 365:
                raise ValidationError('Date range cannot exceed 365 days.')
        
        return cleaned_data

class ReportTemplateForm(forms.ModelForm):
    """Form for creating and editing report templates"""
    
    class Meta:
        model = ReportTemplate
        fields = [
            'name', 'description', 'report_type', 'query_template',
            'parameters', 'frequency', 'auto_generate', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter template name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter template description'
            }),
            'report_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'query_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enter SQL query template for the report'
            }),
            'parameters': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter parameters as JSON'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'auto_generate': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

class ReportFilterForm(forms.Form):
    """Form for filtering reports in list view"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    REPORT_TYPE_CHOICES = [
        ('', 'All Types'),
        ('referral_analytics', 'Referral Analytics'),
        ('appointment_analytics', 'Appointment Analytics'),
        ('patient_demographics', 'Patient Demographics'),
        ('doctor_performance', 'Doctor Performance'),
        ('system_usage', 'System Usage'),
        ('compliance', 'Compliance'),
        ('financial', 'Financial'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search reports...'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

class ReportScheduleForm(forms.ModelForm):
    """Form for creating and editing report schedules"""
    
    class Meta:
        model = ReportSchedule
        fields = [
            'name', 'template', 'frequency', 'time_of_day',
            'day_of_week', 'day_of_month', 'default_parameters',
            'recipients', 'is_enabled'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter schedule name'
            }),
            'template': forms.Select(attrs={
                'class': 'form-control'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'time_of_day': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'day_of_week': forms.Select(attrs={
                'class': 'form-control'
            }),
            'day_of_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 31
            }),
            'default_parameters': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter default parameters as JSON'
            }),
            'recipients': forms.SelectMultiple(attrs={
                'class': 'form-control'
            }),
            'is_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['template'].queryset = ReportTemplate.objects.filter(is_active=True)
        self.fields['day_of_week'].required = False
        self.fields['day_of_month'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        frequency = cleaned_data.get('frequency')
        day_of_week = cleaned_data.get('day_of_week')
        day_of_month = cleaned_data.get('day_of_month')
        
        if frequency == 'weekly' and not day_of_week:
            raise ValidationError('Day of week is required for weekly schedules.')
        
        if frequency == 'monthly' and not day_of_month:
            raise ValidationError('Day of month is required for monthly schedules.')
        
        return cleaned_data

class ComplianceReportForm(forms.ModelForm):
    """Form for creating compliance reports"""
    
    class Meta:
        model = ComplianceReport
        fields = [
            'report_type', 'period_start', 'period_end',
            'findings', 'recommendations'
        ]
        widgets = {
            'report_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'period_start': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'period_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'findings': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter findings as JSON'
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter recommendations as JSON'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date range (last 30 days)
        if not self.instance.pk:
            self.fields['period_end'].initial = timezone.now()
            self.fields['period_start'].initial = timezone.now() - timedelta(days=30)
    
    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')
        
        if period_start and period_end:
            if period_start > period_end:
                raise ValidationError('Start date must be before end date.')
            
            if period_end > timezone.now():
                raise ValidationError('End date cannot be in the future.')
        
        return cleaned_data

class AnalyticsFilterForm(forms.Form):
    """Form for filtering analytics data"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    metric_type = forms.ChoiceField(
        choices=[
            ('', 'All Metrics'),
            ('referrals', 'Referrals'),
            ('appointments', 'Appointments'),
            ('system_usage', 'System Usage'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date range (last 30 days)
        if not self.data:
            self.fields['date_to'].initial = timezone.now().date()
            self.fields['date_from'].initial = timezone.now().date() - timedelta(days=30)

class BulkReportForm(forms.Form):
    """Form for generating multiple reports at once"""
    
    templates = forms.ModelMultipleChoiceField(
        queryset=ReportTemplate.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=True
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    email_when_complete = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date range (last 30 days)
        if not self.data:
            self.fields['date_to'].initial = timezone.now().date()
            self.fields['date_from'].initial = timezone.now().date() - timedelta(days=30)
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        templates = cleaned_data.get('templates')
        
        if date_from and date_to:
            if date_from > date_to:
                raise ValidationError('Start date must be before end date.')
            
            if date_to > timezone.now().date():
                raise ValidationError('End date cannot be in the future.')
        
        if not templates:
            raise ValidationError('At least one template must be selected.')
        
        return cleaned_data

class ReportShareForm(forms.Form):
    """Form for sharing reports with other users"""
    
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False
    )
    
    make_public = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Make this report visible to all users'
    )
    
    send_notification = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Send notification to shared users'
    )
    
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional message to include with the shared report'
        })
    )

class ReportExportForm(forms.Form):
    """Form for configuring report exports"""
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]
    
    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    include_charts = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Include charts and visualizations (PDF only)'
    )
    
    include_raw_data = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Include raw data tables'
    )
    
    email_export = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Email the exported report'
    )
    
    email_address = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email_export = cleaned_data.get('email_export')
        email_address = cleaned_data.get('email_address')
        
        if email_export and not email_address:
            raise ValidationError('Email address is required when email export is selected.')
        
        return cleaned_data