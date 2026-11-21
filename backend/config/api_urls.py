from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts import views as accounts
from apps.core import views as core
from apps.dues import views as dues
from apps.finance import views as finance
from apps.posts import views as posts
from apps.reports import views as reports
from apps.residents import views as residents

router = DefaultRouter()
router.register("households", residents.HouseholdViewSet, basename="household")
router.register("residents", residents.ResidentViewSet, basename="resident")
router.register("change-requests", residents.ChangeRequestViewSet, basename="change-request")
router.register("fee-types", dues.FeeTypeViewSet, basename="fee-type")
router.register("bills", dues.BillViewSet, basename="bill")
router.register("payments", dues.PaymentViewSet, basename="payment")
router.register("payment-proofs", dues.PaymentProofViewSet, basename="payment-proof")
router.register("posts", posts.PostViewSet, basename="post")
router.register("cash-entries", finance.CashEntryViewSet, basename="cash-entry")
router.register("registrations", residents.RegistrationViewSet, basename="registration")
router.register("documents", residents.DocumentViewSet, basename="document")

urlpatterns = [
    path("auth/csrf/", accounts.csrf, name="auth-csrf"),
    path("auth/login/", accounts.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", accounts.LogoutView.as_view(), name="auth-logout"),
    path("auth/register/", residents.RegisterView.as_view(), name="auth-register"),
    path("auth/me/", accounts.MeView.as_view(), name="auth-me"),
    path("auth/password/", accounts.ChangePasswordView.as_view(), name="auth-password"),
    path("me/household/", residents.MyHouseholdView.as_view(), name="my-household"),
    path("me/residents/<int:pk>/", residents.MyResidentUpdateView.as_view(), name="my-resident"),
    path("exports/<str:kind>/", reports.ExportView.as_view(), name="export"),
    path("dashboard/", core.DashboardView.as_view(), name="dashboard"),
    *router.urls,
]
