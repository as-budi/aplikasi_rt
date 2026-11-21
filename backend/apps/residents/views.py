import json

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.files import protected_file_response, validate_private_upload
from apps.core.models import audit
from apps.core.permissions import IsStaffRT, is_staff_rt
from apps.core.utils import current_period
from apps.dues.models import Bill

from . import registration, services
from .models import ChangeRequest, Document, Household, Registration, Resident
from .serializers import (
    ChangeRequestSerializer,
    DocumentSerializer,
    HouseholdDetailSerializer,
    HouseholdListSerializer,
    HouseholdOwnSerializer,
    HouseholdWriteSerializer,
    RegisterSerializer,
    RegistrationSerializer,
    ResidentOwnSerializer,
    ResidentSelfUpdateSerializer,
    ResidentSerializer,
)


class HouseholdViewSet(viewsets.ModelViewSet):
    """Data KK. Hanya pengurus/admin."""

    permission_classes = [IsStaffRT]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active", "block", "occupancy", "residence_status"]
    search_fields = ["block", "house_number", "address", "members__name"]

    def get_queryset(self):
        return Household.objects.prefetch_related(
            "members__user",
            Prefetch("bills", queryset=Bill.objects.filter(period=current_period()), to_attr="current_bills"),
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return HouseholdWriteSerializer
        if self.action == "retrieve":
            return HouseholdDetailSerializer
        return HouseholdListSerializer

    def perform_create(self, serializer):
        obj = serializer.save()
        audit(self.request.user, "tambah_kk", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        audit(self.request.user, "ubah_kk", obj, fields=list(serializer.validated_data))

    def destroy(self, request, *args, **kwargs):
        """KK tidak dihapus, hanya dinonaktifkan (riwayat iuran tetap tersimpan)."""
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=["is_active", "updated_at"])
        audit(request.user, "nonaktifkan_kk", obj)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResidentViewSet(viewsets.ModelViewSet):
    """Anggota keluarga. Hanya pengurus/admin."""

    permission_classes = [IsStaffRT]
    serializer_class = ResidentSerializer
    filterset_fields = ["household", "status"]

    def get_queryset(self):
        return Resident.objects.select_related("household", "user")

    def perform_create(self, serializer):
        obj = serializer.save()
        audit(self.request.user, "tambah_warga", obj, household=obj.household_id)

    def perform_update(self, serializer):
        obj = serializer.save()
        audit(self.request.user, "ubah_warga", obj, fields=list(serializer.validated_data))

    def perform_destroy(self, instance):
        audit(self.request.user, "hapus_warga", instance, household=instance.household_id)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="create-account")
    def create_account(self, request, pk=None):
        """Buat akun login (peran warga) untuk anggota keluarga ini."""
        resident = self.get_object()
        if getattr(resident, "user", None):
            raise ValidationError("Warga ini sudah punya akun.")
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username:
            raise ValidationError({"username": "Username wajib diisi."})
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError({"username": "Username sudah dipakai."})
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise ValidationError({"password": list(e.messages)})
        user = User.objects.create_user(
            username=username, password=password, first_name=resident.name,
            phone=resident.phone, role=User.Role.WARGA, resident=resident,
        )
        audit(request.user, "buat_akun", user, resident=resident.pk)
        return Response({"id": user.pk, "username": user.username}, status=status.HTTP_201_CREATED)


class MyHouseholdView(APIView):
    """Data keluarga milik pengguna yang login."""

    def get(self, request):
        household = request.user.household
        if not household:
            return Response(
                {"detail": "Akun Anda belum terhubung ke data warga. Hubungi pengurus RT."},
                status=status.HTTP_404_NOT_FOUND,
            )
        household = Household.objects.prefetch_related("members").get(pk=household.pk)
        return Response(HouseholdOwnSerializer(household).data)


class MyResidentUpdateView(APIView):
    """Warga mengubah data anggota keluarganya sendiri."""

    def patch(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk, household=request.user.household)
        ser = ResidentSelfUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        applied, change_request = services.update_own_resident(resident, ser.validated_data, request.user)
        return Response({
            "applied": applied,
            "change_request": ChangeRequestSerializer(change_request).data if change_request else None,
            "resident": ResidentOwnSerializer(resident).data,
        })


class ChangeRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ChangeRequestSerializer
    filterset_fields = ["status"]

    def get_queryset(self):
        user = self.request.user
        qs = ChangeRequest.objects.select_related("household", "resident", "requested_by", "reviewed_by")
        if not user.is_authenticated:  # pembuatan skema OpenAPI
            return qs.none()
        if not is_staff_rt(user) or self.request.query_params.get("mine"):
            qs = qs.filter(household=user.household)
        return qs

    def perform_create(self, serializer):
        household = self.request.user.household
        if not household:
            raise ValidationError("Akun Anda belum terhubung ke data warga.")
        resident = serializer.validated_data.get("resident")
        if resident and resident.household_id != household.pk:
            raise ValidationError({"resident": "Anggota keluarga tidak ditemukan."})
        obj = serializer.save(household=household, requested_by=self.request.user)
        audit(self.request.user, "ajukan_perubahan", obj, note=obj.note)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffRT])
    def approve(self, request, pk=None):
        cr = services.approve_change(self.get_object(), request.user, request.data.get("review_note", ""))
        return Response(self.get_serializer(cr).data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffRT])
    def reject(self, request, pk=None):
        cr = services.reject_change(self.get_object(), request.user, request.data.get("review_note", ""))
        return Response(self.get_serializer(cr).data)


class RegisterView(APIView):
    """Pendaftaran mandiri warga baru (tanpa login). Akun aktif setelah disetujui pengurus."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """multipart: `data` = JSON pendaftaran, `kk_file` = foto/scan KK, `ktp_file` = foto KTP pendaftar."""
        try:
            payload = json.loads(request.data.get("data") or "{}")
        except ValueError:
            raise ValidationError({"data": "Format data tidak valid."})
        ser = RegisterSerializer(data=payload)
        ser.is_valid(raise_exception=True)
        files = {}
        for field, label in (("kk_file", "Foto Kartu Keluarga"), ("ktp_file", "Foto KTP")):
            f = request.FILES.get(field)
            if not f:
                raise ValidationError({field: f"{label} wajib diunggah."})
            try:
                files[field] = validate_private_upload(f, label)
            except ValidationError as e:
                raise ValidationError({field: e.detail})
        registration.register(ser.validated_data, **files)
        return Response(
            {"detail": "Pendaftaran terkirim. Anda bisa masuk setelah akun diaktifkan oleh pengurus RT."},
            status=status.HTTP_201_CREATED,
        )


class RegistrationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsStaffRT]
    serializer_class = RegistrationSerializer
    filterset_fields = ["status"]

    def get_queryset(self):
        return Registration.objects.select_related("user", "reviewed_by", "household")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        household = None
        if request.data.get("household"):
            household = get_object_or_404(Household, pk=request.data["household"], is_active=True)
        reg = registration.approve(self.get_object(), request.user, household)
        return Response(self.get_serializer(reg).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        reg = registration.reject(self.get_object(), request.user, request.data.get("review_note", ""))
        return Response(self.get_serializer(reg).data)


class DocumentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Dokumen KK/KTP. Pengurus: semua; warga: dokumen KK sendiri (boleh mengunggah, tidak boleh menghapus)."""

    serializer_class = DocumentSerializer
    filterset_fields = ["household", "kind", "registration"]

    def get_queryset(self):
        user = self.request.user
        qs = Document.objects.select_related("resident", "uploaded_by")
        if not user.is_authenticated:  # pembuatan skema OpenAPI
            return qs.none()
        if is_staff_rt(user):
            return qs
        return qs.filter(household=user.household) if user.household else qs.none()

    def get_permissions(self):
        if self.action == "destroy":
            return [IsStaffRT()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        if is_staff_rt(user) and self.request.data.get("household"):
            household = get_object_or_404(Household, pk=self.request.data["household"])
        else:
            household = user.household
        if not household:
            raise ValidationError("Akun Anda belum terhubung ke data warga.")
        resident = serializer.validated_data.get("resident")
        if resident and resident.household_id != household.pk:
            raise ValidationError({"resident": "Anggota keluarga tidak ditemukan di KK ini."})
        doc = serializer.save(household=household, uploaded_by=user)
        audit(user, "unggah_dokumen", doc, household=household.pk, kind=doc.kind)

    def perform_destroy(self, instance):
        audit(self.request.user, "hapus_dokumen", instance, household=instance.household_id, kind=instance.kind)
        instance.delete()

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        return protected_file_response(self.get_object().file)
