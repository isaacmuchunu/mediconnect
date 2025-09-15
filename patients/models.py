from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_cryptography.fields import encrypt
from datetime import date, timedelta
import uuid

User = get_user_model()

def validate_birth_date(value):
    """Validate that birth date is reasonable"""
    if value > date.today():
        raise ValidationError(_('Birth date cannot be in the future'))
    if value < date.today() - timedelta(days=150*365):  # 150 years ago
        raise ValidationError(_('Birth date seems unrealistic'))

def validate_phone_number(value):
    """Validate phone number format"""
    if not value.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
        raise ValidationError(_('Phone number contains invalid characters'))

class BaseModel(models.Model):
    """Abstract base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        abstract = True

class Patient(BaseModel):
    """Comprehensive patient model with demographics and identifiers"""
    
    # Core Identity
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient')
    patient_id = models.CharField(_('Patient ID'), max_length=20, unique=True, 
                                 help_text=_('Unique hospital identifier'))
    
    # Personal Information
    first_name = models.CharField(_('First Name'), max_length=100)
    middle_name = models.CharField(_('Middle Name'), max_length=100, blank=True)
    last_name = models.CharField(_('Last Name'), max_length=100)
    preferred_name = models.CharField(_('Preferred Name'), max_length=100, blank=True)
    
    date_of_birth = models.DateField(_('Date of Birth'), validators=[validate_birth_date])
    
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
        ('NB', _('Non-binary')),
        ('O', _('Other')),
        ('P', _('Prefer not to say'))
    ]
    gender = models.CharField(_('Gender'), max_length=2, choices=GENDER_CHOICES)
    
    MARITAL_STATUS_CHOICES = [
        ('S', _('Single')),
        ('M', _('Married')),
        ('D', _('Divorced')),
        ('W', _('Widowed')),
        ('P', _('Partnership')),
        ('O', _('Other'))
    ]
    marital_status = models.CharField(_('Marital Status'), max_length=1, 
                                    choices=MARITAL_STATUS_CHOICES, blank=True)
    
    # Contact Information (Encrypted)
    phone_primary = encrypt(models.CharField(_('Primary Phone'), max_length=20, 
                                           validators=[validate_phone_number]))
    phone_secondary = encrypt(models.CharField(_('Secondary Phone'), max_length=20, 
                                             validators=[validate_phone_number], blank=True))
    email = encrypt(models.EmailField(_('Email Address')))
    
    # Address Information (Encrypted)
    address_line1 = encrypt(models.CharField(_('Address Line 1'), max_length=255))
    address_line2 = encrypt(models.CharField(_('Address Line 2'), max_length=255, blank=True))
    city = encrypt(models.CharField(_('City'), max_length=100))
    state_province = encrypt(models.CharField(_('State/Province'), max_length=100))
    postal_code = encrypt(models.CharField(_('Postal Code'), max_length=20))
    country = models.CharField(_('Country'), max_length=100, default='Kenya')
    
    # Emergency Contacts (Encrypted)
    emergency_contact_1_name = encrypt(models.CharField(_('Emergency Contact 1 Name'), max_length=255))
    emergency_contact_1_phone = encrypt(models.CharField(_('Emergency Contact 1 Phone'), max_length=20,
                                                       validators=[validate_phone_number]))
    emergency_contact_1_relationship = models.CharField(_('Relationship'), max_length=50)
    
    emergency_contact_2_name = encrypt(models.CharField(_('Emergency Contact 2 Name'), max_length=255, blank=True))
    emergency_contact_2_phone = encrypt(models.CharField(_('Emergency Contact 2 Phone'), max_length=20,
                                                       validators=[validate_phone_number], blank=True))
    emergency_contact_2_relationship = models.CharField(_('Relationship'), max_length=50, blank=True)
    
    # Insurance Information (Encrypted)
    insurance_provider = encrypt(models.CharField(_('Insurance Provider'), max_length=255, blank=True))
    insurance_policy_number = encrypt(models.CharField(_('Policy Number'), max_length=100, blank=True))
    insurance_group_number = encrypt(models.CharField(_('Group Number'), max_length=100, blank=True))

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    # Clinical Information
    blood_type = models.CharField(_('Blood Type'), max_length=5, blank=True,
                                choices=[('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
                                       ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')])
    
    # Preferences
    preferred_language = models.CharField(_('Preferred Language'), max_length=50, default='English')
    religion = models.CharField(_('Religion'), max_length=100, blank=True)
    
    # System Fields
    registration_date = models.DateTimeField(_('Registration Date'), auto_now_add=True)
    last_visit = models.DateTimeField(_('Last Visit'), null=True, blank=True)
    is_vip = models.BooleanField(_('VIP Patient'), default=False)
    notes = models.TextField(_('Administrative Notes'), blank=True)
    
    @property
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.middle_name} {self.last_name}".strip()
    
    @property
    def age(self):
        """Calculate patient age"""
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def __str__(self):
        return f"{self.patient_id} - {self.full_name}"
    
    class Meta:
        verbose_name = _('Patient')
        verbose_name_plural = _('Patients')
        indexes = [
            models.Index(fields=['patient_id']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['date_of_birth']),
            models.Index(fields=['registration_date']),
        ]

class MedicalHistory(BaseModel):
    """Comprehensive medical history with encrypted sensitive fields"""
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='medical_history')
    
    # Allergies and Reactions
    allergies = encrypt(models.TextField(_('Known Allergies'), blank=True,
                                       help_text=_('List all known allergies and reactions')))
    allergy_severity = models.CharField(_('Allergy Severity'), max_length=20, blank=True,
                                      choices=[('mild', _('Mild')), ('moderate', _('Moderate')), 
                                             ('severe', _('Severe')), ('life_threatening', _('Life Threatening'))])
    
    # Medical Conditions
    chronic_conditions = encrypt(models.TextField(_('Chronic Conditions'), blank=True))
    past_illnesses = encrypt(models.TextField(_('Past Illnesses'), blank=True))
    mental_health_history = encrypt(models.TextField(_('Mental Health History'), blank=True))
    
    # Medications
    current_medications = encrypt(models.TextField(_('Current Medications'), blank=True))
    medication_allergies = encrypt(models.TextField(_('Medication Allergies'), blank=True))
    
    # Surgical History
    surgeries = encrypt(models.TextField(_('Past Surgeries'), blank=True))
    surgical_complications = encrypt(models.TextField(_('Surgical Complications'), blank=True))
    
    # Family History
    family_history = encrypt(models.TextField(_('Family Medical History'), blank=True))
    genetic_conditions = encrypt(models.TextField(_('Known Genetic Conditions'), blank=True))
    
    # Lifestyle Factors
    SMOKING_CHOICES = [
        ('never', _('Never')),
        ('former', _('Former smoker')),
        ('current', _('Current smoker')),
        ('social', _('Social smoker'))
    ]
    smoking_status = models.CharField(_('Smoking Status'), max_length=10, 
                                    choices=SMOKING_CHOICES, default='never')
    
    ALCOHOL_CHOICES = [
        ('never', _('Never')),
        ('rarely', _('Rarely')),
        ('moderate', _('Moderate')),
        ('heavy', _('Heavy'))
    ]
    alcohol_consumption = models.CharField(_('Alcohol Consumption'), max_length=10,
                                         choices=ALCOHOL_CHOICES, default='never')
    
    exercise_frequency = models.CharField(_('Exercise Frequency'), max_length=50, blank=True)
    diet_restrictions = encrypt(models.TextField(_('Dietary Restrictions'), blank=True))
    
    # Additional Information
    additional_notes = encrypt(models.TextField(_('Additional Notes'), blank=True))
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                       related_name='medical_history_updates')
    
    def __str__(self):
        return f"Medical History - {self.patient.full_name}"
    
    class Meta:
        verbose_name = _('Medical History')
        verbose_name_plural = _('Medical Histories')

class ConsentCategory(BaseModel):
    """Categories of consent for flexible consent management"""
    name = models.CharField(_('Category Name'), max_length=100, unique=True)
    description = models.TextField(_('Description'))
    is_required = models.BooleanField(_('Required'), default=False)
    display_order = models.PositiveIntegerField(_('Display Order'), default=0)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Consent Category')
        verbose_name_plural = _('Consent Categories')
        ordering = ['display_order', 'name']

class ConsentForm(BaseModel):
    """Digital consent forms with versioning and audit trail"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='consent_forms')
    category = models.ForeignKey(ConsentCategory, on_delete=models.CASCADE, related_name='consent_forms')
    
    # Consent Details
    consent_given = models.BooleanField(_('Consent Given'), default=False)
    consent_text = models.TextField(_('Consent Text'))
    consent_version = models.CharField(_('Consent Version'), max_length=10, default='1.0')
    
    # Digital Signature Information
    signature_method = models.CharField(_('Signature Method'), max_length=20,
                                      choices=[('digital', _('Digital Signature')), 
                                             ('verbal', _('Verbal Consent')),
                                             ('written', _('Written Consent'))])
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    # Timing
    signed_at = models.DateTimeField(_('Signed At'))
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    revoked_at = models.DateTimeField(_('Revoked At'), null=True, blank=True)
    
    # Audit Trail
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                 related_name='signed_consents')
    witness = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='witnessed_consents')
    
    def is_valid(self):
        """Check if consent is currently valid"""
        if not self.consent_given or not self.is_active:
            return False
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
    
    def revoke_consent(self, user):
        """Revoke consent with audit trail"""
        self.revoked_at = timezone.now()
        self.is_active = False
        self.save()
        
        ConsentAuditLog.objects.create(
            consent_form=self,
            action='revoked',
            performed_by=user,
            details='Consent revoked by user'
        )
    
    def __str__(self):
        status = 'Valid' if self.is_valid() else 'Invalid'
        return f"{self.patient.full_name} - {self.category.name} ({status})"
    
    class Meta:
        verbose_name = _('Consent Form')
        verbose_name_plural = _('Consent Forms')
        unique_together = ['patient', 'category', 'consent_version']
        indexes = [
            models.Index(fields=['patient', 'category']),
            models.Index(fields=['signed_at']),
            models.Index(fields=['expires_at']),
        ]

