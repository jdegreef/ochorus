"""The thin Resend layer: send one email, and verify an inbound webhook.

We call Resend's REST API with ``requests`` rather than pulling in the SDK — one
POST, no extra dependency. Webhooks are signed with Svix (Resend's webhook
provider); we verify them with the standard library so we don't depend on the
``svix`` package either.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_SEND_URL = "https://api.resend.com/emails"
_TIMEOUT = 15
#: Reject a webhook whose timestamp is more than this far from now (replay guard).
_WEBHOOK_TOLERANCE_S = 5 * 60


class ResendError(RuntimeError):
    """A send that Resend rejected (or that we refused to attempt)."""


def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    headers: dict | None = None,
    idempotency_key: str | None = None,
) -> str:
    """Send one email through Resend and return its message id.

    Raises :class:`ResendError` when Resend isn't configured or the API rejects
    the send — the caller records the failure on the message row.
    """
    api_key = settings.RESEND_API_KEY
    if not api_key:
        raise ResendError("RESEND_API_KEY is not configured")

    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if headers:
        payload["headers"] = headers

    request_headers = {"Authorization": f"Bearer {api_key}"}
    if idempotency_key:
        # Resend honours an Idempotency-Key header — a second belt on top of our
        # own unique key, so a retried HTTP call never doubles a send.
        request_headers["Idempotency-Key"] = idempotency_key

    try:
        resp = requests.post(
            _SEND_URL, json=payload, headers=request_headers, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise ResendError(f"Resend send failed: {exc}") from exc
    except ValueError as exc:  # non-JSON body
        raise ResendError("Resend returned a non-JSON response") from exc

    message_id = data.get("id")
    if not message_id:
        raise ResendError(f"Resend response had no id: {data!r}")
    return message_id


def verify_webhook(payload: bytes, headers) -> bool:
    """True if an inbound webhook body genuinely came from Resend.

    Implements Svix signature verification: HMAC-SHA256 over
    ``{id}.{timestamp}.{body}`` keyed by the base64 secret behind the
    ``whsec_`` prefix, compared constant-time against every offered signature,
    with a timestamp tolerance to blunt replays. Missing secret ⇒ fail closed.
    """
    secret = settings.RESEND_WEBHOOK_SECRET
    if not secret:
        logger.warning("RESEND_WEBHOOK_SECRET unset; rejecting webhook")
        return False

    svix_id = headers.get("svix-id") or headers.get("webhook-id")
    svix_timestamp = headers.get("svix-timestamp") or headers.get("webhook-timestamp")
    svix_signature = headers.get("svix-signature") or headers.get("webhook-signature")
    if not (svix_id and svix_timestamp and svix_signature):
        return False

    if not _timestamp_ok(svix_timestamp):
        return False

    key = _secret_key(secret)
    if key is None:
        return False

    signed = svix_id.encode() + b"." + svix_timestamp.encode() + b"." + payload
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()

    # The header carries a space-separated list of "<version>,<b64sig>" pairs.
    for part in svix_signature.split():
        _, _, sig = part.partition(",")
        if sig and hmac.compare_digest(sig, expected):
            return True
    return False


def _secret_key(secret: str) -> bytes | None:
    raw = secret.split("_", 1)[1] if secret.startswith("whsec_") else secret
    try:
        return base64.b64decode(raw)
    except (ValueError, TypeError):
        logger.warning("RESEND_WEBHOOK_SECRET is not valid base64")
        return None


def _timestamp_ok(raw: str) -> bool:
    try:
        ts = int(raw)
    except (TypeError, ValueError):
        return False
    return abs(time.time() - ts) <= _WEBHOOK_TOLERANCE_S
