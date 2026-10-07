"""Admin dashboard API — delete one reader's account outright, for test
sign-ups: the Supabase sign-in (freeing the email) and every Ochorus row
(:func:`accounts.deletion.delete_account`).

Super-admin only (``IsAdminEmail``), like the reader's email panel: it is
destructive and irreversible. Audited as ``user.delete``; the log keeps the
masked email, since the record must outlive the account without becoming a
copy of it.
"""

from __future__ import annotations

from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import supabase_admin
from accounts.deletion import delete_account
from accounts.models import UserProfile
from accounts.permissions import IsAdminEmail

from ..audit import AdminAudited
from ..models import AdminAction
from .analytics import mask_email


class AdminUserDeleteView(AdminAudited, APIView):
    """DELETE a reader: their Supabase sign-in, then all their Ochorus data.

    Refuses to delete the account making the request. If Supabase fails, nothing
    local is touched (502), so a retry finds the account whole.
    """

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.USER_DELETE

    def audit_entry(self, request, response):
        return f"user:{self.kwargs.get('uid')}", response.data or {}

    def delete(self, request, uid):
        profile = UserProfile.objects.select_related("user").filter(supabase_uid=uid).first()
        if profile is None:
            return Response({"detail": "No such user."}, status=http_status.HTTP_404_NOT_FOUND)
        if profile.user_id == getattr(request.user, "pk", None):
            return Response(
                {"detail": "You can't delete the account you're signed in with."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        try:
            auth_deleted = delete_account(profile)
        except supabase_admin.SupabaseDeleteError as exc:
            return Response(
                {"detail": f"Couldn't delete the Supabase sign-in ({exc}). Nothing was deleted."},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"email": mask_email(profile.email), "auth_deleted": auth_deleted},
            status=http_status.HTTP_200_OK,
        )