class ConsentAuditLog(BaseModel):
    """Audit log for consent changes"""
    consent_form = models.ForeignKey(ConsentForm, on_delete=models.CASCADE, related_name='audit_logs')
    
    ACTION_CHOICES = [
        ('created', _('Created')),
        ('updated', _('Updated')),
        ('revoked', _('Revoked')),
        ('expired', _('Expired')),
        ('renewed', _('Renewed'))
    ]
    action = models.CharField(_('Action'), max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    details = models.TextField(_('Details'), blank=True)
    
    def __str__(self):
        return f"{self.consent_form.patient.full_name} - {self.action} - {self.created_at}"
    
    class Meta:
        verbose_name = _('Consent Audit Log')
        verbose_name_plural = _('Consent Audit Logs')
        ordering = ['-created_at']

class MedicalCondition(BaseModel):
    """Standardized medical conditions for better data consistency"""
    code = models.CharField(_('Condition Code'), max_length=20, unique=True,
                           help_text=_('ICD-10 or custom code'))
    name = models.CharField(_('Condition Name'), max_length=255)
    category = models.CharField(_('Category'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    is_chronic = models.BooleanField(_('Chronic Condition'), default=False)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        verbose_name = _('Medical Condition')
        verbose_name_plural = _('Medical Conditions')
        ordering = ['category', 'name']

class PatientCondition(BaseModel):
    """Link patients to their medical conditions with timeline"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='conditions')
    condition = models.ForeignKey(MedicalCondition, on_delete=models.CASCADE)
    
    diagnosed_date = models.DateField(_('Diagnosed Date'))
    resolved_date = models.DateField(_('Resolved Date'), null=True, blank=True)
    
    SEVERITY_CHOICES = [
        ('mild', _('Mild')),
        ('moderate', _('Moderate')),
        ('severe', _('Severe')),
        ('critical', _('Critical'))
    ]
    severity = models.CharField(_('Severity'), max_length=10, choices=SEVERITY_CHOICES)
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('resolved', _('Resolved')),
        ('chronic', _('Chronic')),
        ('in_remission', _('In Remission'))
    ]
    status = models.CharField(_('Status'), max_length=15, choices=STATUS_CHOICES, default='active')
    
    notes = encrypt(models.TextField(_('Clinical Notes'), blank=True))
    diagnosed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='diagnosed_conditions')
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.condition.name}"
    
    class Meta:
        verbose_name = _('Patient Condition')
        verbose_name_plural = _('Patient Conditions')
        unique_together = ['patient', 'condition', 'diagnosed_date']

class Medication(BaseModel):
    """Standardized medication database"""
    name = models.CharField(_('Medication Name'), max_length=255)
    generic_name = models.CharField(_('Generic Name'), max_length=255, blank=True)
    drug_class = models.CharField(_('Drug Class'), max_length=100)
    manufacturer = models.CharField(_('Manufacturer'), max_length=255, blank=True)
    
    # Drug Identification
    ndc_number = models.CharField(_('NDC Number'), max_length=20, blank=True, unique=True)
    dosage_forms = models.CharField(_('Dosage Forms'), max_length=255,
                                  help_text=_('e.g., tablet, capsule, injection'))
    
    # Safety Information
    contraindications = models.TextField(_('Contraindications'), blank=True)
    side_effects = models.TextField(_('Common Side Effects'), blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.generic_name})" if self.generic_name else self.name
    
    class Meta:
        verbose_name = _('Medication')
        verbose_name_plural = _('Medications')
        ordering = ['name']

class PatientMedication(BaseModel):
    """Patient's current and past medications"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medications')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    
    # Prescription Details
    dosage = models.CharField(_('Dosage'), max_length=100)
    frequency = models.CharField(_('Frequency'), max_length=100)
    route = models.CharField(_('Route of Administration'), max_length=50,
                           choices=[('oral', _('Oral')), ('injection', _('Injection')),
                                  ('topical', _('Topical')), ('inhalation', _('Inhalation')),
                                  ('other', _('Other'))])
    
    # Timeline
    start_date = models.DateField(_('Start Date'))
    end_date = models.DateField(_('End Date'), null=True, blank=True)
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('discontinued', _('Discontinued')),
        ('paused', _('Paused'))
    ]
    status = models.CharField(_('Status'), max_length=15, choices=STATUS_CHOICES, default='active')
    
    # Clinical Information
    prescribed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='prescribed_medications')
    indication = encrypt(models.TextField(_('Indication'), blank=True))
    instructions = encrypt(models.TextField(_('Special Instructions'), blank=True))
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.medication.name}"
    
    class Meta:
        verbose_name = _('Patient Medication')
        verbose_name_plural = _('Patient Medications')
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['start_date']),
        ]

