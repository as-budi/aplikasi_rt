import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_login_dengan_no_hp_dan_csrf(warga):
    warga.phone = "081299990000"
    warga.save()
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/v1/auth/csrf/")
    token = client.cookies["csrftoken"].value
    res = client.post("/api/v1/auth/login/", {"identifier": "081299990000", "password": "rahasia-123"}, HTTP_X_CSRFTOKEN=token)
    assert res.status_code == 200, res.data
    assert res.data["username"] == "budi"
    assert res.data["household_label"] == "A-1"
    assert client.get("/api/v1/auth/me/").status_code == 200


def test_login_salah_ditolak(warga):
    res = APIClient().post("/api/v1/auth/login/", {"identifier": "budi", "password": "salah"})
    assert res.status_code == 400


def test_anonim_tidak_bisa_akses_api():
    assert APIClient().get("/api/v1/auth/me/").status_code == 403


def test_superuser_selalu_berperan_admin(db):
    user = User.objects.create_superuser("root", password="rahasia-123")
    assert user.role == User.Role.ADMIN
    assert user.is_staff_rt
