from collections import defaultdict

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import audit
from apps.core.utils import aggregate_status, current_period, is_valid_period
from apps.residents.models import Household

from .models import Bill, FeeType, Payment, PaymentProof


MAX_PREPAY_MONTHS = 12  # bayar di muka maksimal 12 bulan setelah bulan berjalan


def add_months(period: str, n: int) -> str:
    y, m = map(int, period.split("-"))
    idx = y * 12 + (m - 1) + n
    return f"{idx // 12}-{idx % 12 + 1:02d}"


def generate_bills(period: str | None = None) -> int:
    """Buat tagihan iuran bulanan untuk semua KK aktif, lalu lunasi dari saldo titipan bila cukup.

    Aman dijalankan berulang: tagihan yang sudah ada (termasuk yang dibayar di muka) tidak dibuat lagi.
    """
    period = period or current_period()
    if not is_valid_period(period):
        raise ValidationError({"period": "Format periode harus YYYY-MM."})
    fees = list(FeeType.objects.filter(is_active=True, period=FeeType.Period.BULANAN))
    created = 0
    for household in Household.objects.filter(is_active=True):
        for fee in fees:
            _, was_created = Bill.objects.get_or_create(
                household=household, fee_type=fee, period=period, defaults={"amount": fee.amount}
            )
            created += was_created
    for household in Household.objects.filter(is_active=True, credit__gt=0):
        apply_credit(household)
    return created


def ensure_future_bills(household, periods) -> list[int]:
    """Buat tagihan untuk bulan mendatang (bayar di muka). Tarif mengikuti jenis iuran yang aktif saat ini."""
    periods = sorted(set(periods or []))
    if not periods:
        return []
    current = current_period()
    last = add_months(current, MAX_PREPAY_MONTHS)
    fees = list(FeeType.objects.filter(is_active=True, period=FeeType.Period.BULANAN))
    if not fees:
        raise ValidationError({"periods": "Belum ada jenis iuran bulanan yang aktif."})
    ids = []
    for period in periods:
        if not is_valid_period(period) or not (current < period <= last):
            raise ValidationError({"periods": f"Bulan {period} tidak bisa dibayar di muka (maksimal {MAX_PREPAY_MONTHS} bulan ke depan)."})
        for fee in fees:
            bill, _ = Bill.objects.get_or_create(household=household, fee_type=fee, period=period, defaults={"amount": fee.amount})
            ids.append(bill.pk)
    return ids


def _drop_unpaid_future_bills(bills_qs) -> None:
    """Tagihan bulan mendatang hanya boleh ada bila lunas/menunggu; sisanya dihapus (akan dibuat lagi saat bulannya tiba)."""
    bills_qs.filter(period__gt=current_period(), status=Bill.Status.BELUM, payment__isnull=True).delete()


def _lock_bills(household, bill_ids, allowed_statuses):
    bills = list(Bill.objects.select_for_update().select_related("fee_type").filter(pk__in=bill_ids))
    if not bills or len(bills) != len(set(bill_ids)):
        raise ValidationError({"bills": "Pilih minimal satu tagihan yang valid."})
    for bill in bills:
        if bill.household_id != household.pk:
            raise ValidationError({"bills": "Tagihan bukan milik KK ini."})
        if bill.status not in allowed_statuses:
            label = dict(Bill.Status.choices)[bill.status].lower()
            raise ValidationError({"bills": f"Tagihan {bill.fee_type.name} {bill.period} berstatus {label}."})
    return sorted(bills, key=lambda b: (b.period, b.fee_type_id))


def allocate(bills, available: int) -> int:
    """Berapa tagihan pertama (urut bulan tertua) yang lunas dengan uang `available`.

    Dialokasikan per BULAN UTUH: satu bulan baru lunas bila semua jenis iurannya tertutup,
    agar tidak ada bulan yang lunas sebagian. Sisa uang menjadi saldo titipan.
    """
    count, i = 0, 0
    while i < len(bills):
        j = i
        while j < len(bills) and bills[j].period == bills[i].period:
            j += 1
        month_total = sum(b.amount for b in bills[i:j])
        if available < month_total:
            break
        available -= month_total
        count = j
        i = j
    return count


