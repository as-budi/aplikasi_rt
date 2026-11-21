from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Catatan siapa mengubah apa. Dilihat admin lewat Django Admin."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField("Aksi", max_length=50)
    target = models.CharField("Objek", max_length=200)
    data = models.JSONField("Detail", default=dict, blank=True)
    created_at = models.DateTimeField("Waktu", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Log aktivitas"
        verbose_name_plural = "Log aktivitas"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.target}"


def audit(user, action: str, target, **data) -> None:
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        target=str(target)[:200],
        data=data,
    )
