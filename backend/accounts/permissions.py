"""Access control for the admin content dashboard.

Ochorus has no ``is_staff`` concept of its own — every user is a Supabase
account mapped to a bare Django ``User`` (see ``accounts.authentication``). Admin
access is therefore an *email allowlist*: ``ADMIN_EMAILS`` in settings (driven by
the env var of the same name) lists the addresses allowed to see the dashboard
and hit ``/api/admin/*``.

In ``DEBUG`` (local dev, usually with auth unconfigured and no signed-in user)
the check is bypassed so the dashboard is reachable without wiring up Supabase —
but only for requests arriving from the loopback interface. The admin surface
mutates state (publish, author-create, translation jobs), so the bypass must
not turn a single misconfigured env var (``DJANGO_DEBUG=true`` on the host)
into a world-open admin API: a remote client never gets the bypass, DEBUG or
not. Production always requires an authenticated user whose email is on the
list.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework import permissions

from .authentication import token_email_is_verified

#: Client addresses that count as "the developer's own machine".
_LOOPBACK_ADDRS = frozenset({"127.0.0.1", "::1"})


def _is_loopback(request) -> bool:
    return (
        request is not None
        and request.META.get("REMOTE_ADDR") in _LOOPBACK_ADDRS
    )


def is_admin_user(user, request=None) -> bool:
    """True if ``user`` may view the admin dashboard.

    Under ``DEBUG`` the allowlist is skipped for loopback requests only (the
    local-dev convenience). Everywhere else — including any remote request on a
    DEBUG server — the user's email must be in ``settings.ADMIN_EMAILS`` *and*
    the token must assert that email is verified (so a disabled email-confirmation
    setting can't let anyone claim the admin's address).
    """
    if settings.DEBUG and _is_loopback(request):
        return True
    email = (getattr(user, "email", "") or "").strip().lower()
    if not (email and email in settings.ADMIN_EMAILS):
        return False
    # An allowlisted address only grants admin when the token proves the address
    # is *verified*. Otherwise — e.g. if Supabase email confirmation is disabled —
    # anyone could register claiming the admin's email and inherit admin. DRF puts
    # the decoded JWT on ``request.auth``; absent (no token) → not verified.
    return token_email_is_verified(getattr(request, "auth", None))


class IsAdminEmail(permissions.BasePermission):
    """Allow only allowlisted admins (see :func:`is_admin_user`)."""

    message = "Admin access is required for this endpoint."

    def has_permission(self, request, view) -> bool:
        return is_admin_user(request.user, request)


def _verified_email(user, request) -> str | None:
    """The signed-in user's email, but only if the token proves it verified —
    the same bar :func:`is_admin_user` holds the allowlist to. ``None`` otherwise."""
    email = (getattr(user, "email", "") or "").strip().lower()
    if not email:
        return None
    if not token_email_is_verified(getattr(request, "auth", None)):
        return None
    return email


def has_capability(request, capability, verb, language=None) -> bool:
    """True if this request may perform ``verb`` on ``capability`` (in
    ``language`` when the action is language-scoped).

    Super admins (the ``ADMIN_EMAILS`` allowlist, and the DEBUG-loopback
    convenience) always pass — that's the bootstrap. Everyone else must hold a
    covering :class:`~accounts.models.AdminGrant` on a *verified* account. With no
    grants issued, this is exactly today's behaviour: super admins in, all others
    out.
    """
    if is_admin_user(request.user, request):
        return True
    email = _verified_email(request.user, request)
    if email is None:
        return False
    from .models import AdminGrant  # local: models import at call time, not app-load

    return AdminGrant.allows(email, capability, verb, language)


def allowed_languages(request, capability, verb):
    """The languages this request may act on for ``capability`` at ``verb``.

    Returns ``None`` for "all" — a super admin, or a grant scoped to ``*`` — and
    otherwise the set of covered codes (possibly empty). This is how endpoints
    whose language is *per row* rather than per request (a batch review decision,
    a multi-language list) enforce scope where the view-level
    :class:`RequireCapability` can't: filter reads to the set, and refuse writes
    to rows outside it. Callers treat ``None`` as "no restriction".
    """
    if is_admin_user(request.user, request):
        return None
    email = _verified_email(request.user, request)
    if email is None:
        return set()
    from .models import ALL_LANGUAGES, AdminGrant

    codes = set()
    for g in AdminGrant.objects.filter(email=email, capability=capability):
        if not g.satisfies(verb):
            continue
        languages = g.language_set
        if ALL_LANGUAGES in languages:
            return None
        codes |= languages
    return codes


class RequireCapability(permissions.BasePermission):
    """Gate an admin endpoint on a scoped capability grant (or super admin).

    The view declares what it needs, co-located with the view:

    * ``admin_capability`` — an :class:`~accounts.models.AdminCapability` value.
    * ``admin_verb`` — the required :class:`~accounts.models.AdminVerb` for every
      method, OR ``admin_verbs`` — a ``{method: verb}`` map when a view reads at
      one verb and writes at another (e.g. review-queue: GET ``view``, POST
      ``act``).
    * ``admin_language_arg`` — for a language-scoped view, where the target
      language is: a URL kwarg name (``"code"``) or a request field (``"language"``).
      Omitted ⇒ the action is global and the grant's language scope is ignored.

    A view that declares no capability denies everyone but a super admin — fail
    closed. ``library.tests_admin_access`` walks the URL conf and fails the build
    if any admin route ships without a valid declaration, so that can't happen
    silently.
    """

    message = "You don't have access to this admin capability."

    def has_permission(self, request, view) -> bool:
        if is_admin_user(request.user, request):
            return True
        capability = getattr(view, "admin_capability", None)
        verb = self._required_verb(request, view)
        if not capability or not verb:
            return False
        language = self._language(request, view)
        # A view that declares a language dimension but whose language we cannot
        # resolve must FAIL CLOSED — the same ``None`` that means "global" for an
        # unscoped view would otherwise wave a scoped request through with no
        # language check. A view whose language is per-item (a batch) declares no
        # ``admin_language_arg`` and enforces scope per item in the handler (see
        # ``allowed_languages``); the coverage test guards that choice.
        if getattr(view, "admin_language_arg", None) and language is None:
            return False
        return has_capability(request, capability, verb, language)

    @staticmethod
    def _required_verb(request, view):
        verbs = getattr(view, "admin_verbs", None)
        if verbs and request.method in verbs:
            return verbs[request.method]
        return getattr(view, "admin_verb", None)

    @staticmethod
    def _language(request, view):
        arg = getattr(view, "admin_language_arg", None)
        if not arg:
            return None
        match = getattr(request, "resolver_match", None)
        if match and arg in (match.kwargs or {}):
            return (str(match.kwargs[arg]).strip().lower() or None)
        val = None
        if request.method not in ("GET", "HEAD", "OPTIONS") and hasattr(request, "data"):
            val = request.data.get(arg)
        if val is None and hasattr(request, "query_params"):
            val = request.query_params.get(arg)
        return (str(val).strip().lower() or None) if val is not None else None


def requires(capability, *, verb=None, verbs=None, language_arg=None):
    """Class decorator declaring an admin view's required capability + verb and
    wiring :class:`RequireCapability` as its permission — the whole gate in one
    co-located line above the view. Pass ``verb`` for a single required verb
    across all methods, or ``verbs={"GET": "view", "POST": "act"}`` when a view
    reads and writes at different verbs; ``language_arg`` names where the target
    language is for a language-scoped view (a URL kwarg like ``"code"`` or a
    request field like ``"language"``).
    """

    def deco(cls):
        cls.admin_capability = capability
        if verbs:
            cls.admin_verbs = dict(verbs)
            cls.admin_verb = verb or "view"  # fallback for methods not in the map
        elif verb is not None:
            cls.admin_verb = verb
        else:
            raise ValueError(f"@requires on {cls.__name__} needs verb or verbs")
        cls.admin_language_arg = language_arg
        cls.permission_classes = [RequireCapability]
        return cls

    return deco
