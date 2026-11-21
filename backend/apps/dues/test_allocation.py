"""Bayar beberapa bulan sekaligus, bayar di muka, lebih/kurang bayar, dan saldo titipan.

Tarif di fixture `fees`: Kebersihan 20.000 + Keamanan 30.000 = 50.000 per bulan.
"""

from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.utils import current_period
from apps.dues.models import Bill, Payment
from apps.dues.services import add_months, generate_bills
from apps.finance.models import CashEntry
from apps.finance.services import current_balance

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def bill_ids(hh, *periods):
    qs = Bill.objects.filter(household=hh)
    if periods:
        qs = qs.filter(period__in=periods)
    return list(qs.values_list("pk", flat=True))


def statuses(hh):
    out = {}
    for b in Bill.objects.filter(household=hh):
        out.setdefault(b.period, set()).add(b.status)
    return {p: (s.pop() if len(s) == 1 else s) for p, s in sorted(out.items())}


def pay(api, user, hh, amount=None, refund=False, periods=(), bills=None):
    body = {"household": hh.pk, "bills": bill_ids(hh) if bills is None else bills, "periods": list(periods),
            "method": "tunai", "paid_at": "2026-01-05", "refund_excess": refund}
    if amount is not None:
        body["amount"] = amount
    return api(user).post("/api/v1/payments/", body, format="json")


def upload(api, user, amount, bills=(), periods=()):
    return api(user).post(
        "/api/v1/payment-proofs/",
        {"bills": list(bills), "periods": list(periods), "amount": amount, "transfer_date": "2026-01-03",
         "method": "transfer", "file": SimpleUploadedFile("b.png", PNG, content_type="image/png")},
        format="multipart",
    )


# ---------- lebih bayar ----------

