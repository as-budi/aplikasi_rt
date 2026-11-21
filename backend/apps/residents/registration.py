"""Pendaftaran mandiri warga baru dan aktivasinya oleh pengurus."""

import json
from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.core.models import audit

from .models import Household, Registration, Resident

MEMBER_FIELDS = (
    "name", "nik", "gender", "birth_place", "birth_date", "religion",
    "marital_status", "relation", "occupation", "phone",
)
HOUSEHOLD_FIELDS = ("no_kk", "block", "house_number", "address", "occupancy", "residence_status", "since")


def _plain(d: dict, fields) -> dict:
    return {f: (d.get(f).isoformat() if isinstance(d.get(f), date) else d.get(f)) for f in fields if f in d}


def _date(value):
    return date.fromisoformat(value) if value else None


def matching_household(label_block: str, label_number: str):
    return Household.objects.filter(block__iexact=label_block, house_number__iexact=label_number, is_active=True).first()


@transaction.atomic
def register(data: dict) -> Registration:
    """Buat akun NONAKTIF + data pendaftaran terenkripsi. members[0] adalah pendaftar sendiri."""
    household, members = data["household"], data["members"]
    user = User.objects.create_user(
        username=data["username"], password=data["password"], phone=data["phone"], email=data.get("email", ""),
        first_name=members[0]["name"], role=User.Role.WARGA, is_active=False,
    )
    payload = {
        "household": _plain(household, HOUSEHOLD_FIELDS),
        "members": [_plain(m, MEMBER_FIELDS) for m in members],
    }
    registration = Registration.objects.create(
        user=user, name=members[0]["name"], house_label=f"{household['block']}-{household['house_number']}",
        payload=json.dumps(payload),
    )
    audit(None, "pendaftaran_baru", registration)
    return registration


@transaction.atomic
def approve(reg: Registration, reviewer, household: Household | None = None) -> Registration:
    """Aktifkan akun. Buat KK baru, atau tambahkan anggota ke KK yang sudah ada (`household`)."""
    reg = Registration.objects.select_for_update().select_related("user").get(pk=reg.pk)
    if reg.status != Registration.Status.PENDING:
        raise ValidationError("Pendaftaran ini sudah diproses.")
    data = reg.data

    if household is None:
        h = data["household"]
        if matching_household(h["block"], h["house_number"]):
            raise ValidationError({
                "household": f"Rumah {reg.house_label} sudah terdaftar. Pilih 'Gabung ke KK yang sudah ada' atau tolak pendaftaran."
            })
        household = Household.objects.create(
            no_kk=h.get("no_kk") or "", block=h["block"], house_number=h["house_number"],
            address=h.get("address") or "", occupancy=h.get("occupancy") or Household.Occupancy.PEMILIK,
            residence_status=h.get("residence_status") or "menetap", since=_date(h.get("since")),
        )

    residents = [
        Resident.objects.create(
            household=household, **{f: (_date(m.get(f)) if f == "birth_date" else (m.get(f) or "")) for f in MEMBER_FIELDS}
        )
        for m in data["members"]
    ]

    user = reg.user
    user.resident = residents[0]
    user.is_active = True
    user.save(update_fields=["resident", "is_active"])

    reg.status = Registration.Status.APPROVED
    reg.household = household
    reg.reviewed_by = reviewer
    reg.reviewed_at = timezone.now()
    reg.payload = ""  # data pribadi sudah dipindahkan ke Household/Resident
    reg.save()
    audit(reviewer, "aktivasi_akun", reg, household=household.pk, members=len(residents))
    return reg


@transaction.atomic
def reject(reg: Registration, reviewer, note: str) -> Registration:
    if reg.status != Registration.Status.PENDING:
        raise ValidationError("Pendaftaran ini sudah diproses.")
    if not (note or "").strip():
        raise ValidationError({"review_note": "Tuliskan alasan penolakan; alasan ini ditampilkan saat pendaftar mencoba masuk."})
    reg.status = Registration.Status.REJECTED
    reg.review_note = note
    reg.reviewed_by = reviewer
    reg.reviewed_at = timezone.now()
    reg.payload = ""
    reg.save()
    audit(reviewer, "tolak_pendaftaran", reg, note=note)
    return reg
