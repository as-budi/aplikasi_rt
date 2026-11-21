"""Data contoh untuk pengembangan & demo. JANGAN dijalankan di produksi."""

from datetime import date, timedelta
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from apps.accounts.models import User
from apps.dues.models import Bill, FeeType
from apps.dues.services import generate_bills, record_payment, submit_proof
from apps.finance.models import CashEntry
from apps.posts.models import Post
from apps.residents.models import ChangeRequest, Household, Registration, Resident
from apps.residents.registration import register

PASSWORD = "rtkita123"
K, I, S, A = Resident.Relation.KEPALA, Resident.Relation.ISTRI, Resident.Relation.SUAMI, Resident.Relation.ANAK

# (blok, no, hunian, username kepala keluarga, [(nama, hubungan, L/P, umur, pekerjaan)])
HOUSEHOLDS = [
    ("A", "1", "pemilik", "budi", [("Budi Santoso", K, "L", 44, "Karyawan swasta"), ("Sri Wahyuni", I, "P", 41, "Guru"), ("Dimas Santoso", A, "L", 15, "Pelajar"), ("Laras Santoso", A, "P", 10, "Pelajar")]),
    ("A", "2", "pemilik", "ketua", [("Ahmad Fauzi", K, "L", 52, "Wiraswasta"), ("Nur Aini", I, "P", 49, "Ibu rumah tangga"), ("Rizki Fauzi", A, "L", 22, "Mahasiswa")]),
    ("A", "3", "kontrak", "yohanes", [("Yohanes Situmorang", K, "L", 33, "Programmer"), ("Maria Simanjuntak", I, "P", 30, "Perawat"), ("Grace Situmorang", A, "P", 3, "Belum sekolah")]),
    ("B", "1", "pemilik", "bendahara", [("Dewi Lestari", K, "P", 58, "Pensiunan"), ("Agus Pratama", A, "L", 29, "Karyawan BUMN")]),
    ("B", "2", "pemilik", "hendra", [("Hendra Wijaya", K, "L", 47, "Pedagang"), ("Lina Wijaya", I, "P", 45, "Pedagang"), ("Kevin Wijaya", A, "L", 19, "Mahasiswa"), ("Cindy Wijaya", A, "P", 16, "Pelajar")]),
    ("B", "3", "kos", "slamet", [("Slamet Riyadi", K, "L", 27, "Ojek online")]),
    ("C", "1", "pemilik", "ketut", [("Ketut Arsana", K, "L", 39, "Dosen"), ("Made Sari", I, "P", 36, "Dokter"), ("Putu Arsana", A, "L", 8, "Pelajar")]),
    ("C", "2", "kontrak", "rina", [("Rina Marlina", K, "P", 35, "Desainer"), ("Fajar Nugroho", S, "L", 37, "Teknisi"), ("Alya Nugroho", A, "P", 6, "Pelajar")]),
]

# Pola status per bulan (2 lunas, 1 menunggu verifikasi, 0 belum), berulang tiap 11 bulan
PATTERN = {
    "A-1": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],
    "A-2": [2] * 11,
    "A-3": [2, 2, 2, 0, 0, 2, 2, 2, 2, 1, 1],
    "B-1": [2] * 11,
    "B-2": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    "B-3": [2, 2, 0, 0, 0, 0, 2, 2, 0, 0, 0],
    "C-1": [2] * 11,
    "C-2": [2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0],
}


def proof_image(label: str, amount: int) -> ContentFile:
    img = Image.new("RGB", (600, 800), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=30)
    small = ImageFont.load_default(size=22)
    draw.rectangle((0, 0, 600, 110), fill=(15, 118, 110))
    draw.text((30, 35), "BUKTI TRANSFER (CONTOH)", fill="white", font=font)
    lines = [f"Dari  : KK {label}", f"Ke    : Kas RT 05", f"Jumlah: Rp{amount:,}".replace(",", "."), "Status: BERHASIL"]
    for i, line in enumerate(lines):
        draw.text((30, 170 + i * 50), line, fill="black", font=small)
    buf = BytesIO()
    img.save(buf, "PNG")
    return ContentFile(buf.getvalue(), name="bukti.png")


def document_image(title: str, lines: list[str]) -> ContentFile:
    """Gambar contoh pengganti foto KK/KTP (bukan dokumen asli)."""
    img = Image.new("RGB", (900, 560), (235, 244, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 900, 90), fill=(15, 118, 110))
    draw.text((30, 25), f"{title} — CONTOH", fill="white", font=ImageFont.load_default(size=34))
    for i, line in enumerate(lines):
        draw.text((30, 130 + i * 48), line, fill="black", font=ImageFont.load_default(size=26))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=80)
    return ContentFile(buf.getvalue(), name=f"{title.lower().replace(' ', '-')}.jpg")


