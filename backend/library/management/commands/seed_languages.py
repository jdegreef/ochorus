"""Seed the Language registry from the repo's seed table (idempotent).

Runs on every deploy (see release.py). The repo owns a language's *identity* —
its names, its Bible, its glossary, its script direction — so those are
re-asserted each run and a fix in ``library/language_seed.py`` reaches
production on the next deploy.

Only languages listed in that file are touched. A language created from the
admin ("Add a language") is absent from it, so the seed never overwrites what
an admin typed — the database owns those rows outright.

CREATE-ONLY, and this is the important part: ``status``, ``went_live_at``, the
readiness thresholds and ``notes`` are written **only when the row is first
created**. They are owned by a workflow *after* creation — an admin launching a
language, or tuning its bar — and the seed re-runs on every single deploy. Were
they in the update set, the deploy after a launch would quietly put the language
back to draft and throw away the thresholds someone chose. (backend/CLAUDE.md
calls this out; it has bitten this codebase before, and there is a test below in
tests.py pinning it.)

Initial status is derived from what the site advertises TODAY, so the registry
starts out agreeing with reality rather than resetting it:
``INITIALLY_LIVE`` mirrors ``frontend/src/lib/advertised-locales.ts``.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.language_seed import SEED_LANGUAGES
from library.models import Language

# The source language: content is authored in English, so it is exempt from every
# readiness check and is never a translation target.
SOURCE = {
    "code": "en",
    "name": "English",
    "native_name": "English",
    "bible_code": "",
    "bible_label": "",
    "glossary": {},
    "rtl": False,
    "is_source": True,
}

# Mirrors ADVERTISED_LOCALES in the frontend at the time this registry landed.
# Only used for the FIRST insert of each row — afterwards status is the admin's.
INITIALLY_LIVE = {"en", "es", "sw", "lg", "pt"}

# Scripts that read right-to-left. Kept here rather than in the seed table
# because it is a property of the writing system, not of the translation
# pipeline.
RTL_CODES = {"ar", "he", "fa", "ur"}

# Display order: the source first, then by how established the language is.
ORDER = ["en", "es", "sw", "lg", "pt", "ar"]


def _rows() -> list[dict]:
    rows = [dict(SOURCE)]
    for code, cfg in SEED_LANGUAGES.items():
        rows.append(
            {
                "code": code,
                "name": cfg["name"],
                "native_name": cfg["native"],
                "bible_code": cfg["bible"],
                "bible_label": cfg["bible_label"],
                "rtl": code in RTL_CODES,
                "is_source": False,
                "glossary": cfg["glossary"],
            }
        )
    return rows


class Command(BaseCommand):
    help = "Seed/refresh the Language registry (identity only; status is preserved)."

    def handle(self, *args, **opts):
        created = updated = 0
        for row in _rows():
            code = row["code"]
            # Identity: safe to re-assert every deploy.
            identity = {
                "name": row["name"],
                "native_name": row["native_name"],
                "bible_code": row["bible_code"],
                "bible_label": row["bible_label"],
                "glossary": row["glossary"],
                "rtl": row["rtl"],
                "is_source": row["is_source"],
                "sort_order": ORDER.index(code) if code in ORDER else 99,
            }
            obj = Language.objects.filter(code=code).first()
            if obj is None:
                Language.objects.create(
                    code=code,
                    status=(
                        Language.Status.LIVE
                        if code in INITIALLY_LIVE
                        else Language.Status.DRAFT
                    ),
                    **identity,
                )
                created += 1
                continue
            # Update identity only. Never status / thresholds / went_live_at /
            # notes — see the module docstring.
            changed = [f for f, v in identity.items() if getattr(obj, f) != v]
            if changed:
                for f, v in identity.items():
                    setattr(obj, f, v)
                obj.save(update_fields=changed)
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Languages: {created} created, {updated} updated.")
        )
