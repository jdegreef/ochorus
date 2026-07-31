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
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "EXCEPTION_HANDLER": "common.exception_handler.detail_exception_handler",
    # Only the endpoints that opt in are throttled — a global anon rate would
    # cap search-as-you-type, which is a legitimate burst. Generous enough that a
    # reader opening several results per search never notices, low enough that
    # the one unauthenticated WRITE endpoint can't be used to grow a table.
    # Backed by the default local-memory cache, so the limit is per worker and
    # approximate: a bound, not an access control.
    "DEFAULT_THROTTLE_RATES": {
        "search-click": "60/min",
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

# Public origin of the READER (e.g. https://ochorus.com), used to confirm after a
# deploy that a newly live locale actually appears in the built sitemap. Optional:
# without it the post-deploy check reports "unknown" instead of guessing.
PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "").strip().rstrip("/")
GITHUB_TRANSLATION_REPO = os.getenv("GITHUB_TRANSLATION_REPO", "jdegreef/ochorus")


# --- CORS ---------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        # Local dev: both Vite's default (5173) and the launch.json port (5180).
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5180,http://127.0.0.1:5180",
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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Required-config fail-fast + production hardening -------------------------
# Applied only in real deployments (DEBUG off). Skipped for commands that
# legitimately run without the production runtime config.

_NO_CONFIG_COMMANDS = {"test", "collectstatic", "makemigrations"}
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
        # Errors only by default; raise these later if you want tracing/profiling.
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0")),
        send_default_pii=False,
    )
