from django.contrib import admin

from .models import ChangeRequest, Household, Registration, Resident


class ResidentInline(admin.TabularInline):
    model = Resident
    extra = 0
    fields = ("name", "nik", "gender", "relation", "birth_date", "phone", "status")


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("label", "head_name", "occupancy", "residence_status", "is_active")
    list_filter = ("is_active", "occupancy", "residence_status", "block")
    search_fields = ("block", "house_number", "members__name")
    inlines = [ResidentInline]


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ("name", "household", "relation", "gender", "phone", "status")
    list_filter = ("status", "gender", "relation")
    search_fields = ("name", "phone")
    raw_id_fields = ("household",)


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "resident", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("household", "resident", "requested_by", "reviewed_by")


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("name", "house_label", "status", "created_at", "reviewed_by")
    list_filter = ("status",)
    exclude = ("payload",)  # data terenkripsi; ditinjau lewat aplikasi
    raw_id_fields = ("user", "reviewed_by", "household")