class Allergy(BaseModel):
    """Patient allergies with detailed tracking"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='allergies')
    
    ALLERGEN_TYPES = [
        ('drug', _('Drug/Medication')),
        ('food', _('Food')),
        ('environmental', _('Environmental')),
        ('contact', _('Contact')),
        ('other', _('Other'))
    ]
    allergen_type = models.CharField(_('Allergen Type'), max_length=15, choices=ALLERGEN_TYPES)
    allergen_name = encrypt(models.CharField(_('Allergen Name'), max_length=255))
    
    SEVERITY_CHOICES = [
        ('mild', _('Mild')),
        ('moderate', _('Moderate')),
        ('severe', _('Severe')),
        ('anaphylaxis', _('Anaphylaxis'))
    ]
    severity = models.CharField(_('Severity'), max_length=15, choices=SEVERITY_CHOICES)
    
    # Reaction Details
    symptoms = encrypt(models.TextField(_('Symptoms'), blank=True))
    onset_date = models.DateField(_('First Reaction Date'), null=True, blank=True)
    last_reaction_date = models.DateField(_('Last Reaction Date'), null=True, blank=True)
    
    # Clinical Information
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  related_name='verified_allergies')
    verification_method = models.CharField(_('Verification Method'), max_length=50, blank=True,
                                         choices=[('patient_report', _('Patient Report')),
                                                ('clinical_test', _('Clinical Test')),
                                                ('medical_record', _('Medical Record'))])
    
    notes = encrypt(models.TextField(_('Additional Notes'), blank=True))
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.allergen_name} ({self.severity})"
    
    class Meta:
        verbose_name = _('Allergy')
        verbose_name_plural = _('Allergies')
        unique_together = ['patient', 'allergen_name']

class VitalSigns(BaseModel):
    """Patient vital signs tracking"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vital_signs')
    
    # Measurements
    height_cm = models.DecimalField(_('Height (cm)'), max_digits=5, decimal_places=1, 
                                   null=True, blank=True,
                                   validators=[MinValueValidator(30), MaxValueValidator(300)])
    weight_kg = models.DecimalField(_('Weight (kg)'), max_digits=5, decimal_places=1,
                                   null=True, blank=True,
                                   validators=[MinValueValidator(0.5), MaxValueValidator(500)])
    
    # Blood Pressure
    systolic_bp = models.PositiveIntegerField(_('Systolic BP'), null=True, blank=True,
                                            validators=[MinValueValidator(50), MaxValueValidator(300)])
    diastolic_bp = models.PositiveIntegerField(_('Diastolic BP'), null=True, blank=True,
                                             validators=[MinValueValidator(30), MaxValueValidator(200)])
    
    # Other Vitals
    heart_rate = models.PositiveIntegerField(_('Heart Rate (bpm)'), null=True, blank=True,
                                           validators=[MinValueValidator(30), MaxValueValidator(250)])
    temperature_c = models.DecimalField(_('Temperature (°C)'), max_digits=4, decimal_places=1,
                                       null=True, blank=True,
                                       validators=[MinValueValidator(30), MaxValueValidator(45)])
    respiratory_rate = models.PositiveIntegerField(_('Respiratory Rate'), null=True, blank=True,
                                                 validators=[MinValueValidator(5), MaxValueValidator(60)])
    oxygen_saturation = models.PositiveIntegerField(_('Oxygen Saturation (%)'), null=True, blank=True,
                                                   validators=[MinValueValidator(50), MaxValueValidator(100)])
    
    # Clinical Context
    measurement_date = models.DateTimeField(_('Measurement Date'), default=timezone.now)
    measured_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='vital_measurements')
    notes = models.TextField(_('Notes'), blank=True)
    
    @property
    def bmi(self):
        """Calculate BMI if height and weight are available"""
        if self.height_cm and self.weight_kg:
            height_m = float(self.height_cm) / 100
            return round(float(self.weight_kg) / (height_m ** 2), 1)
        return None
    
    def __str__(self):
        return f"{self.patient.full_name} - Vitals {self.measurement_date.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        verbose_name = _('Vital Signs')
        verbose_name_plural = _('Vital Signs')
        ordering = ['-measurement_date']
        indexes = [
            models.Index(fields=['patient', 'measurement_date']),
        ]

