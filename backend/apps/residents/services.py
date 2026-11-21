from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import audit
from apps.core.utils import mask

from .models import ChangeRequest, Resident


def _plain(value):
    return value.isoformat() if isinstance(value, date) else value


@transaction.atomic
def update_own_resident(resident: Resident, data: dict, user):
    """Warga mengubah data anggota keluarganya sendiri.

    Field kontak langsung disimpan; field identitas menjadi ChangeRequest.
    Mengembalikan (daftar field yang tersimpan, ChangeRequest | None).
    """
    applied, pending = [], {}
    for field, new in data.items():
        old = getattr(resident, field)
        if (old or "") == (new or ""):
            continue
        if field in Resident.CONTACT_FIELDS:
            setattr(resident, field, new)
            applied.append(field)
        elif field in Resident.IDENTITY_FIELDS:
            old_plain = mask(old) if field == "nik" else _plain(old)
            pending[field] = {"old": old_plain, "new": _plain(new)}

    if applied:
        resident.save(update_fields=[*applied, "updated_at"])
        audit(user, "warga_ubah_kontak", resident, fields=applied)

    change_request = None
    if pending:
        change_request = ChangeRequest.objects.create(
            household=resident.household, resident=resident, requested_by=user, changes=pending
        )
        audit(user, "ajukan_perubahan", change_request, fields=list(pending))
    return applied, change_request


@transaction.atomic
def approve_change(cr: ChangeRequest, user, note: str = "") -> ChangeRequest:
    if cr.status != ChangeRequest.Status.PENDING:
        raise ValidationError("Pengajuan ini sudah diproses.")
    allowed = set(Resident.IDENTITY_FIELDS) | set(Resident.CONTACT_FIELDS)
    if cr.resident and cr.changes:
        for field, change in cr.changes.items():
            if field not in allowed:
                continue
            value = change.get("new")
            if field == "birth_date" and value:
                value = date.fromisoformat(value)
            setattr(cr.resident, field, value if value is not None else "")
        cr.resident.save()
    cr.status = ChangeRequest.Status.APPROVED
    cr.review_note = note
    cr.reviewed_by = user
    cr.reviewed_at = timezone.now()
    cr.save()
    audit(user, "setujui_perubahan", cr)
    return cr


@transaction.atomic
def reject_change(cr: ChangeRequest, user, note: str) -> ChangeRequest:
    if cr.status != ChangeRequest.Status.PENDING:
        raise ValidationError("Pengajuan ini sudah diproses.")
    if not note.strip():
        raise ValidationError({"review_note": "Tuliskan alasan penolakan."})
    cr.status = ChangeRequest.Status.REJECTED
    cr.review_note = note
    cr.reviewed_by = user
    cr.reviewed_at = timezone.now()
    cr.save()
    audit(user, "tolak_perubahan", cr, note=note)
    return cr
