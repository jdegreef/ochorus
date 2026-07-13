from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """App-side profile for a Supabase-authenticated user.

    Auth lives in Supabase; this row stores reading preferences and links the
    Supabase user (by UUID) to a Django User for DRF's permission machinery.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    supabase_uid = models.UUIDField(unique=True)
    email = models.EmailField(blank=True)
    display_name = models.CharField(max_length=120, blank=True)
    # Preferred reading language (BCP-47-ish short code, e.g. "en", "sw").
    locale = models.CharField(max_length=10, default="en")
    # Reader preferences.
    theme = models.CharField(max_length=20, default="paper")
    font_scale = models.FloatField(default=1.0)
    # Listening (Text-to-Speech) preferences. tts_voice_uri is the device
    # SpeechSynthesis voiceURI — best-effort across devices (a voice absent on
    # another device is ignored and the default is used).
    tts_rate = models.FloatField(default=1.0)
    tts_voice_uri = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.email or str(self.supabase_uid)
