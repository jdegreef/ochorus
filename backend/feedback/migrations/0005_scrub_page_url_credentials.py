"""Scrub sign-in credentials out of feedback already on file.

Until this release the feedback dialog stored ``window.location.href`` verbatim,
so a reader who opened it straight after a magic-link sign-in filed their live
Supabase session (``#access_token=…&refresh_token=…``) with their suggestion,
where every admin with the feedback capability could read it. The submit view
now scrubs the URL on the way in; this pass cleans the rows already stored.

The scrub is frozen here rather than imported, so the migration keeps meaning
what it meant if the view's copy changes later.
"""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db import migrations

_SECRET_KEY = re.compile(r"token|code|secret|password|key|auth|session", re.IGNORECASE)


def _scrub(url):
    parts = urlsplit(url)
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _SECRET_KEY.search(k)]
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def scrub(apps, schema_editor):
    Feedback = apps.get_model("feedback", "Feedback")
    for row in Feedback.objects.exclude(page_url="").only("id", "page_url").iterator():
        clean = _scrub(row.page_url)
        if clean != row.page_url:
            Feedback.objects.filter(pk=row.pk).update(page_url=clean)


class Migration(migrations.Migration):
    dependencies = [
        ("feedback", "0004_feedback_anchor_block_feedback_selected_text_and_more"),
    ]

    # Irreversible by nature (the secret is gone), but a no-op reverse lets the
    # app migrate backwards past it.
    operations = [migrations.RunPython(scrub, migrations.RunPython.noop)]
