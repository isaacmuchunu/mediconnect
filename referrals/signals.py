from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Referral
from notifications.tasks import send_referral_notification

@receiver(post_save, sender=Referral)
def handle_referral_save(sender, instance, created, **kwargs):
    if created:
        # Send notification when a new referral is created
        send_referral_notification.delay(instance.id)