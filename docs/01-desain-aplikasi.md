# Desain Aplikasi Administrasi RT

## 1. Ringkasan

Aplikasi ini membantu pengurus RT mengelola **data warga**, **iuran**, dan **berita/kegiatan**.
Aplikasi dipakai dari HP (tampilan seperti aplikasi) dan dari laptop/PC (tampilan web penuh).

Prinsip desain:
- **Satu backend, banyak tampilan.** Aturan bisnis dan hak akses hanya ada di server. Web dan aplikasi HP hanya menampilkan data.
- **Unit iuran adalah keluarga/rumah (KK), bukan per orang.** Satu KK punya beberapa anggota, tetapi tagihannya satu.
- **Privasi warga.** Warga hanya bisa melihat data dirinya dan keluarganya. Rekap iuran keseluruhan yang dilihat warga hanya berisi nama kepala keluarga, nomor rumah, dan status bayar, tanpa NIK, telepon, atau data pribadi lain. Ini sejalan dengan UU No. 27/2022 tentang Pelindungan Data Pribadi.

## 2. Peran dan hak akses

| Fitur | Admin | Pengurus | Warga |
|---|---|---|---|
| Kelola akun pengguna & peran | ✅ | ❌ | ❌ |
| Pengaturan RT (nama RT, jenis & nominal iuran, rekening) | ✅ | ❌ | ❌ |
| Lihat data **semua** warga | ✅ | ✅ | ❌ |
| Tambah / ubah / nonaktifkan data warga | ✅ | ✅ | ❌ |
| Lihat & ubah data **diri sendiri / keluarga sendiri** | ✅ | ✅ | ✅ |
| Setujui perubahan data sensitif dari warga (NIK, No. KK) | ✅ | ✅ | ❌ |
| Buat tagihan iuran bulanan | ✅ | ✅ | ❌ |
| Catat pembayaran (lunas / belum) | ✅ | ✅ | ❌ |
| Verifikasi bukti bayar dari warga | ✅ | ✅ | ❌ |
| Lihat rekap iuran per warga & keseluruhan (lengkap) | ✅ | ✅ | ❌ |
| Lihat rekap iuran **sendiri** | ✅ | ✅ | ✅ |
| Lihat rekap iuran **keseluruhan** (versi ringkas) | ✅ | ✅ | ✅ |
| Unggah bukti pembayaran | ✅ | ✅ | ✅ |
| Buat / ubah / hapus berita & kegiatan | ✅ | ✅ | ❌ |
| Baca berita & kegiatan | ✅ | ✅ | ✅ |
| Lihat log aktivitas (audit) | ✅ | ❌ | ❌ |

Catatan:
- Seorang pengurus juga warga. Satu akun bisa punya peran `pengurus` sekaligus terhubung ke data warganya sendiri.
- **Usulan perubahan data warga:** perubahan data kontak (telepon, pekerjaan, foto) langsung tersimpan. Perubahan data identitas (NIK, No. KK, nama, tanggal lahir) masuk antrean **"Menunggu persetujuan"** dan baru berlaku setelah disetujui pengurus. Dengan begitu warga tetap bisa memperbarui datanya, tetapi data resmi RT tetap valid.

## 3. Modul dan fitur

### 3.1 Data Warga
- **Keluarga (KK):** No. KK, alamat/blok/no. rumah, status hunian (pemilik / kontrak / kos), tanggal mulai tinggal.
- **Anggota keluarga:** NIK, nama, jenis kelamin, tempat & tanggal lahir, agama, status perkawinan, hubungan dalam keluarga, pekerjaan, no. HP, status (aktif / pindah / meninggal).
- Pengurus: daftar warga dengan pencarian & filter (blok, status hunian, status aktif), detail keluarga, tambah/ubah, ekspor ke Excel/PDF.
- Warga: halaman "Data Saya" berisi data keluarga sendiri, tombol **Ajukan perubahan**, dan riwayat pengajuan.
- Statistik ringkas: jumlah KK, jumlah jiwa, komposisi usia dan jenis kelamin.

### 3.2 Iuran
- **Jenis iuran** diatur admin, misalnya Kebersihan Rp20.000, Keamanan Rp30.000, Kas Sosial Rp10.000. Bisa bulanan atau sekali bayar (misalnya iuran 17 Agustus).
- **Tagihan** dibuat otomatis tiap awal bulan untuk setiap KK aktif, atau dibuat manual oleh pengurus.
- **Status tagihan:** `belum_bayar` → `menunggu_verifikasi` (warga sudah unggah bukti) → `lunas`. Jika bukti ditolak, status kembali ke `belum_bayar` dengan alasan penolakan.
- **Pengurus mencatat pembayaran:** pilih KK, centang bulan yang dibayar, lalu pilih metode (tunai / transfer / QRIS). Satu pembayaran bisa melunasi beberapa bulan sekaligus.
- **Warga mengunggah bukti:** pilih bulan yang dibayar, unggah foto/screenshot transfer, isi nominal dan tanggal transfer, lalu kirim. Pengurus mendapat notifikasi.
- **Rekap:**
  - *Per warga:* riwayat semua tagihan dan pembayaran satu KK beserta total tunggakan.
  - *Keseluruhan:* tabel matriks rumah × bulan (✅ lunas / ⏳ menunggu / ❌ belum), total pemasukan per bulan, dan persentase kepatuhan.
  - Warga melihat versi ringkas (nama kepala keluarga, no. rumah, status), tanpa nominal pribadi dan tanpa data kontak.
