from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        PENGURUS = "pengurus", "Pengurus"
        WARGA = "warga", "Warga"

    role = models.CharField(
        "Peran",
        max_length=10,
        choices=Role.choices,
        default=Role.WARGA,
        help_text="Admin selalu superuser. Untuk menurunkan admin, ubah peran dan hapus centang 'Superuser status'.",
    )
    phone = models.CharField("No. HP", max_length=20, blank=True)
    resident = models.OneToOneField(
        "residents.Resident",
        verbose_name="Data warga",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user",
        help_text="Menautkan akun ke data warga (untuk 'Data Saya' dan iuran keluarga).",
    )

    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Pengguna"

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        if self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        return self.get_full_name() or (self.resident.name if self.resident else "") or self.username

    @property
    def is_staff_rt(self) -> bool:
        return self.role in (self.Role.ADMIN, self.Role.PENGURUS)

    @property
    def household(self):
        return self.resident.household if self.resident_id else None
