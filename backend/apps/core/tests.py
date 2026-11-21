import pytest
from django.core.management import call_command

from apps.finance.models import CashEntry
from apps.residents.models import Household, Registration

pytestmark = pytest.mark.django_db


def test_seed_demo_dari_kosong_dan_idempoten(settings, tmp_path):
    call_command("seed_demo")
    assert Household.objects.count() == 8
    assert Household.objects.filter(residence_status="singgah").count() == 1
    assert CashEntry.objects.exists()
    assert Registration.objects.filter(status="pending").count() == 1
    call_command("seed_demo")  # dijalankan ulang tidak menggandakan data
    assert Household.objects.count() == 8
    assert Registration.objects.count() == 1
