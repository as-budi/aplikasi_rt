# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Aplikasi administrasi RT (data warga, iuran, berita/kegiatan) untuk tiga peran: **admin**, **pengurus**, dan **warga**. UI dan dokumentasi dalam Bahasa Indonesia; nama model, field, dan kode dalam bahasa Inggris; nilai enum berbahasa Indonesia (`belum_bayar`, `lunas`, `kontrak`, …).

Rujukan desain: `docs/01-desain-aplikasi.md` (hak akses, model data, alur), `docs/02-arsitektur.md`, `docs/03-pengembangan-docker.md` (Docker & deploy VPS), `docs/mockup/index.html` (prototipe awal UI).

## Perintah

Semua dijalankan lewat Docker Compose; tidak ada Python/Node di host. Jalankan `export UID GID=$(id -g)` dulu agar file dari container tidak dimiliki root.

```bash
docker compose up -d                                    # api, worker, beat, db, redis, web, mailpit
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_demo      # data contoh; dilewati bila sudah ada data
docker compose exec api pytest                          # tes backend (MySQL sungguhan, DB test_aplikasi_rt)
docker compose exec api pytest apps/dues/tests.py::test_alur_bukti_bayar_diterima
docker compose exec api pytest -k bukti
docker compose exec api python manage.py makemigrations
docker compose exec web npm run build                   # vue-tsc --noEmit + vite build (cek tipe frontend)
docker compose exec web npm run typecheck
```
Aplikasi: http://localhost:5173 (Vite mem-proxy `/api`, `/admin`, `/static` ke Django) · Django Admin: http://localhost:5173/admin/ · Swagger: http://localhost:8000/api/docs/

Healthcheck MySQL harus memakai `-h 127.0.0.1` (TCP). Ping lewat socket sudah sukses saat server sementara masih inisialisasi, sehingga Django gagal konek.

## Arsitektur

- `backend/` (Django 5.2 + DRF). Config ada di `backend/config/` (`settings.py` membaca env via django-environ, `api_urls.py` memuat semua route `/api/v1/`). App di `backend/apps/`:
  - `core`: permission bersama (`is_staff_rt`, `IsStaffRT`, `IsStaffOrReadOnly`), `EncryptedCharField`, `AuditLog` + `audit()`, `protected_file_response`, `DashboardView`, perintah `seed_demo`.
  - `accounts`: `User` kustom (`role`, `resident` 1-1 ke `Resident`; properti `household`, `is_staff_rt`). Login dengan username/no. HP/email memakai session + CSRF.
  - `residents`: `Household` (KK), `Resident`, `ChangeRequest`; `services.py` berisi alur perubahan data oleh warga.
  - `dues`: `FeeType`, `Bill`, `Payment`, `PaymentProof`; **semua perubahan status tagihan lewat `dues/services.py`** (`generate_bills`, `record_payment`, `submit_proof`, `approve_proof`, `reject_proof`, `bill_summary`). Celery beat menjalankan `generate_monthly_bills` tiap tanggal 1.
  - `posts`: `Post` (berita/kegiatan).
  - `finance`: `CashEntry` (pemasukan lain & pengeluaran). `services.cash_report()` menghitung iuran dari `Payment.paid_at`, jadi **iuran tidak pernah dicatat sebagai CashEntry**. Semua user yang login boleh membaca; hanya pengurus yang menulis. `services.ledger(private=...)` menggabungkan CashEntry + Payment untuk daftar transaksi dan ekspor: `private=True` menampilkan iuran per rumah dengan nama. Secara default ini berlaku untuk semua warga (`CASH_LEDGER_PUBLIC_DETAIL=True`, keputusan pemilik proyek demi transparansi kas; lihat `finance.views.show_detail`). Jika dimatikan, warga hanya mendapat ringkasan per bulan. Ini pengecualian yang disengaja dari aturan rekap iuran di bawah: rekap iuran (`bill_summary`) tetap tanpa nominal untuk warga.
  - `reports`: ekspor `GET /api/v1/exports/<residents|dues|cash>/?file=xlsx|pdf`. Pakai parameter `file`, bukan `format`, karena `format` dipakai DRF untuk content negotiation. `documents.py` menyusun tabel, lalu `render.py` menulis openpyxl/reportlab. Font DejaVu dari paket apt `fonts-dejavu-core` dipakai untuk ✓ ✕ ….
  - `residents/registration.py`: pendaftaran mandiri (`POST /auth/register/` **multipart**: `data` JSON + `kk_file` + `ktp_file` wajib; user `is_active=False`, payload terenkripsi di `Registration`) → `approve()` membuat KK/anggota atau menggabungkan ke KK yang ada, lalu memindahkan `Document` KK/KTP ke KK tersebut → payload dikosongkan. `reject()` menghapus dokumen beserta filenya.
  - `Document` (KK/KTP, file privat): `DocumentViewSet`; warga hanya untuk KK sendiri dan tidak boleh menghapus. Semua unggahan privat divalidasi lewat `core.files.validate_private_upload`.
