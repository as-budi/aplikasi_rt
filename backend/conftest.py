from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.dues.models import FeeType
from apps.residents.models import Household, Resident


@pytest.fixture(autouse=True)
def _media_tmp(settings, tmp_path):
    from django.core.cache import cache

    settings.MEDIA_ROOT = tmp_path / "media"
    settings.USE_X_ACCEL_REDIRECT = False
    cache.clear()  # penghitung throttle (login/daftar) tidak terbawa antar tes


def make_household(block="A", number="1", head="Budi Santoso", nik="3201000000000011"):
    hh = Household.objects.create(block=block, house_number=number, no_kk="3201000000000001")
    head = Resident.objects.create(
        household=hh, name=head, gender="L", relation=Resident.Relation.KEPALA, nik=nik,
        birth_date=date(1980, 5, 17), phone="081200000001",
    )
    return hh, head


@pytest.fixture
def fees(db):
    return [
        FeeType.objects.create(name="Kebersihan", amount=20000),
        FeeType.objects.create(name="Keamanan", amount=30000),
    ]


@pytest.fixture
def hh_a(db):
    return make_household("A", "1", "Budi Santoso")


@pytest.fixture
def hh_b(db):
    return make_household("B", "2", "Siti Aminah", nik="3201000000000022")


@pytest.fixture
def warga(hh_a):
    _, head = hh_a
    return User.objects.create_user("budi", password="rahasia-123", resident=head)


@pytest.fixture
def warga_b(hh_b):
    _, head = hh_b
    return User.objects.create_user("siti", password="rahasia-123", resident=head)


@pytest.fixture
def pengurus(db):
    return User.objects.create_user("ketua", password="rahasia-123", role=User.Role.PENGURUS)


@pytest.fixture
def api():
    def _client(user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    return _client
