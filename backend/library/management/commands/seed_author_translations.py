"""Seed the translated author bios (AuthorTranslation) from the in-repo data.

The es/sw/lg author bios shipped only as data migrations (0021/0023/0024),
which are guarded skip-if-absent: on a fresh DB the authors are seeded *after*
migrate runs, so those migrations deliberately no-op there — and a rebuild
silently loses all 39 translated bios (the same latent loss PR #204 fixed for
the Spanish sermons). AuthorTranslation is not one of the fixture models, so
the backend/CLAUDE.md rule ("put the same fact in the fixture, not only the
migration") takes its release-step form here: this command upserts the rows
from the same data files the migrations read
(``migrations/data/author_bios_<lang>/``). Runs on every deploy (see the
release command).

Ownership follows the seed_sermons split: the repo files are the single source
of truth for **unreviewed** rows — new bios are created and corrected ones
updated on the next deploy — while a row an approver has flipped to
``reviewed=True`` belongs to the review workflow: its wording is never
rewritten, and only a still-EMPTY field may land (e.g. a long-form bio_html
batch arriving after the short bio was approved), which re-gates the row to
``reviewed=False`` exactly as migrations 0023/0024 did. Fields are only ever
written, never blanked: a missing short.json entry or .html file leaves the
stored value alone.

Future bio translations (or corrections) ship by editing ``short.json`` and/or
``<slug>.html`` under a ``data/author_bios_<lang>/`` directory — no new
migration per batch. NOTE: migration 0021 embeds the es short bios in code;
``author_bios_es/short.json`` supersedes that immutable copy — edit only the
data files. Corrections must land here, not in the prod DB: this seed re-asserts
the files over hand-edited unreviewed rows on the next deploy.
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


def read_bios(d: Path) -> dict[str, dict[str, str]]:
    """slug -> {bio, bio_html} for one language dir (absent fields omitted)."""
    bios: dict[str, dict[str, str]] = {}
    short_path = d / "short.json"
    if short_path.exists():
        for slug, bio in json.loads(short_path.read_text(encoding="utf-8")).items():
            if bio:
                bios.setdefault(slug, {})["bio"] = bio
    for path in d.glob("*.html"):
        html = path.read_text(encoding="utf-8").strip()
        if html:
            bios.setdefault(path.stem, {})["bio_html"] = html
    return bios


class Command(BaseCommand):
    help = "Upsert unreviewed translated author bios from migrations/data (deploy step)."

    def handle(self, *args, **opts):
        per_lang = {lang: read_bios(d) for lang, d in language_dirs()}
        slugs = {slug for bios in per_lang.values() for slug in bios}
        authors = Author.objects.in_bulk(slugs, field_name="slug")
        # Scoped to seeded authors: pipeline-translated rows for other authors
        # (translate_author) are none of this command's business.
        existing = {
            (tr.author_id, tr.language): tr
            for tr in AuthorTranslation.objects.filter(
                language__in=per_lang, author__slug__in=slugs
            )
        }

        upserted = 0
        skipped: list[str] = []
        for lang, bios in per_lang.items():
            for slug, fields in sorted(bios.items()):
                author = authors.get(slug)
                if author is None:
                    # Soft slug-reference (like seed_topics): the data can land
                    # ahead of its author without failing the deploy.
                    skipped.append(f"{slug} [{lang}]")
                    continue
                tr = existing.get((author.id, lang))
                if tr is None:
                    tr = AuthorTranslation(author=author, language=lang)
                if tr.pk and tr.reviewed:
                    # Approver-owned wording: only a still-empty field may land
                    # (a later-shipped bio_html), re-gating the row for review.
                    changed = [n for n in fields if not getattr(tr, n)]
                else:
                    changed = [n for n, v in fields.items() if getattr(tr, n) != v]
                if not changed:
                    continue
                for name in changed:
                    setattr(tr, name, fields[name])
                tr.reviewed = False
                # Clear staleness only when the SHORT bio itself was rewritten —
                # that is the field the flag tracks. Merely filling an empty
                # bio_html leaves the short bio still describing the superseded
                # English, so the flag must survive.
                if "bio" in changed:
                    tr.source_stale = False
                tr.save()
                upserted += 1
        if skipped:
            self.stdout.write(
                self.style.WARNING(f"No author yet for: {', '.join(skipped)}")
            )
        if upserted:
            self.stdout.write(
                self.style.SUCCESS(f"Author translations: {upserted} created/updated.")
            )
        else:
            self.stdout.write("Author translations already up to date.")
