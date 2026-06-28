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
    """Return the authenticated user's profile (and create it on first call)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"supabase_uid": request.user.username, "email": request.user.email},
        )
        return Response(
            {
                "email": profile.email,
                "display_name": profile.display_name,
                "locale": profile.locale,
                "theme": profile.theme,
                "font_scale": profile.font_scale,
            }
        )
