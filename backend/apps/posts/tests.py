import pytest

from apps.posts.models import Post

pytestmark = pytest.mark.django_db


def test_warga_tidak_bisa_membuat_posting(api, warga):
    res = api(warga).post("/api/v1/posts/", {"type": "berita", "title": "x", "body": "y"})
    assert res.status_code == 403


def test_pengurus_membuat_kegiatan_wajib_tanggal(api, pengurus):
    res = api(pengurus).post("/api/v1/posts/", {"type": "kegiatan", "title": "Kerja bakti", "body": "Bawa sapu"})
    assert res.status_code == 400
    res = api(pengurus).post(
        "/api/v1/posts/",
        {"type": "kegiatan", "title": "Kerja bakti", "body": "Bawa sapu", "event_at": "2030-01-05T07:00"},
    )
    assert res.status_code == 201, res.data
    assert res.data["author_name"] == "ketua"
    assert res.data["event_at"].startswith("2030-01-05T07:00:00+07:00")


def test_draf_tidak_terlihat_warga(api, warga, pengurus):
    Post.objects.create(title="Draf", body="-", is_published=False)
    Post.objects.create(title="Terbit", body="-")
    assert [p["title"] for p in api(warga).get("/api/v1/posts/").data["results"]] == ["Terbit"]
    assert api(pengurus).get("/api/v1/posts/").data["count"] == 2
