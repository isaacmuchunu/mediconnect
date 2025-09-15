from django.contrib import admin
from .models import User, Profile, DoctorProfile, PatientProfile, AmbulanceStaffProfile

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_verified', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_verified')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    actions = ['verify_users']

    def verify_users(self, request, queryset):
        queryset.update(is_verified=True)
    verify_users.short_description = "Mark selected users as verified"

admin.site.register(User, UserAdmin)
admin.site.register(Profile)

admin.site.register(PatientProfile)
admin.site.register(AmbulanceStaffProfile)