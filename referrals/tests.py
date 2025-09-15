from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta

from .models import Referral, ReferralAttachment, ReferralStatusHistory, ReferralTemplate
from patients.models import Patient
from doctors.models import DoctorProfile, Hospital, Specialty

User = get_user_model()

class ReferralModelTest(TestCase):

    def setUp(self):
        self.patient = Patient.objects.create(
            name="John Doe",
            age=30,
            gender="M",
            contact="1234567890",
            address="123 Main St"
        )
        self.referring_doctor = Doctor.objects.create(
            name="Dr. Smith",
            specialty="Cardiology",
            hospital_affiliation="General Hospital"
        )
        self.target_doctor = Doctor.objects.create(
            name="Dr. Jones",
            specialty="Neurology",
            hospital_affiliation="Specialty Clinic"
        )
        self.referral = Referral.objects.create(
            patient=self.patient,
            referring_doctor=self.referring_doctor,
            target_doctor=self.target_doctor,
            status="Draft",
            notes="Need a follow-up consultation."
        )

    def test_referral_creation(self):
        self.assertEqual(self.referral.patient.name, "John Doe")
        self.assertEqual(self.referral.referring_doctor.name, "Dr. Smith")
        self.assertEqual(self.referral.target_doctor.name, "Dr. Jones")
        self.assertEqual(self.referral.status, "Draft")
        self.assertEqual(self.referral.notes, "Need a follow-up consultation.")

    def test_referral_str(self):
        self.assertEqual(str(self.referral), f"Referral from {self.referring_doctor.name} to {self.target_doctor.name} for {self.patient.name}")

    def test_referral_status_update(self):
        self.referral.status = "Sent"
        self.referral.save()
        self.assertEqual(self.referral.status, "Sent")