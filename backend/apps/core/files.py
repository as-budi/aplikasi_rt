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
