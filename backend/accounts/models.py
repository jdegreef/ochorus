from django.conf import settings
from django.db import models


def split_providers(value: str) -> list[str]:
    """The comma-joined ``UserProfile.providers`` string, back to a list.

    The single home for the "blank entries mean nothing" convention, shared by
    the model property and the admin analytics (which reads the raw column via
    ``values_list`` and so can't use the property)."""
    return [p for p in value.split(",") if p]


#: The logged-out home sign-up band arms (``UserProfile.signup_variant``). Three
#: random A/B arms shown to first-time visitors, plus ``progress`` — the
#: progress-targeted variant shown only to readers who already have local
#: reading. Kept here so the JWT capture (``accounts.authentication``) and the
#: admin breakdown (``library.admin_views.analytics``) share one vocabulary; an
#: unknown value from a stray client is dropped rather than stored.
SIGNUP_VARIANTS = ("keep", "habit", "library", "progress")


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

    # Which logged-out sign-up band drove this account — the home page's A/B +
    # targeted sign-up prompt (see SIGNUP_VARIANTS). Captured from the JWT's
    # ``user_metadata.signup_variant`` at profile CREATION only (a create-only
    # observation, like the fixture-owned fields): a later login never revisits
    # it, so it records the arm that was showing when the reader actually signed
    # up. Blank for accounts created before this shipped and for sign-ups that
    # carried no variant (e.g. Google OAuth, which can't pass metadata).
    signup_variant = models.CharField(max_length=32, blank=True, default="")

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


class AdminCapability(models.TextChoices):
    """The feature areas admin access is granted over. Each maps to a set of
    ``/api/admin/*`` endpoints, which declare their capability via the
    ``admin_capability``/``admin_verb`` attributes the ``RequireCapability``
    permission reads (coverage enforced by ``library.tests_admin_access``).
    ``USERS`` is split from ``REPORTING`` on purpose: it exposes PII (names,
    emails, sign-in providers), so viewing it is a distinct grant."""

    REPORTING = "reporting", "Reporting & analytics"
    USERS = "users", "User analytics (PII)"
    AUDIT = "audit", "Content audit & quality"
    REVIEW = "review", "Content review"
    PUBLISH = "publish", "Publishing & imports"
    TRANSLATE = "translate", "Translation queue"
    CONTENT_EDIT = "content_edit", "Content-edit queue"
    AUTHORS = "authors", "Author records"
    LANGUAGE_ADMIN = "language_admin", "Language administration"
    EMAIL = "email", "Email campaigns (compose & send)"
    FEEDBACK = "feedback", "Reader feedback queue"


class AdminVerb(models.TextChoices):
    """How far a grant lets someone go, as a ladder — a grant at a higher rank
    satisfies any requirement at or below it (see ``VERB_RANK``)."""

    VIEW = "view", "View"
    SUGGEST = "suggest", "Suggest (file a job; apply nothing)"
    ACT = "act", "Act (apply changes)"
    APPROVE = "approve", "Approve (confirm others' work; pull high-privilege levers)"


#: Ability ladder as data, so the check is a comparison rather than a chain of
#: ``if``s. A grant of ``act`` also satisfies a required ``view``/``suggest``.
VERB_RANK = {
    AdminVerb.VIEW: 0,
    AdminVerb.SUGGEST: 1,
    AdminVerb.ACT: 2,
    AdminVerb.APPROVE: 3,
}

#: Sentinel in ``AdminGrant.languages`` meaning "every language".
ALL_LANGUAGES = "*"


class AdminGrant(models.Model):
    """One scoped admin permission for one person.

    The super admin is still the ``ADMIN_EMAILS`` allowlist (see
    ``accounts.permissions``) — that bootstrap sits OUTSIDE this table so a bad
    grant edit can never lock everyone out. Everyone else's admin power is the
    set of these rows.

    A grant is keyed by EMAIL, not a user FK, so it can be issued before the
    person has ever signed in (there is no local ``User``/``UserProfile`` row
    until then) and activates when that *verified* account authenticates. The
    unit is ``(email, capability) → verb`` over a language scope; a named role
    (Contributor, Reviewer) is just a bundle of these rows applied together (see
    the ``admin_grants`` command) — the rows are the truth, the role is a label.
    """

    email = models.EmailField()
    capability = models.CharField(max_length=20, choices=AdminCapability.choices)
    verb = models.CharField(max_length=10, choices=AdminVerb.choices)
    #: Comma-joined language codes this grant covers, or ``"*"`` for all. Endpoints
    #: that aren't language-scoped ignore it (see ``AdminGrant.covers_language``).
    languages = models.CharField(max_length=200, default=ALL_LANGUAGES)
    #: The super admin who issued it, for the access review. The grant/revoke
    #: *events* are recorded in the append-only ``AdminAction`` log.
    granted_by = models.EmailField(blank=True)
    role_label = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # The unique constraint's composite index (email, capability) already
        # serves the email-led lookups (scopes_for / allows), so no separate
        # single-column index is needed.
        constraints = [
            models.UniqueConstraint(fields=["email", "capability"], name="uniq_admin_grant"),
        ]

    def __str__(self) -> str:
        return f"{self.email} · {self.capability}:{self.verb} [{self.languages}]"

    @property
    def language_set(self) -> set[str]:
        # split_providers is the single home for the comma-split "blanks mean
        # nothing" convention (shared with UserProfile.providers).
        return set(split_providers(self.languages))

    def covers_language(self, language) -> bool:
        """True if this grant applies to ``language``. ``None`` means the action
        isn't language-scoped, which any grant for the capability covers."""
        if language is None:
            return True
        codes = self.language_set
        return ALL_LANGUAGES in codes or language in codes

    def satisfies(self, verb) -> bool:
        """True if this grant's verb is at least ``verb`` on the ladder."""
        return VERB_RANK.get(self.verb, -1) >= VERB_RANK.get(verb, 99)

    @classmethod
    def allows(cls, email, capability, verb, language=None) -> bool:
        """Does any grant for ``email`` permit ``verb`` on ``capability`` in
        ``language``? A blank email never matches — the allowlist path is checked
        separately, in :func:`accounts.permissions.has_capability`."""
        email = (email or "").strip().lower()
        if not email:
            return False
        return any(
            g.satisfies(verb) and g.covers_language(language)
            for g in cls.objects.filter(email=email, capability=capability)
        )

    @classmethod
    def scopes_for(cls, email) -> list[dict]:
        """Every grant for ``email`` as plain dicts — for ``/api/auth/me`` and the
        team console."""
        email = (email or "").strip().lower()
        if not email:
            return []
        return [
            {
                "capability": g.capability,
                "verb": g.verb,
                "languages": sorted(g.language_set),
                "role": g.role_label,
            }
            for g in cls.objects.filter(email=email).order_by("capability")
        ]
