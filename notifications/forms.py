from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import (
    Notification, NotificationPreference, NotificationTemplate,
    NotificationLog
)

User = get_user_model()

class NotificationForm(forms.ModelForm):
    """Form for creating notifications"""
    
    class Meta:
        model = Notification
        fields = [
            'user', 'title', 'message', 'priority', 'template',
            'metadata', 'scheduled_for'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter notification title'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter notification message'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            }),
            'user': forms.Select(attrs={
                'class': 'form-control'
            }),
            'template': forms.Select(attrs={
                'class': 'form-control'
            }),
            'metadata': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter JSON metadata (optional)'
            }),
            'scheduled_for': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(is_active=True)
        self.fields['template'].queryset = NotificationTemplate.objects.filter(
            is_active=True
        )
        self.fields['template'].required = False
        self.fields['metadata'].required = False
        self.fields['scheduled_for'].required = False

class NotificationPreferenceForm(forms.ModelForm):
    """Form for managing notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_notifications', 'sms_notifications', 'push_notifications',
            'referral_notifications', 'appointment_notifications', 
            'ambulance_notifications', 'system_notifications', 
            'emergency_notifications', 'quiet_hours_start', 'quiet_hours_end', 
            'weekend_notifications', 'digest_frequency'
        ]
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sms_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'push_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'referral_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'appointment_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'ambulance_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'system_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'emergency_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'weekend_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'digest_frequency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quiet_hours_start': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'quiet_hours_end': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text
        self.fields['email_notifications'].help_text = 'Receive notifications via email'
        self.fields['sms_notifications'].help_text = 'Receive notifications via SMS'
        self.fields['push_notifications'].help_text = 'Receive push notifications in browser'
        self.fields['referral_notifications'].help_text = 'Notifications about referrals'
        self.fields['appointment_notifications'].help_text = 'Notifications about appointments'
        self.fields['ambulance_notifications'].help_text = 'Notifications about ambulance requests'
        self.fields['system_notifications'].help_text = 'System and security notifications'
        self.fields['emergency_notifications'].help_text = 'Emergency notifications'
        self.fields['weekend_notifications'].help_text = 'Receive notifications on weekends'
        self.fields['digest_frequency'].help_text = 'How often to receive digest notifications'
        self.fields['quiet_hours_start'].help_text = 'Start of quiet hours (no notifications)'
        self.fields['quiet_hours_end'].help_text = 'End of quiet hours'

class NotificationTemplateForm(forms.ModelForm):
    """Form for creating and editing notification templates"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'notification_type', 'subject_template', 'message_template',
            'email_template', 'sms_template', 'is_email_enabled', 
            'is_sms_enabled', 'is_push_enabled', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter template name'
            }),
            'notification_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'subject_template': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter subject template with variables like {patient_name}'
            }),
            'message_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter message template with variables'
            }),
            'email_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Enter email template (HTML allowed)'
            }),
            'sms_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter SMS template (160 chars max)'
            }),
            'is_email_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_sms_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_push_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notification_type'].help_text = 'Type of notification this template is for'
        self.fields['subject_template'].help_text = 'Use variables like {patient_name}, {doctor_name}, {date}'
        self.fields['message_template'].help_text = 'Use variables like {patient_name}, {doctor_name}, {date}'

class BulkNotificationForm(forms.Form):
    """Form for sending bulk notifications"""
    
    RECIPIENT_CHOICES = [
        ('all_users', 'All Users'),
        ('doctors', 'All Doctors'),
        ('patients', 'All Patients'),
        ('staff', 'Staff Members'),
        ('custom', 'Custom Selection')
    ]
    
    recipients = forms.ChoiceField(
        choices=RECIPIENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    custom_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': '10'
        })
    )
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter notification title'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter notification message'
        })
    )
    
    priority = forms.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        initial='medium',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    scheduled_for = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['custom_users'].help_text = 'Select specific users (only when Custom Selection is chosen)'
        self.fields['scheduled_for'].help_text = 'Leave empty to send immediately'
    
    def clean(self):
        cleaned_data = super().clean()
        recipients = cleaned_data.get('recipients')
        custom_users = cleaned_data.get('custom_users')
        
        if recipients == 'custom' and not custom_users:
            raise forms.ValidationError(
                'Please select at least one user when using custom selection.'
            )
        
        return cleaned_data

class NotificationFilterForm(forms.Form):
    """Form for filtering notifications"""
    
    STATUS_CHOICES = [
        ('', 'All'),
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ]
    
    PRIORITY_CHOICES = [
        ('', 'All Priorities')
    ] + Notification.PRIORITY_CHOICES
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search notifications...'
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
    
    notification_type = forms.ModelChoiceField(
        queryset=NotificationTemplate.objects.filter(is_active=True),
        required=False,
        empty_label='All Types',
        widget=forms.Select(attrs={'class': 'form-control'})
    )