class DataSharingAgreement(BaseModel):
    """Data sharing agreements for referrals and partnerships"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='sharing_agreements')
    
    # Sharing Details
    SHARING_TYPES = [
        ('referral', _('Medical Referral')),
        ('emergency', _('Emergency Services')),
        ('research', _('Research Study')),
        ('insurance', _('Insurance Processing')),
        ('pharmacy', _('Pharmacy')),
        ('lab', _('Laboratory')),
        ('imaging', _('Medical Imaging')),
        ('other', _('Other'))
    ]
    sharing_type = models.CharField(_('Sharing Type'), max_length=15, choices=SHARING_TYPES)
    
    # Recipient Information
    recipient_organization = models.CharField(_('Recipient Organization'), max_length=255)
    recipient_contact = models.CharField(_('Recipient Contact'), max_length=255, blank=True)
    recipient_email = models.EmailField(_('Recipient Email'), blank=True)
    
    # Data Categories
    include_demographics = models.BooleanField(_('Include Demographics'), default=True)
    include_medical_history = models.BooleanField(_('Include Medical History'), default=False)
    include_medications = models.BooleanField(_('Include Medications'), default=False)
    include_allergies = models.BooleanField(_('Include Allergies'), default=True)
    include_vital_signs = models.BooleanField(_('Include Vital Signs'), default=False)
    include_lab_results = models.BooleanField(_('Include Lab Results'), default=False)
    
    # Agreement Terms
    purpose = models.TextField(_('Purpose of Sharing'))
    data_retention_period = models.PositiveIntegerField(_('Data Retention Period (days)'), 
                                                       default=365)
    
    # Timing
    effective_date = models.DateTimeField(_('Effective Date'), default=timezone.now)
    expiration_date = models.DateTimeField(_('Expiration Date'))
    
    # Authorization
    authorized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='authorized_sharing_agreements')
    patient_signature = models.TextField(_('Patient Digital Signature'), blank=True)
    
    def is_valid(self):
        """Check if sharing agreement is valid"""
        now = timezone.now()
        return (self.is_active and 
                self.effective_date <= now <= self.expiration_date)
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.recipient_organization} ({self.sharing_type})"
    
    class Meta:
        verbose_name = _('Data Sharing Agreement')
        verbose_name_plural = _('Data Sharing Agreements')
        indexes = [
            models.Index(fields=['patient', 'sharing_type']),
            models.Index(fields=['expiration_date']),
        ]

class PatientDocument(BaseModel):
    """Patient document management with encryption"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='documents')
    
    DOCUMENT_TYPES = [
        ('id_document', _('ID Document')),
        ('insurance_card', _('Insurance Card')),
        ('medical_report', _('Medical Report')),
        ('lab_result', _('Lab Result')),
        ('imaging_report', _('Imaging Report')),
        ('consent_form', _('Consent Form')),
        ('referral_letter', _('Referral Letter')),
        ('discharge_summary', _('Discharge Summary')),
        ('other', _('Other'))
    ]
    document_type = models.CharField(_('Document Type'), max_length=20, choices=DOCUMENT_TYPES)
    
    title = models.CharField(_('Document Title'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    
    # File Information
    file_name = encrypt(models.CharField(_('Original File Name'), max_length=255))
    file_size = models.PositiveIntegerField(_('File Size (bytes)'))
    mime_type = models.CharField(_('MIME Type'), max_length=100)
    file_hash = models.CharField(_('File Hash'), max_length=64,
                               help_text=_('SHA-256 hash for integrity verification'))
    
    # Access Control
    is_confidential = models.BooleanField(_('Confidential'), default=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='uploaded_documents')
    
    # Audit
    last_accessed = models.DateTimeField(_('Last Accessed'), null=True, blank=True)
    access_count = models.PositiveIntegerField(_('Access Count'), default=0)
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.title}"
    
    class Meta:
        verbose_name = _('Patient Document')
        verbose_name_plural = _('Patient Documents')
        indexes = [
            models.Index(fields=['patient', 'document_type']),
            models.Index(fields=['created_at']),
        ]

class DocumentAccess(BaseModel):
    """Audit trail for document access"""
    document = models.ForeignKey(PatientDocument, on_delete=models.CASCADE, related_name='access_logs')
    accessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    access_type = models.CharField(_('Access Type'), max_length=20,
                                 choices=[('view', _('View')), ('download', _('Download')),
                                        ('print', _('Print')), ('share', _('Share'))])
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    def __str__(self):
        return f"{self.document.title} - {self.access_type} by {self.accessed_by}"
    
    class Meta:
        verbose_name = _('Document Access Log')
        verbose_name_plural = _('Document Access Logs')
        ordering = ['-created_at']

class HealthcareProvider(BaseModel):
    """Healthcare providers and facilities"""
    name = models.CharField(_('Provider Name'), max_length=255)
    provider_type = models.CharField(_('Provider Type'), max_length=50,
                                   choices=[('hospital', _('Hospital')), ('clinic', _('Clinic')),
                                          ('pharmacy', _('Pharmacy')), ('laboratory', _('Laboratory')),
                                          ('imaging_center', _('Imaging Center')), ('specialist', _('Specialist')),
                                          ('emergency_service', _('Emergency Service')), ('other', _('Other'))])
    
    # Contact Information
    address = models.TextField(_('Address'))
    phone = models.CharField(_('Phone Number'), max_length=20, validators=[validate_phone_number])
    email = models.EmailField(_('Email Address'), blank=True)
    website = models.URLField(_('Website'), blank=True)
    
    # Professional Information
    license_number = models.CharField(_('License Number'), max_length=100, blank=True)
    specialties = models.TextField(_('Specialties'), blank=True)
    
    # Network Information
    is_preferred_provider = models.BooleanField(_('Preferred Provider'), default=False)
    accepts_insurance = models.BooleanField(_('Accepts Insurance'), default=True)
    
    def __str__(self):
        return f"{self.name} ({self.provider_type})"
    
    class Meta:
        verbose_name = _('Healthcare Provider')
        verbose_name_plural = _('Healthcare Providers')
        ordering = ['name']

class PatientProviderRelationship(BaseModel):
    """Track patient relationships with healthcare providers"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='provider_relationships')
    provider = models.ForeignKey(HealthcareProvider, on_delete=models.CASCADE, related_name='patient_relationships')
    
    RELATIONSHIP_TYPES = [
        ('primary_care', _('Primary Care Physician')),
        ('specialist', _('Specialist')),
        ('consulting', _('Consulting Physician')),
        ('referring', _('Referring Physician')),
        ('emergency', _('Emergency Contact')),
        ('pharmacy', _('Pharmacy')),
        ('other', _('Other'))
    ]
    relationship_type = models.CharField(_('Relationship Type'), max_length=20, choices=RELATIONSHIP_TYPES)
    
    start_date = models.DateField(_('Relationship Start Date'))
    end_date = models.DateField(_('Relationship End Date'), null=True, blank=True)
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('transferred', _('Transferred'))
    ]
    status = models.CharField(_('Status'), max_length=15, choices=STATUS_CHOICES, default='active')
    
    notes = models.TextField(_('Notes'), blank=True)
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.provider.name} ({self.relationship_type})"
    
    class Meta:
        verbose_name = _('Patient-Provider Relationship')
        verbose_name_plural = _('Patient-Provider Relationships')
        unique_together = ['patient', 'provider', 'relationship_type']

class EmergencyContact(BaseModel):
    """Enhanced emergency contact management"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='emergency_contacts')
    
    # Contact Information (Encrypted)
    first_name = encrypt(models.CharField(_('First Name'), max_length=100))
    last_name = encrypt(models.CharField(_('Last Name'), max_length=100))
    relationship = models.CharField(_('Relationship'), max_length=50)
    
    phone_primary = encrypt(models.CharField(_('Primary Phone'), max_length=20,
                                           validators=[validate_phone_number]))
    phone_secondary = encrypt(models.CharField(_('Secondary Phone'), max_length=20,
                                             validators=[validate_phone_number], blank=True))
    email = encrypt(models.EmailField(_('Email Address'), blank=True))
    
    # Address (Encrypted)
    address = encrypt(models.TextField(_('Address'), blank=True))
    
    # Priority and Preferences
    priority_order = models.PositiveIntegerField(_('Priority Order'), default=1,
                                               help_text=_('1 = Primary contact, 2 = Secondary, etc.'))
    can_make_medical_decisions = models.BooleanField(_('Can Make Medical Decisions'), default=False)
    preferred_contact_method = models.CharField(_('Preferred Contact Method'), max_length=20,
                                              choices=[('phone', _('Phone')), ('email', _('Email')),
                                                     ('sms', _('SMS')), ('any', _('Any Method'))],
                                              default='phone')
    
    # Availability
    available_24_7 = models.BooleanField(_('Available 24/7'), default=True)
    availability_notes = models.TextField(_('Availability Notes'), blank=True)
    
    def __str__(self):
        return f"{self.patient.full_name} - Emergency Contact: {self.first_name} {self.last_name}"
    
    class Meta:
        verbose_name = _('Emergency Contact')
        verbose_name_plural = _('Emergency Contacts')
        ordering = ['priority_order']
        unique_together = ['patient', 'priority_order']

class InsurancePolicy(BaseModel):
    """Comprehensive insurance policy management"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='insurance_policies')
    
    # Policy Information (Encrypted)
    insurance_company = encrypt(models.CharField(_('Insurance Company'), max_length=255))
    policy_number = encrypt(models.CharField(_('Policy Number'), max_length=100))
    group_number = encrypt(models.CharField(_('Group Number'), max_length=100, blank=True))
    member_id = encrypt(models.CharField(_('Member ID'), max_length=100, blank=True))
    
    # Policy Details
    POLICY_TYPES = [
        ('primary', _('Primary Insurance')),
        ('secondary', _('Secondary Insurance')),
        ('supplemental', _('Supplemental Insurance')),
        ('SHIF', _('SHIF')),
        ('SHA', _('SHA')),
        ('workers_comp', _('Workers Compensation')),
        ('other', _('Other'))
    ]
    policy_type = models.CharField(_('Policy Type'), max_length=15, choices=POLICY_TYPES)
    
    # Coverage Dates
    effective_date = models.DateField(_('Effective Date'))
    expiration_date = models.DateField(_('Expiration Date'), null=True, blank=True)
    
    # Coverage Details (Encrypted)
    coverage_details = encrypt(models.TextField(_('Coverage Details'), blank=True))
    copay_amount = encrypt(models.DecimalField(_('Copay Amount'), max_digits=8, decimal_places=2,
                                             null=True, blank=True))
    deductible_amount = encrypt(models.DecimalField(_('Deductible Amount'), max_digits=10, decimal_places=2,
                                                  null=True, blank=True))
    
    # Contact Information (Encrypted)
    insurance_phone = encrypt(models.CharField(_('Insurance Phone'), max_length=20, blank=True))
    claims_address = encrypt(models.TextField(_('Claims Address'), blank=True))
    
    # Status
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
        ('suspended', _('Suspended'))
    ]
    status = models.CharField(_('Status'), max_length=15, choices=STATUS_CHOICES, default='active')
    
    # Verification
    last_verified = models.DateTimeField(_('Last Verified'), null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='verified_insurance_policies')
    
    def is_current(self):
        """Check if policy is currently active"""
        today = date.today()
        return (self.status == 'active' and 
                self.effective_date <= today and
                (not self.expiration_date or self.expiration_date >= today))
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.insurance_company} ({self.policy_type})"
    
    class Meta:
        verbose_name = _('Insurance Policy')
        verbose_name_plural = _('Insurance Policies')
        ordering = ['policy_type', '-effective_date']
        indexes = [
            models.Index(fields=['patient', 'policy_type']),
            models.Index(fields=['effective_date', 'expiration_date']),
        ]

class PatientNote(BaseModel):
    """Clinical notes and observations"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='clinical_notes')
    
    NOTE_TYPES = [
        ('clinical', _('Clinical Note')),
        ('progress', _('Progress Note')),
        ('discharge', _('Discharge Note')),
        ('consultation', _('Consultation Note')),
        ('administrative', _('Administrative Note')),
        ('care_plan', _('Care Plan')),
        ('other', _('Other'))
    ]
    note_type = models.CharField(_('Note Type'), max_length=15, choices=NOTE_TYPES)
    
    title = models.CharField(_('Note Title'), max_length=255)
    content = encrypt(models.TextField(_('Note Content')))
    
    # Clinical Context
    visit_date = models.DateTimeField(_('Visit Date'), default=timezone.now)
    department = models.CharField(_('Department'), max_length=100, blank=True)
    
    # Authorship
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                              related_name='authored_notes')
    co_signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='co_signed_notes')
    
    # Status
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('final', _('Final')),
        ('amended', _('Amended')),
        ('deleted', _('Deleted'))
    ]
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES, default='draft')
    
    # Confidentiality
    CONFIDENTIALITY_LEVELS = [
        ('normal', _('Normal')),
        ('restricted', _('Restricted')),
        ('confidential', _('Confidential')),
        ('sensitive', _('Sensitive'))
    ]
    confidentiality_level = models.CharField(_('Confidentiality Level'), max_length=15,
                                           choices=CONFIDENTIALITY_LEVELS, default='normal')
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.title} ({self.note_type})"
    
    class Meta:
        verbose_name = _('Patient Note')
        verbose_name_plural = _('Patient Notes')
        ordering = ['-visit_date']
        indexes = [
            models.Index(fields=['patient', 'note_type']),
            models.Index(fields=['visit_date']),
            models.Index(fields=['author']),
        ]

