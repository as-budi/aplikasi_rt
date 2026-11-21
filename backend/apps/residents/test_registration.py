import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.residents.models import Household, Registration

pytestmark = pytest.mark.django_db


def payload(**overrides):
    data = {
        "username": "andi",
        "password": "kuat-sekali-77",
        "phone": "081377778888",
        "consent": True,
        "household": {
            "no_kk": "3201999900001111", "block": "D", "house_number": "7",
            "occupancy": "kontrak", "residence_status": "singgah",
        },
        "members": [
            {"name": "Andi Saputra", "nik": "3201999900001112", "gender": "L", "relation": "kepala_keluarga", "birth_date": "1990-04-02", "phone": "081377778888"},
            {"name": "Rani Saputra", "gender": "P", "relation": "istri"},
        ],
    }
    data.update(overrides)
    return data


def login(username, password="kuat-sekali-77"):
    return APIClient().post("/api/v1/auth/login/", {"identifier": username, "password": password})


def test_daftar_lalu_menunggu_aktivasi():
    res = APIClient().post("/api/v1/auth/register/", payload(), format="json")
    assert res.status_code == 201, res.data
    user = User.objects.get(username="andi")
    assert user.is_active is False
    assert Household.objects.count() == 0  # belum dibuat sebelum disetujui
    blocked = login("andi")
    assert blocked.status_code == 403
    assert "menunggu aktivasi" in blocked.data["detail"]
    assert login("andi", "salah").status_code == 400  # status tidak dibocorkan tanpa sandi benar


def test_data_pendaftaran_terenkripsi_dan_hanya_untuk_pengurus(api, warga, pengurus):
    APIClient().post("/api/v1/auth/register/", payload(), format="json")
    reg = Registration.objects.get()
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT payload FROM residents_registration WHERE id=%s", [reg.pk])
        assert b"3201999900001112" not in cur.fetchone()[0].encode()
    assert api(warga).get("/api/v1/registrations/").status_code == 403
    detail = api(pengurus).get(f"/api/v1/registrations/{reg.pk}/").data
    assert detail["data"]["members"][0]["nik"] == "3201999900001112"


def test_aktivasi_membuat_kk_dan_akun_bisa_login(api, pengurus):
    APIClient().post("/api/v1/auth/register/", payload(), format="json")
    reg = Registration.objects.get()
    res = api(pengurus).post(f"/api/v1/registrations/{reg.pk}/approve/")
    assert res.status_code == 200, res.data
    hh = Household.objects.get(block="D", house_number="7")
    assert hh.residence_status == "singgah"
    assert [m.name for m in hh.members.all()] == ["Andi Saputra", "Rani Saputra"]
    reg.refresh_from_db()
    assert reg.payload == ""  # salinan data pribadi dihapus
    me = login("andi")
    assert me.status_code == 200
    assert me.data["household_label"] == "D-7"


def test_aktivasi_bergabung_ke_kk_yang_sudah_ada(api, pengurus, hh_a):
    hh, _ = hh_a
    APIClient().post("/api/v1/auth/register/", payload(household={**payload()["household"], "block": "A", "house_number": "1"}), format="json")
    reg = Registration.objects.get()
    detail = api(pengurus).get(f"/api/v1/registrations/{reg.pk}/").data
    assert detail["matching_household"]["id"] == hh.pk
    # tanpa memilih KK -> ditolak karena rumah sudah terdaftar
    assert api(pengurus).post(f"/api/v1/registrations/{reg.pk}/approve/").status_code == 400
    ok = api(pengurus).post(f"/api/v1/registrations/{reg.pk}/approve/", {"household": hh.pk})
    assert ok.status_code == 200
    assert Household.objects.count() == 1
    assert hh.members.count() == 3


def test_tolak_pendaftaran_dengan_alasan(api, pengurus):
    APIClient().post("/api/v1/auth/register/", payload(), format="json")
    reg = Registration.objects.get()
    assert api(pengurus).post(f"/api/v1/registrations/{reg.pk}/reject/").status_code == 400
    api(pengurus).post(f"/api/v1/registrations/{reg.pk}/reject/", {"review_note": "Bukan warga RT 05"})
    res = login("andi")
    assert res.status_code == 403
    assert "Bukan warga RT 05" in res.data["detail"]


def test_validasi_pendaftaran(hh_a, warga):
    client = APIClient()
    assert client.post("/api/v1/auth/register/", payload(consent=False), format="json").status_code == 400
    assert client.post("/api/v1/auth/register/", payload(members=[]), format="json").status_code == 400
    assert client.post("/api/v1/auth/register/", payload(username="budi"), format="json").data["username"]
    assert client.post("/api/v1/auth/register/", payload(password="123"), format="json").data["password"]
    bad_nik = payload()
    bad_nik["members"][0]["nik"] = "12ab"
    assert client.post("/api/v1/auth/register/", bad_nik, format="json").status_code == 400


def test_filter_status_rumah(api, pengurus, hh_a, hh_b):
    hh_b[0].residence_status = "singgah"
    hh_b[0].save()
    res = api(pengurus).get("/api/v1/households/", {"residence_status": "singgah"})
    assert [h["label"] for h in res.data["results"]] == ["B-2"]
