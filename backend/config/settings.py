"""
Django settings for Ochorus — a free reader for public-domain Christian classics.

Configuration is driven by environment variables (loaded from a local .env file
in development). See .env.example for the full list. Patterns here mirror the
Take Root backend so the two projects stay operationally consistent.
"""

import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

from common.env import origin_url

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


# --- Core ---------------------------------------------------------------------

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-change-me-ochorus-^0iz7_g&x+_b8*q*bcvmr",
)

DEBUG = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

_external_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if _external_host:
    ALLOWED_HOSTS.append(_external_host)


# --- Applications -------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Needed for SearchVectorField (library.fts); harmless under SQLite dev.
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Local apps
    "accounts",
    "emails",
    "feedback",
    "library",
    "reading",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # must come before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Database -----------------------------------------------------------------
# Set DATABASE_URL to the Supabase Postgres connection string in production.
# Until then, fall back to local SQLite so the skeleton runs with no services.

DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# models.W038: "SQLite does not support deferrable unique constraints."
# `Book`'s one-volume-per-language constraint is DEFERRED so a series can be
# renumbered inside one seed transaction (see the model). Postgres — CI and
# prod — builds it and never raises this; SQLite, the local dev fallback, simply
# skips the constraint and warned about it on every manage.py command. The
# fixture gate (tests_fixture.SeriesMembershipTests) holds the same rule there.
SILENCED_SYSTEM_CHECKS = ["models.W038"]


# --- Auth / passwords ---------------------------------------------------------
# Auth is handled by Supabase (see accounts/authentication.py). Django's own
# password validators only apply to local admin/superuser accounts.

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]


# --- DRF ----------------------------------------------------------------------
# The library (book content) is public, so the default permission is AllowAny.
# Endpoints that touch a user's own data (reading progress, later) opt in to
# IsAuthenticated explicitly.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.SupabaseJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    # JSON only in production. The browsable API renders an interactive HTML
    # console over every endpoint — enumerating fields and drawing write forms
    # for the admin ones — on an origin whose entire job is to serve JSON to a
    # separate SPA. Nothing consumes the HTML, so in production it is pure
    # attack surface (and an HTML-rendering sink on the API origin). Kept in
    # DEBUG, where clicking through endpoints by hand is genuinely useful.
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        *(["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    ],
    "EXCEPTION_HANDLER": "common.exception_handler.detail_exception_handler",
    # No DEFAULT_PAGINATION_CLASS, deliberately. The shelves are a WHOLE-SET
    # contract, not a convenience: the reader filters, facets and sorts them
    # client-side, and the static build prerenders from them — so a page-1
    # response wouldn't shorten a list, it would silently drop books from the
    # shelf and pages from the sitemap. The sets are also small and bounded by
    # editorial effort (one row per work per language), not by user input.
    # Search, the one endpoint whose result set ISN'T bounded that way, pages
    # explicitly via ?type=&offset= (library.views.SearchView).
    # If a shelf ever does outgrow one response, page it there and update the
    # frontend's helper — don't switch the default on, which would change the
    # shape of every list at once from a bare array to {count, results}.
    #
    # Only the endpoints that opt in are throttled — a global anon rate would
    # cap search-as-you-type, which is a legitimate burst. Generous enough that a
    # reader opening several results per search never notices, low enough that
    # the one unauthenticated WRITE endpoint can't be used to grow a table.
    # Backed by the "throttle" local-memory cache (see CACHES), so the limit is
    # per worker and approximate: a bound, not an access control.
    "DEFAULT_THROTTLE_RATES": {
        "search-click": "60/min",
        # Search is a read that writes: every unscoped query logs a row, and a
        # miss runs the fuzzy-suggestion scan. Sized far above a reader (the
        # page debounces at 250ms, so even continuous typing settles well below
        # this) and far below a script that wants to grow the query log.
        "search": "120/min",
        # Per-account cap on reading-state writes (progress, marks, favorites,
        # activity, plan progress, and the sign-in merge). Generous — a reader
        # highlighting or scrolling fast never approaches it — but finite, so a
        # scripted account can't amplify sync into unbounded writes. A bound, not
        # access control: per-worker local-memory cache, keyed by user id.
        "reading": "240/min",
        # Reads of reading state (one per chapter open, for "continue on your
        # other device"): their own budget, so they never eat into the writes' —
        # and still a ceiling.
        "reading-read": "600/min",
        # Resolves a batch of saved-quote slugs to cards (QuoteResolveView). The
        # batch is capped at 200, but the call is a public POST that joins four
        # tables — so it gets a ceiling for parity with the other public
        # endpoints. Sized well above a reader (the shelf resolves once per load).
        "quote-resolve": "120/min",
        # A signed-in reader filing feedback (FeedbackView). Occasional by
        # nature — a handful a day at most — so this only catches a script
        # flooding the queue, never a genuine submitter. Per account.
        "feedback": "20/hour",
        # Whole-book downloads (BookEpubView): each builds an entire book.
        "book-download": "30/min",
    },
    # Exactly one proxy (Render's) sits in front of the app, so the client
    # address is the LAST entry in X-Forwarded-For. Without this, DRF keys
    # throttles on the whole header — which the client writes, so anyone could
    # mint an unlimited supply of fresh buckets by varying it.
    "NUM_PROXIES": 1,
}


# --- Supabase -----------------------------------------------------------------

# Normalized to the project origin: the auth layer appends the JWKS path to
# this, so a pasted REST/auth path (…/rest/v1) would otherwise break token
# validation. See common.env.origin_url.
SUPABASE_URL = origin_url(os.getenv("SUPABASE_URL", ""))
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_JWT_AUDIENCE = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
# The `iss` every token must carry. Left empty, the auth layer derives it from
# SUPABASE_URL as "<origin>/auth/v1", which is what Supabase stamps. Set this
# only for a self-hosted GoTrue whose issuer is not the project origin — it is
# the escape hatch for a derived value being wrong, which would otherwise
# resolve every authenticated request to anonymous.
SUPABASE_JWT_ISSUER = os.getenv("SUPABASE_JWT_ISSUER", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


# --- Admin dashboard ----------------------------------------------------------
# Emails allowed to view the /admin content dashboard and call /api/admin/*.
# There is no is_staff concept (auth is Supabase-only), so admin access is an
# email allowlist. Comma-separated; defaults to the project owner so the
# dashboard works out of the box on deploy. Under DEBUG the check is bypassed
# (see accounts.permissions.is_admin_user).
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "james.degreef@gmail.com").split(",")
    if e.strip()
}

