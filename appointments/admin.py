from django.contrib import admin
from .models import Appointment

class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('referral', 'appointment_date', 'status')
    list_filter = ('status',)
    search_fields = ('referral__patient__name', 'referral__doctor__name')

admin.site.register(Appointment, AppointmentAdmin)