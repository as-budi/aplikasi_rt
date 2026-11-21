from django.contrib import admin

from .models import CashEntry


@admin.register(CashEntry)
class CashEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "kind", "category", "description", "amount", "recorded_by")
    list_filter = ("kind", "category")
    search_fields = ("description",)
    exclude = ("receipt",)  # nota privat dibuka lewat aplikasi
