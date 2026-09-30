from rest_framework.permissions import BasePermission


def _active_role(user):
    return getattr(user, "role", None)


class IsKaazbir(BasePermission):
    """Allows only the currently active kaazbir role.

    One account may unlock both roles; ``user.role`` always holds the
    active one, so switching roles flips these checks without relogin.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _active_role(request.user) == "kaazbir"
        )


class IsHirer(BasePermission):
    """Allows only the currently active hirer role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _active_role(request.user) == "hirer"
        )


class HasRole(BasePermission):
    """Allows any unlocked role, regardless of which is active.

    Useful for discoverability (e.g. a hirer browsing kaazbirs should see
    users who unlocked kaazbir even while they are acting as hirer).
    Use ``HasRole(\"kaazbir\")`` as ``permission_classes = [HasRole(\"x\")]``
    only via subclassing; see ``HasKaazbirUnlocked`` below.
    """

    role = None

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        has_role = getattr(user, "has_role", None)
        if callable(has_role):
            return bool(has_role(self.role))
        return _active_role(user) == self.role


class HasKaazbirUnlocked(HasRole):
    role = "kaazbir"


class HasHirerUnlocked(HasRole):
    role = "hirer"
