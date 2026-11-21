from django.contrib.auth import login, logout, update_session_auth_hash
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import User
from .serializers import ChangePasswordSerializer, LoginSerializer, MeSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    """Memastikan cookie `csrftoken` terpasang sebelum login."""
    return Response({"detail": "ok"})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ident = ser.validated_data["identifier"].strip()
        # Urutan prioritas: username, lalu no. HP, lalu email
        user = (
            User.objects.filter(username__iexact=ident).first()
            or User.objects.filter(phone=ident).first()
            or User.objects.filter(email__iexact=ident).first()
        )
        wrong = Response({"detail": "Username/No. HP atau kata sandi salah."}, status=status.HTTP_400_BAD_REQUEST)
        if not user or not user.check_password(ser.validated_data["password"]):
            return wrong
        if not user.is_active:
            # Beri tahu status pendaftaran hanya kepada pemilik akun (kata sandi sudah benar)
            reg = getattr(user, "registration", None)
            if reg and reg.status == "pending":
                return Response({"detail": "Pendaftaran Anda sedang menunggu aktivasi oleh pengurus RT."}, status=status.HTTP_403_FORBIDDEN)
            if reg and reg.status == "ditolak":
                return Response({"detail": f"Pendaftaran ditolak pengurus RT: {reg.review_note}"}, status=status.HTTP_403_FORBIDDEN)
            return wrong
        login(request, user)
        return Response(MeSerializer(user).data)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)


class ChangePasswordView(APIView):
    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        request.user.set_password(ser.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)
        return Response({"detail": "Kata sandi berhasil diubah."})