class Command(BaseCommand):
    help = "Isi data contoh: 8 KK, akun admin/pengurus/warga, iuran tahun berjalan, berita."

    @transaction.atomic
    def handle(self, *args, **options):
        if Household.objects.exists():
            self.stdout.write(self.style.WARNING("Data inti sudah ada, dilewati. (Kosongkan dengan: docker compose down -v)"))
        else:
            self.seed_core()
        self.seed_extras()

    def seed_extras(self):
        """Kas RT, rumah singgah, dan pendaftaran menunggu — ditambahkan bila belum ada."""
        today = timezone.localdate()
        Household.objects.filter(block="B", house_number="3").update(residence_status="singgah")

        if not CashEntry.objects.exists():
            recorder = User.objects.filter(username="bendahara").first()
            entry = lambda kind, cat, desc, amount, d: CashEntry.objects.create(  # noqa: E731
                kind=kind, category=cat, description=desc, amount=amount, date=d, recorded_by=recorder
            )
            entry("pemasukan", "saldo_awal", f"Saldo kas akhir {today.year - 1}", 2_500_000, date(today.year - 1, 12, 31))
            for m in range(1, today.month + 1):
                entry("pengeluaran", "kebersihan", "Honor petugas sampah", 150_000, date(today.year, m, 25))
                entry("pengeluaran", "keamanan", "Honor ronda malam", 200_000, date(today.year, m, 26))
            extras = [
                (5, "pengeluaran", "perbaikan", "Ganti 3 lampu jalan Blok B", 350_000),
                (8, "pemasukan", "donasi", "Sumbangan warga untuk 17 Agustus", 500_000),
                (8, "pengeluaran", "kegiatan", "Lomba & hadiah 17 Agustus", 750_000),
                (10, "pengeluaran", "sosial", "Santunan warga sakit (C-1)", 300_000),
                (11, "pengeluaran", "operasional", "Fotokopi & ATK rapat warga", 45_000),
            ]
            for month, kind, cat, desc, amount in extras:
                if month <= today.month:
                    entry(kind, cat, desc, amount, date(today.year, month, 15))
            self.stdout.write("Transaksi kas contoh dibuat.")

        if not Registration.objects.exists():
            register({
                "username": "andi", "password": PASSWORD, "phone": "081377778888", "email": "",
                "household": {"no_kk": "3201000000000009", "block": "C", "house_number": "3", "address": "",
                              "occupancy": "kontrak", "residence_status": "menetap", "since": date(today.year, today.month, 1)},
                "members": [
                    {"name": "Andi Saputra", "nik": "3201091504900001", "gender": "L", "relation": "kepala_keluarga",
                     "birth_place": "Bandung", "birth_date": date(1990, 4, 15), "religion": "Islam",
                     "marital_status": "Kawin", "occupation": "Guru", "phone": "081377778888"},
                    {"name": "Rani Saputra", "nik": "3201094809920002", "gender": "P", "relation": "istri",
                     "birth_place": "Bogor", "birth_date": date(1992, 9, 8), "religion": "Islam",
                     "marital_status": "Kawin", "occupation": "Perawat", "phone": ""},
                ],
            },
                kk_file=document_image("KARTU KELUARGA", ["No. KK : 3201000000000009", "Kepala : ANDI SAPUTRA", "Alamat : Blok C No. 3"]),
                ktp_file=document_image("KTP", ["NIK  : 3201091504900001", "Nama : ANDI SAPUTRA", "Lahir: Bandung, 15-04-1990"]),
            )
            self.stdout.write("Pendaftaran warga baru contoh (andi, menunggu aktivasi) dibuat.")

    def seed_core(self):
        today = timezone.localdate()
        fees = [
            FeeType.objects.create(name="Kebersihan", amount=20000, description="Petugas sampah & kebersihan selokan"),
            FeeType.objects.create(name="Keamanan", amount=30000, description="Honor satpam & ronda"),
            FeeType.objects.create(name="Kas Sosial", amount=10000, description="Santunan & kegiatan warga"),
        ]
        monthly_total = sum(f.amount for f in fees)

        User.objects.create_superuser("admin", password=PASSWORD, first_name="Admin RT")
        users, households = {}, {}
        for idx, (block, number, occupancy, username, members) in enumerate(HOUSEHOLDS, start=1):
            hh = Household.objects.create(
                block=block, house_number=number, occupancy=occupancy, no_kk=f"3201{idx:012d}",
                residence_status="singgah" if (block, number) == ("B", "3") else "menetap",
                since=date(2012 + idx, (idx % 12) + 1, 1),
            )
            households[hh.label] = hh
            for j, (name, relation, gender, age, job) in enumerate(members):
                resident = Resident.objects.create(
                    household=hh, name=name, relation=relation, gender=gender, occupation=job,
                    nik=f"3201{idx:02d}{j:02d}{(today.year - age) % 100:02d}{idx * 7 + j:06d}",
                    birth_date=date(today.year - age, ((idx + j) % 12) + 1, 10 + j),
                    birth_place="Bogor", religion="Islam" if idx % 3 else "Kristen",
                    marital_status="Kawin" if relation in (K, I, S) else "Belum kawin",
                    phone=f"08{12 + idx}{idx:04d}{j:04d}" if relation in (K, I, S) else "",
                )
                if relation == K:
                    role = {"ketua": User.Role.PENGURUS, "bendahara": User.Role.PENGURUS}.get(username, User.Role.WARGA)
                    users[username] = User.objects.create_user(
                        username, password=PASSWORD, first_name=name, phone=resident.phone, role=role, resident=resident
                    )

        # Tagihan Januari s.d. bulan ini + pembayaran sesuai pola
        recorder = users["bendahara"]
        pending: dict[str, list[int]] = {}
        for month in range(1, today.month + 1):
            period = f"{today.year}-{month:02d}"
            generate_bills(period)
            for label, hh in households.items():
                state = PATTERN[label][(month - 1) % 11]
                bill_ids = list(Bill.objects.filter(household=hh, period=period).values_list("pk", flat=True))
                if state == 2:
                    record_payment(
                        household=hh, bill_ids=bill_ids, method="transfer" if month % 2 else "tunai",
                        paid_at=date(today.year, month, min(5 + len(label), 28)), user=recorder,
                    )
                elif state == 1:
                    pending.setdefault(label, []).extend(bill_ids)

        for label, bill_ids in pending.items():
            hh = households[label]
            head_user = next(u for u in users.values() if u.resident and u.resident.household_id == hh.pk)
            amount = len(bill_ids) // len(fees) * monthly_total
            submit_proof(
                household=hh, user=head_user, bill_ids=bill_ids, file=proof_image(label, amount), amount=amount,
                transfer_date=today - timedelta(days=1), method="transfer", note="Sudah transfer ke rekening bendahara",
            )

        now = timezone.now()
        author = users["ketua"]
        Post.objects.create(
            type=Post.Type.KEGIATAN, title="Kerja Bakti Bersih Selokan", is_pinned=True, author=author,
            event_at=timezone.localtime(now + timedelta(days=8)).replace(hour=7, minute=0, second=0, microsecond=0),
            location="Kumpul di Pos Ronda Blok A",
            body="Mohon setiap KK mengirim minimal 1 perwakilan dan membawa cangkul atau sapu.\n\nKonsumsi disediakan dari kas RT.",
        )
        Post.objects.create(
            type=Post.Type.BERITA, title="Iuran Bulan Depan Naik Rp5.000 untuk Kas Banjir", author=author,
            body="Berdasarkan rapat warga, iuran kas sosial bertambah Rp5.000 mulai bulan depan untuk persiapan musim hujan.",
        )
        Post.objects.create(
            type=Post.Type.KEGIATAN, title="Posyandu Balita & Lansia", author=users["bendahara"],
            event_at=timezone.localtime(now + timedelta(days=12)).replace(hour=8, minute=0, second=0, microsecond=0), location="Rumah Ibu Dewi (B-1)",
            body="Penimbangan, imunisasi, dan cek tensi gratis untuk lansia.",
        )
        Post.objects.create(
            type=Post.Type.BERITA, title="Jadwal Ronda Bulan Ini", author=author,
            body="Jadwal ronda terbaru sudah ditempel di pos ronda. Silakan cek nama Anda.",
        )

        rina = Resident.objects.get(name="Rina Marlina")
        ChangeRequest.objects.create(
            household=rina.household, resident=rina, requested_by=users["rina"],
            changes={"name": {"old": rina.name, "new": "Rina Marlina Nugroho"}},
        )
        ChangeRequest.objects.create(
            household=rina.household, requested_by=users["rina"],
            note="Mohon tambahkan anak kedua kami: Bima Nugroho, lahir 3 Februari 2024.",
        )

        self.stdout.write(self.style.SUCCESS("Data contoh dibuat."))
        self.stdout.write(f"Kata sandi semua akun: {PASSWORD}")
        self.stdout.write("  admin     -> Admin (Django Admin + aplikasi)")
        self.stdout.write("  ketua     -> Pengurus (Ahmad Fauzi, A-2)")
        self.stdout.write("  bendahara -> Pengurus (Dewi Lestari, B-1)")
        self.stdout.write("  budi      -> Warga (Budi Santoso, A-1)")
        self.stdout.write("  rina, yohanes, hendra, slamet, ketut -> Warga")
        self.stdout.write("  andi      -> pendaftar baru, menunggu aktivasi")
