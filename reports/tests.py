from django.test import TestCase
from .models import Report

class ReportModelTest(TestCase):
    def setUp(self):
        self.report = Report.objects.create(
            title="Test Report",
            content="This is a test report.",
            created_by="admin"
        )

    def test_report_creation(self):
        self.assertEqual(self.report.title, "Test Report")
        self.assertEqual(self.report.content, "This is a test report.")
        self.assertEqual(self.report.created_by, "admin")

    def test_report_str(self):
        self.assertEqual(str(self.report), "Test Report")

    def test_report_fields(self):
        self.assertTrue(hasattr(self.report, 'created_at'))
        self.assertTrue(hasattr(self.report, 'updated_at'))