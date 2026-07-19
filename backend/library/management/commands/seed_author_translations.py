"""Seed the translated author bios (AuthorTranslation) from the in-repo data.

The es/sw/lg author bios shipped only as data migrations (0021/0023/0024),
which are guarded skip-if-absent: on a fresh DB the authors are seeded *after*
migrate runs, so those migrations deliberately no-op there — and a rebuild
silently loses all 39 translated bios (the same latent loss PR #204 fixed for
the Spanish sermons). AuthorTranslation is not one of the fixture models, so
the backend/CLAUDE.md rule ("put the same fact in the fixture, not only the
migration") takes its release-step form here: this command reads the same data
files the migrations read (``migrations/data/author_bios_<lang>/``) and fills
any missing rows or fields. Runs on every deploy (see the release command).

Fill-if-empty, matching the migrations' semantics: a field that already has
content is never overwritten, and ``reviewed`` is stamped False only when a
field is actually filled — an ``approve_author_translation`` flip survives
deploys (the same create-only philosophy as seed_sermons's ``source_type``).
On prod, where every row already has its content, the whole run is a no-op.

Future bio translations ship by adding ``short.json`` entries and/or
``<slug>.html`` files under a ``data/author_bios_<lang>/`` directory — no new
migration needed.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from library.models import Author, AuthorTranslation

DATA_DIR = Path(__file__).resolve().parents[2] / "migrations" / "data"
PREFIX = "author_bios_"


def language_dirs() -> list[tuple[str, Path]]:
    """(language, directory) pairs for every author_bios_<lang> data dir."""
    return sorted(
        (d.name.removeprefix(PREFIX), d)
        for d in DATA_DIR.glob(f"{PREFIX}*")
        if d.is_dir()
    )


class Command(BaseCommand):
    help = "Fill missing translated author bios from migrations/data (deploy step)."

    def handle(self, *args, **opts):
        created = filled = 0
        skipped: list[str] = []
        for lang, d in language_dirs():
            short_path = d / "short.json"
            short = (
                json.loads(short_path.read_text(encoding="utf-8"))
                if short_path.exists()
                else {}
            )
            slugs = sorted(set(short) | {p.stem for p in d.glob("*.html")})
            for slug in slugs:
                author = Author.objects.filter(slug=slug).first()
                if author is None:
                    # Soft slug-reference (like seed_topics): the data can land
                    # ahead of its author without failing the deploy.
                    skipped.append(f"{slug} [{lang}]")
                    continue
                changed = []
                tr = AuthorTranslation.objects.filter(
                    author=author, language=lang
                ).first()
                is_new = tr is None
                if is_new:
                    tr = AuthorTranslation(author=author, language=lang)
                if not tr.bio and short.get(slug):
                    tr.bio = short[slug]
                    changed.append("bio")
                html_path = d / f"{slug}.html"
                if not tr.bio_html and html_path.exists():
                    tr.bio_html = html_path.read_text(encoding="utf-8").strip()
                    changed.append("bio_html")
                if changed:
                    tr.reviewed = False
                    tr.save()
                    created += is_new
                    filled += 1
        if skipped:
            self.stdout.write(
                self.style.WARNING(f"No author yet for: {', '.join(skipped)}")
            )
        if filled:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Author translations: {created} created, {filled} filled."
                )
            )
        else:
            self.stdout.write("Author translations already up to date.")
