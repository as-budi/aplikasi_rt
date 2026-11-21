from django.core.management.base import BaseCommand

from apps.dues.services import generate_bills


class Command(BaseCommand):
    help = "Buat tagihan iuran bulanan untuk semua KK aktif (aman dijalankan berulang)."

    def add_arguments(self, parser):
        parser.add_argument("--period", help="YYYY-MM, default bulan ini")

    def handle(self, *args, period=None, **options):
        created = generate_bills(period)
        self.stdout.write(self.style.SUCCESS(f"{created} tagihan baru dibuat."))
