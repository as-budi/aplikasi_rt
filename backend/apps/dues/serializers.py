import os

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from apps.residents.models import Household

from .models import Bill, FeeType, Payment, PaymentProof

ALLOWED_PROOF_EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


class FeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeType
        fields = ["id", "name", "amount", "period", "description", "is_active"]


class BillSerializer(serializers.ModelSerializer):
    household_label = serializers.CharField(source="household.label", read_only=True)
    fee_type_name = serializers.CharField(source="fee_type.name", read_only=True)
    paid_at = serializers.DateField(source="payment.paid_at", read_only=True, default=None)
    method = serializers.CharField(source="payment.method", read_only=True, default=None)

    class Meta:
        model = Bill
        fields = ["id", "household", "household_label", "fee_type", "fee_type_name", "period", "amount", "status", "payment", "paid_at", "method"]


class BillMiniSerializer(serializers.ModelSerializer):
    fee_type_name = serializers.CharField(source="fee_type.name", read_only=True)

    class Meta:
        model = Bill
        fields = ["id", "period", "fee_type_name", "amount", "status"]


class PaymentCreateSerializer(serializers.Serializer):
    household = serializers.PrimaryKeyRelatedField(queryset=Household.objects.filter(is_active=True))
    bills = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    paid_at = serializers.DateField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")


class PaymentSerializer(serializers.ModelSerializer):
    household_label = serializers.CharField(source="household.label", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.display_name", read_only=True, default=None)
    bills = BillMiniSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "household", "household_label", "total", "method", "paid_at", "recorded_by_name", "note", "bills", "created_at"]


class PaymentProofCreateSerializer(serializers.Serializer):
    bills = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    file = serializers.FileField()
    amount = serializers.IntegerField(min_value=1)
    transfer_date = serializers.DateField()
    method = serializers.ChoiceField(choices=[Payment.Method.TRANSFER, Payment.Method.QRIS])
    note = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")

    def validate_file(self, f):
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_PROOF_EXT:
            raise serializers.ValidationError("Format file harus JPG, PNG, WEBP, atau PDF.")
        if f.size > settings.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError("Ukuran file maksimal 5 MB.")
        return f


class PaymentProofSerializer(serializers.ModelSerializer):
    household_label = serializers.CharField(source="household.label", read_only=True)
    head_name = serializers.CharField(source="household.head_name", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.display_name", read_only=True, default=None)
    verified_by_name = serializers.CharField(source="verified_by.display_name", read_only=True, default=None)
    bills = BillMiniSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()

    class Meta:
        model = PaymentProof
        fields = [
            "id", "household", "household_label", "head_name", "uploaded_by_name", "bills", "amount",
            "transfer_date", "method", "note", "status", "review_note", "verified_by_name", "verified_at",
            "created_at", "file_url", "file_type",
        ]

    def get_file_url(self, obj) -> str:
        return reverse("payment-proof-file", args=[obj.pk])

    def get_file_type(self, obj) -> str:
        return "pdf" if obj.file.name.lower().endswith(".pdf") else "image"
