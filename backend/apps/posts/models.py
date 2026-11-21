from django.conf import settings
from django.db import models
from django.utils import timezone


class Post(models.Model):
    class Type(models.TextChoices):
        BERITA = "berita", "Berita"
        KEGIATAN = "kegiatan", "Kegiatan"

    type = models.CharField("Jenis", max_length=10, choices=Type.choices, default=Type.BERITA)
    title = models.CharField("Judul", max_length=150)
    body = models.TextField("Isi")
    event_at = models.DateTimeField("Waktu kegiatan", null=True, blank=True)
    location = models.CharField("Lokasi", max_length=150, blank=True)
    is_pinned = models.BooleanField("Sematkan", default=False)
    is_published = models.BooleanField("Terbit", default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-published_at", "-created_at"]
        verbose_name = "Berita / kegiatan"
        verbose_name_plural = "Berita & kegiatan"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
