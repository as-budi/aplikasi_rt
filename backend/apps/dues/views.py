import django_filters
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.files import protected_file_response
from apps.core.permissions import IsStaffRT, is_staff_rt
from apps.core.utils import current_period

from . import services
from .models import Bill, FeeType, Payment, PaymentProof
from .serializers import (
    BillSerializer,
    FeeTypeSerializer,
    PaymentCreateSerializer,
    PaymentProofCreateSerializer,
    PaymentProofSerializer,
    PaymentSerializer,
)


def _scope_to_household(qs, request):
    """Warga hanya melihat data KK-nya sendiri. Pengurus melihat semua, kecuali ?mine=1."""
    if not request.user.is_authenticated:  # pembuatan skema OpenAPI
        return qs.none()
    if not is_staff_rt(request.user) or request.query_params.get("mine"):
        return qs.filter(household=request.user.household)
    return qs


class FeeTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Jenis iuran (dikelola admin lewat Django Admin)."""

    serializer_class = FeeTypeSerializer
    queryset = FeeType.objects.filter(is_active=True)
    pagination_class = None


class BillFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter(method="filter_year")

    class Meta:
        model = Bill
        fields = ["household", "period", "status", "fee_type"]

    def filter_year(self, qs, name, value):
        return qs.filter(period__startswith=f"{int(value)}-")


class BillViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BillSerializer
    filterset_class = BillFilter

    def get_queryset(self):
        qs = Bill.objects.select_related("household", "fee_type", "payment")
        return _scope_to_household(qs, self.request)

    @action(detail=False)
    def summary(self, request):
        try:
            year = int(request.query_params.get("year") or timezone.localdate().year)
        except ValueError:
            raise ValidationError({"year": "Tahun tidak valid."})
        return Response(services.bill_summary(year, include_private=is_staff_rt(request.user)))

    @action(detail=False, methods=["post"], permission_classes=[IsStaffRT])
    def generate(self, request):
        period = request.data.get("period") or current_period()
        created = services.generate_bills(period)
        return Response({"period": period, "created": created})

    @action(detail=False, url_path="prepay-options")
    def prepay_options(self, request):
        """Bulan mendatang yang bisa dibayar di muka oleh KK (belum ada tagihannya) + tarif saat ini."""
        from apps.residents.models import Household

        if is_staff_rt(request.user) and request.query_params.get("household"):
            household = Household.objects.filter(pk=request.query_params["household"]).first()
        else:
            household = request.user.household
        if not household:
            return Response({"periods": [], "fees": [], "credit": 0})
        fees = list(FeeType.objects.filter(is_active=True, period=FeeType.Period.BULANAN))
        existing = set(Bill.objects.filter(household=household, period__gt=current_period()).values_list("period", flat=True))
        periods = [p for p in (services.add_months(current_period(), i) for i in range(1, services.MAX_PREPAY_MONTHS + 1)) if p not in existing]
        return Response({
            "periods": periods,
            "fees": [{"name": f.name, "amount": f.amount} for f in fees],
            "monthly_total": sum(f.amount for f in fees),
            "credit": household.credit,
        })


class PaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = PaymentSerializer
    filterset_fields = ["household", "method"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsStaffRT()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Payment.objects.select_related("household", "recorded_by").prefetch_related("bills__fee_type", "household__members")
        return _scope_to_household(qs, self.request)

    def create(self, request, *args, **kwargs):
        ser = PaymentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        with transaction.atomic():  # tagihan bayar di muka ikut dibatalkan bila pencatatan gagal
            payment = services.record_payment(
                household=d["household"], bill_ids=d["bills"] + services.ensure_future_bills(d["household"], d["periods"]),
                method=d["method"], paid_at=d["paid_at"], user=request.user, note=d["note"],
                amount=d["amount"], refund_excess=d["refund_excess"],
            )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentProofViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = PaymentProofSerializer
    filterset_fields = ["status", "household"]

    def get_queryset(self):
        qs = PaymentProof.objects.select_related("household", "uploaded_by", "verified_by").prefetch_related(
            "bills__fee_type", "household__members"
        )
        return _scope_to_household(qs, self.request)

    def create(self, request, *args, **kwargs):
        household = request.user.household
        if not household:
            raise ValidationError("Akun Anda belum terhubung ke data warga.")
        ser = PaymentProofCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        proof = services.submit_proof(
            household=household, user=request.user, bill_ids=d["bills"], file=d["file"],
            amount=d["amount"], transfer_date=d["transfer_date"], method=d["method"], note=d["note"],
            periods=d["periods"],
        )
        return Response(PaymentProofSerializer(proof).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffRT])
    def approve(self, request, pk=None):
        refund = str(request.data.get("refund_excess", "")).lower() in ("1", "true", "yes")
        amount = request.data.get("amount")
        if amount not in (None, ""):
            try:
                amount = int(amount)
            except (TypeError, ValueError):
                raise ValidationError({"amount": "Nominal tidak valid."})
            if amount < 0:
                raise ValidationError({"amount": "Nominal tidak boleh negatif."})
        proof = services.approve_proof(self.get_object(), request.user, request.data.get("review_note", ""), amount, refund)
        return Response(self.get_serializer(proof).data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffRT])
    def reject(self, request, pk=None):
        proof = services.reject_proof(self.get_object(), request.user, request.data.get("review_note", ""))
        return Response(self.get_serializer(proof).data)

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        # get_object() sudah dibatasi ke KK sendiri untuk warga -> 404 bila bukan miliknya
        return protected_file_response(self.get_object().file)