# Translation job queue (admin "Translate" buttons → GitHub issues; see
# library/admin_views/jobs.py). A repo-scoped token that can read/create issues.
# Deliberately NOT an Anthropic credential — prod never holds one; the queued
# jobs are processed by Claude Code worker sessions off-server.
GITHUB_TRANSLATION_TOKEN = os.getenv("GITHUB_TRANSLATION_TOKEN", "")

# Render deploy hook for the WEB service (Render dashboard → ochorus-web →
# Settings → Deploy Hook). Taking a language live has to trigger a rebuild: the
# reader is a prerendered static site, so a status change in the database alone
# changes nothing a reader can see.
#
# Opt-in, like SENTRY_DSN: unset means the go-live action still records the
# launch and tells you plainly that no deploy was fired, rather than pretending
# it shipped. A secret, so it lives in the environment and never in the repo.
RENDER_WEB_DEPLOY_HOOK = os.getenv("RENDER_WEB_DEPLOY_HOOK", "").strip()

# The commit this API instance is serving, surfaced on /api/health/.
#
# The reader is a STATIC site prerendered against this API, and a content commit
# deploys both services at once — so the web build can start while the API is
# still serving the previous release and bake the old content into pages whose
# whole purpose was to show the new content. Publishing the commit here is what
# lets the web build wait for the API to catch up before it prerenders
# (frontend/scripts/await-api-release.mjs).
#
# Render sets RENDER_GIT_COMMIT in every service; unset (local, CI) simply means
# the check has nothing to compare and skips, which is the right default for
# environments where the two aren't deploying together.
RELEASE_COMMIT = os.getenv("RENDER_GIT_COMMIT", "").strip()

# Public origin of the READER (e.g. https://ochorus.com), used to confirm after a
# deploy that a newly live locale actually appears in the built sitemap. Optional:
# without it the post-deploy check reports "unknown" instead of guessing.
PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "").strip().rstrip("/")
GITHUB_TRANSLATION_REPO = os.getenv("GITHUB_TRANSLATION_REPO", "jdegreef/ochorus")


# --- Email programme (Resend) -------------------------------------------------
# Ochorus sends welcome/onboarding, showcase, and update emails through Resend
# and mirrors every open/click/bounce into its own tables (the `emails` app).
#
# EMAIL_ENABLED is the master switch: OFF by default so nothing leaves a dev box
# or CI. Turn it on in production once the sending domain is verified — with it
# off, the pipeline runs and records sends as "skipped" without contacting
# Resend. RESEND_API_KEY and RESEND_WEBHOOK_SECRET are secrets (env only).
EMAIL_ENABLED = env_bool("EMAIL_ENABLED", False)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET", "").strip()
# The From line on outgoing mail, e.g. "Ochorus <hello@news.ochorus.com>". Send
# from a subdomain with DKIM/SPF/DMARC so the root domain's reputation is safe.
EMAIL_FROM = os.getenv("EMAIL_FROM", "Ochorus <hello@news.ochorus.com>").strip()
# This API's own public origin — where unsubscribe/webhook links point. Derived
# from the Render external hostname when unset (production sets that for free).
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "").strip().rstrip("/") or (
    f"https://{_external_host}" if _external_host else ""
)
# Optional cutoff (ISO datetime): the welcome sweep only mails accounts created
# on/after it, so a first run never blasts the back catalogue. Unset ⇒ a short
# recent window (see emails/management/commands/send_welcome_emails.py).
EMAIL_WELCOME_START = os.getenv("EMAIL_WELCOME_START", "").strip()


