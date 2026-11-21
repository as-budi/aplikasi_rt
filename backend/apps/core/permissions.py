from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_staff_rt(user) -> bool:
    """Admin dan pengurus RT."""
    return bool(user and user.is_authenticated and getattr(user, "role", None) in ("admin", "pengurus"))


class IsStaffRT(BasePermission):
    message = "Hanya pengurus RT yang dapat melakukan tindakan ini."

    def has_permission(self, request, view):
        return is_staff_rt(request.user)


class IsStaffOrReadOnly(BasePermission):
    message = "Hanya pengurus RT yang dapat mengubah data ini."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or is_staff_rt(request.user)
