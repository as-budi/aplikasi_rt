# RT Kita: Aplikasi Administrasi RT

Data warga (termasuk pendaftaran mandiri warga baru & status rumah menetap/singgah), iuran (dengan unggah & verifikasi bukti bayar), Kas RT, ekspor Excel/PDF, serta berita/kegiatan untuk **admin**, **pengurus**, dan **warga**.
Satu aplikasi web responsif (PWA) yang bisa dipasang di HP seperti aplikasi native.

- Backend: Django 5.2 + Django REST Framework, MySQL 8.4, Celery + Redis
- Frontend: Vue 3 + Vite + TypeScript + Tailwind CSS, PWA
- Semua dijalankan dengan Docker Compose

Dokumen desain ada di [`docs/`](docs/): desain fitur & data, arsitektur, panduan Docker & deploy.

## Menjalankan (pengembangan)

Prasyarat: Docker Engine + Docker Compose (di WSL2/Linux/macOS).

```bash
export UID GID=$(id -g)                         # agar file dari container milik user Anda
cp backend/.env.example backend/.env            # lalu isi SECRET_KEY & FIELD_ENCRYPTION_KEY
docker compose up -d --build
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_demo   # data contoh (opsional)
```

| Alamat | Isi |
|---|---|
| http://localhost:5173 | Aplikasi (PWA) |
| http://localhost:5173/admin/ | Django Admin (peran admin): pengguna, jenis iuran, log aktivitas |
| http://localhost:8000/api/docs/ | Dokumentasi API (Swagger) |
| http://localhost:8025 | Mailpit (email tangkapan) |

Akun dari `seed_demo` (kata sandi dicetak oleh perintah tersebut): `admin` (admin), `ketua` & `bendahara` (pengurus), `budi`, `rina`, dll. (warga), dan `andi` (pendaftar baru yang menunggu aktivasi).
Untuk mengulang data contoh dari awal: `docker compose down -v`, lalu jalankan langkah di atas lagi.

## Perintah sehari-hari

```bash
docker compose exec api pytest                                   # semua tes backend
docker compose exec api pytest apps/dues/tests.py::test_alur_bukti_bayar_diterima   # satu tes
docker compose exec api python manage.py makemigrations          # setelah mengubah model
docker compose exec api python manage.py generate_bills --period 2026-12   # buat tagihan manual
docker compose exec web npm run build                            # type-check + build PWA
docker compose logs -f api worker web
```

## Deploy

Lihat [docs/03-pengembangan-docker.md](docs/03-pengembangan-docker.md#deploy-ke-vps-yang-sudah-punya-nginx-tanpa-docker-untuk-aplikasi-lain).
Ringkasnya: `compose.prod.yaml` (nginx container di `127.0.0.1:8081`), lalu Nginx host + certbot meneruskan domain ke port itu.
