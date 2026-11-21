import pytest
from django.db import connection

from apps.residents.models import ChangeRequest, Household, Resident

pytestmark = pytest.mark.django_db


def test_nik_tersimpan_terenkripsi(hh_a):
    _, head = hh_a
    with connection.cursor() as cur:
        cur.execute("SELECT nik FROM residents_resident WHERE id = %s", [head.pk])
        raw = cur.fetchone()[0]
    assert raw != "3201000000000011"
    assert Resident.objects.get(pk=head.pk).nik == "3201000000000011"


def test_warga_tidak_bisa_melihat_daftar_kk(api, warga):
    assert api(warga).get("/api/v1/households/").status_code == 403
    assert api(warga).get("/api/v1/residents/").status_code == 403


def test_pengurus_melihat_semua_kk_dan_nik_lengkap(api, pengurus, hh_a, hh_b):
    res = api(pengurus).get("/api/v1/households/")
    assert res.status_code == 200
    assert res.data["count"] == 2
    assert "•" in res.data["results"][0]["no_kk_masked"]
    detail = api(pengurus).get(f"/api/v1/households/{hh_a[0].pk}/")
    assert detail.data["members"][0]["nik"] == "3201000000000011"


def test_pencarian_kk_berdasarkan_nama_anggota(api, pengurus, hh_a, hh_b):
    res = api(pengurus).get("/api/v1/households/", {"search": "siti"})
    assert [r["label"] for r in res.data["results"]] == ["B-2"]


def test_hapus_kk_hanya_menonaktifkan(api, pengurus, hh_a):
    hh, _ = hh_a
    assert api(pengurus).delete(f"/api/v1/households/{hh.pk}/").status_code == 204
    assert Household.objects.get(pk=hh.pk).is_active is False


def test_data_saya_nik_disamarkan(api, warga):
    res = api(warga).get("/api/v1/me/household/")
    assert res.status_code == 200
    member = res.data["members"][0]
    assert "nik" not in member
    assert member["nik_masked"].startswith("3201") and "•" in member["nik_masked"]


def test_warga_tidak_bisa_mengubah_keluarga_lain(api, warga, hh_b):
    _, other = hh_b
    res = api(warga).patch(f"/api/v1/me/residents/{other.pk}/", {"phone": "0800"}, format="json")
    assert res.status_code == 404


def test_ubah_kontak_langsung_identitas_menunggu_persetujuan(api, warga, pengurus, hh_a):
    _, head = hh_a
    res = api(warga).patch(
        f"/api/v1/me/residents/{head.pk}/", {"phone": "081311112222", "name": "Budi S. Santoso"}, format="json"
    )
    assert res.status_code == 200, res.data
    assert res.data["applied"] == ["phone"]
    cr_id = res.data["change_request"]["id"]
    head.refresh_from_db()
    assert head.phone == "081311112222"
    assert head.name == "Budi Santoso"  # belum berubah

    assert api(warga).post(f"/api/v1/change-requests/{cr_id}/approve/").status_code == 403
    assert api(pengurus).post(f"/api/v1/change-requests/{cr_id}/approve/").status_code == 200
    head.refresh_from_db()
    assert head.name == "Budi S. Santoso"


def test_tolak_pengajuan_wajib_alasan(api, warga, pengurus, hh_a):
    _, head = hh_a
    cr = ChangeRequest.objects.create(household=head.household, resident=head, changes={"name": {"old": "a", "new": "b"}})
    assert api(pengurus).post(f"/api/v1/change-requests/{cr.pk}/reject/", {}).status_code == 400
    res = api(pengurus).post(f"/api/v1/change-requests/{cr.pk}/reject/", {"review_note": "Lampirkan KK"})
    assert res.status_code == 200
    assert res.data["status"] == "ditolak"


def test_warga_hanya_melihat_pengajuan_sendiri(api, warga, warga_b, hh_b):
    hh, _ = hh_b
    ChangeRequest.objects.create(household=hh, note="pindah rumah")
    assert api(warga).get("/api/v1/change-requests/").data["count"] == 0
    assert api(warga_b).get("/api/v1/change-requests/").data["count"] == 1


def test_pengurus_membuat_akun_warga(api, pengurus, hh_a):
    _, head = hh_a
    res = api(pengurus).post(f"/api/v1/residents/{head.pk}/create-account/", {"username": "budi2", "password": "aman-sekali-9"})
    assert res.status_code == 201, res.data
    again = api(pengurus).post(f"/api/v1/residents/{head.pk}/create-account/", {"username": "budi3", "password": "aman-sekali-9"})
    assert again.status_code == 400
