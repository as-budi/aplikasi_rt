import re

from rest_framework import serializers

from apps.core.utils import aggregate_status, mask

from .models import ChangeRequest, Household, Resident

DIGITS_16 = re.compile(r"^\d{16}$")


def _validate_16_digits(value: str, label: str) -> str:
    value = (value or "").strip()
    if value and not DIGITS_16.match(value):
        raise serializers.ValidationError(f"{label} harus 16 digit angka.")
    return value


# ---------- Warga (anggota keluarga) ----------

class ResidentSerializer(serializers.ModelSerializer):
    """Untuk pengurus: data lengkap termasuk NIK."""

    age = serializers.IntegerField(read_only=True)
    has_account = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Resident
        fields = [
            "id", "household", "nik", "name", "gender", "birth_place", "birth_date", "religion",
            "marital_status", "relation", "occupation", "phone", "status", "age", "has_account", "username",
        ]

    def validate_nik(self, value):
        return _validate_16_digits(value, "NIK")

    def get_has_account(self, obj) -> bool:
        return getattr(obj, "user", None) is not None

    def get_username(self, obj) -> str | None:
        user = getattr(obj, "user", None)
        return user.username if user else None


class ResidentOwnSerializer(serializers.ModelSerializer):
    """Untuk warga melihat data keluarganya sendiri: NIK disamarkan."""

    age = serializers.IntegerField(read_only=True)
    nik_masked = serializers.SerializerMethodField()

    class Meta:
        model = Resident
        fields = [
            "id", "nik_masked", "name", "gender", "birth_place", "birth_date", "religion",
            "marital_status", "relation", "occupation", "phone", "status", "age",
        ]

    def get_nik_masked(self, obj) -> str:
        return mask(obj.nik)


class ResidentSelfUpdateSerializer(serializers.ModelSerializer):
    """Input warga saat mengubah datanya sendiri."""

    class Meta:
        model = Resident
        fields = list(Resident.IDENTITY_FIELDS + Resident.CONTACT_FIELDS)
        extra_kwargs = {f: {"required": False} for f in fields}

    def validate_nik(self, value):
        return _validate_16_digits(value, "NIK")


# ---------- Keluarga (KK) ----------

class HouseholdListSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)
    head_name = serializers.CharField(read_only=True)
    head_phone = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    no_kk_masked = serializers.SerializerMethodField()
    current_status = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = [
            "id", "label", "block", "house_number", "address", "occupancy", "is_active",
            "head_name", "head_phone", "member_count", "no_kk_masked", "current_status",
        ]

    def get_head_phone(self, obj) -> str:
        head = obj.head
        return head.phone if head else ""

    def get_member_count(self, obj) -> int:
        return sum(1 for m in obj.members.all() if m.status == Resident.Status.AKTIF)

    def get_no_kk_masked(self, obj) -> str:
        return mask(obj.no_kk)

    def get_current_status(self, obj) -> str | None:
        bills = getattr(obj, "current_bills", None)
        return aggregate_status(b.status for b in bills) if bills is not None else None


class HouseholdDetailSerializer(HouseholdListSerializer):
    members = ResidentSerializer(many=True, read_only=True)

    class Meta(HouseholdListSerializer.Meta):
        fields = HouseholdListSerializer.Meta.fields + ["no_kk", "since", "members", "created_at"]


class HouseholdWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["id", "no_kk", "block", "house_number", "address", "occupancy", "since", "is_active"]

    def validate_no_kk(self, value):
        return _validate_16_digits(value, "No. KK")

    def validate(self, attrs):
        block = attrs.get("block", getattr(self.instance, "block", None))
        number = attrs.get("house_number", getattr(self.instance, "house_number", None))
        qs = Household.objects.filter(block__iexact=block, house_number__iexact=number, is_active=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Rumah {block}-{number} sudah terdaftar sebagai KK aktif.")
        return attrs


class HouseholdOwnSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)
    no_kk_masked = serializers.SerializerMethodField()
    members = ResidentOwnSerializer(many=True, read_only=True)

    class Meta:
        model = Household
        fields = ["id", "label", "block", "house_number", "address", "occupancy", "since", "no_kk_masked", "members"]

    def get_no_kk_masked(self, obj) -> str:
        return mask(obj.no_kk)


# ---------- Pengajuan perubahan ----------

class ChangeRequestSerializer(serializers.ModelSerializer):
    household_label = serializers.CharField(source="household.label", read_only=True)
    resident_name = serializers.CharField(source="resident.name", read_only=True, default=None)
    requested_by_name = serializers.CharField(source="requested_by.display_name", read_only=True, default=None)
    reviewed_by_name = serializers.CharField(source="reviewed_by.display_name", read_only=True, default=None)

    class Meta:
        model = ChangeRequest
        fields = [
            "id", "household", "household_label", "resident", "resident_name", "requested_by_name",
            "changes", "note", "status", "review_note", "reviewed_by_name", "reviewed_at", "created_at",
        ]
        read_only_fields = ["household", "changes", "status", "review_note", "reviewed_at", "created_at"]

    def validate(self, attrs):
        if not attrs.get("note", "").strip():
            raise serializers.ValidationError({"note": "Jelaskan perubahan yang diajukan."})
        return attrs
