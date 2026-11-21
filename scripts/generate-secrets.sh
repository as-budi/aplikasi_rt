#!/usr/bin/env bash
# Membuat semua rahasia produksi sekaligus:
#   .env.db              -> password MySQL (user aplikasi & root)
#   backend/.env.prod    -> SECRET_KEY, FIELD_ENCRYPTION_KEY, DATABASE_URL (password sama dengan .env.db), domain
#
# Pemakaian (dari root proyek, di server):
#   ./scripts/generate-secrets.sh rt.domain.id
#
# Hanya butuh `openssl`. File yang sudah ada TIDAK ditimpa (lihat catatan di bawah).
set -euo pipefail

DOMAIN="${1:-}"
if [[ -z "$DOMAIN" ]]; then
  echo "Pemakaian: $0 <domain>   contoh: $0 rt.domain.id" >&2
  exit 1
fi

cd "$(dirname "$0")/.."
DB_ENV=".env.db"
APP_ENV="backend/.env.prod"

for f in "$DB_ENV" "$APP_ENV"; do
  if [[ -e "$f" ]]; then
    cat >&2 <<EOF
$f sudah ada, tidak ditimpa.
- FIELD_ENCRYPTION_KEY yang lama WAJIB dipertahankan; tanpa kunci itu NIK/No. KK tidak bisa dibaca lagi.
- Password MySQL baru tidak berlaku untuk database yang sudah dibuat (volume dbdata).
Hapus file itu secara manual hanya jika ini benar-benar instalasi baru.
EOF
    exit 1
  fi
done

command -v openssl >/dev/null || { echo "openssl tidak ditemukan. Pasang dulu: sudo apt install openssl" >&2; exit 1; }

# Hanya huruf & angka agar aman dipakai di URL (DATABASE_URL) dan file .env
alnum() { openssl rand -base64 64 | tr -dc 'A-Za-z0-9' | head -c "$1"; }

SECRET_KEY="$(alnum 64)"
# Kunci Fernet = 32 byte acak, base64 versi URL-safe (44 karakter)
FIELD_ENCRYPTION_KEY="$(openssl rand -base64 32 | tr '+/' '-_')"
DB_PASSWORD="$(alnum 32)"
DB_ROOT_PASSWORD="$(alnum 32)"

umask 077  # file rahasia hanya bisa dibaca pemiliknya

cat > "$DB_ENV" <<EOF
MYSQL_DATABASE=aplikasi_rt
MYSQL_USER=rt
MYSQL_PASSWORD=$DB_PASSWORD
MYSQL_ROOT_PASSWORD=$DB_ROOT_PASSWORD
EOF

cat > "$APP_ENV" <<EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
# JANGAN diganti setelah ada data: NIK/No. KK yang terenkripsi tidak bisa dibaca lagi. Simpan salinannya di tempat aman.
FIELD_ENCRYPTION_KEY=$FIELD_ENCRYPTION_KEY
ALLOWED_HOSTS=$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN
DATABASE_URL=mysql://rt:$DB_PASSWORD@db:3306/aplikasi_rt
CELERY_BROKER_URL=redis://redis:6379/0
EMAIL_URL=consolemail://
# Tampilkan iuran per rumah di buku kas untuk semua warga (False = ringkasan per bulan)
CASH_LEDGER_PUBLIC_DETAIL=True
EOF

echo "Dibuat: $DB_ENV dan $APP_ENV (izin 600) untuk domain $DOMAIN."
echo
echo "PENTING: simpan salinan FIELD_ENCRYPTION_KEY di password manager / tempat aman di luar server:"
echo "  FIELD_ENCRYPTION_KEY=$FIELD_ENCRYPTION_KEY"
echo
echo "Langkah berikutnya:"
echo "  docker compose -f compose.prod.yaml up -d --build"
echo "  docker compose -f compose.prod.yaml exec api python manage.py migrate"
echo "  docker compose -f compose.prod.yaml exec api python manage.py createsuperuser"
