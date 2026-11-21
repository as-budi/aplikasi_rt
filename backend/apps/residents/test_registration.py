import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
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


PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def submit(data=None, kk=True, ktp=True):
    body = {"data": json.dumps(data if data is not None else payload())}
    if kk:
        body["kk_file"] = SimpleUploadedFile("kk.jpg", PNG, content_type="image/jpeg")
    if ktp:
        body["ktp_file"] = SimpleUploadedFile("ktp.png", PNG, content_type="image/png")
    return APIClient().post("/api/v1/auth/register/", body, format="multipart")


def login(username, password="kuat-sekali-77"):
    return APIClient().post("/api/v1/auth/login/", {"identifier": username, "password": password})


def test_daftar_lalu_menunggu_aktivasi():
    res = submit(payload())
    assert res.status_code == 201, res.data
    user = User.objects.get(username="andi")
    assert user.is_active is False
    assert Household.objects.count() == 0  # belum dibuat sebelum disetujui
    blocked = login("andi")
    assert blocked.status_code == 403
    assert "menunggu aktivasi" in blocked.data["detail"]
    assert login("andi", "salah").status_code == 400  # status tidak dibocorkan tanpa sandi benar


def test_data_pendaftaran_terenkripsi_dan_hanya_untuk_pengurus(api, warga, pengurus):
    submit(payload())
    reg = Registration.objects.get()
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT payload FROM residents_registration WHERE id=%s", [reg.pk])
        assert b"3201999900001112" not in cur.fetchone()[0].encode()
    assert api(warga).get("/api/v1/registrations/").status_code == 403
    detail = api(pengurus).get(f"/api/v1/registrations/{reg.pk}/").data
    assert detail["data"]["members"][0]["nik"] == "3201999900001112"


def test_aktivasi_membuat_kk_dan_akun_bisa_login(api, pengurus):
    submit(payload())
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
    submit(payload(household={**payload()["household"], "block": "A", "house_number": "1"}))
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
    submit(payload())
    reg = Registration.objects.get()
    assert api(pengurus).post(f"/api/v1/registrations/{reg.pk}/reject/").status_code == 400
    api(pengurus).post(f"/api/v1/registrations/{reg.pk}/reject/", {"review_note": "Bukan warga RT 05"})
    res = login("andi")
    assert res.status_code == 403
    assert "Bukan warga RT 05" in res.data["detail"]


def test_validasi_pendaftaran(hh_a, warga):
    assert submit(payload(consent=False)).status_code == 400
    assert submit(payload(members=[])).status_code == 400
    assert submit(payload(username="budi")).data["username"]
    assert submit(payload(password="123")).data["password"]
    bad_nik = payload()
    bad_nik["members"][0]["nik"] = "12ab"
    assert submit(bad_nik).status_code == 400


def test_filter_status_rumah(api, pengurus, hh_a, hh_b):
    hh_b[0].residence_status = "singgah"
    hh_b[0].save()
    res = api(pengurus).get("/api/v1/households/", {"residence_status": "singgah"})
    assert [h["label"] for h in res.data["results"]] == ["B-2"]


def test_pendaftaran_wajib_unggah_kk_dan_ktp():
    no_kk = submit(kk=False)
    assert no_kk.status_code == 400 and "kk_file" in no_kk.data
    no_ktp = submit(ktp=False)
    assert no_ktp.status_code == 400 and "ktp_file" in no_ktp.data
    assert not User.objects.exists()


def test_dokumen_pendaftaran_jadi_data_induk_setelah_aktivasi(api, pengurus, warga):
    from apps.residents.models import Document

    submit()
    reg = Registration.objects.get()
    detail = api(pengurus).get(f"/api/v1/registrations/{reg.pk}/").data
    assert sorted(d["kind"] for d in detail["documents"]) == ["kk", "ktp"]
    kk_url = next(d["file_url"] for d in detail["documents"] if d["kind"] == "kk")
    assert api(pengurus).get(kk_url).status_code == 200
    assert api(warga).get(kk_url).status_code == 404  # warga lain tidak bisa membuka

    api(pengurus).post(f"/api/v1/registrations/{reg.pk}/approve/")
    hh = Household.objects.get(block="D", house_number="7")
    assert hh.documents.count() == 2
    assert Document.objects.get(kind="ktp").resident.name == "Andi Saputra"

    andi = APIClient()
    andi.force_authenticate(User.objects.get(username="andi"))
    own = andi.get("/api/v1/me/household/").data["documents"]
    assert len(own) == 2
    assert andi.get(own[0]["file_url"]).status_code == 200


def test_tolak_pendaftaran_menghapus_dokumen(api, pengurus):
    from apps.residents.models import Document

    submit()
    reg = Registration.objects.get()
    files = [d.file.name for d in Document.objects.all()]
    storage = Document.objects.first().file.storage
    api(pengurus).post(f"/api/v1/registrations/{reg.pk}/reject/", {"review_note": "Data tidak lengkap"})
    assert not Document.objects.exists()
    assert not any(storage.exists(f) for f in files)


def test_unggah_dokumen_warga_dan_pengurus(api, warga, warga_b, pengurus, hh_a, hh_b):
    up = lambda: SimpleUploadedFile("kk-baru.png", PNG, content_type="image/png")  # noqa: E731
    res = api(warga).post("/api/v1/documents/", {"kind": "kk", "file": up(), "note": "KK terbaru"}, format="multipart")
    assert res.status_code == 201, res.data
    assert res.data["household"] == hh_a[0].pk
    # warga tidak bisa menautkan ke anggota KK lain, tidak bisa menghapus, tidak bisa melihat dokumen KK lain
    bad = api(warga).post("/api/v1/documents/", {"kind": "ktp", "file": up(), "resident": hh_b[1].pk}, format="multipart")
    assert bad.status_code == 400
    assert api(warga).delete(f"/api/v1/documents/{res.data['id']}/").status_code == 403
    assert api(warga_b).get(res.data["file_url"]).status_code == 404
    # pengurus mengunggah untuk KK tertentu lalu menghapus
    staff = api(pengurus).post("/api/v1/documents/", {"kind": "ktp", "file": up(), "household": hh_b[0].pk, "resident": hh_b[1].pk}, format="multipart")
    assert staff.status_code == 201 and staff.data["household"] == hh_b[0].pk
    assert api(pengurus).delete(f"/api/v1/documents/{staff.data['id']}/").status_code == 204
    exe = api(warga).post("/api/v1/documents/", {"kind": "kk", "file": SimpleUploadedFile("x.exe", b"MZ")}, format="multipart")
    assert exe.status_code == 400
