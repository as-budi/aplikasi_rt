"""Isi laporan (judul, tabel) yang dirender ke Excel maupun PDF oleh render.py."""

from dataclasses import dataclass, field

from django.db.models import Sum
from django.utils import timezone

from apps.dues.models import Payment
from apps.dues.services import bill_summary
from apps.finance.models import CashEntry
from apps.finance.services import cash_report
from apps.residents.models import Household, Resident

MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
MONTHS_LONG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
STATUS_SYMBOL = {"lunas": "✓", "menunggu_verifikasi": "…", "belum_bayar": "✕", None: ""}


@dataclass
class Section:
    title: str
    headers: list[str]
    rows: list[list]
    widths: list[float]  # bobot relatif lebar kolom (PDF)
    money_cols: set[int] = field(default_factory=set)
    center_cols: set[int] = field(default_factory=set)
    footer: list | None = None
    note: str = ""


@dataclass
class Document:
    title: str
    subtitle: str
    filename: str
    sections: list[Section]
    landscape: bool = False


def _fmt_date(d) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}" if d else ""


def residents_document(year: int | None = None) -> Document:
    households = Household.objects.filter(is_active=True).prefetch_related("members")
    rows = []
    for hh in households:
        for r in hh.members.all():
            if r.status != Resident.Status.AKTIF:
                continue
            rows.append([
                hh.label, hh.get_residence_status_display(), hh.get_occupancy_display(), hh.no_kk, r.name, r.nik,
                r.gender, f"{r.birth_place}, {_fmt_date(r.birth_date)}".strip(", "), r.age if r.age is not None else "",
                r.get_relation_display(), r.religion, r.marital_status, r.occupation, r.phone,
            ])
    singgah = households.filter(residence_status="singgah").count()
    today = timezone.localdate()
    return Document(
        title="Data Warga",
        subtitle=f"{households.count()} KK ({singgah} rumah singgah) · {len(rows)} jiwa · per {_fmt_date(today)}",
        filename=f"data-warga-{today:%Y-%m-%d}",
        landscape=True,
        sections=[Section(
            title="Daftar warga aktif",
            headers=["Rumah", "Status rumah", "Hunian", "No. KK", "Nama", "NIK", "L/P", "Tempat, tgl lahir", "Umur",
                     "Hubungan", "Agama", "Perkawinan", "Pekerjaan", "No. HP"],
            rows=rows,
            widths=[5, 7, 6, 11, 13, 11, 3, 12, 4, 8, 6, 7, 9, 9],
            center_cols={0, 6, 8},
            note="Dokumen berisi data pribadi (NIK, No. KK). Simpan dan bagikan hanya untuk keperluan administrasi RT.",
        )],
    )


def dues_document(year: int) -> Document:
    data = bill_summary(year, include_private=True)
    today = timezone.localdate()
    periods = [p for p in data["periods"] if p <= today.strftime("%Y-%m")] if year == today.year else data["periods"]
    rows = []
    for r in data["rows"]:
        rows.append([r["label"], r["head_name"], *[STATUS_SYMBOL[r["cells"][p]] for p in periods], r["arrears"]])
    income = [data["income"][p] for p in periods]
    n = len(periods)
    return Document(
        title=f"Rekap Iuran {year}",
        subtitle=f"✓ lunas · … menunggu verifikasi · ✕ belum bayar · dicetak {_fmt_date(today)}",
        filename=f"rekap-iuran-{year}",
        landscape=n > 6,
        sections=[Section(
            title="Status iuran per rumah",
            headers=["Rumah", "Kepala keluarga", *[MONTHS[int(p[5:]) - 1] for p in periods], "Tunggakan"],
            rows=rows,
            widths=[5, 16, *([3.2] * n), 9],
            money_cols={n + 2},
            center_cols={0, *range(2, n + 2)},
            footer=["", "Pemasukan iuran", *income, sum(income)],
        )],
    )


def cash_document(year: int) -> Document:
    report = cash_report(year)
    today = timezone.localdate()
    last_month = today.month if year == today.year else 12
    months = [m for m in report["months"] if int(m["period"][5:]) <= last_month]

    summary_rows = [
        [MONTHS_LONG[int(m["period"][5:]) - 1], m["iuran"], m["other_income"], m["expense"], m["balance"]] for m in months
    ]
    t = report["totals"]

    tx_rows = []
    for e in CashEntry.objects.filter(date__year=year).order_by("date", "id"):
        signed_in = e.amount if e.kind == CashEntry.Kind.IN else ""
        signed_out = e.amount if e.kind == CashEntry.Kind.OUT else ""
        tx_rows.append([_fmt_date(e.date), e.get_category_display(), e.description, signed_in, signed_out])
    for m in months:  # iuran warga diringkas per bulan
        month = int(m["period"][5:])
        total = Payment.objects.filter(paid_at__year=year, paid_at__month=month).aggregate(s=Sum("total"))["s"] or 0
        if total:
            tx_rows.append([f"{MONTHS[month - 1]} {year}", "Iuran warga", f"Iuran warga bulan {MONTHS_LONG[month - 1]}", total, ""])

    return Document(
        title=f"Laporan Kas RT {year}",
        subtitle=f"Saldo awal Rp{report['opening_balance']:,} · saldo akhir Rp{report['closing_balance']:,} · dicetak {_fmt_date(today)}".replace(",", "."),
        filename=f"laporan-kas-{year}",
        sections=[
            Section(
                title="Ringkasan per bulan",
                headers=["Bulan", "Iuran warga", "Pemasukan lain", "Pengeluaran", "Saldo"],
                rows=summary_rows,
                widths=[10, 9, 9, 9, 9],
                money_cols={1, 2, 3, 4},
                footer=["Total", t["iuran"], t["other_income"], t["expense"], report["closing_balance"]],
            ),
            Section(
                title="Rincian transaksi",
                headers=["Tanggal", "Kategori", "Keterangan", "Masuk", "Keluar"],
                rows=tx_rows,
                widths=[8, 9, 20, 8, 8],
                money_cols={3, 4},
            ),
        ],
    )


DOCUMENTS = {
    "residents": (residents_document, True),  # (builder, khusus pengurus?)
    "dues": (dues_document, True),
    "cash": (cash_document, False),
}
