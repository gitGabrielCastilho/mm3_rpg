from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


UserModel = get_user_model()


class UsernameOrEmailBackend(ModelBackend):
    """Allow authentication with either username or email.

    This backend first tries to find a user by username; if not found,
    it falls back to lookup by email (case-insensitive). Password check
    and is_active behavior are delegated to ModelBackend.
    """

    def authenticate(self, request, username: Optional[str] = None, password: Optional[str] = None, **kwargs):  # type: ignore[override]
        if username is None or password is None:
            return None

        login = (username or "").strip()
        user: Optional[UserModel] = None

        # First attempt: username
        try:
            user = UserModel.objects.get(username__iexact=login)
        except UserModel.DoesNotExist:
            # Fallback: unique email (case-insensitive)
            try:
                user = UserModel.objects.get(email__iexact=login)
            except UserModel.DoesNotExist:
                user = None
            except UserModel.MultipleObjectsReturned:
                # Ambiguous email; do not allow login by email in this case
                return None

        if user is None:
            return None

        # Delegate password validation to parent class
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