class DataAccessLog(BaseModel):
    """Comprehensive audit log for all patient data access"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='access_logs')
    accessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Access Details
    ACCESS_TYPES = [
        ('view_profile', _('View Profile')),
        ('edit_profile', _('Edit Profile')),
        ('view_medical_history', _('View Medical History')),
        ('edit_medical_history', _('Edit Medical History')),
        ('view_medications', _('View Medications')),
        ('edit_medications', _('Edit Medications')),
        ('view_documents', _('View Documents')),
        ('upload_document', _('Upload Document')),
        ('data_export', _('Data Export')),
        ('data_sharing', _('Data Sharing')),
        ('other', _('Other'))
    ]
    access_type = models.CharField(_('Access Type'), max_length=25, choices=ACCESS_TYPES)
    
    # Technical Details
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    session_id = models.CharField(_('Session ID'), max_length=100, blank=True)
    
    # Context
    purpose = models.TextField(_('Purpose of Access'), blank=True)
    department = models.CharField(_('Department'), max_length=100, blank=True)
    
    # Data Details
    fields_accessed = models.JSONField(_('Fields Accessed'), default=list, blank=True)
    data_exported = models.BooleanField(_('Data Exported'), default=False)
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.access_type} by {self.accessed_by} at {self.created_at}"
    
    class Meta:
        verbose_name = _('Data Access Log')
        verbose_name_plural = _('Data Access Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'access_type']),
            models.Index(fields=['accessed_by']),
            models.Index(fields=['created_at']),
        ]

class PatientPreferences(BaseModel):
    """Patient preferences for communication and care"""
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='preferences')
    
    # Communication Preferences
    COMMUNICATION_METHODS = [
        ('phone', _('Phone Call')),
        ('sms', _('SMS')),
        ('email', _('Email')),
        ('mail', _('Postal Mail')),
        ('portal', _('Patient Portal')),
        ('in_person', _('In Person Only'))
    ]
    preferred_communication = models.CharField(_('Preferred Communication'), max_length=20,
                                             choices=COMMUNICATION_METHODS, default='phone')
    
    # Notification Preferences
    appointment_reminders = models.BooleanField(_('Appointment Reminders'), default=True)
    medication_reminders = models.BooleanField(_('Medication Reminders'), default=False)
    health_tips = models.BooleanField(_('Health Tips'), default=False)
    marketing_communications = models.BooleanField(_('Marketing Communications'), default=False)
    
    # Care Preferences
    preferred_appointment_time = models.CharField(_('Preferred Appointment Time'), max_length=20,
                                                choices=[('morning', _('Morning')), ('afternoon', _('Afternoon')),
                                                       ('evening', _('Evening')), ('no_preference', _('No Preference'))],
                                                default='no_preference')
    
    # Language and Cultural Preferences
    interpreter_needed = models.BooleanField(_('Interpreter Needed'), default=False)
    interpreter_language = models.CharField(_('Interpreter Language'), max_length=50, blank=True)
    
    # Special Needs
    mobility_assistance = models.BooleanField(_('Mobility Assistance Needed'), default=False)
    hearing_assistance = models.BooleanField(_('Hearing Assistance Needed'), default=False)
    visual_assistance = models.BooleanField(_('Visual Assistance Needed'), default=False)
    
    # Privacy Preferences
    allow_voicemail = models.BooleanField(_('Allow Voicemail'), default=True)
    allow_family_discussion = models.BooleanField(_('Allow Family Discussion'), default=True)
    
    special_instructions = encrypt(models.TextField(_('Special Instructions'), blank=True))
    
    def __str__(self):
        return f"Preferences for {self.patient.full_name}"
    
    class Meta:
        verbose_name = _('Patient Preferences')
        verbose_name_plural = _('Patient Preferences')

class ComplianceReport(BaseModel):
    """Generate compliance reports for regulatory requirements"""
    
    REPORT_TYPES = [
        ('hipaa_audit', _('HIPAA Compliance Audit')),
        ('data_access', _('Data Access Report')),
        ('consent_summary', _('Consent Summary')),
        ('data_sharing', _('Data Sharing Report')),
        ('security_breach', _('Security Breach Report')),
        ('patient_rights', _('Patient Rights Report'))
    ]
    report_type = models.CharField(_('Report Type'), max_length=20, choices=REPORT_TYPES)
    
    title = models.CharField(_('Report Title'), max_length=255)
    description = models.TextField(_('Report Description'), blank=True)
    
    # Report Parameters
    date_from = models.DateTimeField(_('Report Period Start'))
    date_to = models.DateTimeField(_('Report Period End'))
    
    # Filters
    department_filter = models.CharField(_('Department Filter'), max_length=100, blank=True)
    user_filter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='compliance_reports_filtered')
    
    # Report Content
    report_data = models.JSONField(_('Report Data'), default=dict)
    findings = models.TextField(_('Key Findings'), blank=True)
    recommendations = models.TextField(_('Recommendations'), blank=True)
    
    # Generation Details
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='generated_compliance_reports')
    generation_completed = models.BooleanField(_('Generation Completed'), default=False)
    
    def __str__(self):
        return f"{self.title} ({self.report_type}) - {self.date_from.strftime('%Y-%m-%d')}"
    
    class Meta:
        verbose_name = _('Compliance Report')
        verbose_name_plural = _('Compliance Reports')
        ordering = ['-created_at']

# Signal handlers for audit logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Patient)
def log_patient_changes(sender, instance, created, **kwargs):
    """Log patient profile changes"""
    if created:
        DataAccessLog.objects.create(
            patient=instance,
            accessed_by=getattr(instance, '_current_user', None),
            access_type='create_profile',
            purpose='Patient registration'
        )

@receiver(post_save, sender=MedicalHistory)
def log_medical_history_changes(sender, instance, created, **kwargs):
    """Log medical history changes"""
    action = 'create_medical_history' if created else 'edit_medical_history'
    DataAccessLog.objects.create(
        patient=instance.patient,
        accessed_by=getattr(instance, '_current_user', None),
        access_type=action,
        purpose='Medical history update'
    )

@receiver(post_save, sender=ConsentForm)
def log_consent_changes(sender, instance, created, **kwargs):
    """Log consent form changes"""
    ConsentAuditLog.objects.create(
        consent_form=instance,
        action='created' if created else 'updated',
        performed_by=getattr(instance, '_current_user', None),
        details=f'Consent form {instance.category.name} {"created" if created else "updated"}'
    )