- **Kas RT (opsional, tahap 2):** catat pengeluaran agar laporan pemasukan dan pengeluaran transparan.

### 3.3 Berita & Kegiatan
- Jenis posting: **Berita** (pengumuman) atau **Kegiatan** (punya tanggal, jam, dan lokasi).
- Isi: judul, isi (teks kaya), gambar sampul, lampiran, status draf/terbit, dan opsi sematkan di atas.
- Warga melihat daftar berita dan kalender kegiatan mendatang. Opsi tahap 2: tombol "Hadir" (RSVP) dan komentar.
- Notifikasi (push/WhatsApp) saat ada posting baru dapat ditambahkan di tahap 2.

### 3.4 Umum
- Login dengan no. HP/email + kata sandi. Akun warga dibuat oleh pengurus, atau warga mendaftar sendiri lalu diverifikasi pengurus.
- Notifikasi dalam aplikasi untuk: bukti bayar baru, bukti diterima/ditolak, pengajuan perubahan data, dan berita baru.
- Log audit untuk setiap perubahan data warga dan pembayaran: siapa, kapan, dan apa yang berubah.

## 4. Model data

```mermaid
erDiagram
    USERS ||--o| RESIDENTS : "terhubung ke"
    HOUSEHOLDS ||--|{ RESIDENTS : "beranggotakan"
    HOUSEHOLDS ||--o{ BILLS : "ditagih"
    FEE_TYPES ||--o{ BILLS : "jenis"
    PAYMENTS ||--|{ BILLS : "melunasi"
    HOUSEHOLDS ||--o{ PAYMENTS : "membayar"
    PAYMENT_PROOFS }o--|{ BILLS : "untuk"
    PAYMENT_PROOFS |o--o| PAYMENTS : "menjadi"
    HOUSEHOLDS ||--o{ CHANGE_REQUESTS : "mengajukan"
    USERS ||--o{ POSTS : "menulis"
```

Nama tabel di bawah mengikuti model Django (tabel fisiknya berawalan nama app, misalnya `dues_bill`).

| Model (app) | Kolom utama |
|---|---|
| `User` (accounts) | username, first_name, phone, email, password, role (`admin`/`pengurus`/`warga`), resident (1-1), is_active |
| `Household` (residents) | no_kk 🔒, block, house_number, address, occupancy (`pemilik`/`kontrak`/`kos`), since, is_active |
| `Resident` (residents) | household, nik 🔒, name, gender, birth_place, birth_date, religion, marital_status, relation, occupation, phone, status (`aktif`/`pindah`/`meninggal`) |
| `ChangeRequest` (residents) | household, resident (opsional), requested_by, changes (json `{field: {old, new}}`), note, status (`pending`/`disetujui`/`ditolak`), review_note, reviewed_by, reviewed_at |
| `FeeType` (dues) | name, amount, period (`bulanan`/`sekali`), description, is_active |
| `Bill` (dues) | household, fee_type, period (`YYYY-MM`), amount, status (`belum_bayar`/`menunggu_verifikasi`/`lunas`), payment |
| `Payment` (dues) | household, total, method (`tunai`/`transfer`/`qris`), paid_at, recorded_by, note |
| `PaymentProof` (dues) | household, uploaded_by, bills (banyak-ke-banyak), file 🔒, amount, transfer_date, method, note, status (`pending`/`diterima`/`ditolak`), review_note, verified_by, payment |
| `Post` (posts) | type (`berita`/`kegiatan`), title, body, event_at, location, is_pinned, is_published, published_at, author |
| `AuditLog` (core) | user, action, target, data (json), created_at |

🔒 = terenkripsi (NIK, No. KK) atau file privat (bukti bayar). Satu tagihan dilunasi oleh tepat satu pembayaran (`Bill.payment`).

Aturan penting:
- `bills` punya indeks unik `(household_id, fee_type_id, period)` agar tidak ada tagihan ganda.
- Nominal disimpan sebagai bilangan bulat rupiah, bukan float.
- NIK dan No. KK disimpan terenkripsi di database dan selalu disamarkan di tampilan (misalnya `3201••••••••0012`), kecuali bagi pengurus yang membuka detail.
- File bukti bayar disimpan di storage privat dan hanya bisa diakses lewat URL bertanda tangan (signed URL), bukan folder publik.

## 5. Alur utama