def test_lebih_bayar_jadi_titipan_dan_kas_mencatat_uang_sebenarnya(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    res = pay(api, pengurus, hh, amount=70_000)
    assert res.status_code == 201, res.data
    assert res.data["total"] == 70_000 and res.data["credit_change"] == 20_000
    hh.refresh_from_db()
    assert hh.credit == 20_000
    assert current_balance() == 70_000  # kas = uang yang benar-benar masuk


def test_lebih_bayar_dikembalikan_dicatat_sebagai_pengeluaran(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    res = pay(api, pengurus, hh, amount=70_000, refund=True)
    assert res.data["refund"] == 20_000
    hh.refresh_from_db()
    assert hh.credit == 0
    entry = CashEntry.objects.get()
    assert (entry.kind, entry.category, entry.amount) == ("pengeluaran", "pengembalian", 20_000)
    assert current_balance() == 50_000


def test_titipan_otomatis_melunasi_tagihan_bulan_berikutnya(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    pay(api, pengurus, hh, amount=110_000)  # 50 rb Jan + titipan 60 rb
    generate_bills("2026-02")
    hh.refresh_from_db()
    assert statuses(hh) == {"2026-01": "lunas", "2026-02": "lunas"}
    assert hh.credit == 10_000
    auto = Payment.objects.get(method="titipan")
    assert auto.total == 0 and auto.credit_change == -50_000
    assert current_balance() == 110_000  # titipan tidak dihitung dua kali


# ---------- kurang bayar ----------

def test_kurang_bayar_bulan_tertua_dulu_sisanya_titipan(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    generate_bills("2026-02")
    res = pay(api, pengurus, hh, amount=70_000)
    assert res.status_code == 201
    hh.refresh_from_db()
    assert statuses(hh) == {"2026-01": "lunas", "2026-02": "belum_bayar"}
    assert hh.credit == 20_000
    # bayar kekurangan 30 rb -> Februari lunas, titipan habis
    pay(api, pengurus, hh, amount=30_000, bills=bill_ids(hh, "2026-02"))
    hh.refresh_from_db()
    assert statuses(hh)["2026-02"] == "lunas" and hh.credit == 0


def test_kurang_bayar_tidak_melunasi_sebagian_bulan(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    pay(api, pengurus, hh, amount=20_000)  # hanya cukup untuk Kebersihan
    hh.refresh_from_db()
    # bulan tidak lunas sebagian: seluruh Januari tetap belum, uang jadi titipan
    assert statuses(hh) == {"2026-01": "belum_bayar"}
    assert hh.credit == 20_000


def test_bayar_nol_ditolak(api, fees, pengurus, hh_a):
    generate_bills("2026-01")
    assert pay(api, pengurus, hh_a[0], amount=0).status_code == 400


# ---------- bukti bayar ----------

def test_bukti_kurang_bayar_bulan_tak_tertutup_kembali_belum(api, fees, warga, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    generate_bills("2026-02")
    proof = upload(api, warga, 60_000, bills=bill_ids(hh)).data
    assert set(statuses(hh).values()) == {"menunggu_verifikasi"}
    ok = api(pengurus).post(f"/api/v1/payment-proofs/{proof['id']}/approve/")
    assert ok.status_code == 200, ok.data
    hh.refresh_from_db()
    assert statuses(hh) == {"2026-01": "lunas", "2026-02": "belum_bayar"}
    assert hh.credit == 10_000


def test_pengurus_bisa_mengoreksi_nominal_yang_masuk(api, fees, warga, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    proof = upload(api, warga, 5_000, bills=bill_ids(hh)).data  # warga salah ketik
    api(pengurus).post(f"/api/v1/payment-proofs/{proof['id']}/approve/", {"amount": 50_000})
    assert statuses(hh) == {"2026-01": "lunas"}
    assert Payment.objects.get().total == 50_000


def test_bukti_lebih_bayar_dengan_pengembalian(api, fees, warga, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    proof = upload(api, warga, 80_000, bills=bill_ids(hh)).data
    assert proof["household_credit"] == 0
    api(pengurus).post(f"/api/v1/payment-proofs/{proof['id']}/approve/", {"refund_excess": True})
    hh.refresh_from_db()
    assert hh.credit == 0
    assert CashEntry.objects.get().amount == 30_000


# ---------- bayar di muka ----------

def test_bayar_di_muka_lewat_bukti(api, fees, warga, pengurus, hh_a):
    hh, _ = hh_a
    now = current_period()
    generate_bills(now)
    future = [add_months(now, 1), add_months(now, 2)]
    opts = api(warga).get("/api/v1/bills/prepay-options/").data
    assert opts["periods"][:2] == future and len(opts["periods"]) == 12 and opts["monthly_total"] == 50_000

    proof = upload(api, warga, 150_000, bills=bill_ids(hh, now), periods=future).data
    assert sorted({b["period"] for b in proof["bills"]}) == [now, *future]
    api(pengurus).post(f"/api/v1/payment-proofs/{proof['id']}/approve/")
    assert statuses(hh) == {now: "lunas", future[0]: "lunas", future[1]: "lunas"}
    # saat bulannya tiba, tagihan tidak dibuat ulang
    assert generate_bills(future[0]) == 0
    assert future[0] not in api(warga).get("/api/v1/bills/prepay-options/").data["periods"]


def test_bayar_di_muka_dibatasi_12_bulan(api, fees, warga, hh_a):
    now = current_period()
    too_far = upload(api, warga, 50_000, periods=[add_months(now, 13)])
    assert too_far.status_code == 400 and "periods" in too_far.data
    past = upload(api, warga, 50_000, periods=[now])
    assert past.status_code == 400


def test_tolak_bukti_bayar_di_muka_menghapus_tagihan_mendatang(api, fees, warga, pengurus, hh_a):
    hh, _ = hh_a
    future = add_months(current_period(), 1)
    proof = upload(api, warga, 50_000, periods=[future]).data
    assert Bill.objects.filter(period=future).count() == 2
    api(pengurus).post(f"/api/v1/payment-proofs/{proof['id']}/reject/", {"review_note": "Bukti buram"})
    assert not Bill.objects.filter(period=future).exists()


def test_kurang_bayar_di_muka_tagihan_mendatang_tidak_tersisa(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    now = current_period()
    generate_bills(now)
    res = pay(api, pengurus, hh, amount=75_000, periods=[add_months(now, 1)])
    assert res.status_code == 201
    hh.refresh_from_db()
    assert statuses(hh) == {now: "lunas"}  # bulan depan tidak tertutup -> tagihannya dihapus
    assert hh.credit == 25_000


def test_buku_kas_menulis_titipan(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    pay(api, pengurus, hh, amount=70_000)
    rows = api(pengurus).get("/api/v1/cash-entries/ledger/", {"year": 2026}).data
    assert rows[0]["description"] == "Iuran Budi Santoso (A-1) · Jan 2026 · tunai · +Rp20.000 titipan"
    assert rows[0]["amount"] == 70_000
    assert date(2026, 1, 5).isoformat() == str(rows[0]["date"])