@transaction.atomic
def record_payment(
    *, household, bill_ids, method, paid_at, user, note="", amount=None, refund_excess=False, _allow_pending=False,
) -> Payment:
    """Catat uang yang masuk dan alokasikan ke tagihan, mulai dari bulan tertua.

    - amount: uang yang benar-benar diterima (default = total tagihan yang dipilih).
    - Tagihan yang tertutup penuh (uang + saldo titipan) menjadi lunas.
    - Sisa uang menjadi saldo titipan KK, kecuali refund_excess=True: kelebihan dikembalikan
      dan dicatat sebagai pengeluaran kas.
    - Tagihan yang tidak tertutup tetap belum bayar (tagihan bulan mendatang dihapus).
    """
    from apps.finance.models import CashEntry

    household = Household.objects.select_for_update().get(pk=household.pk)
    allowed = {Bill.Status.BELUM, Bill.Status.MENUNGGU} if _allow_pending else {Bill.Status.BELUM}
    bills = _lock_bills(household, bill_ids, allowed)
    received = sum(b.amount for b in bills) if amount is None else int(amount)
    if received < 0:
        raise ValidationError({"amount": "Nominal tidak boleh negatif."})

    credit_before = household.credit
    n_paid = allocate(bills, received + credit_before)
    paid, unpaid = bills[:n_paid], bills[n_paid:]
    if received == 0 and not paid:
        raise ValidationError({"amount": "Nominal pembayaran kosong."})
    allocated = sum(b.amount for b in paid)
    leftover = received + credit_before - allocated
    refund = max(0, min(leftover, received - allocated)) if refund_excess and not unpaid else 0

    payment = Payment.objects.create(
        household=household, total=received, method=method, paid_at=paid_at, recorded_by=user, note=note,
        credit_change=leftover - refund - credit_before, refund=refund,
    )
    if paid:
        Bill.objects.filter(pk__in=[b.pk for b in paid]).update(status=Bill.Status.LUNAS, payment=payment)
    if unpaid:
        unpaid_qs = Bill.objects.filter(pk__in=[b.pk for b in unpaid])
        unpaid_qs.filter(status=Bill.Status.MENUNGGU).update(status=Bill.Status.BELUM)
        _drop_unpaid_future_bills(unpaid_qs)
    household.credit = leftover - refund
    household.save(update_fields=["credit", "updated_at"])

    if refund:
        CashEntry.objects.create(
            kind=CashEntry.Kind.OUT, category=CashEntry.Category.PENGEMBALIAN, amount=refund, date=paid_at,
            description=f"Pengembalian lebih bayar iuran {household.head_name} ({household.label})", recorded_by=user,
        )
    audit(
        user, "catat_pembayaran", payment, received=received, allocated=allocated, method=method,
        paid=[b.pk for b in paid], unpaid=[b.pk for b in unpaid], credit=household.credit, refund=refund,
    )
    apply_credit(household, user)
    return payment


@transaction.atomic
def apply_credit(household, user=None) -> Payment | None:
    """Lunasi tagihan yang belum dibayar (bulan tertua dulu) dari saldo titipan KK."""
    household = Household.objects.select_for_update().get(pk=household.pk)
    if household.credit <= 0:
        return None
    bills = list(
        Bill.objects.select_for_update()
        .filter(household=household, status=Bill.Status.BELUM, period__lte=current_period())
        .order_by("period", "fee_type_id")
    )
    n = allocate(bills, household.credit)
    if not n:
        return None
    covered = bills[:n]
    used = sum(b.amount for b in covered)
    payment = Payment.objects.create(
        household=household, total=0, method=Payment.Method.TITIPAN, paid_at=timezone.localdate(),
        recorded_by=user if user and user.is_authenticated else None, note="Dibayar dari saldo titipan", credit_change=-used,
    )
    Bill.objects.filter(pk__in=[b.pk for b in covered]).update(status=Bill.Status.LUNAS, payment=payment)
    household.credit -= used
    household.save(update_fields=["credit", "updated_at"])
    audit(user, "pakai_titipan", payment, used=used, bills=[b.pk for b in covered])
    return payment


