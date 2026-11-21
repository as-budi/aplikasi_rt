from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import is_staff_rt
from apps.core.utils import aggregate_status, current_period
from apps.dues.models import Bill, PaymentProof
from apps.dues.serializers import BillSerializer
from apps.finance.services import current_balance
from apps.posts.models import Post
from apps.posts.serializers import PostSerializer
from apps.residents.models import ChangeRequest, Household, Registration, Resident


class DashboardView(APIView):
    """Ringkasan untuk halaman Beranda, disesuaikan dengan peran."""

    def get(self, request):
        user = request.user
        period = current_period()
        data = {"period": period, "me": None, "staff": None, "cash_balance": current_balance()}

        household = user.household
        if household:
            bills = list(Bill.objects.filter(household=household).select_related("fee_type", "payment", "household"))
            current = [b for b in bills if b.period == period]
            unpaid = [b for b in bills if b.status == Bill.Status.BELUM]
            data["me"] = {
                "household_id": household.pk,
                "household_label": household.label,
                "head_name": household.head_name,
                "current_status": aggregate_status(b.status for b in current),
                "current_bills": BillSerializer(current, many=True).data,
                "arrears_total": sum(b.amount for b in unpaid),
                "arrears_months": len({b.period for b in unpaid}),
            }

        if is_staff_rt(user):
            active = Household.objects.filter(is_active=True)
            current_bills = Bill.objects.filter(period=period, household__is_active=True)
            per_household = {}
            for hh_id, st in current_bills.values_list("household_id", "status"):
                per_household.setdefault(hh_id, []).append(st)
            paid = sum(1 for sts in per_household.values() if aggregate_status(sts) == Bill.Status.LUNAS)

            top = (
                Bill.objects.filter(status=Bill.Status.BELUM, household__is_active=True)
                .values("household")
                .annotate(total=Sum("amount"), months=Count("period", distinct=True))
                .order_by("-total")[:5]
            )
            labels = {h.pk: h for h in active.filter(pk__in=[t["household"] for t in top]).prefetch_related("members")}
            data["staff"] = {
                "households": active.count(),
                "residents": Resident.objects.filter(household__is_active=True, status=Resident.Status.AKTIF).count(),
                "billed_households": len(per_household),
                "paid_households": paid,
                "income": current_bills.filter(status=Bill.Status.LUNAS).aggregate(s=Sum("amount"))["s"] or 0,
                "target": current_bills.aggregate(s=Sum("amount"))["s"] or 0,
                "pending_proofs": PaymentProof.objects.filter(status=PaymentProof.Status.PENDING).count(),
                "pending_changes": ChangeRequest.objects.filter(status=ChangeRequest.Status.PENDING).count(),
                "pending_registrations": Registration.objects.filter(status=Registration.Status.PENDING).count(),
                "top_arrears": [
                    {
                        "household_id": t["household"],
                        "label": labels[t["household"]].label,
                        "head_name": labels[t["household"]].head_name,
                        "months": t["months"],
                        "total": t["total"],
                    }
                    for t in top
                    if t["household"] in labels
                ],
            }

        published = Post.objects.filter(is_published=True).select_related("author")
        data["upcoming_events"] = PostSerializer(
            published.filter(type=Post.Type.KEGIATAN, event_at__gte=timezone.now()).order_by("event_at")[:3], many=True
        ).data
        data["latest_news"] = PostSerializer(published.filter(type=Post.Type.BERITA)[:3], many=True).data
        return Response(data)
