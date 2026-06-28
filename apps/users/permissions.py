from rest_framework.permissions import BasePermission


class IsKaazbir(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "kaazbir"
        )


class IsHirer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "hirer"
        )
