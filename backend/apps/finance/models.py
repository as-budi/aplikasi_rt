import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def receipt_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"receipts/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class CashEntry(models.Model):
    """Transaksi kas RT di luar iuran warga (iuran dihitung otomatis dari Payment)."""

    class Kind(models.TextChoices):
        IN = "pemasukan", "Pemasukan"
        OUT = "pengeluaran", "Pengeluaran"

    class Category(models.TextChoices):
        SALDO_AWAL = "saldo_awal", "Saldo awal"
        DONASI = "donasi", "Donasi / sumbangan"
        KEBERSIHAN = "kebersihan", "Kebersihan"
        KEAMANAN = "keamanan", "Keamanan"
        SOSIAL = "sosial", "Sosial / santunan"
        KEGIATAN = "kegiatan", "Kegiatan warga"
        OPERASIONAL = "operasional", "Operasional & ATK"
        PERBAIKAN = "perbaikan", "Perbaikan fasilitas"
        LAINNYA = "lainnya", "Lainnya"

    # Kategori yang hanya masuk akal untuk pemasukan
    INCOME_ONLY = {Category.SALDO_AWAL, Category.DONASI}

    kind = models.CharField("Jenis", max_length=12, choices=Kind.choices)
    category = models.CharField("Kategori", max_length=12, choices=Category.choices)
    description = models.CharField("Keterangan", max_length=200)
    amount = models.PositiveIntegerField("Jumlah (Rp)")
    date = models.DateField("Tanggal")
    receipt = models.FileField("Nota / kuitansi", upload_to=receipt_upload_to, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Transaksi kas"
        verbose_name_plural = "Transaksi kas"

    def __str__(self):
        return f"{self.date} {self.get_kind_display()} {self.description}"
