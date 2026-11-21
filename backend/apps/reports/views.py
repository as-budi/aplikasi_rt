from django.http import Http404, HttpResponse
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.views import APIView

from apps.core.models import audit
from apps.core.permissions import is_staff_rt
from apps.finance.views import show_detail

from .documents import DOCUMENTS
from .render import to_pdf, to_xlsx

CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


class ExportView(APIView):
    """GET /api/v1/exports/<residents|dues|cash>/?file=xlsx|pdf&year=2026

    Parameter bernama `file` (bukan `format`, yang dipakai DRF untuk content negotiation).
    """

    def get(self, request, kind):
        if kind not in DOCUMENTS:
            raise Http404
        builder, staff_only = DOCUMENTS[kind]
        if staff_only and not is_staff_rt(request.user):
            raise PermissionDenied("Hanya pengurus RT yang dapat mengekspor data ini.")
        fmt = request.query_params.get("file", "xlsx")
        if fmt not in CONTENT_TYPES:
            raise ValidationError({"file": "Pilih xlsx atau pdf."})
        try:
            year = int(request.query_params.get("year") or timezone.localdate().year)
        except ValueError:
            raise ValidationError({"year": "Tahun tidak valid."})

        doc = builder(year, private=show_detail(request.user))
        content = to_xlsx(doc) if fmt == "xlsx" else to_pdf(doc)
        audit(request.user, f"ekspor_{kind}", f"{doc.filename}.{fmt}")

        response = HttpResponse(content, content_type=CONTENT_TYPES[fmt])
        response["Content-Disposition"] = f'attachment; filename="{doc.filename}.{fmt}"'
        response["Cache-Control"] = "private, no-store"
        return response
