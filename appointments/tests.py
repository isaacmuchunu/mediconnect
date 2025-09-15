from django.test import TestCase
from django.urls import reverse
from .models import Appointment
from referrals.models import Referral
from users.models import User

class AppointmentModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            email='testuser@example.com'
        )
        self.referral = Referral.objects.create(
            patient=self.user,
            referring_doctor=self.user,
            target_doctor=self.user,
            status='Draft',
            notes='Test referral'
        )
        self.appointment = Appointment.objects.create(
            referral=self.referral,
            date_time='2025-01-01 10:00:00',
            status='Scheduled'
        )

    def test_appointment_creation(self):
        self.assertEqual(self.appointment.referral, self.referral)
        self.assertEqual(self.appointment.date_time.strftime('%Y-%m-%d %H:%M:%S'), '2025-01-01 10:00:00')
        self.assertEqual(self.appointment.status, 'Scheduled')

class AppointmentViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            email='testuser@example.com'
        )
        self.client.login(username='testuser', password='testpassword')

    def test_appointment_list_view(self):
        response = self.client.get(reverse('appointments:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'appointments/list.html')

    def test_book_appointment_view(self):
        referral = Referral.objects.create(
            patient=self.user,
            referring_doctor=self.user,
            target_doctor=self.user,
            status='Draft',
            notes='Test referral'
        )
        response = self.client.post(reverse('appointments:book', args=[referral.id]), {
            'date_time': '2025-01-01 10:00:00'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful booking
        self.assertTrue(Appointment.objects.filter(referral=referral).exists())