@transaction.atomic
def submit_proof(*, household, user, bill_ids, file, amount, transfer_date, method, note="", periods=None) -> PaymentProof:
    """Warga mengunggah bukti bayar (boleh beberapa bulan, termasuk bayar di muka). Tagihan menjadi 'menunggu verifikasi'."""
    bill_ids = list(bill_ids) + ensure_future_bills(household, periods)
    bills = _lock_bills(household, bill_ids, {Bill.Status.BELUM})
    proof = PaymentProof.objects.create(
        household=household, uploaded_by=user, file=file, amount=amount,
        transfer_date=transfer_date, method=method, note=note,
    )
    proof.bills.set(bills)
    Bill.objects.filter(pk__in=[b.pk for b in bills]).update(status=Bill.Status.MENUNGGU)
    audit(user, "unggah_bukti", proof, amount=amount, bills=[b.pk for b in bills])
    return proof


@transaction.atomic
def approve_proof(proof: PaymentProof, user, note: str = "", amount=None, refund_excess=False) -> PaymentProof:
    """Terima bukti bayar. `amount` = uang yang benar-benar masuk (default: nominal yang diisi warga)."""
    proof = PaymentProof.objects.select_for_update().get(pk=proof.pk)
    if proof.status != PaymentProof.Status.PENDING:
        raise ValidationError("Bukti ini sudah diverifikasi.")
    received = proof.amount if amount in (None, "") else int(amount)
    payment = record_payment(
        household=proof.household, bill_ids=list(proof.bills.values_list("pk", flat=True)),
        method=proof.method, paid_at=proof.transfer_date, user=user, amount=received,
        refund_excess=refund_excess, note=f"Bukti bayar #{proof.pk}", _allow_pending=True,
    )
    proof.status = PaymentProof.Status.ACCEPTED
    proof.review_note = note
    proof.verified_by = user
    proof.verified_at = timezone.now()
    proof.payment = payment
    proof.save()
    audit(user, "terima_bukti", proof, received=received)
    return proof


@transaction.atomic
def reject_proof(proof: PaymentProof, user, note: str) -> PaymentProof:
    proof = PaymentProof.objects.select_for_update().get(pk=proof.pk)
    if proof.status != PaymentProof.Status.PENDING:
        raise ValidationError("Bukti ini sudah diverifikasi.")
    if not (note or "").strip():
        raise ValidationError({"review_note": "Tuliskan alasan penolakan agar warga tahu yang harus diperbaiki."})
    proof.bills.filter(status=Bill.Status.MENUNGGU).update(status=Bill.Status.BELUM)
    _drop_unpaid_future_bills(proof.bills.all())
    proof.status = PaymentProof.Status.REJECTED
    proof.review_note = note
    proof.verified_by = user
    proof.verified_at = timezone.now()
    proof.save()
    audit(user, "tolak_bukti", proof, note=note)
    return proof


def bill_summary(year: int, include_private: bool) -> dict:
    """Rekap matriks rumah × bulan.

    include_private=False (warga): hanya label rumah, nama kepala keluarga, dan status.
    """
    periods = [f"{year}-{m:02d}" for m in range(1, 13)]
    per_household = defaultdict(lambda: defaultdict(list))
    for b in Bill.objects.filter(period__startswith=f"{year}-").values("household_id", "period", "status", "amount"):
        per_household[b["household_id"]][b["period"]].append(b)

    income = dict.fromkeys(periods, 0)
    rows = []
    for household in Household.objects.filter(is_active=True).prefetch_related("members"):
        cells, arrears = {}, 0
        for p in periods:
            items = per_household[household.pk].get(p, [])
            cells[p] = aggregate_status(i["status"] for i in items)
            for i in items:
                if i["status"] == Bill.Status.LUNAS:
                    income[p] += i["amount"]
                elif i["status"] == Bill.Status.BELUM:
                    arrears += i["amount"]
        row = {"household_id": household.pk, "label": household.label, "head_name": household.head_name, "cells": cells}
        if include_private:
            row["arrears"] = arrears
            row["credit"] = household.credit
        rows.append(row)

    data = {"year": year, "periods": periods, "rows": rows}
    if include_private:
        data["income"] = income
    return data
