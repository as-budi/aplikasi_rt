import django_filters
from django.http import Http404
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.files import protected_file_response
from apps.core.models import audit
from apps.core.permissions import IsStaffOrReadOnly, is_staff_rt

from .models import CashEntry
from .serializers import CashEntrySerializer
from .services import cash_report, ledger


class CashEntryFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter(field_name="date", lookup_expr="year")
    month = django_filters.NumberFilter(field_name="date", lookup_expr="month")

    class Meta:
        model = CashEntry
        fields = ["kind", "category", "year", "month"]


class CashEntryViewSet(viewsets.ModelViewSet):
    """Kas RT. Semua warga boleh melihat (transparansi); hanya pengurus yang mencatat."""

    serializer_class = CashEntrySerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_class = CashEntryFilter

    def get_queryset(self):
        return CashEntry.objects.select_related("recorded_by")

    def perform_create(self, serializer):
        entry = serializer.save(recorded_by=self.request.user)
        audit(self.request.user, "catat_kas", entry, kind=entry.kind, amount=entry.amount)

    def perform_update(self, serializer):
        entry = serializer.save()
        audit(self.request.user, "ubah_kas", entry, amount=entry.amount)

    def perform_destroy(self, instance):
        audit(self.request.user, "hapus_kas", instance, kind=instance.kind, amount=instance.amount)
        if instance.receipt:
            instance.receipt.delete(save=False)
        instance.delete()

    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        entry = self.get_object()
        if not entry.receipt:
            raise Http404
        return protected_file_response(entry.receipt)

    @action(detail=False)
    def report(self, request):
        return Response(cash_report(_year(request)))

    @action(detail=False)
    def ledger(self, request):
        """Buku kas gabungan (transaksi kas + iuran). Rincian per rumah: lihat CASH_LEDGER_PUBLIC_DETAIL."""
        try:
            month = int(request.query_params["month"]) if request.query_params.get("month") else None
        except ValueError:
            raise ValidationError({"month": "Bulan tidak valid."})
        rows = ledger(_year(request), month, request.query_params.get("kind") or None, private=show_detail(request.user))
        for r in rows:
            r["receipt_url"] = reverse("cash-entry-receipt", args=[r["id"]]) if r.pop("receipt") else None
        return Response(rows)


def show_detail(user) -> bool:
    """Apakah iuran ditampilkan per rumah (nama & no. rumah) untuk user ini."""
    return is_staff_rt(user) or settings.CASH_LEDGER_PUBLIC_DETAIL


def _year(request) -> int:
    try:
        return int(request.query_params.get("year") or timezone.localdate().year)
    except ValueError:
        raise ValidationError({"year": "Tahun tidak valid."})
