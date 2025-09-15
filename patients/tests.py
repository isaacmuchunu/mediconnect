from django.test import TestCase
from .models import PatientHistory
from django.urls import reverse

class PatientHistoryModelTests(TestCase):

    def setUp(self):
        self.patient = PatientHistory.objects.create(
            user_id=1,
            allergies='None',
            medications='None'
        )

    def test_patient_history_creation(self):
        self.assertEqual(self.patient.user_id, 1)
        self.assertEqual(self.patient.allergies, 'None')
        self.assertEqual(self.patient.medications, 'None')

class PatientHistoryViewTests(TestCase):

    def setUp(self):
        self.patient = PatientHistory.objects.create(
            user_id=1,
            allergies='None',
            medications='None'
        )

    def test_patient_dashboard_view(self):
        response = self.client.get(reverse('patients:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Patient Dashboard')

    def test_history_update_view(self):
        response = self.client.post(reverse('patients:history_update'), {
            'allergies': 'Peanuts',
            'medications': 'Ibuprofen'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful update
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.allergies, 'Peanuts')
        self.assertEqual(self.patient.medications, 'Ibuprofen')