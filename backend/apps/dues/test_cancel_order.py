"""Pembatalan pembayaran & aturan urutan bulan. Tarif fixture: 50.000/bulan."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.utils import current_period
from apps.dues.models import Bill, Payment, PaymentProof
from apps.dues.services import add_months, generate_bills
from apps.finance.models import CashEntry
from apps.finance.services import current_balance

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def ids(hh, *periods):
    qs = Bill.objects.filter(household=hh)
    return list((qs.filter(period__in=periods) if periods else qs).values_list("pk", flat=True))


def statuses(hh):
    return dict(sorted({b.period: b.status for b in Bill.objects.filter(household=hh)}.items()))


def pay(api, user, hh, bills, amount=None, periods=(), refund=False):
    body = {"household": hh.pk, "bills": bills, "periods": list(periods), "method": "tunai", "paid_at": "2026-01-05", "refund_excess": refund}
    if amount is not None:
        body["amount"] = amount
    res = api(user).post("/api/v1/payments/", body, format="json")
    assert res.status_code == 201, res.data
    return res.data


def cancel(api, user, payment_id, reason="Uang tidak masuk ke rekening"):
    return api(user).post(f"/api/v1/payments/{payment_id}/cancel/", {"reason": reason})


def upload(api, user, bills=(), periods=(), amount=50_000):
    return api(user).post(
        "/api/v1/payment-proofs/",
        {"bills": list(bills), "periods": list(periods), "amount": amount, "transfer_date": "2026-01-03",
         "method": "transfer", "file": SimpleUploadedFile("b.png", PNG, content_type="image/png")},
        format="multipart",
    )


# ---------- pembatalan ----------

def test_batalkan_pembayaran_mengembalikan_tagihan_dan_kas(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    p = pay(api, pengurus, hh, ids(hh))
    assert current_balance() == 50_000
    assert cancel(api, pengurus, p["id"], "").status_code == 400  # alasan wajib
    res = cancel(api, pengurus, p["id"])
    assert res.status_code == 200, res.data
    assert res.data["cancelled_at"] and res.data["cancel_reason"] == "Uang tidak masuk ke rekening"
    assert statuses(hh) == {"2026-01": "belum_bayar"}
    assert current_balance() == 0
    assert cancel(api, pengurus, p["id"]).status_code == 400  # tidak bisa dua kali
    # tetap tampil di riwayat (tidak dihapus), tapi hilang dari buku kas
    assert api(pengurus).get("/api/v1/payments/", {"household": hh.pk}).data["count"] == 1
    assert api(pengurus).get("/api/v1/cash-entries/ledger/", {"year": 2026}).data == []


def test_warga_tidak_bisa_membatalkan(api, fees, pengurus, warga, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    p = pay(api, pengurus, hh, ids(hh))
    assert cancel(api, warga, p["id"]).status_code == 403


def test_batalkan_bukti_yang_sudah_diterima(api, fees, warga, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills(current_period())
    proof = upload(api, warga, ids(hh)).data
    approved = api(pengurus).post(f"/api/v1/payment-proofs/{proof['id']}/approve/").data
    payment = Payment.objects.get()
    cancel(api, pengurus, payment.pk, "Mutasi ternyata dari KK lain")
    proof_obj = PaymentProof.objects.get(pk=approved["id"])
    assert proof_obj.status == "dibatalkan"
    assert "KK lain" in proof_obj.review_note
    assert set(statuses(hh).values()) == {"belum_bayar"}


def test_batalkan_bayar_di_muka_menghapus_tagihan_mendatang(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    nxt = add_months(current_period(), 1)
    p = pay(api, pengurus, hh, [], periods=[nxt])
    assert Bill.objects.filter(period=nxt).exists()
    cancel(api, pengurus, p["id"])
    assert not Bill.objects.filter(period=nxt).exists()


def test_batalkan_lebih_bayar_mengurangi_titipan(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    p = pay(api, pengurus, hh, ids(hh), amount=70_000)
    hh.refresh_from_db()
    assert hh.credit == 20_000
    cancel(api, pengurus, p["id"])
    hh.refresh_from_db()
    assert hh.credit == 0


def test_batalkan_pengembalian_ikut_dihapus_dari_kas(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    p = pay(api, pengurus, hh, ids(hh), amount=70_000, refund=True)
    assert CashEntry.objects.count() == 1
    cancel(api, pengurus, p["id"])
    assert CashEntry.objects.count() == 0
    assert current_balance() == 0


def test_batalkan_berantai_pemakaian_titipan_otomatis(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    p = pay(api, pengurus, hh, ids(hh), amount=100_000)  # Jan lunas + titipan 50 rb
    generate_bills("2026-02")  # Feb lunas otomatis dari titipan
    assert statuses(hh) == {"2026-01": "lunas", "2026-02": "lunas"}
    auto = Payment.objects.get(method="titipan")
    assert cancel(api, pengurus, auto.pk).status_code == 400  # tidak dibatalkan langsung
    assert cancel(api, pengurus, p["id"]).status_code == 200
    hh.refresh_from_db()
    assert statuses(hh) == {"2026-01": "belum_bayar", "2026-02": "belum_bayar"}
    assert hh.credit == 0
    auto.refresh_from_db()
    assert auto.cancelled_at is not None


def test_batal_ditolak_bila_titipan_sudah_dipakai_pembayaran_lain(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    generate_bills("2026-02")
    first = pay(api, pengurus, hh, ids(hh, "2026-01"), amount=70_000)  # titipan 20 rb
    second = pay(api, pengurus, hh, ids(hh, "2026-02"), amount=30_000)  # 30 rb + titipan 20 rb
    res = cancel(api, pengurus, first["id"])
    assert res.status_code == 400
    assert f"#{second['id']}" in str(res.data)
    # urutan yang benar: batalkan yang terbaru dulu
    assert cancel(api, pengurus, second["id"]).status_code == 200
    assert cancel(api, pengurus, first["id"]).status_code == 200
    hh.refresh_from_db()
    assert hh.credit == 0 and set(statuses(hh).values()) == {"belum_bayar"}


def test_batalkan_pembayaran_yang_memakai_titipan_mengembalikan_titipan(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    generate_bills("2026-02")
    pay(api, pengurus, hh, ids(hh, "2026-01"), amount=70_000)  # titipan 20 rb
    second = pay(api, pengurus, hh, ids(hh, "2026-02"), amount=30_000)
    hh.refresh_from_db()
    assert hh.credit == 0
    cancel(api, pengurus, second["id"])
    hh.refresh_from_db()
    assert hh.credit == 20_000 and statuses(hh)["2026-02"] == "belum_bayar"


# ---------- urutan bulan (warga) ----------

def test_warga_harus_mulai_dari_tunggakan_tertua(api, fees, warga, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    generate_bills("2026-02")
    skip = upload(api, warga, ids(hh, "2026-02"))
    assert skip.status_code == 400 and "Jan 2026" in str(skip.data)
    assert upload(api, warga, ids(hh, "2026-01")).status_code == 201  # tertua dulu: boleh


def test_bayar_di_muka_harus_melunasi_tunggakan_dan_berurutan(api, fees, warga, hh_a):
    hh, _ = hh_a
    now = current_period()
    generate_bills(now)
    n1, n2 = add_months(now, 1), add_months(now, 2)
    no_arrears = upload(api, warga, [], periods=[n1])
    assert no_arrears.status_code == 400 and "tunggakan" in str(no_arrears.data)
    gap = upload(api, warga, ids(hh, now), periods=[n2])
    assert gap.status_code == 400 and "periods" in gap.data
    assert not Bill.objects.filter(period__gt=now).exists()  # tidak ada tagihan yatim
    assert upload(api, warga, ids(hh, now), periods=[n1, n2], amount=150_000).status_code == 201


def test_tagihan_menunggu_verifikasi_tidak_menghalangi(api, fees, warga, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    generate_bills("2026-02")
    assert upload(api, warga, ids(hh, "2026-01")).status_code == 201  # Jan menunggu verifikasi
    assert upload(api, warga, ids(hh, "2026-02")).status_code == 201


def test_pengurus_boleh_mencatat_tidak_berurutan(api, fees, pengurus, hh_a):
    hh, _ = hh_a
    generate_bills("2026-01")
    generate_bills("2026-02")
    pay(api, pengurus, hh, ids(hh, "2026-02"))  # pengecualian (mis. kesepakatan) tetap bisa dicatat
    assert statuses(hh) == {"2026-01": "belum_bayar", "2026-02": "lunas"}
