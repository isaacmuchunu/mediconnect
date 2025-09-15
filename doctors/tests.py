from django.test import TestCase
from .models import DoctorProfile

class DoctorProfileModelTest(TestCase):

    def setUp(self):
        self.doctor = DoctorProfile.objects.create(
            name="Dr. John Doe",
            license_number="123456",
            specialties="Cardiology",
            hospital_affiliation="General Hospital"
        )

    def test_doctor_creation(self):
        self.assertEqual(self.doctor.name, "Dr. John Doe")
        self.assertEqual(self.doctor.license_number, "123456")
        self.assertEqual(self.doctor.specialties, "Cardiology")
        self.assertEqual(self.doctor.hospital_affiliation, "General Hospital")

    def test_doctor_str(self):
        self.assertEqual(str(self.doctor), "Dr. John Doe")