from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'can_manage_multiple_companies']
    list_filter = UserAdmin.list_filter + ('can_manage_multiple_companies',)
    fieldsets = UserAdmin.fieldsets + (
        ('Permissions NORMXIA', {'fields': ('can_manage_multiple_companies',)}),
    )