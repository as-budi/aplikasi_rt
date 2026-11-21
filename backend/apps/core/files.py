import mimetypes

from django.conf import settings
from django.http import FileResponse, HttpResponse


def protected_file_response(field_file):
    """Kirim file privat SETELAH hak akses diperiksa oleh view pemanggil.

    Produksi: Nginx melayani file lewat lokasi `internal` /protected-media/ (X-Accel-Redirect).
    Pengembangan: Django mengirim file langsung.
    """
    content_type = mimetypes.guess_type(field_file.name)[0] or "application/octet-stream"
    if settings.USE_X_ACCEL_REDIRECT:
        response = HttpResponse(content_type=content_type)
        response["X-Accel-Redirect"] = "/protected-media/" + field_file.name
    else:
        response = FileResponse(field_file.open("rb"), content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    return response


ALLOWED_UPLOAD_EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


def validate_private_upload(f, label="File"):
    """Validasi unggahan privat (bukti bayar, nota, KK/KTP): format & ukuran."""
    import os

    from rest_framework.exceptions import ValidationError

    if not f:
        return f
    if os.path.splitext(f.name)[1].lower() not in ALLOWED_UPLOAD_EXT:
        raise ValidationError(f"{label} harus berformat JPG, PNG, WEBP, atau PDF.")
    if f.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(f"Ukuran {label.lower()} maksimal 5 MB.")
    return f
