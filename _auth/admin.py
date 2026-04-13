from django.contrib import admin
from .models import OTPCode


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('is_used',)
    readonly_fields = ('code', 'created_at')
