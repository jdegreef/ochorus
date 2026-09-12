"""Generate answered study questions for English sermons and write them into the
sermon fixtures (off-server, needs ANTHROPIC_API_KEY / an ``ant auth`` profile).

Like ``translate_sermon``, this runs locally and produces content shipped in the
fixture — prod holds no model credentials. It writes ``study_questions`` straight
into ``fixtures/content/sermons/<slug>.en.json`` (the source of truth, rendered
with the canonical ``render_rows`` so the diff is only the new field), so there is
no DB round-trip and no regen step. Reads the sermon's text from the fixture too.

Idempotent: a sermon that already has ``study_questions`` is skipped unless
``--force``. Grounding and shape are the generator's job (see
``library.sermon_questions``); this command is the batch driver.

Usage:
    # Pilot: the first 10 sermons that have none yet
    manage.py generate_sermon_questions --limit 10
    # Specific sermons
    manage.py generate_sermon_questions the-immutability-of-god free-grace
    # See the plan without spending a token
    manage.py generate_sermon_questions --limit 10 --dry-run
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from library.content_fixtures import SERMONS_DIR, render_rows
from library.management.commands._translate_base import EFFORT_CHOICES
from library.sermon_questions import QUESTION_COUNT, generate_questions
from library.text import html_to_text


def _insert_after(fields: dict, after_key: str, key: str, value) -> dict:
    """Return ``fields`` with ``key: value`` placed right after ``after_key``.

    A present key is updated in place (order preserved); a new key lands directly
    after ``after_key``, or at the end if ``after_key`` is absent. Rebuilds the
    dict rather than mutating, so the caller's original is untouched.
    """
    if key in fields:
        return {**fields, key: value}
    out: dict = {}
    for k, v in fields.items():
        out[k] = v
        if k == after_key:
            out[key] = value
    if key not in out:
        out[key] = value
    return out


class Command(BaseCommand):
    help = "AI-generate answered study questions for English sermons (into fixtures)."

    def add_arguments(self, parser):
        parser.add_argument(
            "slugs",
            nargs="*",
            help="Sermon slugs to process; omit to take every en sermon that has none.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Cap how many sermons to generate for (the pilot switch).",
        )
        parser.add_argument("--count", type=int, default=QUESTION_COUNT)
        parser.add_argument("--effort", default="high", choices=EFFORT_CHOICES)
        parser.add_argument("--force", action="store_true", help="Regenerate if present")
        parser.add_argument(
            "--dry-run", action="store_true", help="Show the plan, generate nothing"
        )

    def _fixture_path(self, slug: str):
        return SERMONS_DIR / f"{slug}.en.json"

    def _targets(self, slugs, limit, force):
        """The (path, rows, fields) to process, in slug order.

        A named slug that doesn't exist is an error (a typo must not pass as a
        silent no-op); without slugs, take every en sermon still missing
        questions (or all of them under --force).
        """
        if slugs:
            paths = []
            for slug in slugs:
                p = self._fixture_path(slug)
                if not p.exists():
                    raise CommandError(f"no English sermon fixture for slug {slug!r}")
                paths.append(p)
        else:
            paths = sorted(SERMONS_DIR.glob("*.en.json"))

        out = []
        for p in paths:
            rows = json.loads(p.read_text(encoding="utf-8"))
            fields = rows[0]["fields"]
            if fields.get("study_questions") and not force:
                continue
            out.append((p, rows, fields))
            if limit and len(out) >= limit:
                break
        return out

    def handle(self, slugs, limit, count, effort, force, dry_run, **opts):
        targets = self._targets(slugs, limit, force)
        if not targets:
            self.stdout.write("Every selected sermon already has study questions.")
            return

        self.stdout.write(
            f"{len(targets)} sermon(s) to process, effort={effort}, count={count}"
            + (" [dry run]" if dry_run else "")
        )
        if dry_run:
            for _p, _rows, f in targets:
                self.stdout.write(f"  would generate: {f['title'][:60]} [{f.get('scripture_ref', '')}]")
            return

        client = self.client()
        done = skipped = 0
        for path, rows, fields in targets:
            title = fields["title"]
            # Prefer the stored plain text; fall back to stripping the body.
            body_text = fields.get("body_text") or html_to_text(fields.get("body_html", ""))
            if not body_text.strip():
                self.stdout.write(self.style.WARNING(f"  ∅ {title[:60]}: empty body, skipped"))
                skipped += 1
                continue

            items, usage = generate_questions(
                client,
                title=title,
                scripture_ref=fields.get("scripture_ref", ""),
                body_text=body_text,
                effort=effort,
                count=count,
            )
            if not items:
                # No usable output — leave the sermon untouched rather than write
                # an empty list, so a re-run retries it.
                self.stdout.write(self.style.WARNING(f"  ∅ {title[:60]}: no usable questions, skipped"))
                skipped += 1
                continue

            # Insert after `summary` (where the hand-written examples put it) so
            # batch-generated rows read the same as those — position is otherwise
            # irrelevant (keyed by name everywhere), but a uniform corpus keeps
            # diffs and review clean. In-place when regenerating (--force).
            rows[0]["fields"] = _insert_after(fields, "summary", "study_questions", items)
            path.write_text(render_rows(rows), encoding="utf-8")
            done += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ {title[:60]}: {len(items)} questions "
                    f"({usage.input_tokens}in/{usage.output_tokens}out)"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"Done: {done} written, {skipped} skipped.")
            + " Review the diff, then ship via the ship-content-fix skill."
        )

    def client(self):
        """The Anthropic client (ANTHROPIC_API_KEY / ant auth profile)."""
        import anthropic

        return anthropic.Anthropic()