### Pembayaran iuran oleh warga
```mermaid
sequenceDiagram
    participant S as Sistem
    participant W as Warga
    participant P as Pengurus
    S->>S: Tgl 1 tiap bulan: buat tagihan untuk semua KK aktif
    W->>S: Unggah bukti transfer (pilih bulan + foto)
    S->>S: Status tagihan = menunggu_verifikasi
    S-->>P: Notifikasi bukti baru
    alt Bukti valid
        P->>S: Terima
        S->>S: Buat payment, tagihan = lunas
        S-->>W: Notifikasi "Pembayaran diterima"
    else Bukti tidak valid
        P->>S: Tolak + alasan
        S->>S: Tagihan = belum_bayar
        S-->>W: Notifikasi "Bukti ditolak: <alasan>"
    end
```

### Pembayaran tunai
Pengurus membuka **Iuran → Catat Pembayaran**, memilih KK, mencentang bulan, memilih metode *tunai*, lalu menyimpan. Tagihan langsung berstatus `lunas`.

### Perubahan data oleh warga
Warga membuka **Data Saya → Ajukan perubahan**. Field kontak langsung tersimpan. Field identitas masuk `change_requests` dan menunggu persetujuan pengurus, yang melihat tampilan perbandingan data lama dan baru.

## 6. Daftar layar

| Layar | Admin | Pengurus | Warga |
|---|---|---|---|
| Login, lupa kata sandi | ✅ | ✅ | ✅ |
| Beranda / dasbor | statistik + aktivitas | statistik, bukti menunggu, tunggakan | status iuran saya, berita terbaru, kegiatan mendatang |
| Data Warga: daftar, detail KK, form | ✅ | ✅ | — |
| Data Saya + ajukan perubahan | ✅ | ✅ | ✅ |
| Persetujuan perubahan data | ✅ | ✅ | — |
| Iuran: rekap matriks keseluruhan | lengkap | lengkap | ringkas |
| Iuran: riwayat per KK | semua KK | semua KK | KK sendiri |
| Iuran: catat pembayaran | ✅ | ✅ | — |
| Iuran: verifikasi bukti | ✅ | ✅ | — |
| Iuran: unggah bukti | ✅ | ✅ | ✅ |
| Berita & Kegiatan: daftar, detail | ✅ | ✅ | ✅ |
| Berita & Kegiatan: form posting | ✅ | ✅ | — |
| Pengaturan RT, jenis iuran, pengguna | ✅ | — | — |
| Profil & ganti kata sandi | ✅ | ✅ | ✅ |

### Tata letak responsif
- **HP (< 768px):** header ringkas di atas dan **navigasi bawah** dengan 4–5 ikon (Beranda, Warga/Data Saya, Iuran, Berita, Akun). Daftar ditampilkan sebagai kartu. Tombol aksi utama mengambang (FAB), dan form ditampilkan layar penuh. Aplikasi dipasang sebagai **PWA** sehingga tampil tanpa address bar.
- **Tablet/Desktop (≥ 768px):** **sidebar** kiri, area konten lebar, daftar dalam bentuk tabel dengan filter, dan form di panel samping atau modal.
- Komponen dan data sama; hanya tata letak yang berubah. Lihat prototipe di [`docs/mockup/index.html`](mockup/index.html).

## 7. Garis besar API (REST, JSON)

Semua endpoint ada di bawah `/api/v1` (Django REST Framework) dan memakai session cookie + CSRF. Hak akses diperiksa di server melalui `get_queryset()` dan permission class, bukan di tampilan.

| Metode | Endpoint | Peran |
|---|---|---|
| POST | `/auth/login`, `/auth/logout` | semua |
| GET | `/me`, `/me/household` | semua |
| POST | `/me/change-requests` | semua |
| GET/POST/PUT | `/households`, `/households/{id}`, `/residents/{id}` | pengurus+ |
| GET/POST | `/change-requests`, `/change-requests/{id}/approve`, `/change-requests/{id}/reject` | pengurus+ |
| GET | `/bills?household_id=&period=` | pengurus+ (warga: otomatis difilter ke KK sendiri) |
| GET | `/bills/summary?year=` | semua (warga mendapat versi ringkas) |
| POST | `/payments` | pengurus+ |
| POST | `/payment-proofs` | semua |
| POST | `/payment-proofs/{id}/approve`, `/payment-proofs/{id}/reject` | pengurus+ |
| GET | `/posts`, `/posts/{id}` | semua |
| POST/PUT/DELETE | `/posts`, `/posts/{id}` | pengurus+ |
| CRUD | `/fee-types`, `/users`, `/settings` | admin |

## 8. Tahapan pengembangan

1. **MVP:** login & peran, data warga (CRUD + Data Saya), jenis iuran, tagihan bulanan, catat pembayaran, rekap, berita.
2. **Tahap 2:** unggah & verifikasi bukti bayar, pengajuan perubahan data, notifikasi, PWA, ekspor Excel/PDF.
3. **Tahap 3:** notifikasi Web Push, kas RT, RSVP kegiatan, notifikasi WhatsApp, pembayaran QRIS otomatis.
