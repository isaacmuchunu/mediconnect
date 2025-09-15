from django.contrib import admin
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import Token

# Customize Token admin to show more information
class CustomTokenAdmin(TokenAdmin):
    list_display = ('key', 'user', 'created')
    list_filter = ('created',)
    search_fields = ('user__username', 'user__email', 'key')
    readonly_fields = ('key', 'created')
    
    def has_add_permission(self, request):
        return True
    
    def has_change_permission(self, request, obj=None):
        return True
    
    def has_delete_permission(self, request, obj=None):
        return True

# Unregister the default TokenAdmin if it's registered, then register our custom one
if admin.site.is_registered(Token):
    admin.site.unregister(Token)
admin.site.register(Token, CustomTokenAdmin)

# Note: Other models are already registered in their respective apps
# This admin.py focuses on API-specific configurations like authentication tokens