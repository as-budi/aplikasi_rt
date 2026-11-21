import re

from django.utils import timezone

PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Status tagihan (disalin agar modul lain tidak saling import)
BELUM = "belum_bayar"
MENUNGGU = "menunggu_verifikasi"
LUNAS = "lunas"


def current_period() -> str:
    return timezone.localdate().strftime("%Y-%m")


def is_valid_period(value: str) -> bool:
    return bool(value) and bool(PERIOD_RE.match(value))


def mask(value: str | None, keep_start: int = 4, keep_end: int = 4) -> str:
    """3201123456780012 -> 3201••••••••0012"""
    if not value:
        return ""
    if len(value) <= keep_start + keep_end:
        return "•" * len(value)
    return value[:keep_start] + "•" * (len(value) - keep_start - keep_end) + value[-keep_end:]


def aggregate_status(statuses) -> str | None:
    """Gabungkan status beberapa tagihan (beberapa jenis iuran) dalam satu bulan."""
    statuses = set(statuses)
    if not statuses:
        return None
    if statuses == {LUNAS}:
        return LUNAS
    if MENUNGGU in statuses:
        return MENUNGGU
    return BELUM
