from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_notification_email(user_email, subject, message):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )

@shared_task
def send_sms_notification(phone_number, message):
    # Placeholder for SMS sending logic
    pass

@shared_task
def notify_user_of_referral(referral_id):
    # Logic to notify user about a new referral
    pass

@shared_task
def notify_user_of_appointment(appointment_id):
    # Logic to notify user about an appointment
    pass