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
        _sum(Payment.objects.active().filter(paid_at__lt=day), "total")
        + _sum(entries.filter(kind=CashEntry.Kind.IN))
        - _sum(entries.filter(kind=CashEntry.Kind.OUT))
    )


def current_balance() -> int:
    return (
        _sum(Payment.objects.active(), "total")
        + _sum(CashEntry.objects.filter(kind=CashEntry.Kind.IN))
        - _sum(CashEntry.objects.filter(kind=CashEntry.Kind.OUT))
    )


def cash_report(year: int) -> dict:
    """Laporan kas per bulan. Iuran warga dihitung dari tanggal pembayaran."""
    opening = balance_before(date(year, 1, 1))
    entries = CashEntry.objects.filter(date__year=year)
    payments = Payment.objects.active().filter(paid_at__year=year)

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


MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
MONTHS_LONG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def periods_label(periods) -> str:
    """['2025-12', '2026-01', '2026-02'] -> 'Des 2025, Jan, Feb 2026'"""
    by_year: dict[str, list[str]] = {}
    for p in sorted(set(periods)):
        by_year.setdefault(p[:4], []).append(MONTHS[int(p[5:]) - 1])
    return ", ".join(f"{', '.join(ms)} {y}" for y, ms in by_year.items())


def ledger(year: int, month: int | None = None, kind: str | None = None, private: bool = False) -> list[dict]:
    """Buku kas gabungan: transaksi kas + pemasukan iuran, terbaru lebih dulu.

    private=True (pengurus): setiap pembayaran iuran tampil dengan nama kepala keluarga & no. rumah.
    private=False (warga): iuran diringkas per bulan, tanpa nama/nominal per rumah.
    """
    rows = []
    entries = CashEntry.objects.filter(date__year=year).select_related("recorded_by")
    if month:
        entries = entries.filter(date__month=month)
    if kind:
        entries = entries.filter(kind=kind)
    for e in entries:
        rows.append({
            "source": "kas", "id": e.pk, "kind": e.kind, "category": e.category,
            "category_label": e.get_category_display(), "description": e.description, "amount": e.amount,
            "date": e.date, "receipt": bool(e.receipt), "recorded_by_name": e.recorded_by.display_name if e.recorded_by else None,
            "household_id": None,
        })

    if kind in (None, "", CashEntry.Kind.IN):
        payments = Payment.objects.active().filter(paid_at__year=year, total__gt=0).select_related("household", "recorded_by").prefetch_related(
            "bills", "household__members"
        )
        if month:
            payments = payments.filter(paid_at__month=month)
        if private:
            for p in payments:
                periods = periods_label(b.period for b in p.bills.all())
                extra = ""
                if p.credit_change > 0:
                    extra = f" · +Rp{p.credit_change:,} titipan".replace(",", ".")
                elif p.credit_change < 0:
                    extra = f" · pakai titipan Rp{-p.credit_change:,}".replace(",", ".")
                rows.append({
                    "source": "iuran", "id": p.pk, "kind": CashEntry.Kind.IN, "category": "iuran",
                    "category_label": "Iuran warga",
                    "description": f"Iuran {p.household.head_name} ({p.household.label}) · {periods or 'titipan'} · {p.get_method_display().lower()}{extra}",
                    "amount": p.total, "date": p.paid_at, "receipt": False,
                    "recorded_by_name": p.recorded_by.display_name if p.recorded_by else None,
                    "household_id": p.household_id,
                })
        else:
            per_month: dict[int, dict] = {}
            for p in Payment.objects.active().filter(pk__in=payments.values("pk")).only("total", "paid_at"):
                m = per_month.setdefault(p.paid_at.month, {"amount": 0, "count": 0, "date": p.paid_at})
                m["amount"] += p.total
                m["count"] += 1
                m["date"] = max(m["date"], p.paid_at)
            for m, agg in per_month.items():
                rows.append({
                    "source": "iuran", "id": m, "kind": CashEntry.Kind.IN, "category": "iuran",
                    "category_label": "Iuran warga",
                    "description": f"Iuran warga bulan {MONTHS_LONG[m - 1]} ({agg['count']} pembayaran)",
                    "amount": agg["amount"], "date": agg["date"], "receipt": False, "recorded_by_name": None,
                    "household_id": None,
                })

    rows.sort(key=lambda r: (r["date"], r["source"] == "kas", r["id"]), reverse=True)
    return rows