- `web/` (Vue 3 + Vite + TS + Tailwind v4 + Pinia, PWA via `vite-plugin-pwa`). `src/api/http.ts` berisi axios + `errMsg()` + `fetchAll()`; `src/stores/auth.ts` menyimpan user aktif; `src/router.ts` memakai `meta.staff` untuk halaman pengurus. Satu layout (`components/AppLayout.vue`): sidebar di ≥768px dan navigasi bawah di HP. Warna lewat token CSS di `src/style.css` (`bg-surface`, `text-muted`, `bg-primary-soft`, …; dark mode otomatis). Tab iuran ada di `views/dues/`.
- Produksi: `compose.prod.yaml` + `docker/nginx/` (image nginx berisi PWA hasil build, proxy `/api` & `/admin`, `/protected-media/` internal). Di VPS, Nginx host hanya menangani TLS dan memproksi ke `127.0.0.1:8081`.

## Aturan yang tidak boleh dilanggar

- **Hak akses di server.** ViewSet membatasi `get_queryset()`: warga hanya mendapat data `request.user.household`; pengurus melihat semua, kecuali `?mine=1` (lihat `_scope_to_household` di `dues/views.py`). Objek milik KK lain menghasilkan **404**, bukan 403.
- Rekap iuran untuk warga (`bill_summary(include_private=False)`) hanya berisi label rumah, nama kepala keluarga, dan status, tanpa nominal tunggakan, pemasukan, NIK, atau no. HP. Ada tesnya.
- NIK & No. KK memakai `EncryptedCharField` (Fernet, kunci `FIELD_ENCRYPTION_KEY`). Field ini tidak bisa difilter, dicari, atau dijadikan unik di DB. Warga hanya melihat versi tersamar (`mask()`). Jangan pernah mengganti kunci setelah ada data.
- Bukti bayar disimpan di `MEDIA_ROOT` yang privat dan hanya disajikan lewat action `payment-proofs/{id}/file/` (`X-Accel-Redirect` di produksi). Jangan menambah `MEDIA_URL` publik.
- Unit tagihan adalah KK. `Bill` unik per `(household, fee_type, period)`; `period` = `"YYYY-MM"`. Status: `belum_bayar` → `menunggu_verifikasi` (bukti diunggah) → `lunas`; bukti ditolak → kembali `belum_bayar` dan alasan wajib diisi.
- **Pembayaran = uang yang benar-benar diterima** (`Payment.total`), bukan total tagihan. `dues.services.record_payment` mengalokasikan uang + `Household.credit` per **bulan utuh** mulai dari bulan tertua (`allocate()`); frontend memakai aturan yang sama di `web/src/utils/allocation.ts`, jadi ubah keduanya bersamaan. Sisa → saldo titipan (atau `refund_excess` → `CashEntry` kategori `pengembalian`). `apply_credit()` dipanggil setelah pembayaran dan setelah `generate_bills()`, lalu membuat `Payment` bermetode `titipan` dengan total 0 (tidak dihitung lagi di kas).
- **Kas hanya menghitung `Payment.objects.active()`** (tidak dibatalkan). Pembatalan lewat `cancel_payment()` (soft cancel, berantai ke pemakaian titipan otomatis, ditolak bila titipan dipakai pembayaran nyata yang lebih baru). Jangan pernah menghapus `Payment`.
- Urutan bulan untuk unggahan warga ditegakkan `check_sequential()` di `submit_proof`; `record_payment` (pengurus) sengaja tidak memeriksanya.
- Bayar di muka maks. `MAX_PREPAY_MONTHS` (12) lewat `periods` → `ensure_future_bills()`. Aturan tetap: tagihan bulan mendatang hanya ada jika lunas atau menunggu verifikasi; jika tidak tertutup/ditolak, tagihannya dihapus (`_drop_unpaid_future_bills`).
- Perubahan identitas oleh warga (`Resident.IDENTITY_FIELDS`) menjadi `ChangeRequest`; `CONTACT_FIELDS` langsung tersimpan.
- Uang = integer rupiah. `TIME_ZONE="Asia/Jakarta"`, `USE_TZ=True`. Hindari lookup `__date`/`__month` pada DateTimeField (tabel zona waktu MySQL tidak dimuat).
- `is_superuser` ⇒ `role=admin` dan sebaliknya (`User.save`). Admin mengelola pengguna, jenis iuran, dan log lewat Django Admin.
- Setiap aksi tulis penting memanggil `audit(user, aksi, objek, **detail)`.
- Login user nonaktif hanya membocorkan status pendaftaran jika kata sandinya benar (lihat `LoginView`).
- Endpoint publik hanya `auth/csrf`, `auth/login`, dan `auth/register` (throttle `login` 10/menit, `register` 5/jam). Tes membersihkan cache di `conftest.py` agar throttle tidak terbawa antar tes.
- `Household.residence_status`: `menetap`/`singgah`, terpisah dari `occupancy` (pemilik/kontrak/kos).
