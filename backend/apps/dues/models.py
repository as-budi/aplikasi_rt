import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.utils import BELUM, LUNAS, MENUNGGU


class FeeType(models.Model):
    class Period(models.TextChoices):
        BULANAN = "bulanan", "Bulanan"
        SEKALI = "sekali", "Sekali bayar"

    name = models.CharField("Nama iuran", max_length=60)
    amount = models.PositiveIntegerField("Nominal (Rp)")
    period = models.CharField("Periode", max_length=10, choices=Period.choices, default=Period.BULANAN)
    description = models.CharField("Keterangan", max_length=200, blank=True)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Jenis iuran"
        verbose_name_plural = "Jenis iuran"

    def __str__(self):
        return f"{self.name} (Rp{self.amount:,})".replace(",", ".")


class Payment(models.Model):
    class Method(models.TextChoices):
        TUNAI = "tunai", "Tunai"
        TRANSFER = "transfer", "Transfer"
        QRIS = "qris", "QRIS"

    household = models.ForeignKey("residents.Household", on_delete=models.PROTECT, related_name="payments")
    total = models.PositiveIntegerField("Total (Rp)")
    method = models.CharField("Metode", max_length=10, choices=Method.choices)
    paid_at = models.DateField("Tanggal bayar")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField("Catatan", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at", "-id"]
        verbose_name = "Pembayaran"
        verbose_name_plural = "Pembayaran"

    def __str__(self):
        return f"Pembayaran #{self.pk} {self.household.label}"


class Bill(models.Model):
    """Tagihan satu jenis iuran untuk satu KK pada satu periode (YYYY-MM)."""

    class Status(models.TextChoices):
        BELUM = BELUM, "Belum bayar"
        MENUNGGU = MENUNGGU, "Menunggu verifikasi"
        LUNAS = LUNAS, "Lunas"

    household = models.ForeignKey("residents.Household", on_delete=models.PROTECT, related_name="bills")
    fee_type = models.ForeignKey(FeeType, on_delete=models.PROTECT, related_name="bills")
    period = models.CharField("Periode", max_length=7, help_text="Format YYYY-MM")
    amount = models.PositiveIntegerField("Nominal (Rp)")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BELUM)
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="bills")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["period", "household", "fee_type"]
        verbose_name = "Tagihan"
        verbose_name_plural = "Tagihan"
        constraints = [
            models.UniqueConstraint(fields=["household", "fee_type", "period"], name="uniq_bill_household_fee_period"),
        ]
        indexes = [models.Index(fields=["period", "status"])]

    def __str__(self):
        return f"{self.household.label} {self.fee_type.name} {self.period}"


def proof_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"proofs/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class PaymentProof(models.Model):
    """Bukti transfer yang diunggah warga, menunggu verifikasi pengurus."""

    class Status(models.TextChoices):
        PENDING = "pending", "Menunggu"
        ACCEPTED = "diterima", "Diterima"
        REJECTED = "ditolak", "Ditolak"

    household = models.ForeignKey("residents.Household", on_delete=models.PROTECT, related_name="payment_proofs")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    bills = models.ManyToManyField(Bill, related_name="proofs")
    file = models.FileField("File bukti", upload_to=proof_upload_to)
    amount = models.PositiveIntegerField("Nominal (Rp)")
    transfer_date = models.DateField("Tanggal transfer")
    method = models.CharField("Metode", max_length=10, choices=Payment.Method.choices, default=Payment.Method.TRANSFER)
    note = models.CharField("Catatan warga", max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    review_note = models.CharField("Catatan pengurus", max_length=255, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)
    payment = models.OneToOneField(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="proof")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bukti bayar"
        verbose_name_plural = "Bukti bayar"

    def __str__(self):
        return f"Bukti #{self.pk} {self.household.label}"
