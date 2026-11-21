import os

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from .models import CashEntry

ALLOWED_RECEIPT_EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


class CashEntrySerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.display_name", read_only=True, default=None)
    receipt = serializers.FileField(write_only=True, required=False, allow_null=True)
    receipt_url = serializers.SerializerMethodField()

    class Meta:
        model = CashEntry
        fields = [
            "id", "kind", "kind_label", "category", "category_label", "description", "amount", "date",
            "receipt", "receipt_url", "recorded_by_name", "created_at",
        ]

    def get_receipt_url(self, obj) -> str | None:
        return reverse("cash-entry-receipt", args=[obj.pk]) if obj.receipt else None

    def validate_receipt(self, f):
        if not f:
            return f
        if os.path.splitext(f.name)[1].lower() not in ALLOWED_RECEIPT_EXT:
            raise serializers.ValidationError("Format nota harus JPG, PNG, WEBP, atau PDF.")
        if f.size > settings.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError("Ukuran file maksimal 5 MB.")
        return f

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Jumlah harus lebih dari 0.")
        return value

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        category = attrs.get("category", getattr(self.instance, "category", None))
        if kind == CashEntry.Kind.OUT and category in CashEntry.INCOME_ONLY:
            raise serializers.ValidationError({"category": "Kategori ini hanya untuk pemasukan."})
        return attrs
