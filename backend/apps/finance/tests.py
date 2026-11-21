from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.dues.models import Bill
from apps.dues.services import generate_bills, record_payment
from apps.finance.models import CashEntry
from apps.finance.services import cash_report, current_balance

pytestmark = pytest.mark.django_db


def _entry(kind, amount, d, category="lainnya"):
    return CashEntry.objects.create(kind=kind, category=category, description="x", amount=amount, date=d)


def test_laporan_kas_menghitung_saldo(fees, hh_a, pengurus):
    _entry("pemasukan", 1_000_000, date(2025, 12, 31), "saldo_awal")
    generate_bills("2026-01")
    record_payment(
        household=hh_a[0], bill_ids=list(Bill.objects.values_list("pk", flat=True)), method="tunai",
        paid_at=date(2026, 1, 5), user=pengurus,
    )
    _entry("pengeluaran", 200_000, date(2026, 1, 10), "kebersihan")
    _entry("pemasukan", 300_000, date(2026, 2, 1), "donasi")

    r = cash_report(2026)
    assert r["opening_balance"] == 1_000_000
    jan, feb = r["months"][0], r["months"][1]
    assert (jan["iuran"], jan["expense"], jan["balance"]) == (50_000, 200_000, 850_000)
    assert (feb["other_income"], feb["balance"]) == (300_000, 1_150_000)
    assert r["closing_balance"] == 1_150_000 == current_balance()
    assert r["expense_by_category"] == [{"category": "kebersihan", "label": "Kebersihan", "amount": 200_000}]


def test_warga_bisa_melihat_tapi_tidak_mencatat_kas(api, warga):
    _entry("pengeluaran", 50_000, date(2026, 3, 1))
    assert api(warga).get("/api/v1/cash-entries/").data["count"] == 1
    assert api(warga).get("/api/v1/cash-entries/report/", {"year": 2026}).status_code == 200
    res = api(warga).post("/api/v1/cash-entries/", {"kind": "pengeluaran", "category": "lainnya", "description": "x", "amount": 1, "date": "2026-03-01"})
    assert res.status_code == 403


def test_pengurus_mencatat_pengeluaran_dengan_nota(api, pengurus, warga):
    nota = SimpleUploadedFile("nota.pdf", b"%PDF-1.4 contoh", content_type="application/pdf")
    res = api(pengurus).post(
        "/api/v1/cash-entries/",
        {"kind": "pengeluaran", "category": "perbaikan", "description": "Ganti lampu jalan", "amount": 150000, "date": "2026-03-02", "receipt": nota},
        format="multipart",
    )
    assert res.status_code == 201, res.data
    assert res.data["receipt_url"]
    assert api(warga).get(res.data["receipt_url"]).status_code == 200  # transparansi: warga bisa lihat nota


def test_kategori_pemasukan_tidak_boleh_untuk_pengeluaran(api, pengurus):
    res = api(pengurus).post("/api/v1/cash-entries/", {"kind": "pengeluaran", "category": "donasi", "description": "x", "amount": 1, "date": "2026-03-01"})
    assert res.status_code == 400
    assert "category" in res.data


def _bayar(hh, pengurus, period="2026-01", paid=date(2026, 1, 5)):
    generate_bills(period)
    return record_payment(
        household=hh, bill_ids=list(Bill.objects.filter(household=hh, period=period).values_list("pk", flat=True)),
        method="transfer", paid_at=paid, user=pengurus,
    )


def test_buku_kas_pengurus_menampilkan_nama_dan_rumah(api, fees, hh_a, hh_b, pengurus):
    _bayar(hh_a[0], pengurus)
    _bayar(hh_b[0], pengurus)
    _entry("pengeluaran", 10_000, date(2026, 1, 20), "kebersihan")
    rows = api(pengurus).get("/api/v1/cash-entries/ledger/", {"year": 2026}).data
    iuran = [r for r in rows if r["source"] == "iuran"]
    assert {r["description"] for r in iuran} == {
        "Iuran Budi Santoso (A-1) · Jan 2026 · transfer",
        "Iuran Siti Aminah (B-2) · Jan 2026 · transfer",
    }
    assert rows[0]["description"] == "x"  # terbaru (20 Jan) lebih dulu
    assert iuran[0]["household_id"] in (hh_a[0].pk, hh_b[0].pk)


def test_buku_kas_warga_melihat_rincian_secara_default(api, fees, hh_a, hh_b, pengurus, warga):
    _bayar(hh_a[0], pengurus)
    _bayar(hh_b[0], pengurus)
    rows = api(warga).get("/api/v1/cash-entries/ledger/", {"year": 2026}).data
    assert {r["description"] for r in rows} == {
        "Iuran Budi Santoso (A-1) · Jan 2026 · transfer",
        "Iuran Siti Aminah (B-2) · Jan 2026 · transfer",
    }


def test_buku_kas_warga_hanya_ringkasan_bila_dimatikan(api, settings, fees, hh_a, hh_b, pengurus, warga):
    settings.CASH_LEDGER_PUBLIC_DETAIL = False
    _bayar(hh_a[0], pengurus)
    _bayar(hh_b[0], pengurus)
    rows = api(warga).get("/api/v1/cash-entries/ledger/", {"year": 2026}).data
    assert len(rows) == 1
    assert rows[0]["description"] == "Iuran warga bulan Januari (2 pembayaran)"
    assert rows[0]["amount"] == 100_000
    assert rows[0]["household_id"] is None
    assert "Siti" not in str(rows)


def test_buku_kas_filter_bulan_dan_jenis(api, fees, hh_a, pengurus):
    _bayar(hh_a[0], pengurus)
    _entry("pengeluaran", 10_000, date(2026, 2, 3))
    assert len(api(pengurus).get("/api/v1/cash-entries/ledger/", {"year": 2026, "month": 2}).data) == 1
    assert api(pengurus).get("/api/v1/cash-entries/ledger/", {"year": 2026, "kind": "pengeluaran"}).data[0]["amount"] == 10_000


def test_periods_label():
    from apps.finance.services import periods_label

    assert periods_label(["2026-02", "2025-12", "2026-01", "2026-01"]) == "Des 2025, Jan, Feb 2026"
