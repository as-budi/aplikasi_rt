from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "display_name", "role", "phone", "resident", "is_active", "last_login")
    list_filter = ("role", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "phone")
    raw_id_fields = ("resident",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Profil", {"fields": ("first_name", "last_name", "email", "phone")}),
        ("Aplikasi RT", {"fields": ("role", "resident")}),
        ("Status", {"fields": ("is_active", "is_superuser")}),
        ("Waktu", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2", "role", "resident")}),
    )
