from django.conf import settings
from django.db import models


def split_providers(value: str) -> list[str]:
    """The comma-joined ``UserProfile.providers`` string, back to a list.

    The single home for the "blank entries mean nothing" convention, shared by
    the model property and the admin analytics (which reads the raw column via
    ``values_list`` and so can't use the property)."""
    return [p for p in value.split(",") if p]


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

    # Which Supabase auth providers this account has signed in with, as a
    # comma-joined sorted list (e.g. "email,google"). Captured from the JWT's
    # ``app_metadata.providers`` on each authenticated request, so it fills in
    # going forward — a row created before this existed stays blank until its
    # owner signs in again. Blank means "not yet observed", not "no provider".
    providers = models.CharField(max_length=255, blank=True, default="")
    # Last time an authenticated request from this account was seen. Distinct
    # from ``updated_at`` (which only moves when the profile is *saved*): touched
    # by authentication, throttled to at most once per LAST_SEEN_THROTTLE so it
    # isn't a write on every request. Null until the first sign-in after it was
    # added.
    last_seen_at = models.DateTimeField(null=True, blank=True)

    # The reader's browser IANA timezone (e.g. "Europe/London"), captured
    # client-side on sign-in. NOT an IP address — a rough, privacy-light
    # geography signal only, from which the admin analytics derive an
    # approximate country (accounts/geo.py). Blank until first observed; a row
    # created before this existed stays blank until its owner signs in again.
    timezone = models.CharField(max_length=40, blank=True, default="")

    # Indexed: the admin's recent-sign-ups list orders by it, and the sign-up
    # range counts (signups_7d/30d) filter on it.
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.email or str(self.supabase_uid)

    @property
    def provider_list(self) -> list[str]:
        """The recorded sign-in providers, split back into a list."""
        return split_providers(self.providers)