# --- CORS ---------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        # Local dev: Vite's dev default (5173), the launch.json port (5180), and
        # Vite's PREVIEW default (4173) — the port `npm run preview` and the
        # Playwright smoke suite serve the built site on. Without 4173 a locally
        # previewed build silently can't reach the API (every fetch is blocked by
        # CORS, so shelves and search come up empty). Production overrides this
        # whole list via the env var, so these are dev/CI only.
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5180,http://127.0.0.1:5180,"
        "http://localhost:4173,http://127.0.0.1:4173",
    ).split(",")
    if o.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]


# --- Internationalization -----------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# --- Static files -------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Throttle counters live in their own cache, separate from anything else that
# caches. Two reasons, and the second is why it is not just tidiness:
#
#  * A throttle bucket is not application data — flushing one must never mean
#    flushing the other, in either direction.
#  * Under `manage.py test` this alias is a DUMMY cache, so throttle state
#    cannot leak between tests. It otherwise does: the anonymous search throttle
#    keys on the client address, every test request comes from 127.0.0.1, and
#    DRF's history is process-global — so the suite's ~90 search requests all
#    land in ONE 60-second bucket and unrelated tests start 429ing as soon as
#    someone adds a few more. The two tests that assert enforcement patch a real
#    cache back in, so the behaviour is still proven, just not ambient.
_TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

CACHES = {
    # Dummy under test, for the same reason as "throttle" below: LocMemCache
    # lives for the whole process, so one test's memoised value is served to the
    # next one and the failure looks like the endpoint returning nothing. Two
    # existing tests broke exactly that way the moment anything started using
    # this cache. A test that wants to exercise caching should opt in with
    # override_settings rather than every other test having to remember to
    # clear it.
    "default": {
        "BACKEND": (
            "django.core.cache.backends.dummy.DummyCache"
            if _TESTING
            else "django.core.cache.backends.locmem.LocMemCache"
        )
    },
    "throttle": {
        "BACKEND": (
            "django.core.cache.backends.dummy.DummyCache"
            if _TESTING
            else "django.core.cache.backends.locmem.LocMemCache"
        ),
        "LOCATION": "throttle",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Required-config fail-fast + production hardening -------------------------
# Applied only in real deployments (DEBUG off). Skipped for commands that
# legitimately run without the production runtime config.

# content_version is here for the same reason collectstatic is: the image build
# runs it (Dockerfile) to bake the content digest, long before DATABASE_URL or
# SUPABASE_URL exist. It reads files and touches neither.
_NO_CONFIG_COMMANDS = {"test", "collectstatic", "makemigrations", "content_version"}
_skip_config_checks = len(sys.argv) > 1 and sys.argv[1] in _NO_CONFIG_COMMANDS

if not DEBUG and not _skip_config_checks:
    from django.core.exceptions import ImproperlyConfigured

    from common.settings_check import missing_required_config

    _missing = missing_required_config(
        secret_key=SECRET_KEY,
        database_url=DATABASE_URL,
        supabase_url=SUPABASE_URL,
    )
    if _missing:
        raise ImproperlyConfigured(
            "Refusing to start without required configuration: "
            + "; ".join(_missing)
            + ". (Set DJANGO_DEBUG=true for local development.)"
        )

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


# --- Error monitoring (Sentry) ------------------------------------------------
# Opt-in: does nothing until SENTRY_DSN is set, so local dev and unconfigured
# deploys are unaffected. Set SENTRY_DSN in the Render dashboard to turn it on.
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production" if not DEBUG else "development"),
        # WHICH deploy an error came from. Without it every report is attributed
        # to one undifferentiated "production", so a regression cannot be traced
        # to the release that introduced it — the first question anyone asks.
        # RELEASE_COMMIT is already read above for the API/web release-sync
        # check; this is the same value, doing a second job. Empty (local, CI)
        # sends no release rather than a wrong one.
        release=RELEASE_COMMIT or None,
        # Errors only by default; raise these later if you want tracing/profiling.
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0")),
        send_default_pii=False,
    )
