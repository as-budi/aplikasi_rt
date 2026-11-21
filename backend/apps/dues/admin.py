from django.contrib import admin

from .models import Bill, FeeType, Payment, PaymentProof


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "period", "is_active")
    list_editable = ("amount", "is_active")


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("household", "fee_type", "period", "amount", "status")
    list_filter = ("status", "period", "fee_type")
    raw_id_fields = ("household", "payment")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "total", "method", "paid_at", "recorded_by")
    list_filter = ("method",)
    raw_id_fields = ("household", "recorded_by")


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "amount", "transfer_date", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("household", "uploaded_by", "verified_by", "payment", "bills")
    exclude = ("file",)  # file privat dibuka lewat aplikasi, bukan URL publik
