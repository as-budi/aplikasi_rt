from datetime import date

from django.conf import settings
from django.db import models

from apps.core.fields import EncryptedCharField


class Household(models.Model):
    """Keluarga (KK) / rumah. Unit penagihan iuran."""

    class Occupancy(models.TextChoices):
        PEMILIK = "pemilik", "Pemilik"
        KONTRAK = "kontrak", "Kontrak"
        KOS = "kos", "Kos"

    no_kk = EncryptedCharField("No. KK", max_length=16, blank=True)
    block = models.CharField("Blok", max_length=10)
    house_number = models.CharField("No. rumah", max_length=10)
    address = models.CharField("Alamat", max_length=200, blank=True)
    occupancy = models.CharField("Status hunian", max_length=10, choices=Occupancy.choices, default=Occupancy.PEMILIK)
    residence_status = models.CharField(
        "Status rumah",
        max_length=10,
        choices=[("menetap", "Menetap"), ("singgah", "Rumah singgah")],
        default="menetap",
        help_text="Menetap: dihuni sehari-hari. Rumah singgah: hanya sesekali ditinggali.",
    )
    since = models.DateField("Tinggal sejak", null=True, blank=True)
    is_active = models.BooleanField("Aktif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["block", "house_number"]
        verbose_name = "Keluarga (KK)"
        verbose_name_plural = "Keluarga (KK)"

    def __str__(self):
        return f"{self.label} · {self.head_name}"

    @property
    def label(self) -> str:
        return f"{self.block}-{self.house_number}"

    @property
    def head(self):
        # Memakai prefetch `members` bila tersedia
        members = [m for m in self.members.all() if m.status == Resident.Status.AKTIF]
        for m in members:
            if m.relation == Resident.Relation.KEPALA:
                return m
        return members[0] if members else None

    @property
    def head_name(self) -> str:
        head = self.head
        return head.name if head else "—"


class Resident(models.Model):
    class Gender(models.TextChoices):
        L = "L", "Laki-laki"
        P = "P", "Perempuan"

    class Relation(models.TextChoices):
        KEPALA = "kepala_keluarga", "Kepala Keluarga"
        SUAMI = "suami", "Suami"
        ISTRI = "istri", "Istri"
        ANAK = "anak", "Anak"
        ORANG_TUA = "orang_tua", "Orang Tua"
        FAMILI = "famili", "Famili Lain"
        LAINNYA = "lainnya", "Lainnya"

    class Status(models.TextChoices):
        AKTIF = "aktif", "Aktif"
        PINDAH = "pindah", "Pindah"
        MENINGGAL = "meninggal", "Meninggal"

    # Field yang perubahannya oleh warga harus disetujui pengurus
    IDENTITY_FIELDS = ("name", "nik", "gender", "birth_place", "birth_date")
    # Field yang boleh langsung diubah warga sendiri
    CONTACT_FIELDS = ("phone", "occupation", "religion", "marital_status")

    household = models.ForeignKey(Household, verbose_name="Keluarga", on_delete=models.CASCADE, related_name="members")
    nik = EncryptedCharField("NIK", max_length=16, blank=True)
    name = models.CharField("Nama", max_length=100)
    gender = models.CharField("Jenis kelamin", max_length=1, choices=Gender.choices)
    birth_place = models.CharField("Tempat lahir", max_length=60, blank=True)
    birth_date = models.DateField("Tanggal lahir", null=True, blank=True)
    religion = models.CharField("Agama", max_length=20, blank=True)
    marital_status = models.CharField("Status perkawinan", max_length=20, blank=True)
    relation = models.CharField("Hubungan keluarga", max_length=20, choices=Relation.choices, default=Relation.ANAK)
    occupation = models.CharField("Pekerjaan", max_length=60, blank=True)
    phone = models.CharField("No. HP", max_length=20, blank=True)
    status = models.CharField("Status", max_length=10, choices=Status.choices, default=Status.AKTIF)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["household", "id"]
        verbose_name = "Warga"
        verbose_name_plural = "Warga"

    def __str__(self):
        return self.name

    @property
    def age(self) -> int | None:
        if not self.birth_date:
            return None
        today = date.today()
        b = self.birth_date
        return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


class ChangeRequest(models.Model):
    """Pengajuan perubahan data oleh warga, menunggu persetujuan pengurus."""

    class Status(models.TextChoices):
        PENDING = "pending", "Menunggu"
        APPROVED = "disetujui", "Disetujui"
        REJECTED = "ditolak", "Ditolak"

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="change_requests")
    resident = models.ForeignKey(Resident, null=True, blank=True, on_delete=models.CASCADE, related_name="change_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    # {"field": {"old": ..., "new": ...}}
    changes = models.JSONField("Perubahan", default=dict, blank=True)
    note = models.TextField("Catatan warga", blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    review_note = models.CharField("Catatan pengurus", max_length=255, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pengajuan perubahan data"
        verbose_name_plural = "Pengajuan perubahan data"

    def __str__(self):
        return f"Pengajuan #{self.pk} {self.household.label}"


class Registration(models.Model):
    """Pendaftaran mandiri warga baru. Akun baru aktif setelah disetujui pengurus.

    Data lengkap (termasuk NIK) disimpan terenkripsi di `payload` dan dihapus setelah
    diproses, karena saat disetujui datanya sudah dipindahkan ke Household/Resident.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Menunggu"
        APPROVED = "disetujui", "Disetujui"
        REJECTED = "ditolak", "Ditolak"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registration")
    name = models.CharField("Nama pendaftar", max_length=100)
    house_label = models.CharField("Rumah", max_length=25)
    payload = EncryptedCharField("Data pendaftaran", blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    review_note = models.CharField("Catatan pengurus", max_length=255, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    household = models.ForeignKey(Household, null=True, blank=True, on_delete=models.SET_NULL, related_name="registrations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pendaftaran warga"
        verbose_name_plural = "Pendaftaran warga"

    def __str__(self):
        return f"Pendaftaran {self.name} ({self.house_label})"

    @property
    def data(self) -> dict:
        import json

        return json.loads(self.payload) if self.payload else {}
