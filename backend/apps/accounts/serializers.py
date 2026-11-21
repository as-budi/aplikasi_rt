from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class MeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="display_name", read_only=True)
    is_staff_rt = serializers.BooleanField(read_only=True)
    household_id = serializers.SerializerMethodField()
    household_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "role", "phone", "email", "is_staff_rt", "resident", "household_id", "household_label"]

    def get_household_id(self, obj) -> int | None:
        hh = obj.household
        return hh.pk if hh else None

    def get_household_label(self, obj) -> str | None:
        hh = obj.household
        return hh.label if hh else None


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(label="Username / No. HP / email")
    password = serializers.CharField(label="Kata sandi", trim_whitespace=False)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(label="Kata sandi lama", trim_whitespace=False)
    new_password = serializers.CharField(label="Kata sandi baru", trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Kata sandi lama salah."})
        validate_password(attrs["new_password"], user)
        return attrs
