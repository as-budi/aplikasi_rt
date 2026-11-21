from django.urls import reverse
from rest_framework import serializers

from apps.core.files import validate_private_upload
from apps.residents.models import Household

from .models import Bill, FeeType, Payment, PaymentProof


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


class _BillSelectionMixin(serializers.Serializer):
    """Tagihan yang dipilih: `bills` (sudah ada) dan/atau `periods` (bulan mendatang, bayar di muka)."""

    bills = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    periods = serializers.ListField(child=serializers.RegexField(r"^\d{4}-(0[1-9]|1[0-2])$"), required=False, default=list)

    def validate(self, attrs):
        if not attrs.get("bills") and not attrs.get("periods"):
            raise serializers.ValidationError({"bills": "Pilih minimal satu bulan."})
        return attrs


class PaymentCreateSerializer(_BillSelectionMixin):
    household = serializers.PrimaryKeyRelatedField(queryset=Household.objects.filter(is_active=True))
    method = serializers.ChoiceField(choices=[(m.value, m.label) for m in Payment.MANUAL_METHODS])
    paid_at = serializers.DateField()
    amount = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None,
                                      help_text="Uang yang diterima; kosong = sama dengan total tagihan")
    refund_excess = serializers.BooleanField(required=False, default=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")


class PaymentSerializer(serializers.ModelSerializer):
    household_label = serializers.CharField(source="household.label", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.display_name", read_only=True, default=None)
    cancelled_by_name = serializers.CharField(source="cancelled_by.display_name", read_only=True, default=None)
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    bills = BillMiniSerializer(many=True, read_only=True)
    proof_id = serializers.SerializerMethodField()

    def get_proof_id(self, obj) -> int | None:
        proof = getattr(obj, "proof", None)
        return proof.pk if proof else None

    class Meta:
        model = Payment
        fields = [
            "id", "household", "household_label", "total", "credit_change", "refund", "method", "method_label", "paid_at",
            "recorded_by_name", "note", "bills", "periods_label", "proof_id", "cancelled_at", "cancelled_by_name", "cancel_reason",
            "created_at",
        ]


class PaymentProofCreateSerializer(_BillSelectionMixin):
    file = serializers.FileField()
    amount = serializers.IntegerField(min_value=1)
    transfer_date = serializers.DateField()
    method = serializers.ChoiceField(choices=[Payment.Method.TRANSFER, Payment.Method.QRIS])
    note = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")

    def validate_file(self, f):
        return validate_private_upload(f, "File")


class PaymentProofSerializer(serializers.ModelSerializer):
    household_label = serializers.CharField(source="household.label", read_only=True)
    head_name = serializers.CharField(source="household.head_name", read_only=True)
    household_credit = serializers.IntegerField(source="household.credit", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.display_name", read_only=True, default=None)
    verified_by_name = serializers.CharField(source="verified_by.display_name", read_only=True, default=None)
    bills = BillMiniSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()

    class Meta:
        model = PaymentProof
        fields = [
            "id", "household", "household_label", "head_name", "household_credit", "uploaded_by_name", "bills", "amount",
            "transfer_date", "method", "note", "status", "review_note", "verified_by_name", "verified_at",
            "created_at", "file_url", "file_type",
        ]

    def get_file_url(self, obj) -> str:
        return reverse("payment-proof-file", args=[obj.pk])

    def get_file_type(self, obj) -> str:
        return "pdf" if obj.file.name.lower().endswith(".pdf") else "image"
