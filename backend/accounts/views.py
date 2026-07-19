from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Liveness probe used by Render's health check."""
    return Response({"status": "ok", "service": "ochorus"})


class MeView(APIView):
    """Read/update the authenticated user's profile (reading preferences)."""

    permission_classes = [IsAuthenticated]

    def _profile(self, request):
        from .models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"supabase_uid": request.user.username, "email": request.user.email},
        )
        return profile

    def _serialize(self, profile) -> dict:
        return {
            "email": profile.email,
            "display_name": profile.display_name,
            "locale": profile.locale,
            "theme": profile.theme,
            "font_scale": profile.font_scale,
            "tts_rate": profile.tts_rate,
            "tts_voice_uri": profile.tts_voice_uri,
        }

    def get(self, request):
        from .permissions import is_admin_user

        data = self._serialize(self._profile(request))
        data["is_admin"] = is_admin_user(request.user, request)
        return Response(data)

    def patch(self, request):
        profile = self._profile(request)
        data = request.data
        updated = []

        if isinstance(data.get("locale"), str) and data["locale"]:
            profile.locale = data["locale"][:10]
            updated.append("locale")
        if data.get("theme") in ("paper", "light", "dark"):
            profile.theme = data["theme"]
            updated.append("theme")
        try:
            if data.get("font_scale") is not None:
                profile.font_scale = max(0.8, min(1.6, float(data["font_scale"])))
                updated.append("font_scale")
        except (TypeError, ValueError):
            pass
        try:
            if data.get("tts_rate") is not None:
                profile.tts_rate = max(0.5, min(3.0, float(data["tts_rate"])))
                updated.append("tts_rate")
        except (TypeError, ValueError):
            pass
        if isinstance(data.get("tts_voice_uri"), str):
            profile.tts_voice_uri = data["tts_voice_uri"][:255]
            updated.append("tts_voice_uri")

        if updated:
            profile.save(update_fields=[*updated, "updated_at"])
        return Response(self._serialize(profile))
