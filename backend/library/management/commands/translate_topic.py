"""Translate topical-shelf labels (title + description) into a target language.

Runs locally (needs ANTHROPIC_API_KEY); the result is ``TopicTranslation`` rows
(unreviewed). To SHIP them the command also writes
``library/data/topic_translations/<language>.json`` — that file is the delivery
path (like the plan-prose and author-bio data files): it survives a fresh-DB
rebuild and is re-upserted on every deploy, so rows written any other way don't
stick. Review the git diff and commit the file; shipping is a commit, not a
retype.

**Why a shelf's translation is not optional.** Topic prose has no English
fallback: a shelf with no title in a language is omitted from that language's
list and its page 404s there (``Topic.is_translated_into``). So an untranslated
topic is an *invisible* topic, not an English one — which is why the seed pins
full per-language coverage.

Scripture is handled apart from the prose, and never invented: the shelf's verse
is fetched verbatim from that language's Bible via the Take Root API
(``fetch_verse_text``), and only its reference — the book name — is translated.
If the fetch fails, the verse ships empty rather than paraphrased; the topic page
renders no verse block, so the shelf is still complete.

Idempotent/resumable: an already-translated field is skipped unless --force.

Usage:
    manage.py translate_topic --language es              # every published shelf
    manage.py translate_topic prayer --language sw
    manage.py translate_topic --language pt --dry-run
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import CommandError

from library.management.commands._translate_base import TranslateCommand
from library.models import Topic, TopicTranslation
from library.translation import (
    fetch_verse_text,
    translate_scripture_ref,
    translate_topic_meta,
)


def _write_language_file(language: str, rows: list[dict]) -> Path:
    """Merge the translated shelves into ``data/topic_translations/<lang>.json``.

    This used to emit a Python block to paste into ``seed_topics.py``, on the
    reasoning that a command must not rewrite source. The delivery target is
    now a DATA file with its own CI gates (``TopicTranslationFileTests``), so
    writing directly is safe in the way editing source was not: a botched
    write fails loudly in CI and shows plainly in ``git diff`` before commit.
    Merge semantics — existing entries not in ``rows`` are left alone, and an
    entry's ``note`` survives a re-translation of its prose.
    """
    from library.topic_translations import DATA_DIR

    path = DATA_DIR / f"{language}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for row in rows:
        entry = data.setdefault(row["slug"], {})
        entry["title"] = row["title"]
        entry["description"] = row["description"]
        if row.get("scripture_ref") and row.get("scripture_text"):
            entry["scripture"] = {
                "reference": row["scripture_ref"],
                "text": row["scripture_text"],
            }
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


class Command(TranslateCommand):
    help = "AI-translate topical-shelf titles/descriptions into a language."

    # This command defines its own arguments rather than using the base's
    # add_target_arguments hook: it has no --effort, and inheriting one would
    # advertise a flag it ignores. The preflight and client below are what it
    # shares — which is the part that matters.
    def add_arguments(self, parser):
        parser.add_argument(
            "slugs", nargs="*", help="Topic slugs (default: every published topic)"
        )
        parser.add_argument("--language", required=True, help="Target language code (see the admin)")
        parser.add_argument(
            "--force", action="store_true", help="Re-translate existing fields"
        )
        parser.add_argument(
            "--scripture",
            action="store_true",
            help="Also localize the shelf's verse (reference + verbatim Bible text)",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Show the plan, translate nothing"
        )

    def handle(self, slugs, language, force, scripture, dry_run, **opts):
        cfg = self.language_config(language)

        topics = Topic.objects.filter(is_published=True)
        if slugs:
            topics = topics.filter(slug__in=slugs)
        topics = list(topics.order_by("sort_order", "title"))
        if not topics:
            raise CommandError("no matching published topics")

        existing = {
            t.topic_id: t
            for t in TopicTranslation.objects.filter(topic__in=topics, language=language)
        }

        def needs(topic, field):
            tr = existing.get(topic.id)
            return force or not (tr and getattr(tr, field))

        plan = [t for t in topics if needs(t, "title") or needs(t, "description")]
        if scripture:
            plan = [
                t
                for t in topics
                if t in plan or (t.scripture_ref and needs(t, "scripture_text"))
            ]

        self.stdout.write(
            f"{len(plan)}/{len(topics)} shelf/shelves to translate → "
            f"{cfg['name']}"
            f"{' (+ scripture)' if scripture else ''}"
        )
        if dry_run:
            for t in plan:
                fields = [f for f in ("title", "description") if needs(t, f)]
                if scripture and t.scripture_ref and needs(t, "scripture_text"):
                    fields.append("scripture")
                self.stdout.write(f"  {t.slug}: {', '.join(fields)}")
            return
        if not plan:
            return

        self.preflight(language)

        client = self.client()
        bible = cfg["bible"]
        shipped: list[dict] = []

        for t in plan:
            tr = existing.get(t.id)
            title_out = tr.title if tr else ""
            desc_out = tr.description if tr else ""
            ref_out = tr.scripture_ref if tr else ""
            text_out = tr.scripture_text if tr else ""

            if needs(t, "title") or needs(t, "description"):
                self.stdout.write(f"→ {t.slug}: title + description")
                meta = translate_topic_meta(client, language, t.title, t.description)
                title_out = meta["title"].strip()
                desc_out = meta["description"].strip()

            if scripture and t.scripture_ref and needs(t, "scripture_text"):
                # The verse comes from the Bible; only the reference is translated.
                verse = fetch_verse_text(bible, t.scripture_ref)
                if verse:
                    ref_out = translate_scripture_ref(client, language, t.scripture_ref)
                    text_out = verse
                    self.stdout.write(f"→ {t.slug}: scripture ({ref_out})")
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {t.slug}: no {bible} text for {t.scripture_ref} — "
                            "shipping without a verse rather than paraphrasing"
                        )
                    )

            TopicTranslation.objects.update_or_create(
                topic=t,
                language=language,
                defaults={
                    "title": title_out,
                    "description": desc_out,
                    "scripture_ref": ref_out,
                    "scripture_text": text_out,
                },
            )
            shipped.append({
                "slug": t.slug,
                "title": title_out,
                "description": desc_out,
                "scripture_ref": ref_out,
                "scripture_text": text_out,
            })

        self.stdout.write(self.style.SUCCESS(f"\n{len(shipped)} shelf/shelves translated."))
        path = _write_language_file(language, shipped)
        self.stdout.write(
            f"\nWrote {path} — the seed is the delivery path, so review the "
            "git diff and commit that file; a row not in it is reverted on the "
            "next deploy. Scripture (when fetched) is embedded per entry."
        )
