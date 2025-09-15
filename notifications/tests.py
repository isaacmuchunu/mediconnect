from django.test import TestCase
from .models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.notification = Notification.objects.create(
            user=self.user,
            message='Test notification message',
            type='email'
        )

    def test_notification_creation(self):
        self.assertEqual(self.notification.user, self.user)
        self.assertEqual(self.notification.message, 'Test notification message')
        self.assertEqual(self.notification.type, 'email')

    def test_str_method(self):
        self.assertEqual(str(self.notification), f'Notification for {self.user.username}: {self.notification.message}')