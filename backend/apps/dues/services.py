from collections import defaultdict

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import audit
from apps.core.utils import aggregate_status, current_period, is_valid_period
from apps.residents.models import Household

from .models import Bill, FeeType, Payment, PaymentProof


def generate_bills(period: str | None = None) -> int:
    """Buat tagihan iuran bulanan untuk semua KK aktif. Aman dijalankan berulang."""
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
    return created


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
    return bills


@transaction.atomic
def record_payment(*, household, bill_ids, method, paid_at, user, note="", _allow_pending=False) -> Payment:
    """Pengurus mencatat pembayaran (mis. tunai). Tagihan langsung lunas."""
    allowed = {Bill.Status.BELUM, Bill.Status.MENUNGGU} if _allow_pending else {Bill.Status.BELUM}
    bills = _lock_bills(household, bill_ids, allowed)
    payment = Payment.objects.create(
        household=household, total=sum(b.amount for b in bills), method=method,
        paid_at=paid_at, recorded_by=user, note=note,
    )
    Bill.objects.filter(pk__in=[b.pk for b in bills]).update(status=Bill.Status.LUNAS, payment=payment)
    audit(user, "catat_pembayaran", payment, total=payment.total, bills=[b.pk for b in bills], method=method)
    return payment


@transaction.atomic
def submit_proof(*, household, user, bill_ids, file, amount, transfer_date, method, note="") -> PaymentProof:
    """Warga mengunggah bukti bayar. Tagihan menjadi 'menunggu verifikasi'."""
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
def approve_proof(proof: PaymentProof, user, note: str = "") -> PaymentProof:
    proof = PaymentProof.objects.select_for_update().get(pk=proof.pk)
    if proof.status != PaymentProof.Status.PENDING:
        raise ValidationError("Bukti ini sudah diverifikasi.")
    payment = record_payment(
        household=proof.household, bill_ids=list(proof.bills.values_list("pk", flat=True)),
        method=proof.method, paid_at=proof.transfer_date, user=user,
        note=f"Bukti bayar #{proof.pk}", _allow_pending=True,
    )
    proof.status = PaymentProof.Status.ACCEPTED
    proof.review_note = note
    proof.verified_by = user
    proof.verified_at = timezone.now()
    proof.payment = payment
    proof.save()
    audit(user, "terima_bukti", proof)
    return proof


@transaction.atomic
def reject_proof(proof: PaymentProof, user, note: str) -> PaymentProof:
    proof = PaymentProof.objects.select_for_update().get(pk=proof.pk)
    if proof.status != PaymentProof.Status.PENDING:
        raise ValidationError("Bukti ini sudah diverifikasi.")
    if not (note or "").strip():
        raise ValidationError({"review_note": "Tuliskan alasan penolakan agar warga tahu yang harus diperbaiki."})
    proof.bills.filter(status=Bill.Status.MENUNGGU).update(status=Bill.Status.BELUM)
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
        rows.append(row)

    data = {"year": year, "periods": periods, "rows": rows}
    if include_private:
        data["income"] = income
    return data
