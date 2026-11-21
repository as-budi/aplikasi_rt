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
