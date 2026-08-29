"""Idempotently sync author bios (``bio_html``) and sermons from the committed
fixture onto existing rows.

``seed_if_empty`` only populates a *fresh* database, so bio/sermon content added
to the fixture never reaches an already-seeded production DB. Data migrations call
this helper to re-apply that content to live rows without a re-import. The fixture
stays the single source of truth; fresh installs (which loaddata it directly) are
unaffected because there are no live rows to update yet.

Historical: called only by data migrations (0005-0036 era). On the
natural-key fixture it deliberately no-ops (format guard below). Do not wire
new callers to it — new content ships via the seed commands.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "launch.json"


def _date(value):
    if isinstance(value, str) and value:
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return value or None


def backfill_bios_and_sermons(apps, fixture: Path = FIXTURE) -> tuple[int, int]:
    """Upsert every author ``bio_html`` and every sermon found in the fixture.

    Returns ``(authors_updated, sermons_upserted)``. Safe to run repeatedly.
    """
    Author = apps.get_model("library", "Author")
    Sermon = apps.get_model("library", "Sermon")

    try:
        rows = json.loads(Path(fixture).read_text())
    except (OSError, ValueError):
        return (0, 0)

    if rows and "pk" not in rows[0]:
        # Natural-key-format fixture (no integer pks): these historical
        # backfills predate the format switch and their content is already IN
        # the fixture the seeds load — correct no-op for fresh installs, and
        # prod applied them long ago.
        print("content_sync: natural-key fixture detected — historical backfill skipped")
        return (0, 0)

    pk_to_slug: dict[int, str] = {}
    authors_updated = 0
    sermons_upserted = 0

    for row in rows:
        if row.get("model") != "library.author":
            continue
        f = row["fields"]
        pk_to_slug[row["pk"]] = f["slug"]
        author = Author.objects.filter(slug=f["slug"]).first()
        if not author:
            continue
        changed = []
        bio = f.get("bio_html") or ""
        if bio and author.bio_html != bio:
            author.bio_html = bio
            changed.append("bio_html")
        # Like bio_html, the short bio follows the fixture when they differ —
        # the fixture is the single source of truth (prod is never hand-edited).
        short = f.get("bio") or ""
        if short and author.bio != short:
            author.bio = short
            changed.append("bio")
        photo = f.get("photo_url") or ""
        if photo and author.photo_url != photo:
            author.photo_url = photo
            changed.append("photo_url")
        if not author.birth_year and f.get("birth_year"):
            author.birth_year = f["birth_year"]
            changed.append("birth_year")
        if not author.death_year and f.get("death_year"):
            author.death_year = f["death_year"]
            changed.append("death_year")
        if changed:
            author.save(update_fields=changed)
            authors_updated += 1

    for row in rows:
        if row.get("model") != "library.sermon":
            continue
        f = row["fields"]
        slug = pk_to_slug.get(f.get("author"))
        author = Author.objects.filter(slug=slug).first() if slug else None
        if not author:
            continue
        Sermon.objects.update_or_create(
            slug=f["slug"],
            language=f.get("language", "en"),
            defaults={
                "author": author,
                "title": f.get("title", ""),
                "scripture_ref": f.get("scripture_ref", ""),
                "preached_on": _date(f.get("preached_on")),
                "body_html": f.get("body_html", ""),
                # word_count deliberately not carried across: Sermon.save()
                # derives it from the body this just set, so a stale count in
                # the feed cannot outrank the prose it describes.
                "source_url": f.get("source_url", ""),
                "sort_order": f.get("sort_order", 0),
                "is_published": f.get("is_published", True),
            },
        )
        sermons_upserted += 1

    return (authors_updated, sermons_upserted)
