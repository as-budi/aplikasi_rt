from io import BytesIO

import pytest
from openpyxl import load_workbook

from apps.dues.services import generate_bills

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("kind", ["residents", "dues", "cash"])
def test_pengurus_ekspor_excel_dan_pdf(api, pengurus, fees, hh_a, kind):
    generate_bills()
    xlsx = api(pengurus).get(f"/api/v1/exports/{kind}/", {"file": "xlsx"})
    assert xlsx.status_code == 200
    assert xlsx["Content-Disposition"].startswith("attachment;")
    wb = load_workbook(BytesIO(xlsx.content))
    assert wb.worksheets[0]["A1"].value

    pdf = api(pengurus).get(f"/api/v1/exports/{kind}/", {"file": "pdf"})
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_ekspor_data_warga_berisi_nik_lengkap(api, pengurus, hh_a):
    res = api(pengurus).get("/api/v1/exports/residents/", {"file": "xlsx"})
    values = [c.value for row in load_workbook(BytesIO(res.content)).worksheets[0].iter_rows() for c in row]
    assert "3201000000000011" in values


def test_warga_hanya_boleh_ekspor_kas(api, warga):
    assert api(warga).get("/api/v1/exports/residents/", {"file": "xlsx"}).status_code == 403
    assert api(warga).get("/api/v1/exports/dues/", {"file": "pdf"}).status_code == 403
    assert api(warga).get("/api/v1/exports/cash/", {"file": "pdf"}).status_code == 200


def test_ekspor_tidak_dikenal(api, pengurus):
    assert api(pengurus).get("/api/v1/exports/rahasia/").status_code == 404
    assert api(pengurus).get("/api/v1/exports/cash/", {"file": "docx"}).status_code == 400


@pytest.mark.parametrize("public", [True, False])
def test_ekspor_kas_rincian_nama_sesuai_pengaturan(api, settings, pengurus, warga, fees, hh_a, public):
    settings.CASH_LEDGER_PUBLIC_DETAIL = public
    from datetime import date

    from apps.dues.models import Bill
    from apps.dues.services import record_payment

    generate_bills("2026-01")
    record_payment(household=hh_a[0], bill_ids=list(Bill.objects.values_list("pk", flat=True)), method="tunai", paid_at=date(2026, 1, 5), user=pengurus)

    def cells(user):
        res = api(user).get("/api/v1/exports/cash/", {"file": "xlsx", "year": 2026})
        ws = load_workbook(BytesIO(res.content)).worksheets[1]
        return [c.value for row in ws.iter_rows() for c in row]

    assert "Iuran Budi Santoso (A-1) · Jan 2026 · tunai" in cells(pengurus)
    warga_cells = cells(warga)
    if public:
        assert "Iuran Budi Santoso (A-1) · Jan 2026 · tunai" in warga_cells
    else:
        assert "Iuran warga bulan Januari (1 pembayaran)" in warga_cells
        assert not any("Budi" in str(v) for v in warga_cells)
