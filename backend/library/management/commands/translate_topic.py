"""Translate topical-shelf labels (title + description) into a target language.

Runs locally (needs ANTHROPIC_API_KEY); the result is ``TopicTranslation`` rows
(unreviewed). To SHIP them, paste the emitted block into ``TOPIC_TRANSLATIONS``
in ``seed_topics`` — that dict is the delivery path (like the author-bio data
files): it survives a fresh-DB rebuild and is re-upserted on every deploy, so
rows written any other way don't stick. The command prints the block ready to
paste, so shipping is a copy, not a retype.

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

import anthropic
from django.core.management.base import BaseCommand, CommandError

from library.models import Topic, TopicTranslation
from library.translation import (
    LANGUAGES,
    fetch_verse_text,
    translate_scripture_ref,
    translate_topic_meta,
    verify_bible_code,
)


def _seed_block(language: str, rows: list[tuple[str, str, str]]) -> str:
    """The TOPIC_TRANSLATIONS entry for this language, ready to paste.

    Emitted rather than written into the file: seed_topics.py is source, and a
    command that rewrites source in place is a worse failure mode than one that
    asks for a paste (a botched edit is silent; a missing paste is obvious).
    """
    lines = [f'    "{language}": {{']
    for slug, title, description in rows:
        lines.append(f'        "{slug}": (')
        lines.append(f'            "{title}",')
        # Keep the description on one logical string; the repo's formatter will
        # wrap it. Escape only what would break the literal.
        lines.append(f'            "{description}",')
        lines.append("        ),")
    lines.append("    },")
    return "\n".join(lines)


class Command(BaseCommand):
    help = "AI-translate topical-shelf titles/descriptions into a language."

    def add_arguments(self, parser):
        parser.add_argument(
            "slugs", nargs="*", help="Topic slugs (default: every published topic)"
        )
        parser.add_argument("--language", required=True, choices=sorted(LANGUAGES))
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
            f"{LANGUAGES[language]['name']}"
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

        # Preflight: a bad Bible code silently omits scripture, so check before
        # any paid model work (see verify_bible_code).
        try:
            verify_bible_code(language)
        except ValueError as e:
            raise CommandError(str(e)) from e

        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY / ant auth profile
        bible = LANGUAGES[language]["bible"]
        shipped: list[tuple[str, str, str]] = []

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
            shipped.append((t.slug, title_out, desc_out))

        self.stdout.write(self.style.SUCCESS(f"\n{len(shipped)} shelf/shelves translated."))
        self.stdout.write(
            "\nPaste into TOPIC_TRANSLATIONS in "
            "library/management/commands/seed_topics.py — the seed is the delivery "
            "path, so a row that isn't in that dict is reverted on the next deploy:\n"
        )
        self.stdout.write(_seed_block(language, shipped))
        if scripture:
            self.stdout.write(
                "\n(Scripture goes in TOPIC_SCRIPTURE_TR, keyed the same way.)"
            )
