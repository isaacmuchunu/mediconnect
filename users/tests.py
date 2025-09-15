from django.test import TestCase
from django.urls import reverse
from .models import User

class UserTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword',
            first_name='Test',
            last_name='User'
        )

    def test_user_creation(self):
        self.assertEqual(self.user.email, 'testuser@example.com')
        self.assertTrue(self.user.check_password('testpassword'))

    def test_user_login(self):
        response = self.client.post(reverse('login'), {
            'email': 'testuser@example.com',
            'password': 'testpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome')

    def test_user_profile_update(self):
        self.client.login(email='testuser@example.com', password='testpassword')
        response = self.client.post(reverse('profile_update'), {
            'first_name': 'Updated',
            'last_name': 'User'
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'User')

    def test_password_reset(self):
        response = self.client.post(reverse('password_reset'), {
            'email': 'testuser@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password reset email sent')