import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.dues.models import Bill, Payment, PaymentProof
from apps.dues.services import generate_bills

pytestmark = pytest.mark.django_db

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _upload(name="bukti.png", content=PNG):
    return SimpleUploadedFile(name, content, content_type="image/png")


def test_generate_bills_idempoten(fees, hh_a, hh_b):
    assert generate_bills("2026-01") == 4
    assert generate_bills("2026-01") == 0
    assert Bill.objects.count() == 4


def test_warga_hanya_melihat_tagihan_sendiri(api, fees, warga, hh_a, hh_b):
    generate_bills("2026-01")
    res = api(warga).get("/api/v1/bills/", {"page_size": 100})
    assert res.data["count"] == 2
    assert {b["household_label"] for b in res.data["results"]} == {"A-1"}
    # filter household milik orang lain tetap kosong
    res = api(warga).get("/api/v1/bills/", {"household": hh_b[0].pk})
    assert res.data["count"] == 0


def test_rekap_untuk_warga_tanpa_data_pribadi(api, fees, warga, pengurus, hh_a, hh_b):
    generate_bills("2026-01")
    res = api(warga).get("/api/v1/bills/summary/", {"year": 2026})
    assert res.status_code == 200
    assert "income" not in res.data
    row = res.data["rows"][0]
    assert set(row) == {"household_id", "label", "head_name", "cells"}
    assert row["cells"]["2026-01"] == "belum_bayar"
    assert row["cells"]["2026-02"] is None

    staff = api(pengurus).get("/api/v1/bills/summary/", {"year": 2026})
    assert staff.data["rows"][0]["arrears"] == 50000
    assert "income" in staff.data


def test_pengurus_catat_pembayaran_tunai(api, fees, pengurus, hh_a):
    generate_bills("2026-01")
    hh, _ = hh_a
    ids = list(Bill.objects.filter(household=hh).values_list("pk", flat=True))
    res = api(pengurus).post(
        "/api/v1/payments/", {"household": hh.pk, "bills": ids, "method": "tunai", "paid_at": "2026-01-05"}, format="json"
    )
    assert res.status_code == 201, res.data
    assert res.data["total"] == 50000
    assert set(Bill.objects.values_list("status", flat=True)) == {"lunas"}
    # tidak bisa dibayar dua kali
    again = api(pengurus).post(
        "/api/v1/payments/", {"household": hh.pk, "bills": ids, "method": "tunai", "paid_at": "2026-01-05"}, format="json"
    )
    assert again.status_code == 400


def test_warga_tidak_bisa_mencatat_pembayaran(api, fees, warga, hh_a):
    generate_bills("2026-01")
    ids = list(Bill.objects.values_list("pk", flat=True))
    res = api(warga).post(
        "/api/v1/payments/", {"household": hh_a[0].pk, "bills": ids, "method": "tunai", "paid_at": "2026-01-05"}, format="json"
    )
    assert res.status_code == 403


def test_alur_bukti_bayar_diterima(api, fees, warga, pengurus, hh_a):
    generate_bills("2026-01")
    ids = list(Bill.objects.values_list("pk", flat=True))
    res = api(warga).post(
        "/api/v1/payment-proofs/",
        {"bills": ids, "file": _upload(), "amount": 50000, "transfer_date": "2026-01-03", "method": "transfer"},
        format="multipart",
    )
    assert res.status_code == 201, res.data
    assert set(Bill.objects.values_list("status", flat=True)) == {"menunggu_verifikasi"}

    proof_id = res.data["id"]
    file_res = api(warga).get(res.data["file_url"])
    assert file_res.status_code == 200
    assert b"".join(file_res.streaming_content) == PNG

    assert api(warga).post(f"/api/v1/payment-proofs/{proof_id}/approve/").status_code == 403
    ok = api(pengurus).post(f"/api/v1/payment-proofs/{proof_id}/approve/")
    assert ok.status_code == 200, ok.data
    assert set(Bill.objects.values_list("status", flat=True)) == {"lunas"}
    assert Payment.objects.get().method == "transfer"


def test_alur_bukti_bayar_ditolak(api, fees, warga, pengurus, hh_a):
    generate_bills("2026-01")
    ids = list(Bill.objects.values_list("pk", flat=True))
    res = api(warga).post(
        "/api/v1/payment-proofs/",
        {"bills": ids, "file": _upload(), "amount": 50000, "transfer_date": "2026-01-03", "method": "transfer"},
        format="multipart",
    )
    proof_id = res.data["id"]
    assert api(pengurus).post(f"/api/v1/payment-proofs/{proof_id}/reject/").status_code == 400
    rej = api(pengurus).post(f"/api/v1/payment-proofs/{proof_id}/reject/", {"review_note": "Nominal kurang"})
    assert rej.status_code == 200
    assert PaymentProof.objects.get().status == "ditolak"
    assert set(Bill.objects.values_list("status", flat=True)) == {"belum_bayar"}


def test_bukti_bayar_keluarga_lain_tidak_bisa_dibuka(api, fees, warga, warga_b, hh_a, hh_b):
    generate_bills("2026-01")
    ids = list(Bill.objects.filter(household=hh_a[0]).values_list("pk", flat=True))
    res = api(warga).post(
        "/api/v1/payment-proofs/",
        {"bills": ids, "file": _upload(), "amount": 50000, "transfer_date": "2026-01-03", "method": "transfer"},
        format="multipart",
    )
    assert api(warga_b).get(res.data["file_url"]).status_code == 404


def test_tidak_bisa_unggah_bukti_untuk_tagihan_keluarga_lain(api, fees, warga, hh_a, hh_b):
    generate_bills("2026-01")
    ids = list(Bill.objects.filter(household=hh_b[0]).values_list("pk", flat=True))
    res = api(warga).post(
        "/api/v1/payment-proofs/",
        {"bills": ids, "file": _upload(), "amount": 50000, "transfer_date": "2026-01-03", "method": "transfer"},
        format="multipart",
    )
    assert res.status_code == 400


def test_file_bukti_harus_gambar_atau_pdf(api, fees, warga, hh_a):
    generate_bills("2026-01")
    ids = list(Bill.objects.values_list("pk", flat=True))
    res = api(warga).post(
        "/api/v1/payment-proofs/",
        {"bills": ids, "file": _upload("virus.exe", b"MZ"), "amount": 1, "transfer_date": "2026-01-03", "method": "transfer"},
        format="multipart",
    )
    assert res.status_code == 400
    assert "file" in res.data


def test_x_accel_redirect_di_produksi(api, settings, fees, warga, hh_a):
    generate_bills("2026-01")
    ids = list(Bill.objects.values_list("pk", flat=True))
    res = api(warga).post(
        "/api/v1/payment-proofs/",
        {"bills": ids, "file": _upload(), "amount": 50000, "transfer_date": "2026-01-03", "method": "transfer"},
        format="multipart",
    )
    settings.USE_X_ACCEL_REDIRECT = True
    file_res = api(warga).get(res.data["file_url"])
    assert file_res["X-Accel-Redirect"].startswith("/protected-media/proofs/")


def test_dashboard_sesuai_peran(api, fees, warga, pengurus, hh_a):
    generate_bills()
    w = api(warga).get("/api/v1/dashboard/").data
    assert w["staff"] is None
    assert w["me"]["arrears_total"] == 50000
    s = api(pengurus).get("/api/v1/dashboard/").data
    assert s["staff"]["households"] == 1
    assert s["staff"]["top_arrears"][0]["label"] == "A-1"
