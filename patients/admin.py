from django.contrib import admin
from .models import Patient, MedicalHistory, ConsentForm

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'gender', 'date_of_birth', 'phone_primary', 'email', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone_primary')
    list_filter = ('gender', 'created_at')
    date_hierarchy = 'created_at'

@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ('patient', 'created_at', 'updated_at')
    search_fields = ('patient__name',)
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        # Only allow adding through the patient interface
        return False

@admin.register(ConsentForm)
class ConsentFormAdmin(admin.ModelAdmin):
    list_display = ('patient', 'category', 'consent_given', 'signed_at', 'revoked_at')
    list_filter = ('category', 'consent_given', 'signed_at', 'revoked_at')
    search_fields = ('patient__name',)
    date_hierarchy = 'signed_at'
    readonly_fields = ('ip_address', 'signed_at', 'consent_text')