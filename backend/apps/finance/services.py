from datetime import date

from django.db.models import Sum

from apps.dues.models import Payment

from .models import CashEntry


def _sum(qs, field="amount") -> int:
    return qs.aggregate(s=Sum(field))["s"] or 0


def balance_before(day: date) -> int:
    """Saldo kas sebelum tanggal `day` (iuran + pemasukan lain − pengeluaran)."""
    entries = CashEntry.objects.filter(date__lt=day)
    return (
        _sum(Payment.objects.filter(paid_at__lt=day), "total")
        + _sum(entries.filter(kind=CashEntry.Kind.IN))
        - _sum(entries.filter(kind=CashEntry.Kind.OUT))
    )


def current_balance() -> int:
    return (
        _sum(Payment.objects.all(), "total")
        + _sum(CashEntry.objects.filter(kind=CashEntry.Kind.IN))
        - _sum(CashEntry.objects.filter(kind=CashEntry.Kind.OUT))
    )


def cash_report(year: int) -> dict:
    """Laporan kas per bulan. Iuran warga dihitung dari tanggal pembayaran."""
    opening = balance_before(date(year, 1, 1))
    entries = CashEntry.objects.filter(date__year=year)
    payments = Payment.objects.filter(paid_at__year=year)

    balance = opening
    months = []
    totals = {"iuran": 0, "other_income": 0, "expense": 0}
    for m in range(1, 13):
        iuran = _sum(payments.filter(paid_at__month=m), "total")
        other = _sum(entries.filter(date__month=m, kind=CashEntry.Kind.IN))
        expense = _sum(entries.filter(date__month=m, kind=CashEntry.Kind.OUT))
        balance += iuran + other - expense
        totals["iuran"] += iuran
        totals["other_income"] += other
        totals["expense"] += expense
        months.append({
            "period": f"{year}-{m:02d}", "iuran": iuran, "other_income": other,
            "expense": expense, "balance": balance,
        })

    labels = dict(CashEntry.Category.choices)
    by_category = [
        {"category": row["category"], "label": labels.get(row["category"], row["category"]), "amount": row["total"]}
        for row in entries.filter(kind=CashEntry.Kind.OUT)
        .values("category").annotate(total=Sum("amount")).order_by("-total")
    ]
    return {
        "year": year,
        "opening_balance": opening,
        "closing_balance": balance,
        "totals": totals,
        "months": months,
        "expense_by_category": by_category,
    }
